# -*- coding: utf-8 -*-
"""
测试活体检测OpenCV错误修复
"""

import cv2
import numpy as np
from liveness_detection import LivenessDetector, LivenessStatus

def test_liveness_detection():
    """测试活体检测功能"""
    print("Testing liveness detection...")
    
    # 创建活体检测器
    detector = LivenessDetector()
    
    # 创建一个测试图像（黑色图像）
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    print("Testing with empty image...")
    result = detector.detect_liveness(test_image)
    print(f"Result: {result}")
    
    # 测试None输入
    print("\nTesting with None image...")
    try:
        result = detector.detect_liveness(None)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error with None input: {e}")
    
    # 测试无效图像数据
    print("\nTesting with invalid image data...")
    try:
        invalid_image = "not an image"
        result = detector.detect_liveness(invalid_image)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error with invalid input: {e}")
    
    print("\nLiveness detection test completed!")

if __name__ == "__main__":
    test_liveness_detection()