#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人脸检测与活体检测系统 - 主入口文件
Face Detection and Liveness Detection System - Main Entry Point

作者: AI Assistant
版本: 1.0.0
日期: 2025-06-25
"""

import sys
import os
import argparse
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="人脸检测与活体检测系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                    # 启动多语言GUI（推荐）
  python main.py --gui simple       # 启动简单GUI
  python main.py --gui lite         # 启动轻量级GUI
  python main.py --gui liveness     # 启动活体检测GUI
  python main.py --gui liveness-en  # 启动英文活体检测GUI
  python main.py --lang en          # 启动英文界面
        """
    )
    
    parser.add_argument(
        "--gui",
        choices=["simple", "lite", "liveness", "liveness-en", "multilang"],
        default="multilang",
        help="选择GUI版本 (默认: multilang)"
    )
    
    parser.add_argument(
        "--lang",
        choices=["zh", "en"],
        default="zh",
        help="界面语言 (默认: zh)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Face Detection System v1.0.0"
    )
    
    args = parser.parse_args()
    
    try:
        # 根据参数启动相应的GUI
        if args.gui == "simple":
            from gui.face_detect_gui import main as gui_main
            gui_main()
        elif args.gui == "lite":
            from gui.face_detect_gui_lite import main as gui_main
            gui_main()
        elif args.gui == "liveness":
            from gui.face_detect_with_liveness_gui import main as gui_main
            gui_main()
        elif args.gui == "liveness-en":
            from gui.face_detect_with_liveness_gui_en import main as gui_main
            gui_main()
        elif args.gui == "multilang":
            from gui.face_detect_with_liveness_gui_multilang import main as gui_main
            gui_main()
        else:
            print(f"未知的GUI类型: {args.gui}")
            sys.exit(1)
            
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保所有依赖已正确安装。")
        print("运行: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()