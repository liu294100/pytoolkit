# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import numpy as np
import cv2
import tempfile
import traceback
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WatermarkRemovalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("水印去除工具")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # --- 样式配置 ---
        self.style = ttk.Style()
        try:
            if os.name == 'nt': self.style.theme_use('vista')
            elif os.uname().sysname == 'Darwin': self.style.theme_use('aqua')
            else: self.style.theme_use('clam')
        except Exception:
            self.style.theme_use('default')

        self.style.configure('Action.TButton', font=('Arial', 12, 'bold'), foreground='blue', padding=10)
        self.style.map('Action.TButton',
            foreground=[('pressed', 'blue'), ('active', 'blue'), ('disabled', 'grey')],
            background=[('pressed', '!disabled', '#CC0000'), ('active', '#E50000'), ('disabled', '#F0F0F0')]
        )
        self.style.configure('TButton', padding=5)
        self.style.configure('TEntry', padding=5)
        self.style.configure('secondary.TLabel', foreground='grey')

        # --- 变量 ---
        self.input_image_path = tk.StringVar()
        self.output_dir_path = tk.StringVar()
        self.removal_method = tk.StringVar(value="region")
        self.color_tolerance = tk.IntVar(value=30)
        self.inpaint_radius = tk.IntVar(value=3)
        self.brightness = tk.DoubleVar(value=1.0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.use_target_color = tk.BooleanVar(value=False)
        self.watermark_color_index = tk.IntVar(value=-1)
        self.target_color_index = tk.IntVar(value=-1)
        
        # 图像相关变量
        self.original_image = None
        self.processed_image = None
        self.display_image = None
        self.mask = None
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.selection_active = False
        self.watermark_color = None  # 水印颜色
        self.target_color = None     # 目标颜色（替换水印的颜色）
        self.color_selection_mode = "watermark"  # 当前颜色选择模式：watermark 或 target

        # --- 主框架 ---
        main_frame = ttk.Frame(root, padding="15 15 15 15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 标题 ---
        ttk.Label(main_frame, text="水印去除工具", font=("Arial", 20, "bold"), anchor=tk.CENTER).pack(pady=(0, 20), fill=tk.X)

        # --- 输入框架 ---
        input_frame = ttk.LabelFrame(main_frame, text=" 1. 选择输入图像 ", padding="10")
        input_frame.pack(fill=tk.X, pady=10)

        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_image_path, width=60)
        self.input_entry.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")
        self.browse_input_btn = ttk.Button(input_frame, text="浏览...", command=self.browse_input, style='TButton')
        self.browse_input_btn.grid(row=0, column=1, padx=5, pady=5)
        input_frame.columnconfigure(0, weight=1)

        # --- 输出框架 ---
        output_frame = ttk.LabelFrame(main_frame, text=" 2. 选择输出目录 ", padding="10")
        output_frame.pack(fill=tk.X, pady=10)

        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_dir_path, width=60)
        self.output_entry.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")
        self.browse_output_btn = ttk.Button(output_frame, text="浏览...", command=self.browse_output, style='TButton')
        self.browse_output_btn.grid(row=0, column=1, padx=5, pady=5)
        output_frame.columnconfigure(0, weight=1)

        # --- 处理选项框架 ---
        options_frame = ttk.LabelFrame(main_frame, text=" 3. 水印去除选项 ", padding="10")
        options_frame.pack(fill=tk.X, pady=10)

        # 水印去除方法
        ttk.Label(options_frame, text="去除方法:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        methods = [
            ("区域选择去除", "region"),
            ("颜色匹配去除", "color"),
            ("图像修复去除", "inpaint")
        ]
        for i, (text, value) in enumerate(methods):
            ttk.Radiobutton(options_frame, text=text, variable=self.removal_method, value=value, 
                           command=self.update_options_visibility).grid(row=0, column=i+1, padx=10, pady=5, sticky=tk.W)

        # 颜色容差选项（初始隐藏）
        self.color_options_frame = ttk.Frame(options_frame)
        self.color_options_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.color_options_frame, text="颜色容差:").pack(side=tk.LEFT, padx=5)
        ttk.Scale(self.color_options_frame, from_=0, to=100, variable=self.color_tolerance, 
                 orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.color_options_frame, textvariable=self.color_tolerance).pack(side=tk.LEFT, padx=5)
        
        # 颜色选择模式选项（初始隐藏）
        self.color_mode_frame = ttk.Frame(options_frame)
        self.color_mode_frame.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.color_mode_frame, text="颜色选择模式:").pack(side=tk.LEFT, padx=5)
        self.watermark_color_btn = ttk.Button(self.color_mode_frame, text="选择水印颜色", 
                                           command=lambda: self.set_color_selection_mode("watermark"))
        self.watermark_color_btn.pack(side=tk.LEFT, padx=5)
        self.target_color_btn = ttk.Button(self.color_mode_frame, text="选择目标颜色", 
                                         command=lambda: self.set_color_selection_mode("target"))
        self.target_color_btn.pack(side=tk.LEFT, padx=5)
        self.use_target_color_cb = ttk.Checkbutton(self.color_mode_frame, text="使用目标颜色替换", 
                                                variable=self.use_target_color)
        self.use_target_color_cb.pack(side=tk.LEFT, padx=15)
        
        # 颜色显示框架
        self.color_display_frame = ttk.Frame(options_frame)
        self.color_display_frame.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.color_display_frame, text="水印颜色:").pack(side=tk.LEFT, padx=5)
        self.watermark_color_canvas = tk.Canvas(self.color_display_frame, width=30, height=20, bg="#FFFFFF", highlightthickness=1, highlightbackground="#000000")
        self.watermark_color_canvas.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.color_display_frame, text="目标颜色:").pack(side=tk.LEFT, padx=15)
        self.target_color_canvas = tk.Canvas(self.color_display_frame, width=30, height=20, bg="#FFFFFF", highlightthickness=1, highlightbackground="#000000")
        self.target_color_canvas.pack(side=tk.LEFT, padx=5)

        # 修复半径选项（初始隐藏）
        self.inpaint_options_frame = ttk.Frame(options_frame)
        self.inpaint_options_frame.grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.inpaint_options_frame, text="修复半径:").pack(side=tk.LEFT, padx=5)
        ttk.Scale(self.inpaint_options_frame, from_=1, to=10, variable=self.inpaint_radius, 
                 orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.inpaint_options_frame, textvariable=self.inpaint_radius).pack(side=tk.LEFT, padx=5)

        # 亮度对比度调整
        adjust_frame = ttk.Frame(options_frame)
        adjust_frame.grid(row=5, column=0, columnspan=4, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(adjust_frame, text="亮度:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Scale(adjust_frame, from_=0.5, to=1.5, variable=self.brightness, 
                 orient=tk.HORIZONTAL, length=200, command=lambda _: self.update_preview()).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(adjust_frame, text="对比度:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Scale(adjust_frame, from_=0.5, to=1.5, variable=self.contrast, 
                 orient=tk.HORIZONTAL, length=200, command=lambda _: self.update_preview()).grid(row=1, column=1, padx=5, pady=5)

        # 初始隐藏选项
        self.update_options_visibility()

        # --- 图像预览区域 ---
        preview_frame = ttk.LabelFrame(main_frame, text=" 图像预览 ", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # 创建一个Frame来包含Canvas和滚动条
        canvas_frame = ttk.Frame(preview_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        # 创建水平和垂直滚动条
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        v_scrollbar = ttk.Scrollbar(canvas_frame)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建Canvas用于显示图像
        self.canvas = tk.Canvas(canvas_frame, xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set, bg="#f0f0f0")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 配置滚动条
        h_scrollbar.config(command=self.canvas.xview)
        v_scrollbar.config(command=self.canvas.yview)

        # 绑定鼠标事件用于区域选择
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        # --- 操作按钮 ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.process_button = ttk.Button(button_frame, text="处理图像", command=self.process_image, style='Action.TButton')
        self.process_button.pack(side=tk.LEFT, padx=5)

        self.save_button = ttk.Button(button_frame, text="保存结果", command=self.save_result, style='TButton', state='disabled')
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.reset_button = ttk.Button(button_frame, text="重置", command=self.reset_image, style='TButton', state='disabled')
        self.reset_button.pack(side=tk.LEFT, padx=5)

        # --- 状态标签 ---
        self.status_label = ttk.Label(main_frame, text="就绪", wraplength=650, anchor=tk.CENTER, justify=tk.CENTER)
        self.status_label.pack(pady=(15, 0), fill=tk.X)

    def browse_input(self):
        """浏览并选择输入图像"""
        file_path = filedialog.askopenfilename(
            title="选择图像文件",
            filetypes=[("图像文件", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("所有文件", "*.*")]
        )
        if file_path:
            self.input_image_path.set(file_path)
            self.load_image(file_path)
            
            # 设置默认输出目录为输入图像所在目录
            output_dir = os.path.dirname(file_path)
            self.output_dir_path.set(output_dir)

    def browse_output(self):
        """浏览并选择输出目录"""
        directory = filedialog.askdirectory(
            title="选择输出目录"
        )
        if directory:
            self.output_dir_path.set(directory)

    def load_image(self, image_path):
        """加载图像并显示在预览区域"""
        try:
            # 加载原始图像
            self.original_image = Image.open(image_path)
            self.processed_image = self.original_image.copy()
            
            # 更新预览
            self.update_preview()
            
            # 启用重置按钮
            self.reset_button.config(state='normal')
            
            # 更新状态
            self.status_label.config(text=f"已加载图像: {os.path.basename(image_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"无法加载图像: {str(e)}")
            logger.error(f"加载图像失败: {e}\n{traceback.format_exc()}")

    def update_preview(self):
        """更新预览区域中的图像"""
        if self.processed_image is None:
            return
            
        # 应用亮度和对比度调整
        img = self.processed_image.copy()
        if self.brightness.get() != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(self.brightness.get())
        if self.contrast.get() != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(self.contrast.get())
            
        # 保存当前显示的图像
        self.display_image = img
        
        # 转换为PhotoImage用于显示
        img_tk = ImageTk.PhotoImage(img)
        
        # 更新Canvas
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        self.canvas.image = img_tk  # 保持引用
        
        # 设置Canvas滚动区域
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def update_options_visibility(self):
        """根据选择的去除方法更新选项可见性"""
        method = self.removal_method.get()
        
        # 隐藏所有选项
        self.color_options_frame.grid_remove()
        self.color_mode_frame.grid_remove()
        self.color_display_frame.grid_remove()
        self.inpaint_options_frame.grid_remove()
        
        # 显示相关选项
        if method == "color":
            self.color_options_frame.grid()
            self.color_mode_frame.grid()
            self.color_display_frame.grid()
        elif method == "inpaint":
            self.inpaint_options_frame.grid()
            
    def set_color_selection_mode(self, mode):
        """设置颜色选择模式"""
        self.color_selection_mode = mode
        if mode == "watermark":
            self.watermark_color_btn.config(style='Action.TButton')
            self.target_color_btn.config(style='TButton')
            self.status_label.config(text="请在图像上选择水印颜色区域")
        else:  # target
            self.watermark_color_btn.config(style='TButton')
            self.target_color_btn.config(style='Action.TButton')
            self.status_label.config(text="请在图像上选择目标颜色区域")

    def on_mouse_down(self, event):
        """鼠标按下事件处理"""
        if self.original_image is not None:
            self.start_x = self.canvas.canvasx(event.x)
            self.start_y = self.canvas.canvasy(event.y)
            self.selection_active = True
            
            # 如果已有选择框，删除它
            if self.rect:
                self.canvas.delete(self.rect)
                self.rect = None

    def on_mouse_move(self, event):
        """鼠标移动事件处理"""
        if self.selection_active:
            cur_x = self.canvas.canvasx(event.x)
            cur_y = self.canvas.canvasy(event.y)
            
            # 如果已有选择框，删除它
            if self.rect:
                self.canvas.delete(self.rect)
            
            # 创建新的选择框
            self.rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, cur_x, cur_y,
                outline="red", width=2
            )

    def on_mouse_up(self, event):
        """鼠标释放事件处理"""
        if self.selection_active:
            self.selection_active = False
            
            # 如果是颜色匹配模式，获取选择区域的颜色
            if self.removal_method.get() == "color":
                coords = self.get_selection_coordinates()
                if coords:
                    x1, y1, x2, y2 = coords
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    # 获取中心点的颜色
                    img_np = np.array(self.original_image)
                    if len(img_np.shape) == 2:  # 灰度图像
                        color = img_np[center_y, center_x]
                        color_rgb = (color, color, color)
                    elif img_np.shape[2] == 4:  # 带透明通道的图像
                        color = img_np[center_y, center_x][:3]
                        color_rgb = tuple(color)
                    else:  # RGB图像
                        color = img_np[center_y, center_x]
                        color_rgb = tuple(color)
                    
                    # 更新相应的颜色
                    if self.color_selection_mode == "watermark":
                        self.watermark_color = color
                        self.watermark_color_index.set(center_y * img_np.shape[1] + center_x)
                        hex_color = f'#{color_rgb[0]:02x}{color_rgb[1]:02x}{color_rgb[2]:02x}'
                        self.watermark_color_canvas.config(bg=hex_color)
                        self.status_label.config(text=f"已选择水印颜色: RGB{color_rgb} 编号: {self.watermark_color_index.get()} 颜色代码: {hex_color}")
                    else:
                        self.target_color = color
                        self.target_color_index.set(center_y * img_np.shape[1] + center_x)
                        hex_color = f'#{color_rgb[0]:02x}{color_rgb[1]:02x}{color_rgb[2]:02x}'
                        self.target_color_canvas.config(bg=hex_color)
                        self.status_label.config(text=f"已选择目标颜色: RGB{color_rgb} 编号: {self.target_color_index.get()} 颜色代码: {hex_color}")

    def process_color_removal(self):
        """基于颜色匹配的水印去除"""
        # 检查是否已选择水印颜色
        if self.watermark_color is None:
            messagebox.showwarning("警告", "请先选择水印颜色")
            return
        # 如果选择使用目标颜色替换但未选择目标颜色
        if self.use_target_color.get() and self.target_color is None:
            messagebox.showwarning("警告", "请先选择目标颜色")
            return
        img_np = np.array(self.original_image)
        if len(img_np.shape) == 2:
            img_np_bgr = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
        elif img_np.shape[2] == 4:
            img_np_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        else:
            img_np_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        tolerance = int(self.color_tolerance.get())
        img_hsv = cv2.cvtColor(img_np_bgr, cv2.COLOR_BGR2HSV)
        target_hsv = cv2.cvtColor(np.uint8([[self.watermark_color]]), cv2.COLOR_BGR2HSV)[0, 0]
        # 修正溢出问题，确保类型为int
        h, s, v = [int(x) for x in target_hsv]
        lower_bound = np.array([
            max(0, h - tolerance),
            max(0, s - tolerance),
            max(0, v - tolerance)
        ], dtype=np.uint8)
        upper_bound = np.array([
            min(179, h + tolerance),
            min(255, s + tolerance),
            min(255, v + tolerance)
        ], dtype=np.uint8)
        mask = cv2.inRange(img_hsv, lower_bound, upper_bound)
        if self.use_target_color.get() and self.target_color is not None:
            result = img_np_bgr.copy()
            target_color_bgr = np.array(self.target_color, dtype=np.uint8)
            result[mask > 0] = target_color_bgr
        else:
            radius = self.inpaint_radius.get()
            result = cv2.inpaint(img_np_bgr, mask, radius, cv2.INPAINT_TELEA)
        result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        self.processed_image = Image.fromarray(result_rgb)

    def process_inpaint_removal(self):
        """基于图像修复算法的水印去除"""
        # 转换为OpenCV格式处理
        img_np = np.array(self.original_image)
        if len(img_np.shape) == 2:  # 灰度图像
            img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
        elif img_np.shape[2] == 4:  # 带透明通道的图像
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        else:  # RGB图像
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
        # 转换为灰度图
        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
        
        # 使用自适应阈值检测水印
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY_INV, 11, 2)
        
        # 形态学操作改善掩码
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # 使用修复算法去除水印
        radius = self.inpaint_radius.get()
        result = cv2.inpaint(img_np, mask, radius, cv2.INPAINT_TELEA)
        
        # 转回PIL格式
        result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        self.processed_image = Image.fromarray(result_rgb)

    def save_result(self):
        """保存处理结果"""
        if self.processed_image is None:
            messagebox.showwarning("警告", "没有处理结果可保存")
            return
            
        output_dir = self.output_dir_path.get()
        if not output_dir:
            messagebox.showwarning("警告", "请先选择输出目录")
            return
            
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录: {str(e)}")
                return
                
        # 生成输出文件名
        input_filename = os.path.basename(self.input_image_path.get())
        name, ext = os.path.splitext(input_filename)
        output_filename = f"{name}_nowatermark{ext}"
        output_path = os.path.join(output_dir, output_filename)
        
        # 保存图像
        try:
            self.display_image.save(output_path)
            messagebox.showinfo("成功", f"图像已保存至:\n{output_path}")
            self.status_label.config(text=f"图像已保存至: {output_filename}")
        except Exception as e:
            messagebox.showerror("保存错误", f"保存图像时出错: {str(e)}")
            logger.error(f"保存图像失败: {e}\n{traceback.format_exc()}")

    def reset_image(self):
        """重置图像到原始状态"""
        if self.original_image is not None:
            self.processed_image = self.original_image.copy()
            self.update_preview()
            self.save_button.config(state='disabled')
            self.status_label.config(text="图像已重置")
            # 删除选择框
            if self.rect:
                self.canvas.delete(self.rect)
                self.rect = None

    def get_selection_coordinates(self):
        """获取选择区域的坐标"""
        if self.rect:
            coords = self.canvas.coords(self.rect)
            # 确保坐标是整数并按左上、右下顺序排列
            x1, y1, x2, y2 = map(int, coords)
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1
            return (x1, y1, x2, y2)
        return None

    def process_image(self):
        """处理图像去除水印"""
        if self.original_image is None:
            messagebox.showwarning("警告", "请先加载图像")
            return
        method = self.removal_method.get()
        try:
            # 禁用按钮
            self.process_button.config(state='disabled')
            self.root.update()
            # 根据不同方法处理
            if method == "region":
                self.process_region_removal()
            elif method == "color":
                self.process_color_removal()
            elif method == "inpaint":
                self.process_inpaint_removal()
            # 更新预览
            self.update_preview()
            # 启用保存按钮
            self.save_button.config(state='normal')
            # 更新状态
            self.status_label.config(text="处理完成，可以保存结果")
        except Exception as e:
            messagebox.showerror("处理错误", f"处理图像时出错: {str(e)}")
            logger.error(f"处理图像失败: {e}\n{traceback.format_exc()}")
        finally:
            # 重新启用按钮
            self.process_button.config(state='normal')

    def process_region_removal(self):
        """基于区域选择的水印去除"""
        coords = self.get_selection_coordinates()
        if not coords:
            messagebox.showwarning("警告", "请先选择水印区域")
            return
        # 获取选择区域
        x1, y1, x2, y2 = coords
        # 转换为OpenCV格式处理
        img_np = np.array(self.original_image)
        if len(img_np.shape) == 2:  # 灰度图像
            img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
        elif img_np.shape[2] == 4:  # 带透明通道的图像
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        else:  # RGB图像
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        # 创建掩码
        mask = np.zeros(img_np.shape[:2], dtype=np.uint8)
        mask[y1:y2, x1:x2] = 255
        # 使用修复算法去除水印
        radius = self.inpaint_radius.get()
        result = cv2.inpaint(img_np, mask, radius, cv2.INPAINT_TELEA)
        # 转回PIL格式
        result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        self.processed_image = Image.fromarray(result_rgb)

def main():
    root = tk.Tk()
    app = WatermarkRemovalApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()