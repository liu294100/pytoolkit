#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人脸检测与活体检测集成GUI应用
集成静态图片检测和实时活体检测功能
支持中英文界面切换
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import time
from pathlib import Path
import json
from datetime import datetime
import os

# 导入自定义模块
try:
    from core.detect import main as detect_faces
    from core.resp_entity import ImageStatus
    from core.liveness_detection import LivenessDetector, LivenessStatus
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保所有依赖模块都在同一目录下")

# 语言配置
class LanguageConfig:
    def __init__(self):
        self.current_language = 'en'  # 默认英文
        self.texts = {
            'en': {
                'title': 'Face Detection & Liveness Detection System',
                'static_tab': 'Static Detection',
                'liveness_tab': 'Liveness Detection',
                'comparison_tab': 'Result Comparison',
                'language_switch': 'Switch to Chinese',
                'select_image': 'Select Image',
                'detect_faces': 'Detect Faces',
                'save_result': 'Save Result',
                'clear_result': 'Clear Result',
                'start_camera': 'Start Camera',
                'stop_camera': 'Stop Camera',
                'start_detection': 'Start Detection',
                'stop_detection': 'Stop Detection',
                'detection_history': 'Detection History',
                'clear_history': 'Clear History',
                'export_history': 'Export History',
                'image_path': 'Image Path:',
                'detection_result': 'Detection Result:',
                'face_count': 'Face Count:',
                'confidence': 'Confidence:',
                'processing_time': 'Processing Time:',
                'camera_status': 'Camera Status:',
                'liveness_status': 'Liveness Status:',
                'blink_count': 'Blink Count:',
                'head_movement': 'Head Movement:',
                'texture_score': 'Texture Score:',
                'detection_time': 'Detection Time:',
                'status_ready': 'Ready',
                'status_detecting': 'Detecting...',
                'status_stopped': 'Stopped',
                'error_no_image': 'Please select an image first',
                'error_camera': 'Camera initialization failed',
                'success_save': 'Result saved successfully',
                'success_export': 'History exported successfully',
                'file_formats': 'Image files',
                'all_files': 'All files'
            },
            'zh': {
                'title': '人脸检测与活体检测系统',
                'static_tab': '静态检测',
                'liveness_tab': '活体检测',
                'comparison_tab': '结果对比',
                'language_switch': '切换到英文',
                'select_image': '选择图片',
                'detect_faces': '检测人脸',
                'save_result': '保存结果',
                'clear_result': '清除结果',
                'start_camera': '启动摄像头',
                'stop_camera': '停止摄像头',
                'start_detection': '开始检测',
                'stop_detection': '停止检测',
                'detection_history': '检测历史',
                'clear_history': '清除历史',
                'export_history': '导出历史',
                'image_path': '图片路径：',
                'detection_result': '检测结果：',
                'face_count': '人脸数量：',
                'confidence': '置信度：',
                'processing_time': '处理时间：',
                'camera_status': '摄像头状态：',
                'liveness_status': '活体状态：',
                'blink_count': '眨眼次数：',
                'head_movement': '头部运动：',
                'texture_score': '纹理得分：',
                'detection_time': '检测时间：',
                'status_ready': '就绪',
                'status_detecting': '检测中...',
                'status_stopped': '已停止',
                'error_no_image': '请先选择图片',
                'error_camera': '摄像头初始化失败',
                'success_save': '结果保存成功',
                'success_export': '历史记录导出成功',
                'file_formats': '图片文件',
                'all_files': '所有文件'
            }
        }
    
    def get_text(self, key):
        return self.texts[self.current_language].get(key, key)
    
    def switch_language(self):
        self.current_language = 'zh' if self.current_language == 'en' else 'en'

class FaceDetectionWithLivenessGUI:
    """人脸检测与活体检测集成GUI"""
    
    def __init__(self, root):
        self.root = root
        
        # 初始化语言配置
        self.lang_config = LanguageConfig()
        
        self.root.title(self.lang_config.get_text('title'))
        self.root.geometry("1200x800")
        
        # 应用状态
        self.current_image = None
        self.current_image_path = None
        self.detection_results = None
        
        # 活体检测相关
        self.liveness_detector = None
        self.camera_active = False
        self.cap = None
        self.liveness_thread = None
        self.current_frame = None
        self.liveness_result = None
        
        # 存储所有需要更新的界面元素
        self.ui_elements = {}
        
        # 创建界面
        self.create_widgets()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """创建GUI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 创建顶部工具栏
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 语言切换按钮
        self.language_btn = ttk.Button(
            toolbar_frame, 
            text=self.lang_config.get_text('language_switch'),
            command=self.switch_language
        )
        self.language_btn.pack(side=tk.RIGHT)
        self.ui_elements['language_btn'] = self.language_btn
        
        # 创建选项卡
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 静态图片检测选项卡
        self.create_static_detection_tab()
        
        # 活体检测选项卡
        self.create_liveness_detection_tab()
        
        # 结果对比选项卡
        self.create_comparison_tab()
        
        # 状态栏
        self.status_var = tk.StringVar(value=self.lang_config.get_text('status_ready'))
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def switch_language(self):
        """切换语言"""
        self.lang_config.switch_language()
        self.update_ui_language()
    
    def update_ui_language(self):
        """更新界面语言"""
        # 更新窗口标题
        self.root.title(self.lang_config.get_text('title'))
        
        # 更新选项卡标题
        self.notebook.tab(0, text=self.lang_config.get_text('static_tab'))
        self.notebook.tab(1, text=self.lang_config.get_text('liveness_tab'))
        self.notebook.tab(2, text=self.lang_config.get_text('comparison_tab'))
        
        # 更新语言切换按钮
        self.language_btn.config(text=self.lang_config.get_text('language_switch'))
        
        # 更新状态栏
        current_status = self.status_var.get()
        if '就绪' in current_status or 'Ready' in current_status:
            self.status_var.set(self.lang_config.get_text('status_ready'))
        
        # 更新所有存储的UI元素
        for key, element in self.ui_elements.items():
            if hasattr(element, 'config') and key.endswith('_btn'):
                text_key = key.replace('_btn', '')
                if text_key in ['select_image', 'detect_faces', 'save_result', 'clear_result',
                               'start_detection', 'stop_detection', 'clear_history', 'export_history']:
                    element.config(text=self.lang_config.get_text(text_key))
                elif key == 'start_camera_btn':
                    # 摄像头按钮需要根据当前状态设置文本
                    if hasattr(self, 'camera_active') and self.camera_active:
                        element.config(text=self.lang_config.get_text('stop_camera'))
                    else:
                        element.config(text=self.lang_config.get_text('start_camera'))
            elif hasattr(element, 'config') and key.endswith('_label'):
                text_key = key.replace('_label', '')
                if text_key in ['image_path', 'detection_result', 'face_count', 'confidence',
                               'processing_time', 'camera_status', 'liveness_status', 'blink_count',
                               'head_movement', 'texture_score', 'detection_time', 'detection_history']:
                    element.config(text=self.lang_config.get_text(text_key))
    
    def create_static_detection_tab(self):
        """创建静态图片检测选项卡"""
        static_frame = ttk.Frame(self.notebook)
        self.notebook.add(static_frame, text=self.lang_config.get_text('static_tab'))
        
        # 左侧控制面板
        control_frame = ttk.LabelFrame(static_frame, text="控制面板", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 图片选择
        self.select_image_btn = ttk.Button(control_frame, text=self.lang_config.get_text('select_image'), command=self.select_image)
        self.select_image_btn.grid(row=0, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_elements['select_image_btn'] = self.select_image_btn
        
        # 检测按钮
        self.detect_btn = ttk.Button(control_frame, text=self.lang_config.get_text('detect_faces'), command=self.detect_faces_static, state=tk.DISABLED)
        self.detect_btn.grid(row=1, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_elements['detect_faces_btn'] = self.detect_btn
        
        # 保存结果按钮
        self.save_btn = ttk.Button(control_frame, text=self.lang_config.get_text('save_result'), command=self.save_results, state=tk.DISABLED)
        self.save_btn.grid(row=2, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_elements['save_result_btn'] = self.save_btn
        
        # 图片信息
        info_frame = ttk.LabelFrame(control_frame, text="图片信息", padding="5")
        info_frame.grid(row=3, column=0, pady=10, sticky=tk.W+tk.E)
        
        self.image_info = tk.Text(info_frame, height=8, width=30)
        self.image_info.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 检测结果
        result_frame = ttk.LabelFrame(control_frame, text="检测结果", padding="5")
        result_frame.grid(row=4, column=0, pady=10, sticky=tk.W+tk.E)
        
        self.result_text = tk.Text(result_frame, height=10, width=30)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 右侧图片显示区域
        image_frame = ttk.LabelFrame(static_frame, text="图片预览", padding="10")
        image_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.image_label = ttk.Label(image_frame, text="请选择图片")
        self.image_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        static_frame.columnconfigure(1, weight=1)
        static_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
    
    def create_liveness_detection_tab(self):
        """创建活体检测选项卡"""
        liveness_frame = ttk.Frame(self.notebook)
        self.notebook.add(liveness_frame, text=self.lang_config.get_text('liveness_tab'))
        
        # 左侧控制面板
        liveness_control_frame = ttk.LabelFrame(liveness_frame, text="Liveness Control", padding="10")
        liveness_control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 摄像头控制
        self.camera_btn = ttk.Button(liveness_control_frame, text=self.lang_config.get_text('start_camera'), command=self.toggle_camera)
        self.camera_btn.grid(row=0, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_elements['start_camera_btn'] = self.camera_btn
        
        # 开始活体检测
        self.liveness_btn = ttk.Button(liveness_control_frame, text=self.lang_config.get_text('start_detection'), 
                                     command=self.start_liveness_detection, state=tk.DISABLED)
        self.liveness_btn.grid(row=1, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_elements['start_detection_btn'] = self.liveness_btn
        
        # 重置检测
        self.reset_btn = ttk.Button(liveness_control_frame, text="Reset Detection", 
                                  command=self.reset_liveness_detection, state=tk.DISABLED)
        self.reset_btn.grid(row=2, column=0, pady=5, sticky=tk.W+tk.E)
        
        # 保存活体检测结果
        self.save_liveness_btn = ttk.Button(liveness_control_frame, text="Save Liveness Result", 
                                          command=self.save_liveness_results, state=tk.DISABLED)
        self.save_liveness_btn.grid(row=3, column=0, pady=5, sticky=tk.W+tk.E)
        
        # 检测说明
        instruction_frame = ttk.LabelFrame(liveness_control_frame, text="检测说明", padding="5")
        instruction_frame.grid(row=4, column=0, pady=10, sticky=tk.W+tk.E)
        
        instructions = (
            "活体检测步骤：\n\n"
            "1. 点击'启动摄像头'\n"
            "2. 点击'开始活体检测'\n"
            "3. 在5秒内完成以下动作：\n"
            "   • 眨眼3次\n"
            "   • 轻微转动头部\n"
            "4. 等待检测结果\n\n"
            "注意：保持面部在摄像头\n"
            "视野内，光线充足"
        )
        
        instruction_label = ttk.Label(instruction_frame, text=instructions, justify=tk.LEFT)
        instruction_label.grid(row=0, column=0, sticky=tk.W)
        
        # 活体检测结果
        liveness_result_frame = ttk.LabelFrame(liveness_control_frame, text="活体检测结果", padding="5")
        liveness_result_frame.grid(row=5, column=0, pady=10, sticky=tk.W+tk.E)
        
        self.liveness_result_text = tk.Text(liveness_result_frame, height=8, width=30)
        self.liveness_result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 右侧摄像头显示区域
        camera_frame = ttk.LabelFrame(liveness_frame, text="摄像头预览", padding="10")
        camera_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.camera_label = ttk.Label(camera_frame, text="摄像头未启动")
        self.camera_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        liveness_frame.columnconfigure(1, weight=1)
        liveness_frame.rowconfigure(0, weight=1)
        camera_frame.columnconfigure(0, weight=1)
        camera_frame.rowconfigure(0, weight=1)
    
    def create_comparison_tab(self):
        """创建结果对比选项卡"""
        comparison_frame = ttk.Frame(self.notebook)
        self.notebook.add(comparison_frame, text="结果对比")
        
        # 对比说明
        instruction_frame = ttk.LabelFrame(comparison_frame, text="功能对比", padding="10")
        instruction_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        comparison_text = (
            "静态图片检测 vs 活体检测\n\n"
            "静态图片检测：\n"
            "• 检测上传图片中的人脸\n"
            "• 标注人脸位置和置信度\n"
            "• 支持多人脸检测\n"
            "• 适用于照片分析\n\n"
            "活体检测：\n"
            "• 实时摄像头检测\n"
            "• 验证是否为真人\n"
            "• 防止照片欺骗\n"
            "• 适用于身份验证\n\n"
            "建议：结合使用两种检测方式可以获得更好的安全性"
        )
        
        comparison_label = ttk.Label(instruction_frame, text=comparison_text, justify=tk.LEFT)
        comparison_label.grid(row=0, column=0, sticky=tk.W)
        
        # 历史记录
        history_frame = ttk.LabelFrame(comparison_frame, text="检测历史", padding="10")
        history_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 创建表格显示历史记录
        columns = ('时间', '类型', '结果', '置信度', '详情')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=120)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 清除历史按钮
        ttk.Button(history_frame, text="清除历史", command=self.clear_history).grid(row=1, column=0, pady=5, sticky=tk.W)
        
        # 配置网格权重
        comparison_frame.columnconfigure(0, weight=1)
        comparison_frame.rowconfigure(1, weight=1)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
    
    def select_image(self):
        """选择图片文件"""
        file_types = [
            (self.lang_config.get_text('file_formats'), '*.jpg *.jpeg *.png *.bmp *.tiff *.webp'),
            ('JPEG文件', '*.jpg *.jpeg'),
            ('PNG文件', '*.png'),
            (self.lang_config.get_text('all_files'), '*.*')
        ]
        
        file_path = filedialog.askopenfilename(
            title="Select Image File" if self.lang_config.current_language == 'en' else "选择图片文件",
            filetypes=file_types
        )
        
        if file_path:
            self.load_image(file_path)
    
    def load_image(self, file_path):
        """加载并显示图片"""
        try:
            self.current_image_path = file_path
            
            # 使用PIL加载图片
            pil_image = Image.open(file_path)
            self.current_image = pil_image.copy()
            
            # 调整图片大小以适应显示
            display_image = self.resize_image_for_display(pil_image, max_size=(600, 400))
            
            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(display_image)
            self.image_label.configure(image=photo, text="")
            self.image_label.image = photo  # 保持引用
            
            # 显示图片信息
            self.show_image_info(pil_image, file_path)
            
            # 启用检测按钮
            self.detect_btn.configure(state=tk.NORMAL)
            
            self.status_var.set(f"已加载图片: {Path(file_path).name}")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载图片失败: {str(e)}")
            self.status_var.set("加载图片失败")
    
    def resize_image_for_display(self, image, max_size):
        """调整图片大小以适应显示"""
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    
    def show_image_info(self, image, file_path):
        """显示图片信息"""
        file_size = Path(file_path).stat().st_size
        
        info = f"文件路径: {file_path}\n"
        info += f"文件大小: {file_size / 1024:.1f} KB\n"
        info += f"图片尺寸: {image.size[0]} x {image.size[1]}\n"
        info += f"图片模式: {image.mode}\n"
        info += f"图片格式: {image.format}\n"
        
        self.image_info.delete(1.0, tk.END)
        self.image_info.insert(1.0, info)
    
    def detect_faces_static(self):
        """执行静态图片人脸检测"""
        if not self.current_image_path:
            messagebox.showwarning("警告", "请先选择图片")
            return
        
        try:
            self.status_var.set("正在检测人脸...")
            self.detect_btn.configure(state=tk.DISABLED)
            
            # 在新线程中执行检测
            def detect_thread():
                try:
                    # 调用检测函数
                    result = detect_faces(self.current_image_path)
                    
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.on_detection_complete(result))
                    
                except Exception as e:
                    self.root.after(0, lambda: self.on_detection_error(str(e)))
            
            threading.Thread(target=detect_thread, daemon=True).start()
            
        except Exception as e:
            self.on_detection_error(str(e))
    
    def on_detection_complete(self, result):
        """检测完成回调"""
        try:
            self.detection_results = result
            
            # 显示检测结果
            if isinstance(result, ImageStatus):
                result_text = f"检测完成！\n\n"
                result_text += f"检测到人脸数量: {len(result.faces)}\n\n"
                
                for i, face in enumerate(result.faces, 1):
                    result_text += f"人脸 {i}:\n"
                    result_text += f"  位置: ({face.x}, {face.y})\n"
                    result_text += f"  大小: {face.width} x {face.height}\n"
                    result_text += f"  置信度: {face.confidence:.3f}\n\n"
                
                # 加载并显示标注后的图片
                if result.output_path and Path(result.output_path).exists():
                    annotated_image = Image.open(result.output_path)
                    display_image = self.resize_image_for_display(annotated_image, max_size=(600, 400))
                    photo = ImageTk.PhotoImage(display_image)
                    self.image_label.configure(image=photo)
                    self.image_label.image = photo
            else:
                result_text = f"检测结果: {str(result)}"
            
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, result_text)
            
            # 添加到历史记录
            self.add_to_history('静态检测', '成功', len(result.faces) if hasattr(result, 'faces') else 0, '详见结果')
            
            # 启用保存按钮
            self.save_btn.configure(state=tk.NORMAL)
            self.detect_btn.configure(state=tk.NORMAL)
            
            self.status_var.set("检测完成")
            
        except Exception as e:
            self.on_detection_error(str(e))
    
    def on_detection_error(self, error_msg):
        """检测错误回调"""
        messagebox.showerror("检测错误", f"人脸检测失败: {error_msg}")
        self.detect_btn.configure(state=tk.NORMAL)
        self.status_var.set("检测失败")
        
        # 添加到历史记录
        self.add_to_history('静态检测', '失败', 0, error_msg)
    
    def save_results(self):
        """保存检测结果"""
        if not self.detection_results:
            messagebox.showwarning("警告", "没有检测结果可保存")
            return
        
        try:
            # 选择保存位置
            file_path = filedialog.asksaveasfilename(
                title="保存检测结果",
                defaultextension=".json",
                filetypes=[('JSON文件', '*.json'), ('所有文件', '*.*')]
            )
            
            if file_path:
                # 准备保存数据
                save_data = {
                    'timestamp': datetime.now().isoformat(),
                    'source_image': self.current_image_path,
                    'detection_type': 'static_face_detection',
                    'results': self.detection_results.__dict__ if hasattr(self.detection_results, '__dict__') else str(self.detection_results)
                }
                
                # 保存到文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("成功", f"结果已保存到: {file_path}")
                self.status_var.set(f"结果已保存: {Path(file_path).name}")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def toggle_camera(self):
        """切换摄像头状态"""
        if not self.camera_active:
            self.start_camera()
        else:
            self.stop_camera()
    
    def start_camera(self):
        """启动摄像头"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                error_title = "Error" if self.lang_config.current_language == 'en' else "错误"
                error_msg = self.lang_config.get_text('error_camera')
                messagebox.showerror(error_title, error_msg)
                return
            
            self.camera_active = True
            self.camera_btn.configure(text=self.lang_config.get_text('stop_camera'))
            self.liveness_btn.configure(state=tk.NORMAL)
            
            # 启动摄像头显示线程
            self.start_camera_thread()
            
            status_text = "Camera started" if self.lang_config.current_language == 'en' else "摄像头已启动"
            self.status_var.set(status_text)
            
        except Exception as e:
            error_title = "Error" if self.lang_config.current_language == 'en' else "错误"
            error_msg = f"Camera startup failed: {str(e)}" if self.lang_config.current_language == 'en' else f"启动摄像头失败: {str(e)}"
            messagebox.showerror(error_title, error_msg)
    
    def stop_camera(self):
        """关闭摄像头"""
        self.camera_active = False
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.camera_btn.configure(text=self.lang_config.get_text('start_camera'))
        self.liveness_btn.configure(state=tk.DISABLED)
        self.reset_btn.configure(state=tk.DISABLED)
        
        status_text = "Camera stopped" if self.lang_config.current_language == 'en' else "摄像头已停止"
        self.status_var.set(status_text)
        
        # 清除摄像头显示
        self.camera_label.configure(image="", text="摄像头未启动")
        
        self.status_var.set("摄像头已关闭")
    
    def start_camera_thread(self):
        """启动摄像头显示线程"""
        def camera_loop():
            while self.camera_active and self.cap:
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame = frame.copy()
                    
                    # 如果正在进行活体检测，添加检测信息
                    if self.liveness_detector and self.liveness_result:
                        frame = self.liveness_detector.draw_liveness_info(frame, self.liveness_result)
                    
                    # 转换为RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # 调整大小
                    height, width = frame_rgb.shape[:2]
                    max_width, max_height = 600, 400
                    
                    if width > max_width or height > max_height:
                        scale = min(max_width/width, max_height/height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame_rgb = cv2.resize(frame_rgb, (new_width, new_height))
                    
                    # 转换为PhotoImage
                    image = Image.fromarray(frame_rgb)
                    photo = ImageTk.PhotoImage(image)
                    
                    # 更新显示
                    self.root.after(0, lambda p=photo: self.update_camera_display(p))
                    
                time.sleep(0.03)  # 约30fps
        
        threading.Thread(target=camera_loop, daemon=True).start()
    
    def update_camera_display(self, photo):
        """更新摄像头显示"""
        if self.camera_active:
            self.camera_label.configure(image=photo, text="")
            self.camera_label.image = photo
    
    def start_liveness_detection(self):
        """开始活体检测"""
        if not self.camera_active:
            messagebox.showwarning("警告", "请先启动摄像头")
            return
        
        try:
            # 初始化活体检测器
            self.liveness_detector = LivenessDetector()
            
            # 更新按钮状态
            self.liveness_btn.configure(state=tk.DISABLED)
            self.reset_btn.configure(state=tk.NORMAL)
            
            # 启动活体检测线程
            self.start_liveness_thread()
            
            self.status_var.set("活体检测进行中...")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动活体检测失败: {str(e)}")
    
    def start_liveness_thread(self):
        """启动活体检测线程"""
        def liveness_loop():
            while self.camera_active and self.liveness_detector:
                if self.current_frame is not None:
                    # 执行活体检测
                    result = self.liveness_detector.detect_liveness(self.current_frame)
                    self.liveness_result = result
                    
                    # 更新结果显示
                    self.root.after(0, lambda r=result: self.update_liveness_result(r))
                    
                    # 检测完成时停止
                    if result.status != LivenessStatus.PROCESSING:
                        self.root.after(0, lambda r=result: self.on_liveness_complete(r))
                        break
                
                time.sleep(0.1)
        
        self.liveness_thread = threading.Thread(target=liveness_loop, daemon=True)
        self.liveness_thread.start()
    
    def update_liveness_result(self, result):
        """更新活体检测结果显示"""
        try:
            result_text = f"活体检测状态: {result.status.value.upper()}\n"
            result_text += f"置信度: {result.confidence:.3f}\n"
            result_text += f"眨眼次数: {result.blink_count}\n"
            result_text += f"头部运动得分: {result.head_movement_score:.3f}\n"
            result_text += f"纹理得分: {result.texture_score:.3f}\n\n"
            
            if result.details:
                result_text += "详细信息:\n"
                for key, value in result.details.items():
                    if key != "error":
                        result_text += f"  {key}: {value}\n"
            
            if result.status == LivenessStatus.PROCESSING:
                elapsed = result.details.get("elapsed_time", 0)
                duration = result.details.get("detection_duration", 5)
                progress = min(elapsed / duration * 100, 100)
                result_text += f"\n检测进度: {progress:.0f}%"
            
            self.liveness_result_text.delete(1.0, tk.END)
            self.liveness_result_text.insert(1.0, result_text)
            
        except Exception as e:
            print(f"更新活体检测结果时出错: {e}")
    
    def on_liveness_complete(self, result):
        """活体检测完成回调"""
        try:
            # 更新按钮状态
            self.liveness_btn.configure(state=tk.NORMAL)
            self.save_liveness_btn.configure(state=tk.NORMAL)
            
            # 添加到历史记录
            status_text = result.status.value
            confidence = result.confidence
            details = f"眨眼:{result.blink_count}, 置信度:{confidence:.3f}"
            
            self.add_to_history('活体检测', status_text, confidence, details)
            
            # 显示完成消息
            if result.status == LivenessStatus.REAL:
                self.status_var.set("活体检测完成 - 真人")
                messagebox.showinfo("检测完成", f"活体检测完成！\n结果: 真人\n置信度: {confidence:.3f}")
            elif result.status == LivenessStatus.FAKE:
                self.status_var.set("活体检测完成 - 假人")
                messagebox.showwarning("检测完成", f"活体检测完成！\n结果: 假人/照片\n置信度: {confidence:.3f}")
            else:
                self.status_var.set("活体检测完成 - 未知")
                messagebox.showinfo("检测完成", f"活体检测完成！\n结果: 无法确定\n置信度: {confidence:.3f}")
            
        except Exception as e:
            print(f"活体检测完成回调时出错: {e}")
    
    def reset_liveness_detection(self):
        """重置活体检测"""
        if self.liveness_detector:
            self.liveness_detector.reset()
            self.liveness_result = None
            
            # 清除结果显示
            self.liveness_result_text.delete(1.0, tk.END)
            self.liveness_result_text.insert(1.0, "活体检测已重置，可以重新开始检测")
            
            # 更新按钮状态
            self.liveness_btn.configure(state=tk.NORMAL)
            self.reset_btn.configure(state=tk.DISABLED)
            self.save_liveness_btn.configure(state=tk.DISABLED)
            
            self.status_var.set("活体检测已重置")
    
    def save_liveness_results(self):
        """保存活体检测结果"""
        if not self.liveness_result:
            messagebox.showwarning("警告", "没有活体检测结果可保存")
            return
        
        try:
            # 选择保存位置
            file_path = filedialog.asksaveasfilename(
                title="保存活体检测结果",
                defaultextension=".json",
                filetypes=[('JSON文件', '*.json'), ('所有文件', '*.*')]
            )
            
            if file_path:
                # 准备保存数据
                save_data = {
                    'timestamp': datetime.now().isoformat(),
                    'detection_type': 'liveness_detection',
                    'status': self.liveness_result.status.value,
                    'confidence': self.liveness_result.confidence,
                    'blink_count': self.liveness_result.blink_count,
                    'head_movement_score': self.liveness_result.head_movement_score,
                    'texture_score': self.liveness_result.texture_score,
                    'details': self.liveness_result.details,
                    'detection_timestamp': self.liveness_result.timestamp
                }
                
                # 保存到文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("成功", f"活体检测结果已保存到: {file_path}")
                self.status_var.set(f"活体结果已保存: {Path(file_path).name}")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def add_to_history(self, detection_type, result, confidence, details):
        """添加记录到历史"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            confidence_str = f"{confidence:.3f}" if isinstance(confidence, (int, float)) else str(confidence)
            
            self.history_tree.insert('', 0, values=(
                timestamp,
                detection_type,
                result,
                confidence_str,
                details
            ))
            
        except Exception as e:
            print(f"添加历史记录时出错: {e}")
    
    def clear_history(self):
        """清除历史记录"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        self.status_var.set("历史记录已清除")
    
    def on_closing(self):
        """应用关闭时的清理工作"""
        try:
            # 停止摄像头
            if self.camera_active:
                self.stop_camera()
            
            # 等待线程结束
            if self.liveness_thread and self.liveness_thread.is_alive():
                self.camera_active = False
                self.liveness_thread.join(timeout=1)
            
            # 释放资源
            cv2.destroyAllWindows()
            
        except Exception as e:
            print(f"关闭应用时出错: {e}")
        finally:
            self.root.destroy()

def main():
    """主函数"""
    try:
        # 检查依赖
        import mediapipe
        print(f"MediaPipe版本: {mediapipe.__version__}")
        
        # 创建并运行GUI
        root = tk.Tk()
        app = FaceDetectionWithLivenessGUI(root)
        root.mainloop()
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保安装了所有必需的依赖包")
    except Exception as e:
        print(f"应用启动失败: {e}")

if __name__ == "__main__":
    main()