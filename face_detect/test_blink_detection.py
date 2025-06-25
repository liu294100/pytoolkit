#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
眨眼检测测试脚本
测试修复后的眨眼检测功能
"""

import cv2
import numpy as np
from liveness_detection import LivenessDetector
import time

def test_blink_detection():
    """测试眨眼检测功能"""
    print("开始测试眨眼检测功能...")
    
    # 初始化活体检测器
    detector = LivenessDetector()
    
    # 初始化摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    
    print("摄像头已启动，请对着摄像头眨眼...")
    print("按 'q' 键退出测试")
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            break
        
        frame_count += 1
        
        # 执行活体检测
        result = detector.detect_liveness(frame)
        
        # 在图像上显示检测信息
        cv2.putText(frame, f"Blink Count: {result.blink_count}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Confidence: {result.confidence:.3f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Status: {result.status.value}", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 显示当前EAR值（如果有的话）
        if 'eye_aspect_ratio' in result.details:
            ear = result.details['eye_aspect_ratio']
            cv2.putText(frame, f"EAR: {ear:.3f}", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 显示帧数
        cv2.putText(frame, f"Frame: {frame_count}", (10, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 显示经过的时间
        elapsed = time.time() - start_time
        cv2.putText(frame, f"Time: {elapsed:.1f}s", (10, 180), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 显示图像
        cv2.imshow('Blink Detection Test', frame)
        
        # 每10帧打印一次检测结果
        if frame_count % 10 == 0:
            print(f"Frame {frame_count}: Blinks={result.blink_count}, "
                  f"Confidence={result.confidence:.3f}, Status={result.status.value}")
        
        # 检查退出条件
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
    
    # 清理资源
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\n测试完成！")
    print(f"总帧数: {frame_count}")
    print(f"总时间: {time.time() - start_time:.1f}秒")
    print(f"最终眨眼次数: {result.blink_count}")
    print(f"最终置信度: {result.confidence:.3f}")

if __name__ == "__main__":
    test_blink_detection()