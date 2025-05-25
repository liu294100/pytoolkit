#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tkinter测试脚本
用于验证Tkinter环境是否正常工作
"""

import tkinter as tk
from tkinter import ttk, messagebox

def main():
    """主函数"""
    try:
        # 创建主窗口
        root = tk.Tk()
        root.title("Tkinter测试")
        root.geometry("400x300")
        
        # 添加标签
        label = tk.Label(root, text="Tkinter测试成功！", font=("Arial", 16))
        label.pack(pady=50)
        
        # 添加按钮
        button = ttk.Button(root, text="点击我", command=lambda: messagebox.showinfo("消息", "按钮点击成功！"))
        button.pack(pady=20)
        
        # 运行主循环
        root.mainloop()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("开始测试Tkinter...")
    main()
    print("测试完成")