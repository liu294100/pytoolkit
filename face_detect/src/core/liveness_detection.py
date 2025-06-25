#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
活体检测模块
实现基于MediaPipe的活体检测功能，包括眨眼检测、头部运动检测等
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import time
import math

class LivenessStatus(Enum):
    """活体检测状态枚举"""
    UNKNOWN = "unknown"
    REAL = "real"  # 真人
    FAKE = "fake"  # 假人/照片
    PROCESSING = "processing"  # 检测中

@dataclass
class LivenessResult:
    """活体检测结果"""
    status: LivenessStatus
    confidence: float  # 置信度 0-1
    blink_count: int  # 眨眼次数
    head_movement_score: float  # 头部运动得分
    texture_score: float  # 纹理得分
    details: Dict[str, any]  # 详细信息
    timestamp: float

class LivenessDetector:
    """活体检测器"""
    
    def __init__(self):
        # 初始化MediaPipe
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 眨眼检测相关
        self.EYE_AR_THRESH = 0.25  # 眼睛长宽比阈值（6点方法的标准值）
        self.EYE_AR_CONSEC_FRAMES = 2  # 连续帧数阈值（降低以提高敏感度）
        self.blink_counter = 0
        self.total_blinks = 0
        self.eye_ar_history = []
        
        # 头部运动检测
        self.head_positions = []
        self.max_head_history = 30
        
        # 纹理分析
        self.texture_history = []
        self.max_texture_history = 10
        
        # 时间相关
        self.start_time = time.time()
        self.detection_duration = 5.0  # 检测持续时间（秒）
        
        # 眼部关键点索引（MediaPipe Face Mesh）
        # 左眼：外眼角、内眼角、上眼睑、下眼睑关键点
        self.LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        self.RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        
        # MediaPipe Face Mesh 眼部关键点（正确的索引）
        # 左眼轮廓关键点
        self.LEFT_EYE_POINTS = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        # 右眼轮廓关键点  
        self.RIGHT_EYE_POINTS = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        
        # 用于EAR计算的关键点（6个点方法）
        # 左眼：P1(外眼角), P2(上眼睑1), P3(上眼睑2), P4(内眼角), P5(下眼睑2), P6(下眼睑1)
        self.LEFT_EYE_EAR = [33, 160, 158, 133, 153, 144]  
        self.RIGHT_EYE_EAR = [362, 385, 387, 263, 373, 380]
        
    def calculate_eye_aspect_ratio(self, landmarks, eye_indices):
        """计算眼睛长宽比（使用6点方法）"""
        try:
            # 获取6个眼部关键点
            if len(eye_indices) < 6:
                return 0.0
                
            points = []
            for idx in eye_indices:
                if idx < len(landmarks):
                    point = landmarks[idx]
                    points.append([point.x, point.y])
            
            if len(points) < 6:
                return 0.0
                
            points = np.array(points)
            
            # 6点方法：P1(外眼角), P2(上眼睑1), P3(上眼睑2), P4(内眼角), P5(下眼睑2), P6(下眼睑1)
            # 计算两个垂直距离
            vertical_1 = np.linalg.norm(points[1] - points[5])  # P2-P6
            vertical_2 = np.linalg.norm(points[2] - points[4])  # P3-P5
            
            # 计算水平距离
            horizontal = np.linalg.norm(points[0] - points[3])  # P1-P4
            
            # 计算EAR
            if horizontal > 0:
                ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
                return ear
            return 0.0
            
        except Exception as e:
            print(f"计算眼睛长宽比时出错: {e}")
            return 0.0
    
    def detect_blink(self, landmarks):
        """检测眨眼"""
        # 计算左右眼的长宽比
        left_ear = self.calculate_eye_aspect_ratio(landmarks, self.LEFT_EYE_EAR)
        right_ear = self.calculate_eye_aspect_ratio(landmarks, self.RIGHT_EYE_EAR)
        
        # 平均长宽比
        ear = (left_ear + right_ear) / 2.0
        self.eye_ar_history.append(ear)
        
        # 保持历史记录长度
        if len(self.eye_ar_history) > 10:
            self.eye_ar_history.pop(0)
        
        # 检测眨眼
        if ear < self.EYE_AR_THRESH:
            self.blink_counter += 1
        else:
            if self.blink_counter >= self.EYE_AR_CONSEC_FRAMES:
                self.total_blinks += 1
            self.blink_counter = 0
        
        return ear
    
    def analyze_head_movement(self, landmarks):
        """分析头部运动"""
        try:
            # 使用鼻尖作为头部位置参考点
            nose_tip = landmarks[1]  # 鼻尖
            current_pos = np.array([nose_tip.x, nose_tip.y, nose_tip.z])
            
            self.head_positions.append(current_pos)
            
            # 保持历史记录长度
            if len(self.head_positions) > self.max_head_history:
                self.head_positions.pop(0)
            
            # 计算头部运动得分
            if len(self.head_positions) < 5:
                return 0.0
            
            positions = np.array(self.head_positions)
            movement_variance = np.var(positions, axis=0)
            movement_score = np.sum(movement_variance)
            
            return min(movement_score * 1000, 1.0)  # 归一化到0-1
            
        except Exception as e:
            print(f"分析头部运动时出错: {e}")
            return 0.0
    
    def analyze_texture(self, image, face_region):
        """分析面部纹理复杂度"""
        try:
            if face_region is None or face_region.size == 0:
                return 0.0
            
            # 检查face_region是否为有效的numpy数组
            if not isinstance(face_region, np.ndarray):
                return 0.0
                
            # 检查图像尺寸
            if len(face_region.shape) < 2 or face_region.shape[0] < 1 or face_region.shape[1] < 1:
                return 0.0
            
            # 转换为灰度图
            if len(face_region.shape) == 3:
                gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            else:
                gray = face_region
            
            # 计算拉普拉斯方差（纹理复杂度）
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 计算局部二值模式（LBP）
            def calculate_lbp(image):
                rows, cols = image.shape
                lbp_image = np.zeros((rows-2, cols-2), dtype=np.uint8)
                
                for i in range(1, rows-1):
                    for j in range(1, cols-1):
                        center = image[i, j]
                        binary_string = ''
                        
                        # 8邻域
                        neighbors = [
                            image[i-1, j-1], image[i-1, j], image[i-1, j+1],
                            image[i, j+1], image[i+1, j+1], image[i+1, j],
                            image[i+1, j-1], image[i, j-1]
                        ]
                        
                        for neighbor in neighbors:
                            binary_string += '1' if neighbor >= center else '0'
                        
                        lbp_image[i-1, j-1] = int(binary_string, 2)
                
                return lbp_image
            
            lbp = calculate_lbp(gray)
            lbp_variance = np.var(lbp)
            
            # 综合纹理得分
            texture_score = (laplacian_var / 1000 + lbp_variance / 10000) / 2
            texture_score = min(texture_score, 1.0)
            
            self.texture_history.append(texture_score)
            if len(self.texture_history) > self.max_texture_history:
                self.texture_history.pop(0)
            
            return texture_score
            
        except Exception as e:
            print(f"分析纹理时出错: {e}")
            return 0.0
    
    def extract_face_region(self, image, landmarks):
        """提取面部区域"""
        try:
            h, w = image.shape[:2]
            
            # 获取面部边界点
            face_points = []
            face_indices = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
                          397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
                          172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
            
            for idx in face_indices:
                if idx < len(landmarks):
                    point = landmarks[idx]
                    x = int(point.x * w)
                    y = int(point.y * h)
                    face_points.append([x, y])
            
            if len(face_points) < 4:
                return None
            
            # 获取边界框
            face_points = np.array(face_points)
            x_min, y_min = np.min(face_points, axis=0)
            x_max, y_max = np.max(face_points, axis=0)
            
            # 添加边距
            margin = 20
            x_min = max(0, x_min - margin)
            y_min = max(0, y_min - margin)
            x_max = min(w, x_max + margin)
            y_max = min(h, y_max + margin)
            
            # 提取面部区域
            face_region = image[y_min:y_max, x_min:x_max]
            return face_region
            
        except Exception as e:
            print(f"提取面部区域时出错: {e}")
            return None
    
    def detect_liveness(self, image) -> LivenessResult:
        """执行活体检测"""
        try:
            # 转换颜色空间
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_image)
            
            current_time = time.time()
            elapsed_time = current_time - self.start_time
            
            if not results.multi_face_landmarks:
                return LivenessResult(
                    status=LivenessStatus.UNKNOWN,
                    confidence=0.0,
                    blink_count=self.total_blinks,
                    head_movement_score=0.0,
                    texture_score=0.0,
                    details={"error": "未检测到人脸"},
                    timestamp=current_time
                )
            
            landmarks = results.multi_face_landmarks[0].landmark
            
            # 眨眼检测
            eye_ar = self.detect_blink(landmarks)
            
            # 头部运动分析
            head_movement_score = self.analyze_head_movement(landmarks)
            
            # 纹理分析
            face_region = self.extract_face_region(image, landmarks)
            texture_score = self.analyze_texture(image, face_region)
            
            # 综合评估
            confidence = 0.0
            status = LivenessStatus.PROCESSING
            
            if elapsed_time >= self.detection_duration:
                # 评估标准
                blink_score = min(self.total_blinks / 3.0, 1.0)  # 期望3次眨眼
                movement_score = min(head_movement_score * 2, 1.0)
                avg_texture_score = np.mean(self.texture_history) if self.texture_history else 0.0
                
                # 加权计算置信度
                confidence = (
                    blink_score * 0.4 +
                    movement_score * 0.3 +
                    avg_texture_score * 0.3
                )
                
                # 判断活体状态
                if confidence >= 0.7:
                    status = LivenessStatus.REAL
                elif confidence <= 0.3:
                    status = LivenessStatus.FAKE
                else:
                    status = LivenessStatus.UNKNOWN
            
            return LivenessResult(
                status=status,
                confidence=confidence,
                blink_count=self.total_blinks,
                head_movement_score=head_movement_score,
                texture_score=texture_score if self.texture_history else 0.0,
                details={
                    "eye_aspect_ratio": eye_ar,
                    "elapsed_time": elapsed_time,
                    "detection_duration": self.detection_duration,
                    "blink_threshold": 3,
                    "avg_texture": np.mean(self.texture_history) if self.texture_history else 0.0
                },
                timestamp=current_time
            )
            
        except Exception as e:
            return LivenessResult(
                status=LivenessStatus.UNKNOWN,
                confidence=0.0,
                blink_count=self.total_blinks,
                head_movement_score=0.0,
                texture_score=0.0,
                details={"error": str(e)},
                timestamp=time.time()
            )
    
    def reset(self):
        """重置检测器状态"""
        self.blink_counter = 0
        self.total_blinks = 0
        self.eye_ar_history.clear()
        self.head_positions.clear()
        self.texture_history.clear()
        self.start_time = time.time()
    
    def draw_liveness_info(self, image, result: LivenessResult):
        """在图像上绘制活体检测信息"""
        try:
            h, w = image.shape[:2]
            
            # 状态颜色
            color_map = {
                LivenessStatus.REAL: (0, 255, 0),      # 绿色
                LivenessStatus.FAKE: (0, 0, 255),      # 红色
                LivenessStatus.UNKNOWN: (0, 255, 255), # 黄色
                LivenessStatus.PROCESSING: (255, 255, 0) # 青色
            }
            
            color = color_map.get(result.status, (128, 128, 128))
            
            # 绘制状态信息
            status_text = f"状态: {result.status.value.upper()}"
            confidence_text = f"置信度: {result.confidence:.2f}"
            blink_text = f"眨眼: {result.blink_count}"
            
            # 文本位置
            y_offset = 30
            texts = [status_text, confidence_text, blink_text]
            
            for i, text in enumerate(texts):
                y_pos = y_offset + i * 25
                cv2.putText(image, text, (10, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # 绘制进度条（检测过程中）
            if result.status == LivenessStatus.PROCESSING:
                elapsed = result.details.get("elapsed_time", 0)
                duration = result.details.get("detection_duration", 5)
                progress = min(elapsed / duration, 1.0)
                
                # 进度条背景
                bar_x, bar_y = 10, h - 30
                bar_w, bar_h = 200, 10
                cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), 
                             (128, 128, 128), -1)
                
                # 进度条前景
                progress_w = int(bar_w * progress)
                cv2.rectangle(image, (bar_x, bar_y), (bar_x + progress_w, bar_y + bar_h), 
                             color, -1)
                
                # 进度文本
                progress_text = f"检测进度: {progress*100:.0f}%"
                cv2.putText(image, progress_text, (bar_x, bar_y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            return image
            
        except Exception as e:
            print(f"绘制活体检测信息时出错: {e}")
            return image

def main():
    """测试活体检测功能"""
    detector = LivenessDetector()
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    
    print("活体检测测试开始...")
    print("请在5秒内进行以下动作：")
    print("1. 眨眼3次")
    print("2. 轻微转动头部")
    print("按 'q' 退出，按 'r' 重置检测")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 执行活体检测
        result = detector.detect_liveness(frame)
        
        # 绘制检测信息
        frame = detector.draw_liveness_info(frame, result)
        
        # 显示结果
        cv2.imshow('活体检测测试', frame)
        
        # 检测完成时显示最终结果
        if result.status != LivenessStatus.PROCESSING:
            print(f"\n检测完成！")
            print(f"状态: {result.status.value}")
            print(f"置信度: {result.confidence:.2f}")
            print(f"眨眼次数: {result.blink_count}")
            print(f"头部运动得分: {result.head_movement_score:.2f}")
            print(f"纹理得分: {result.texture_score:.2f}")
        
        # 按键处理
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            detector.reset()
            print("检测器已重置")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()