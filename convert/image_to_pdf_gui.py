#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片转PDF工具 - 带图形界面
支持PNG、JPG、JPEG、BMP、GIF等格式转换为PDF
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
import threading

class ImageToPDFConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("图片转PDF工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 支持的图片格式
        self.supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
        
        # 图片文件列表
        self.image_files = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="图片转PDF工具", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="选择图片文件", command=self.select_images).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(file_frame, text="清空列表", command=self.clear_list).grid(row=0, column=2, padx=(10, 0))
        
        # 文件列表
        list_frame = ttk.LabelFrame(main_frame, text="已选择的图片文件", padding="10")
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview来显示文件列表
        columns = ('文件名', '路径', '大小')
        self.file_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        # 设置列标题
        for col in columns:
            self.file_tree.heading(col, text=col)
            
        # 设置列宽
        self.file_tree.column('文件名', width=200)
        self.file_tree.column('路径', width=400)
        self.file_tree.column('大小', width=100)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        self.file_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 设置选项
        options_frame = ttk.LabelFrame(main_frame, text="转换选项", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 页面大小选择
        ttk.Label(options_frame, text="页面大小:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        self.page_size_var = tk.StringVar(value="A4")
        page_size_combo = ttk.Combobox(options_frame, textvariable=self.page_size_var, 
                                      values=["A4", "Letter", "自适应"], state="readonly", width=10)
        page_size_combo.grid(row=0, column=1, padx=(0, 20), sticky=tk.W)
        
        # 图片质量
        ttk.Label(options_frame, text="图片质量:").grid(row=0, column=2, padx=(0, 10), sticky=tk.W)
        self.quality_var = tk.IntVar(value=85)
        quality_scale = ttk.Scale(options_frame, from_=50, to=100, variable=self.quality_var, 
                                 orient=tk.HORIZONTAL, length=150)
        quality_scale.grid(row=0, column=3, padx=(0, 10), sticky=tk.W)
        self.quality_label = ttk.Label(options_frame, text="85%")
        self.quality_label.grid(row=0, column=4, sticky=tk.W)
        
        # 绑定质量滑块事件
        quality_scale.configure(command=self.update_quality_label)
        
        # 转换按钮和进度条
        convert_frame = ttk.Frame(main_frame)
        convert_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        convert_frame.columnconfigure(1, weight=1)
        
        self.convert_button = ttk.Button(convert_frame, text="转换为PDF", command=self.convert_to_pdf)
        self.convert_button.grid(row=0, column=0, padx=(0, 10))
        
        self.progress = ttk.Progressbar(convert_frame, mode='determinate')
        self.progress.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.status_label = ttk.Label(convert_frame, text="就绪")
        self.status_label.grid(row=0, column=2)
        
    def update_quality_label(self, value):
        """更新质量标签"""
        self.quality_label.config(text=f"{int(float(value))}%")
        
    def select_images(self):
        """选择图片文件"""
        filetypes = [
            ('所有支持的图片', '*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tiff;*.webp'),
            ('PNG文件', '*.png'),
            ('JPEG文件', '*.jpg;*.jpeg'),
            ('BMP文件', '*.bmp'),
            ('GIF文件', '*.gif'),
            ('TIFF文件', '*.tiff'),
            ('WebP文件', '*.webp'),
            ('所有文件', '*.*')
        ]
        
        files = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=filetypes
        )
        
        if files:
            for file_path in files:
                if file_path.lower().endswith(self.supported_formats):
                    if file_path not in self.image_files:
                        self.image_files.append(file_path)
                        self.add_file_to_tree(file_path)
                else:
                    messagebox.showwarning("不支持的格式", f"文件 {os.path.basename(file_path)} 格式不支持")
                    
    def add_file_to_tree(self, file_path):
        """添加文件到树形视图"""
        filename = os.path.basename(file_path)
        try:
            size = os.path.getsize(file_path)
            size_str = self.format_file_size(size)
        except:
            size_str = "未知"
            
        self.file_tree.insert('', 'end', values=(filename, file_path, size_str))
        
    def format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
            
    def clear_list(self):
        """清空文件列表"""
        self.image_files.clear()
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
    def convert_to_pdf(self):
        """转换图片为PDF"""
        if not self.image_files:
            messagebox.showwarning("警告", "请先选择图片文件")
            return
            
        # 选择保存位置
        output_file = filedialog.asksaveasfilename(
            title="保存PDF文件",
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        
        if not output_file:
            return
            
        # 在新线程中执行转换
        self.convert_button.config(state='disabled')
        self.progress['value'] = 0
        self.status_label.config(text="转换中...")
        
        thread = threading.Thread(target=self._convert_worker, args=(output_file,))
        thread.daemon = True
        thread.start()
        
    def _convert_worker(self, output_file):
        """转换工作线程"""
        try:
            # 获取页面大小
            page_size = self.page_size_var.get()
            if page_size == "A4":
                page_width, page_height = A4
            elif page_size == "Letter":
                page_width, page_height = letter
            else:  # 自适应
                page_width, page_height = None, None
                
            quality = self.quality_var.get()
            
            # 创建PDF
            c = canvas.Canvas(output_file)
            
            total_files = len(self.image_files)
            
            for i, image_path in enumerate(self.image_files):
                try:
                    # 更新进度
                    progress = (i / total_files) * 100
                    self.root.after(0, lambda p=progress: self.progress.config(value=p))
                    self.root.after(0, lambda f=os.path.basename(image_path): 
                                  self.status_label.config(text=f"处理: {f}"))
                    
                    # 打开图片
                    with Image.open(image_path) as img:
                        # 转换为RGB模式（如果需要）
                        if img.mode in ('RGBA', 'LA', 'P'):
                            img = img.convert('RGB')
                            
                        # 获取图片尺寸
                        img_width, img_height = img.size
                        
                        if page_width is None:  # 自适应模式
                            # 使用图片原始尺寸
                            c.setPageSize((img_width, img_height))
                            c.drawImage(ImageReader(img), 0, 0, img_width, img_height)
                        else:
                            # 计算缩放比例以适应页面
                            scale_x = page_width / img_width
                            scale_y = page_height / img_height
                            scale = min(scale_x, scale_y)
                            
                            # 计算居中位置
                            new_width = img_width * scale
                            new_height = img_height * scale
                            x = (page_width - new_width) / 2
                            y = (page_height - new_height) / 2
                            
                            c.setPageSize((page_width, page_height))
                            c.drawImage(ImageReader(img), x, y, new_width, new_height)
                            
                    c.showPage()  # 新建页面
                    
                except Exception as e:
                    print(f"处理图片 {image_path} 时出错: {e}")
                    continue
                    
            c.save()
            
            # 转换完成
            self.root.after(0, lambda: self.progress.config(value=100))
            self.root.after(0, lambda: self.status_label.config(text="转换完成"))
            self.root.after(0, lambda: messagebox.showinfo("成功", f"PDF文件已保存到:\n{output_file}"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"转换失败:\n{str(e)}"))
            self.root.after(0, lambda: self.status_label.config(text="转换失败"))
        finally:
            self.root.after(0, lambda: self.convert_button.config(state='normal'))
            
def main():
    """主函数"""
    root = tk.Tk()
    app = ImageToPDFConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()