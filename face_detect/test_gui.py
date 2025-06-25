#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify face detection GUI dependencies and basic functionality
"""

import sys
import os
import importlib

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing module imports...")
    success = True
    
    try:
        import cv2
        print(f"✓ OpenCV: {cv2.__version__}")
    except ImportError as e:
        print(f"✗ OpenCV import failed: {e}")
        success = False
    
    try:
        import mediapipe as mp
        print(f"✓ MediaPipe: {mp.__version__}")
    except ImportError as e:
        print(f"✗ MediaPipe import failed: {e}")
        print("  Note: MediaPipe is not compatible with Python 3.13")
        # Don't mark as failure since we have lite version
    
    try:
        from PIL import Image
        print(f"✓ Pillow: {Image.__version__ if hasattr(Image, '__version__') else 'Available'}")
    except ImportError as e:
        print(f"✗ Pillow import failed: {e}")
        success = False
    
    try:
        import pydantic
        print(f"✓ Pydantic: {pydantic.__version__}")
    except ImportError as e:
        print(f"✗ Pydantic import failed: {e}")
        success = False
    
    try:
        import numpy as np
        print(f"✓ NumPy: {np.__version__}")
    except ImportError as e:
        print(f"✗ NumPy import failed: {e}")
        success = False
    
    try:
        import tkinter as tk
        print(f"✓ Tkinter: Available")
    except ImportError as e:
        print(f"✗ Tkinter import failed: {e}")
        success = False
    
    return success

def test_gui_files():
    """Test if GUI files exist"""
    print("\nTesting GUI files...")
    
    files_to_check = [
        "face_detect_gui.py",
        "face_detect_gui_lite.py",
        "requirements.txt"
    ]
    
    all_exist = True
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✓ {file}: Found")
        else:
            print(f"✗ {file}: Missing")
            all_exist = False
    
    return all_exist

def main():
    """Main test function"""
    print("Face Detection GUI - Dependency Test")
    print("=" * 40)
    
    # Test Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version >= (3, 13):
        print("⚠ Warning: Python 3.13+ detected - MediaPipe may not be available")
    
    print()
    
    # Test imports
    imports_ok = test_imports()
    
    # Test files
    files_ok = test_gui_files()
    
    print("\n" + "=" * 40)
    
    if imports_ok and files_ok:
        print("✓ All tests passed - GUI should work properly")
        return 0
    elif files_ok:
        print("⚠ Basic functionality available - some features may be limited")
        return 0
    else:
        print("✗ Critical issues found - please check installation")
        return 1

if __name__ == "__main__":
    sys.exit(main())