from pydantic import BaseModel

# -*- coding: utf-8 -*-
"""
响应实体类
Response entity classes
"""

from typing import Optional, Dict, Any
try:
    from pydantic import BaseModel
except ImportError:
    # 如果没有 pydantic，使用简单的类
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


class ImageStatus(BaseModel):
    """图像状态类"""
    legal: bool = False
    face_detected: bool = True
    face_probability: float = 0
    multiple_face: bool = False
    brightness: float = 0


class DetectionResult(BaseModel):
    """检测结果类"""
    success: bool = False
    message: str = ""
    status: Optional[Dict[str, Any]] = None
    confidence: Optional[Dict[str, Any]] = None
    
    def __init__(self, **kwargs):
        if not hasattr(BaseModel, '__init__'):
            # 简单类的初始化
            for key, value in kwargs.items():
                setattr(self, key, value)
        else:
            super().__init__(**kwargs)


class LivenessResult(BaseModel):
    """活体检测结果类"""
    is_alive: bool = False
    confidence: float = 0.0
    message: str = ""
    blink_detected: bool = False
    mouth_movement: bool = False
    
    def __init__(self, **kwargs):
        if not hasattr(BaseModel, '__init__'):
            # 简单类的初始化
            for key, value in kwargs.items():
                setattr(self, key, value)
        else:
            super().__init__(**kwargs)
