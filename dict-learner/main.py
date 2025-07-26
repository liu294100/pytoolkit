#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dict Learner - 单词记忆与英语肌肉记忆锻炼软件
Words learning and English muscle memory training software

基于 qwerty-learner 项目的 Python 客户端实现
Python client implementation based on qwerty-learner project

版本: 1.0.0
日期: 2025-01-15
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
        description="Dict Learner - 单词记忆与英语肌肉记忆锻炼软件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                    # 启动GUI界面（推荐）
  python main.py --mode console     # 启动控制台模式
  python main.py --dict cet4        # 指定词库启动
  python main.py --lang en          # 启动英文界面
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["gui", "console"],
        default="gui",
        help="运行模式 (默认: gui)"
    )
    
    parser.add_argument(
        "--dict",
        choices=["cet4", "cet6", "gre", "toefl", "ielts", "gmat", "sat", "coder"],
        help="指定词库"
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
        version="Dict Learner v1.0.0"
    )
    
    args = parser.parse_args()
    
    try:
        # 根据参数启动相应的模式
        if args.mode == "gui":
            from gui.main_gui import DictLearnerGUI
            app = DictLearnerGUI(language=args.lang, default_dict=args.dict)
            app.run()
        elif args.mode == "console":
            from console.main_console import DictLearnerConsole
            app = DictLearnerConsole(language=args.lang, default_dict=args.dict)
            app.run()
        else:
            print(f"未知的运行模式: {args.mode}")
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