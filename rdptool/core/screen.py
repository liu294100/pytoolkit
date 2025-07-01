#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
屏幕捕获模块

提供跨平台的屏幕捕获功能：
- 全屏和区域截图
- 实时屏幕流
- 图像压缩和优化
- 多显示器支持
"""

import io
import time
import threading
import logging
from typing import Optional, Tuple, List, Callable
from dataclasses import dataclass
from enum import Enum

try:
    from PIL import Image, ImageGrab
except ImportError:
    Image = None
    ImageGrab = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

logger = logging.getLogger(__name__)

class CaptureMethod(Enum):
    """屏幕捕获方法"""
    PIL = "pil"           # PIL/Pillow
    OPENCV = "opencv"     # OpenCV
    MSS = "mss"           # mss库 (可选)
    
class CompressionFormat(Enum):
    """图像压缩格式"""
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    
@dataclass
class CaptureConfig:
    """捕获配置"""
    method: CaptureMethod = CaptureMethod.PIL
    format: CompressionFormat = CompressionFormat.JPEG
    quality: int = 80  # 压缩质量 (1-100)
    fps: int = 30      # 帧率
    region: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height)
    scale_factor: float = 1.0  # 缩放因子
    monitor_index: int = 0     # 显示器索引
    
class ScreenCapture:
    """屏幕捕获器"""
    
    def __init__(self, config: CaptureConfig):
        self.config = config
        self.is_capturing = False
        self.capture_thread = None
        self.frame_callbacks: List[Callable] = []
        self.last_frame = None
        self.frame_count = 0
        self.start_time = None
        
        # 检查依赖
        self._check_dependencies()
        
        # 获取屏幕信息
        self.screen_info = self._get_screen_info()
        
    def _check_dependencies(self):
        """检查依赖库"""
        if self.config.method == CaptureMethod.PIL and not Image:
            raise ImportError("PIL/Pillow库未安装，请运行: pip install pillow")
        
        if self.config.method == CaptureMethod.OPENCV and not cv2:
            raise ImportError("OpenCV库未安装，请运行: pip install opencv-python")
    
    def _get_screen_info(self) -> dict:
        """获取屏幕信息"""
        info = {
            'monitors': [],
            'primary_monitor': None
        }
        
        try:
            if self.config.method == CaptureMethod.PIL:
                # 使用PIL获取主显示器信息
                bbox = ImageGrab.grab().size
                info['primary_monitor'] = {
                    'width': bbox[0],
                    'height': bbox[1],
                    'x': 0,
                    'y': 0
                }
                info['monitors'].append(info['primary_monitor'])
                
        except Exception as e:
            logger.error(f"获取屏幕信息失败: {e}")
            # 默认值
            info['primary_monitor'] = {
                'width': 1920,
                'height': 1080,
                'x': 0,
                'y': 0
            }
            info['monitors'].append(info['primary_monitor'])
        
        return info
    
    def capture_frame(self) -> Optional[bytes]:
        """捕获单帧"""
        try:
            if self.config.method == CaptureMethod.PIL:
                return self._capture_with_pil()
            elif self.config.method == CaptureMethod.OPENCV:
                return self._capture_with_opencv()
            else:
                logger.error(f"不支持的捕获方法: {self.config.method}")
                return None
                
        except Exception as e:
            logger.error(f"捕获帧失败: {e}")
            return None
    
    def _capture_with_pil(self) -> Optional[bytes]:
        """使用PIL捕获屏幕"""
        try:
            # 捕获屏幕
            if self.config.region:
                # 区域截图
                x, y, w, h = self.config.region
                bbox = (x, y, x + w, y + h)
                screenshot = ImageGrab.grab(bbox)
            else:
                # 全屏截图
                screenshot = ImageGrab.grab()
            
            # 缩放
            if self.config.scale_factor != 1.0:
                new_size = (
                    int(screenshot.width * self.config.scale_factor),
                    int(screenshot.height * self.config.scale_factor)
                )
                screenshot = screenshot.resize(new_size, Image.Resampling.LANCZOS)
            
            # 压缩
            return self._compress_image(screenshot)
            
        except Exception as e:
            logger.error(f"PIL捕获失败: {e}")
            return None
    
    def _capture_with_opencv(self) -> Optional[bytes]:
        """使用OpenCV捕获屏幕"""
        try:
            import pyautogui
            
            # 捕获屏幕
            if self.config.region:
                x, y, w, h = self.config.region
                screenshot = pyautogui.screenshot(region=(x, y, w, h))
            else:
                screenshot = pyautogui.screenshot()
            
            # 转换为OpenCV格式
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 缩放
            if self.config.scale_factor != 1.0:
                new_width = int(frame.shape[1] * self.config.scale_factor)
                new_height = int(frame.shape[0] * self.config.scale_factor)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # 压缩
            if self.config.format == CompressionFormat.JPEG:
                _, buffer = cv2.imencode('.jpg', frame, 
                    [cv2.IMWRITE_JPEG_QUALITY, self.config.quality])
            elif self.config.format == CompressionFormat.PNG:
                _, buffer = cv2.imencode('.png', frame)
            else:
                _, buffer = cv2.imencode('.jpg', frame, 
                    [cv2.IMWRITE_JPEG_QUALITY, self.config.quality])
            
            return buffer.tobytes()
            
        except ImportError:
            logger.error("OpenCV方法需要安装pyautogui: pip install pyautogui")
            return None
        except Exception as e:
            logger.error(f"OpenCV捕获失败: {e}")
            return None
    
    def _compress_image(self, image: Image.Image) -> bytes:
        """压缩图像"""
        buffer = io.BytesIO()
        
        if self.config.format == CompressionFormat.JPEG:
            image.save(buffer, format='JPEG', quality=self.config.quality, optimize=True)
        elif self.config.format == CompressionFormat.PNG:
            image.save(buffer, format='PNG', optimize=True)
        elif self.config.format == CompressionFormat.WEBP:
            image.save(buffer, format='WEBP', quality=self.config.quality, method=6)
        else:
            image.save(buffer, format='JPEG', quality=self.config.quality, optimize=True)
        
        return buffer.getvalue()
    
    def start_capture_stream(self, frame_callback: Callable[[bytes], None]):
        """开始捕获流"""
        if self.is_capturing:
            logger.warning("捕获流已在运行")
            return
        
        self.frame_callbacks.append(frame_callback)
        self.is_capturing = True
        self.frame_count = 0
        self.start_time = time.time()
        
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        logger.info(f"开始屏幕捕获流，FPS: {self.config.fps}")
    
    def _capture_loop(self):
        """捕获循环"""
        frame_interval = 1.0 / self.config.fps
        
        while self.is_capturing:
            start_time = time.time()
            
            # 捕获帧
            frame_data = self.capture_frame()
            if frame_data:
                self.last_frame = frame_data
                self.frame_count += 1
                
                # 调用回调函数
                for callback in self.frame_callbacks:
                    try:
                        callback(frame_data)
                    except Exception as e:
                        logger.error(f"帧回调错误: {e}")
            
            # 控制帧率
            elapsed = time.time() - start_time
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def stop_capture_stream(self):
        """停止捕获流"""
        if not self.is_capturing:
            return
        
        self.is_capturing = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        self.frame_callbacks.clear()
        
        # 计算统计信息
        if self.start_time:
            duration = time.time() - self.start_time
            avg_fps = self.frame_count / duration if duration > 0 else 0
            logger.info(f"捕获流已停止，平均FPS: {avg_fps:.2f}")
    
    def add_frame_callback(self, callback: Callable[[bytes], None]):
        """添加帧回调"""
        self.frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable[[bytes], None]):
        """移除帧回调"""
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)
    
    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        monitor = self.screen_info['primary_monitor']
        return monitor['width'], monitor['height']
    
    def get_capture_region(self) -> Tuple[int, int, int, int]:
        """获取捕获区域"""
        if self.config.region:
            return self.config.region
        else:
            width, height = self.get_screen_size()
            return (0, 0, width, height)
    
    def set_capture_region(self, x: int, y: int, width: int, height: int):
        """设置捕获区域"""
        self.config.region = (x, y, width, height)
        logger.info(f"设置捕获区域: {self.config.region}")
    
    def set_quality(self, quality: int):
        """设置压缩质量"""
        self.config.quality = max(1, min(100, quality))
        logger.info(f"设置压缩质量: {self.config.quality}")
    
    def set_fps(self, fps: int):
        """设置帧率"""
        self.config.fps = max(1, min(60, fps))
        logger.info(f"设置帧率: {self.config.fps}")
    
    def set_scale_factor(self, scale: float):
        """设置缩放因子"""
        self.config.scale_factor = max(0.1, min(2.0, scale))
        logger.info(f"设置缩放因子: {self.config.scale_factor}")
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            'is_capturing': self.is_capturing,
            'frame_count': self.frame_count,
            'config': {
                'method': self.config.method.value,
                'format': self.config.format.value,
                'quality': self.config.quality,
                'fps': self.config.fps,
                'scale_factor': self.config.scale_factor,
                'region': self.config.region
            },
            'screen_info': self.screen_info
        }
        
        if self.start_time:
            duration = time.time() - self.start_time
            stats['duration'] = duration
            stats['avg_fps'] = self.frame_count / duration if duration > 0 else 0
        
        return stats

# 工具函数
def get_available_capture_methods() -> List[CaptureMethod]:
    """获取可用的捕获方法"""
    methods = []
    
    if Image and ImageGrab:
        methods.append(CaptureMethod.PIL)
    
    if cv2 and np:
        methods.append(CaptureMethod.OPENCV)
    
    return methods

def create_screen_capture(method: Optional[CaptureMethod] = None, **kwargs) -> ScreenCapture:
    """创建屏幕捕获器"""
    if method is None:
        available_methods = get_available_capture_methods()
        if not available_methods:
            raise RuntimeError("没有可用的屏幕捕获方法，请安装PIL或OpenCV")
        method = available_methods[0]
    
    config = CaptureConfig(method=method, **kwargs)
    return ScreenCapture(config)