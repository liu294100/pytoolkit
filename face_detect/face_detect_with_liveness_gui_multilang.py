#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Face Detection and Liveness Detection Integrated GUI Application
Combines static image face detection and real-time liveness detection
Supports English/Chinese language switching
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import threading
import time
from pathlib import Path
import json
from datetime import datetime

# Import custom modules
try:
    from detect import main as detect_faces
    from resp_entity import ImageStatus
    from liveness_detection import LivenessDetector, LivenessStatus
except ImportError as e:
    print(f"Module import failed: {e}")
    print("Please ensure all dependency modules are in the same directory")

class LanguageManager:
    """Language management class"""
    
    def __init__(self):
        self.current_language = 'en'  # Default to English
        self.texts = {
            'en': {
                'title': 'Face Detection and Liveness Detection System',
                'static_tab': 'Static Image Detection',
                'liveness_tab': 'Liveness Detection',
                'comparison_tab': 'Result Comparison',
                'control_panel': 'Control Panel',
                'select_image': 'Select Image',
                'start_detection': 'Start Detection',
                'save_results': 'Save Results',
                'image_info': 'Image Information',
                'detection_results': 'Detection Results',
                'image_preview': 'Image Preview',
                'please_select_image': 'Please select an image',
                'liveness_control': 'Liveness Detection Control',
                'start_camera': 'Start Camera',
                'stop_camera': 'Stop Camera',
                'start_liveness': 'Start Liveness Detection',
                'reset_detection': 'Reset Detection',
                'save_liveness_results': 'Save Liveness Results',
                'detection_instructions': 'Detection Instructions',
                'liveness_results': 'Liveness Detection Results',
                'camera_preview': 'Camera Preview',
                'camera_not_started': 'Camera not started',
                'function_comparison': 'Function Comparison',
                'detection_history': 'Detection History',
                'clear_history': 'Clear History',
                'ready': 'Ready',
                'language': 'Language',
                'english': 'English',
                'chinese': '中文',
                'instructions_text': (
                    "Liveness Detection Steps:\n\n"
                    "1. Click 'Start Camera'\n"
                    "2. Click 'Start Liveness Detection'\n"
                    "3. Complete the following actions within 5 seconds:\n"
                    "   • Blink 3 times\n"
                    "   • Slightly turn your head\n"
                    "4. Wait for detection results\n\n"
                    "Note: Keep your face within the\n"
                    "camera view with sufficient lighting"
                ),
                'comparison_text': (
                    "Static Image Detection vs Liveness Detection\n\n"
                    "Static Image Detection:\n"
                    "• Detect faces in uploaded images\n"
                    "• Mark face positions and confidence\n"
                    "• Support multi-face detection\n"
                    "• Suitable for photo analysis\n\n"
                    "Liveness Detection:\n"
                    "• Real-time camera detection\n"
                    "• Verify if it's a real person\n"
                    "• Prevent photo spoofing\n"
                    "• Suitable for identity verification\n\n"
                    "Recommendation: Combine both detection methods for better security"
                ),
                'file_path': 'File Path',
                'file_size': 'File Size',
                'image_size': 'Image Size',
                'image_mode': 'Image Mode',
                'image_format': 'Image Format',
                'detection_complete': 'Detection Complete!',
                'faces_detected': 'Faces Detected',
                'face': 'Face',
                'position': 'Position',
                'size': 'Size',
                'confidence': 'Confidence',
                'time': 'Time',
                'type': 'Type',
                'result': 'Result',
                'details': 'Details',
                'static_detection': 'Static Detection',
                'success': 'Success',
                'failed': 'Failed',
                'warning': 'Warning',
                'error': 'Error',
                'please_select_image_first': 'Please select an image first',
                'detecting_faces': 'Detecting faces...',
                'detection_failed': 'Face detection failed',
                'no_results_to_save': 'No detection results to save',
                'save_detection_results': 'Save Detection Results',
                'results_saved_to': 'Results saved to',
                'save_failed': 'Save failed',
                'cannot_open_camera': 'Cannot open camera',
                'camera_start_failed': 'Camera start failed',
                'camera_started': 'Camera started',
                'camera_stopped': 'Camera stopped',
                'liveness_detection_started': 'Liveness detection started',
                'liveness_detection_stopped': 'Liveness detection stopped',
                'liveness_detection_reset': 'Liveness detection reset',
                'image_files': 'Image Files',
                'jpeg_files': 'JPEG Files',
                'png_files': 'PNG Files',
                'all_files': 'All Files',
                'select_image_file': 'Select Image File',
                'image_loaded': 'Image loaded',
                'load_image_failed': 'Load image failed',
                'json_files': 'JSON Files'
            },
            'zh': {
                'title': '人脸检测与活体检测系统',
                'static_tab': '静态图片检测',
                'liveness_tab': '活体检测',
                'comparison_tab': '结果对比',
                'control_panel': '控制面板',
                'select_image': '选择图片',
                'start_detection': '开始检测',
                'save_results': '保存结果',
                'image_info': '图片信息',
                'detection_results': '检测结果',
                'image_preview': '图片预览',
                'please_select_image': '请选择图片',
                'liveness_control': '活体检测控制',
                'start_camera': '启动摄像头',
                'stop_camera': '关闭摄像头',
                'start_liveness': '开始活体检测',
                'reset_detection': '重置检测',
                'save_liveness_results': '保存活体结果',
                'detection_instructions': '检测说明',
                'liveness_results': '活体检测结果',
                'camera_preview': '摄像头预览',
                'camera_not_started': '摄像头未启动',
                'function_comparison': '功能对比',
                'detection_history': '检测历史',
                'clear_history': '清除历史',
                'ready': '就绪',
                'language': '语言',
                'english': 'English',
                'chinese': '中文',
                'instructions_text': (
                    "活体检测步骤：\n\n"
                    "1. 点击'启动摄像头'\n"
                    "2. 点击'开始活体检测'\n"
                    "3. 在5秒内完成以下动作：\n"
                    "   • 眨眼3次\n"
                    "   • 轻微转动头部\n"
                    "4. 等待检测结果\n\n"
                    "注意：保持面部在摄像头\n"
                    "视野内，光线充足"
                ),
                'comparison_text': (
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
                ),
                'file_path': '文件路径',
                'file_size': '文件大小',
                'image_size': '图片尺寸',
                'image_mode': '图片模式',
                'image_format': '图片格式',
                'detection_complete': '检测完成！',
                'faces_detected': '检测到人脸数量',
                'face': '人脸',
                'position': '位置',
                'size': '大小',
                'confidence': '置信度',
                'time': '时间',
                'type': '类型',
                'result': '结果',
                'details': '详情',
                'static_detection': '静态检测',
                'success': '成功',
                'failed': '失败',
                'warning': '警告',
                'error': '错误',
                'please_select_image_first': '请先选择图片',
                'detecting_faces': '正在检测人脸...',
                'detection_failed': '人脸检测失败',
                'no_results_to_save': '没有检测结果可保存',
                'save_detection_results': '保存检测结果',
                'results_saved_to': '结果已保存到',
                'save_failed': '保存失败',
                'cannot_open_camera': '无法打开摄像头',
                'camera_start_failed': '启动摄像头失败',
                'camera_started': '摄像头已启动',
                'camera_stopped': '摄像头已关闭',
                'liveness_detection_started': '活体检测已开始',
                'liveness_detection_stopped': '活体检测已停止',
                'liveness_detection_reset': '活体检测已重置',
                'image_files': '图片文件',
                'jpeg_files': 'JPEG文件',
                'png_files': 'PNG文件',
                'all_files': '所有文件',
                'select_image_file': '选择图片文件',
                'image_loaded': '已加载图片',
                'load_image_failed': '加载图片失败',
                'json_files': 'JSON文件'
            }
        }
    
    def get_text(self, key):
        """Get text in current language"""
        return self.texts.get(self.current_language, {}).get(key, key)
    
    def set_language(self, language):
        """Set current language"""
        if language in self.texts:
            self.current_language = language

class FaceDetectionWithLivenessGUI:
    """Face Detection and Liveness Detection Integrated GUI"""
    
    def __init__(self, root):
        self.root = root
        self.lang_manager = LanguageManager()
        
        # Initialize window
        self.root.title(self.lang_manager.get_text('title'))
        self.root.geometry("1200x800")
        
        # Application state
        self.current_image = None
        self.current_image_path = None
        self.detection_results = None
        
        # Liveness detection related
        self.liveness_detector = None
        self.camera_active = False
        self.cap = None
        self.liveness_thread = None
        self.current_frame = None
        self.liveness_result = None
        
        # UI components references for language switching
        self.ui_components = {}
        
        # Create interface
        self.create_widgets()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """Create GUI components"""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Language selection frame
        lang_frame = ttk.Frame(main_frame)
        lang_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Language label and combobox
        lang_label = ttk.Label(lang_frame, text=self.lang_manager.get_text('language'))
        lang_label.grid(row=0, column=0, padx=(0, 5))
        self.ui_components['lang_label'] = lang_label
        
        self.lang_var = tk.StringVar(value=self.lang_manager.get_text('english'))
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var, 
                                 values=[self.lang_manager.get_text('english'), 
                                        self.lang_manager.get_text('chinese')],
                                 state="readonly", width=10)
        lang_combo.grid(row=0, column=1)
        lang_combo.bind('<<ComboboxSelected>>', self.on_language_change)
        self.ui_components['lang_combo'] = lang_combo
        
        # Create notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create tabs
        self.create_static_detection_tab()
        self.create_liveness_detection_tab()
        self.create_comparison_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value=self.lang_manager.get_text('ready'))
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.ui_components['status_bar'] = status_bar
    
    def on_language_change(self, event=None):
        """Handle language change"""
        selected = self.lang_var.get()
        if selected == self.lang_manager.get_text('english') or selected == 'English':
            self.lang_manager.set_language('en')
        else:
            self.lang_manager.set_language('zh')
        
        # Update all UI text
        self.update_ui_language()
    
    def update_ui_language(self):
        """Update all UI text to current language"""
        # Update window title
        self.root.title(self.lang_manager.get_text('title'))
        
        # Update language combo values
        self.ui_components['lang_combo']['values'] = [
            self.lang_manager.get_text('english'),
            self.lang_manager.get_text('chinese')
        ]
        
        # Update language label
        self.ui_components['lang_label'].config(text=self.lang_manager.get_text('language'))
        
        # Update notebook tabs
        self.notebook.tab(0, text=self.lang_manager.get_text('static_tab'))
        self.notebook.tab(1, text=self.lang_manager.get_text('liveness_tab'))
        self.notebook.tab(2, text=self.lang_manager.get_text('comparison_tab'))
        
        # Update static detection tab
        self.update_static_tab_language()
        
        # Update liveness detection tab
        self.update_liveness_tab_language()
        
        # Update comparison tab
        self.update_comparison_tab_language()
        
        # Update status
        self.status_var.set(self.lang_manager.get_text('ready'))
    
    def create_static_detection_tab(self):
        """Create static image detection tab"""
        static_frame = ttk.Frame(self.notebook)
        self.notebook.add(static_frame, text=self.lang_manager.get_text('static_tab'))
        self.ui_components['static_frame'] = static_frame
        
        # Left control panel
        control_frame = ttk.LabelFrame(static_frame, text=self.lang_manager.get_text('control_panel'), padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        self.ui_components['control_frame'] = control_frame
        
        # Image selection
        select_btn = ttk.Button(control_frame, text=self.lang_manager.get_text('select_image'), command=self.select_image)
        select_btn.grid(row=0, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_components['select_btn'] = select_btn
        
        # Detection button
        self.detect_btn = ttk.Button(control_frame, text=self.lang_manager.get_text('start_detection'), 
                                   command=self.detect_faces_static, state=tk.DISABLED)
        self.detect_btn.grid(row=1, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_components['detect_btn'] = self.detect_btn
        
        # Save results button
        self.save_btn = ttk.Button(control_frame, text=self.lang_manager.get_text('save_results'), 
                                 command=self.save_results, state=tk.DISABLED)
        self.save_btn.grid(row=2, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_components['save_btn'] = self.save_btn
        
        # Image information
        info_frame = ttk.LabelFrame(control_frame, text=self.lang_manager.get_text('image_info'), padding="5")
        info_frame.grid(row=3, column=0, pady=10, sticky=tk.W+tk.E)
        self.ui_components['info_frame'] = info_frame
        
        self.image_info = tk.Text(info_frame, height=8, width=30)
        self.image_info.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Detection results
        result_frame = ttk.LabelFrame(control_frame, text=self.lang_manager.get_text('detection_results'), padding="5")
        result_frame.grid(row=4, column=0, pady=10, sticky=tk.W+tk.E)
        self.ui_components['result_frame'] = result_frame
        
        self.result_text = tk.Text(result_frame, height=10, width=30)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right image display area
        image_frame = ttk.LabelFrame(static_frame, text=self.lang_manager.get_text('image_preview'), padding="10")
        image_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.ui_components['image_frame'] = image_frame
        
        self.image_label = ttk.Label(image_frame, text=self.lang_manager.get_text('please_select_image'))
        self.image_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.ui_components['image_label'] = self.image_label
        
        # Configure grid weights
        static_frame.columnconfigure(1, weight=1)
        static_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
    
    def update_static_tab_language(self):
        """Update static detection tab language"""
        self.ui_components['control_frame'].config(text=self.lang_manager.get_text('control_panel'))
        self.ui_components['select_btn'].config(text=self.lang_manager.get_text('select_image'))
        self.ui_components['detect_btn'].config(text=self.lang_manager.get_text('start_detection'))
        self.ui_components['save_btn'].config(text=self.lang_manager.get_text('save_results'))
        self.ui_components['info_frame'].config(text=self.lang_manager.get_text('image_info'))
        self.ui_components['result_frame'].config(text=self.lang_manager.get_text('detection_results'))
        self.ui_components['image_frame'].config(text=self.lang_manager.get_text('image_preview'))
        
        # Update image label if no image is loaded
        if not self.current_image:
            self.ui_components['image_label'].config(text=self.lang_manager.get_text('please_select_image'))
    
    def create_liveness_detection_tab(self):
        """Create liveness detection tab"""
        liveness_frame = ttk.Frame(self.notebook)
        self.notebook.add(liveness_frame, text=self.lang_manager.get_text('liveness_tab'))
        self.ui_components['liveness_frame'] = liveness_frame
        
        # Left control panel
        liveness_control_frame = ttk.LabelFrame(liveness_frame, text=self.lang_manager.get_text('liveness_control'), padding="10")
        liveness_control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        self.ui_components['liveness_control_frame'] = liveness_control_frame
        
        # Camera control
        self.camera_btn = ttk.Button(liveness_control_frame, text=self.lang_manager.get_text('start_camera'), command=self.toggle_camera)
        self.camera_btn.grid(row=0, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_components['camera_btn'] = self.camera_btn
        
        # Start liveness detection
        self.liveness_btn = ttk.Button(liveness_control_frame, text=self.lang_manager.get_text('start_liveness'), 
                                     command=self.start_liveness_detection, state=tk.DISABLED)
        self.liveness_btn.grid(row=1, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_components['liveness_btn'] = self.liveness_btn
        
        # Reset detection
        self.reset_btn = ttk.Button(liveness_control_frame, text=self.lang_manager.get_text('reset_detection'), 
                                  command=self.reset_liveness_detection, state=tk.DISABLED)
        self.reset_btn.grid(row=2, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_components['reset_btn'] = self.reset_btn
        
        # Save liveness results
        self.save_liveness_btn = ttk.Button(liveness_control_frame, text=self.lang_manager.get_text('save_liveness_results'), 
                                          command=self.save_liveness_results, state=tk.DISABLED)
        self.save_liveness_btn.grid(row=3, column=0, pady=5, sticky=tk.W+tk.E)
        self.ui_components['save_liveness_btn'] = self.save_liveness_btn
        
        # Detection instructions
        instruction_frame = ttk.LabelFrame(liveness_control_frame, text=self.lang_manager.get_text('detection_instructions'), padding="5")
        instruction_frame.grid(row=4, column=0, pady=10, sticky=tk.W+tk.E)
        self.ui_components['instruction_frame'] = instruction_frame
        
        self.instruction_label = ttk.Label(instruction_frame, text=self.lang_manager.get_text('instructions_text'), justify=tk.LEFT)
        self.instruction_label.grid(row=0, column=0, sticky=tk.W)
        self.ui_components['instruction_label'] = self.instruction_label
        
        # Liveness detection results
        liveness_result_frame = ttk.LabelFrame(liveness_control_frame, text=self.lang_manager.get_text('liveness_results'), padding="5")
        liveness_result_frame.grid(row=5, column=0, pady=10, sticky=tk.W+tk.E)
        self.ui_components['liveness_result_frame'] = liveness_result_frame
        
        self.liveness_result_text = tk.Text(liveness_result_frame, height=8, width=30)
        self.liveness_result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right camera display area
        camera_frame = ttk.LabelFrame(liveness_frame, text=self.lang_manager.get_text('camera_preview'), padding="10")
        camera_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.ui_components['camera_frame'] = camera_frame
        
        self.camera_label = ttk.Label(camera_frame, text=self.lang_manager.get_text('camera_not_started'))
        self.camera_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.ui_components['camera_label'] = self.camera_label
        
        # Configure grid weights
        liveness_frame.columnconfigure(1, weight=1)
        liveness_frame.rowconfigure(0, weight=1)
        camera_frame.columnconfigure(0, weight=1)
        camera_frame.rowconfigure(0, weight=1)
    
    def update_liveness_tab_language(self):
        """Update liveness detection tab language"""
        self.ui_components['liveness_control_frame'].config(text=self.lang_manager.get_text('liveness_control'))
        
        # Update camera button text based on current state
        if self.camera_active:
            self.ui_components['camera_btn'].config(text=self.lang_manager.get_text('stop_camera'))
        else:
            self.ui_components['camera_btn'].config(text=self.lang_manager.get_text('start_camera'))
        
        self.ui_components['liveness_btn'].config(text=self.lang_manager.get_text('start_liveness'))
        self.ui_components['reset_btn'].config(text=self.lang_manager.get_text('reset_detection'))
        self.ui_components['save_liveness_btn'].config(text=self.lang_manager.get_text('save_liveness_results'))
        self.ui_components['instruction_frame'].config(text=self.lang_manager.get_text('detection_instructions'))
        self.ui_components['instruction_label'].config(text=self.lang_manager.get_text('instructions_text'))
        self.ui_components['liveness_result_frame'].config(text=self.lang_manager.get_text('liveness_results'))
        self.ui_components['camera_frame'].config(text=self.lang_manager.get_text('camera_preview'))
        
        # Update camera label if camera is not started
        if not self.camera_active:
            self.ui_components['camera_label'].config(text=self.lang_manager.get_text('camera_not_started'))
    
    def create_comparison_tab(self):
        """Create result comparison tab"""
        comparison_frame = ttk.Frame(self.notebook)
        self.notebook.add(comparison_frame, text=self.lang_manager.get_text('comparison_tab'))
        self.ui_components['comparison_frame'] = comparison_frame
        
        # Comparison instructions
        instruction_frame = ttk.LabelFrame(comparison_frame, text=self.lang_manager.get_text('function_comparison'), padding="10")
        instruction_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.ui_components['comparison_instruction_frame'] = instruction_frame
        
        self.comparison_label = ttk.Label(instruction_frame, text=self.lang_manager.get_text('comparison_text'), justify=tk.LEFT)
        self.comparison_label.grid(row=0, column=0, sticky=tk.W)
        self.ui_components['comparison_label'] = self.comparison_label
        
        # History records
        history_frame = ttk.LabelFrame(comparison_frame, text=self.lang_manager.get_text('detection_history'), padding="10")
        history_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.ui_components['history_frame'] = history_frame
        
        # Create table for history records
        self.history_columns = (
            self.lang_manager.get_text('time'), 
            self.lang_manager.get_text('type'), 
            self.lang_manager.get_text('result'), 
            self.lang_manager.get_text('confidence'), 
            self.lang_manager.get_text('details')
        )
        self.history_tree = ttk.Treeview(history_frame, columns=self.history_columns, show='headings', height=15)
        
        for col in self.history_columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=120)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Clear history button
        clear_history_btn = ttk.Button(history_frame, text=self.lang_manager.get_text('clear_history'), command=self.clear_history)
        clear_history_btn.grid(row=1, column=0, pady=5, sticky=tk.W)
        self.ui_components['clear_history_btn'] = clear_history_btn
        
        # Configure grid weights
        comparison_frame.columnconfigure(0, weight=1)
        comparison_frame.rowconfigure(1, weight=1)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
    
    def update_comparison_tab_language(self):
        """Update comparison tab language"""
        self.ui_components['comparison_instruction_frame'].config(text=self.lang_manager.get_text('function_comparison'))
        self.ui_components['comparison_label'].config(text=self.lang_manager.get_text('comparison_text'))
        self.ui_components['history_frame'].config(text=self.lang_manager.get_text('detection_history'))
        self.ui_components['clear_history_btn'].config(text=self.lang_manager.get_text('clear_history'))
        
        # Update history tree column headers
        new_columns = (
            self.lang_manager.get_text('time'), 
            self.lang_manager.get_text('type'), 
            self.lang_manager.get_text('result'), 
            self.lang_manager.get_text('confidence'), 
            self.lang_manager.get_text('details')
        )
        
        for i, col in enumerate(new_columns):
            self.history_tree.heading(f'#{i+1}', text=col)
    
    def select_image(self):
        """Select image file"""
        file_types = [
            (self.lang_manager.get_text('image_files'), '*.jpg *.jpeg *.png *.bmp *.tiff *.webp'),
            (self.lang_manager.get_text('jpeg_files'), '*.jpg *.jpeg'),
            (self.lang_manager.get_text('png_files'), '*.png'),
            (self.lang_manager.get_text('all_files'), '*.*')
        ]
        
        file_path = filedialog.askopenfilename(
            title=self.lang_manager.get_text('select_image_file'),
            filetypes=file_types
        )
        
        if file_path:
            self.load_image(file_path)
    
    def load_image(self, file_path):
        """Load and display image"""
        try:
            self.current_image_path = file_path
            
            # Load image using PIL
            pil_image = Image.open(file_path)
            self.current_image = pil_image.copy()
            
            # Resize image for display
            display_image = self.resize_image_for_display(pil_image, max_size=(600, 400))
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(display_image)
            self.image_label.configure(image=photo, text="")
            self.image_label.image = photo  # Keep reference
            
            # Show image information
            self.show_image_info(pil_image, file_path)
            
            # Enable detection button
            self.detect_btn.configure(state=tk.NORMAL)
            
            self.status_var.set(f"{self.lang_manager.get_text('image_loaded')}: {Path(file_path).name}")
            
        except Exception as e:
            messagebox.showerror(self.lang_manager.get_text('error'), 
                               f"{self.lang_manager.get_text('load_image_failed')}: {str(e)}")
            self.status_var.set(self.lang_manager.get_text('load_image_failed'))
    
    def resize_image_for_display(self, image, max_size):
        """Resize image for display"""
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    
    def show_image_info(self, image, file_path):
        """Show image information"""
        file_size = Path(file_path).stat().st_size
        
        info = f"{self.lang_manager.get_text('file_path')}: {file_path}\n"
        info += f"{self.lang_manager.get_text('file_size')}: {file_size / 1024:.1f} KB\n"
        info += f"{self.lang_manager.get_text('image_size')}: {image.size[0]} x {image.size[1]}\n"
        info += f"{self.lang_manager.get_text('image_mode')}: {image.mode}\n"
        info += f"{self.lang_manager.get_text('image_format')}: {image.format}\n"
        
        self.image_info.delete(1.0, tk.END)
        self.image_info.insert(1.0, info)
    
    def detect_faces_static(self):
        """Execute static image face detection"""
        if not self.current_image_path:
            messagebox.showwarning(self.lang_manager.get_text('warning'), 
                                 self.lang_manager.get_text('please_select_image_first'))
            return
        
        try:
            self.status_var.set(self.lang_manager.get_text('detecting_faces'))
            self.detect_btn.configure(state=tk.DISABLED)
            
            # Execute detection in new thread
            def detect_thread():
                try:
                    # Call detection function
                    result = detect_faces(self.current_image_path)
                    
                    # Update UI in main thread
                    self.root.after(0, lambda: self.on_detection_complete(result))
                    
                except Exception as e:
                    self.root.after(0, lambda: self.on_detection_error(str(e)))
            
            threading.Thread(target=detect_thread, daemon=True).start()
            
        except Exception as e:
            self.on_detection_error(str(e))
    
    def on_detection_complete(self, result):
        """Detection complete callback"""
        try:
            self.detection_results = result
            
            # Show detection results
            if isinstance(result, ImageStatus):
                result_text = f"{self.lang_manager.get_text('detection_complete')}\n\n"
                result_text += f"{self.lang_manager.get_text('faces_detected')}: {len(result.faces)}\n\n"
                
                for i, face in enumerate(result.faces, 1):
                    result_text += f"{self.lang_manager.get_text('face')} {i}:\n"
                    result_text += f"  {self.lang_manager.get_text('position')}: ({face.x}, {face.y})\n"
                    result_text += f"  {self.lang_manager.get_text('size')}: {face.width} x {face.height}\n"
                    result_text += f"  {self.lang_manager.get_text('confidence')}: {face.confidence:.3f}\n\n"
                
                # Load and display annotated image
                if result.output_path and Path(result.output_path).exists():
                    annotated_image = Image.open(result.output_path)
                    display_image = self.resize_image_for_display(annotated_image, max_size=(600, 400))
                    photo = ImageTk.PhotoImage(display_image)
                    self.image_label.configure(image=photo)
                    self.image_label.image = photo
            else:
                result_text = f"{self.lang_manager.get_text('result')}: {str(result)}"
            
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, result_text)
            
            # Add to history
            self.add_to_history(self.lang_manager.get_text('static_detection'), 
                              self.lang_manager.get_text('success'), 
                              len(result.faces) if hasattr(result, 'faces') else 0, 
                              self.lang_manager.get_text('details'))
            
            # Enable save button
            self.save_btn.configure(state=tk.NORMAL)
            self.detect_btn.configure(state=tk.NORMAL)
            
            self.status_var.set(self.lang_manager.get_text('detection_complete'))
            
        except Exception as e:
            self.on_detection_error(str(e))
    
    def on_detection_error(self, error_msg):
        """Detection error callback"""
        messagebox.showerror(self.lang_manager.get_text('error'), 
                           f"{self.lang_manager.get_text('detection_failed')}: {error_msg}")
        self.detect_btn.configure(state=tk.NORMAL)
        self.status_var.set(self.lang_manager.get_text('detection_failed'))
        
        # Add to history
        self.add_to_history(self.lang_manager.get_text('static_detection'), 
                          self.lang_manager.get_text('failed'), 0, error_msg)
    
    def save_results(self):
        """Save detection results"""
        if not self.detection_results:
            messagebox.showwarning(self.lang_manager.get_text('warning'), 
                                 self.lang_manager.get_text('no_results_to_save'))
            return
        
        try:
            # Select save location
            file_path = filedialog.asksaveasfilename(
                title=self.lang_manager.get_text('save_detection_results'),
                defaultextension=".json",
                filetypes=[(self.lang_manager.get_text('json_files'), '*.json'), 
                          (self.lang_manager.get_text('all_files'), '*.*')]
            )
            
            if file_path:
                # Prepare save data
                save_data = {
                    'timestamp': datetime.now().isoformat(),
                    'source_image': self.current_image_path,
                    'detection_type': 'static_face_detection',
                    'results': self.detection_results.__dict__ if hasattr(self.detection_results, '__dict__') else str(self.detection_results)
                }
                
                # Save to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo(self.lang_manager.get_text('success'), 
                                   f"{self.lang_manager.get_text('results_saved_to')}: {file_path}")
                self.status_var.set(f"{self.lang_manager.get_text('results_saved_to')}: {Path(file_path).name}")
                
        except Exception as e:
            messagebox.showerror(self.lang_manager.get_text('error'), 
                               f"{self.lang_manager.get_text('save_failed')}: {str(e)}")
    
    def toggle_camera(self):
        """Toggle camera state"""
        if not self.camera_active:
            self.start_camera()
        else:
            self.stop_camera()
    
    def start_camera(self):
        """Start camera"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror(self.lang_manager.get_text('error'), 
                                    self.lang_manager.get_text('cannot_open_camera'))
                return
            
            self.camera_active = True
            self.camera_btn.configure(text=self.lang_manager.get_text('stop_camera'))
            self.liveness_btn.configure(state=tk.NORMAL)
            
            # Start camera display thread
            self.start_camera_thread()
            
            self.status_var.set(self.lang_manager.get_text('camera_started'))
            
        except Exception as e:
            messagebox.showerror(self.lang_manager.get_text('error'), 
                               f"{self.lang_manager.get_text('camera_start_failed')}: {str(e)}")
    
    def stop_camera(self):
        """Stop camera"""
        self.camera_active = False
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.camera_btn.configure(text=self.lang_manager.get_text('start_camera'))
        self.liveness_btn.configure(state=tk.DISABLED)
        self.reset_btn.configure(state=tk.DISABLED)
        
        # Clear camera display
        self.camera_label.configure(image="", text=self.lang_manager.get_text('camera_not_started'))
        
        self.status_var.set(self.lang_manager.get_text('camera_stopped'))
    
    def start_camera_thread(self):
        """Start camera display thread"""
        def camera_loop():
            while self.camera_active and self.cap:
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame = frame.copy()
                    
                    # If liveness detection is running, add detection info
                    if self.liveness_detector and self.liveness_result:
                        try:
                            frame = self.liveness_detector.draw_liveness_info(frame, self.liveness_result)
                        except Exception as e:
                            print(f"Error drawing liveness info: {e}")
                    
                    # Convert to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Resize
                    height, width = frame_rgb.shape[:2]
                    max_width, max_height = 600, 400
                    
                    if width > max_width or height > max_height:
                        scale = min(max_width/width, max_height/height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame_rgb = cv2.resize(frame_rgb, (new_width, new_height))
                    
                    # Convert to PhotoImage
                    image = Image.fromarray(frame_rgb)
                    photo = ImageTk.PhotoImage(image)
                    
                    # Update UI in main thread
                    self.root.after(0, lambda p=photo: self.update_camera_display(p))
                
                time.sleep(0.03)  # ~30 FPS
        
        threading.Thread(target=camera_loop, daemon=True).start()
    
    def update_camera_display(self, photo):
        """Update camera display"""
        if self.camera_active:
            self.camera_label.configure(image=photo, text="")
            self.camera_label.image = photo
    
    def start_liveness_detection(self):
        """Start liveness detection"""
        if not self.camera_active:
            messagebox.showwarning(self.lang_manager.get_text('warning'), 
                                 self.lang_manager.get_text('camera_not_started'))
            return
        
        try:
            # Initialize liveness detector
            if not self.liveness_detector:
                self.liveness_detector = LivenessDetector()
            
            # Reset detector state for new detection
            self.liveness_detector.reset()
            
            self.liveness_btn.configure(state=tk.DISABLED)
            self.reset_btn.configure(state=tk.NORMAL)
            
            # Start liveness detection in new thread
            def liveness_thread():
                try:
                    frames = []
                    start_time = time.time()
                    
                    # Collect frames for 5 seconds
                    while time.time() - start_time < 5.0 and self.camera_active:
                        if self.current_frame is not None:
                            frames.append(self.current_frame.copy())
                        time.sleep(0.1)
                    
                    if frames:
                        # Perform liveness detection on collected frames
                        # Process frames sequentially to accumulate detection data
                        final_result = None
                        for frame in frames:
                            result = self.liveness_detector.detect_liveness(frame)
                            final_result = result
                            # Don't reset detector between frames to accumulate blink counts
                        
                        self.liveness_result = final_result
                        
                        # Update UI in main thread
                        self.root.after(0, lambda: self.on_liveness_complete(result))
                    else:
                        self.root.after(0, lambda: self.on_liveness_error("No frames captured"))
                        
                except Exception as e:
                    self.root.after(0, lambda: self.on_liveness_error(str(e)))
            
            self.liveness_thread = threading.Thread(target=liveness_thread, daemon=True)
            self.liveness_thread.start()
            
            self.status_var.set(self.lang_manager.get_text('liveness_detection_started'))
            
        except Exception as e:
            messagebox.showerror(self.lang_manager.get_text('error'), 
                               f"{self.lang_manager.get_text('liveness_detection_started')}: {str(e)}")
    
    def on_liveness_complete(self, result):
        """Liveness detection complete callback"""
        try:
            # Display liveness results
            result_text = f"Liveness Detection Results:\n\n"
            result_text += f"Status: {result.status.value}\n"
            result_text += f"Confidence: {result.confidence:.3f}\n"
            result_text += f"Blink Count: {result.blink_count}\n"
            result_text += f"Head Movement Score: {result.head_movement_score:.3f}\n"
            result_text += f"Texture Score: {result.texture_score:.3f}\n"
            
            if result.details:
                result_text += f"\nDetails:\n"
                for key, value in result.details.items():
                    result_text += f"  {key}: {value}\n"
            
            self.liveness_result_text.delete(1.0, tk.END)
            self.liveness_result_text.insert(1.0, result_text)
            
            # Add to history
            self.add_to_history('Liveness Detection', result.status.value, 
                              result.confidence, f"Blinks: {result.blink_count}")
            
            # Enable save button
            self.save_liveness_btn.configure(state=tk.NORMAL)
            self.liveness_btn.configure(state=tk.NORMAL)
            
            self.status_var.set("Liveness detection complete")
            
        except Exception as e:
            self.on_liveness_error(str(e))
    
    def on_liveness_error(self, error_msg):
        """Liveness detection error callback"""
        messagebox.showerror(self.lang_manager.get_text('error'), 
                           f"Liveness detection failed: {error_msg}")
        self.liveness_btn.configure(state=tk.NORMAL)
        self.status_var.set("Liveness detection failed")
        
        # Add to history
        self.add_to_history('Liveness Detection', self.lang_manager.get_text('failed'), 0, error_msg)
    
    def reset_liveness_detection(self):
        """Reset liveness detection"""
        self.liveness_result = None
        self.liveness_result_text.delete(1.0, tk.END)
        self.save_liveness_btn.configure(state=tk.DISABLED)
        self.reset_btn.configure(state=tk.DISABLED)
        self.liveness_btn.configure(state=tk.NORMAL)
        
        self.status_var.set(self.lang_manager.get_text('liveness_detection_reset'))
    
    def save_liveness_results(self):
        """Save liveness detection results"""
        if not self.liveness_result:
            messagebox.showwarning(self.lang_manager.get_text('warning'), 
                                 "No liveness detection results to save")
            return
        
        try:
            # Select save location
            file_path = filedialog.asksaveasfilename(
                title="Save Liveness Detection Results",
                defaultextension=".json",
                filetypes=[(self.lang_manager.get_text('json_files'), '*.json'), 
                          (self.lang_manager.get_text('all_files'), '*.*')]
            )
            
            if file_path:
                # Prepare save data
                save_data = {
                    'timestamp': datetime.now().isoformat(),
                    'detection_type': 'liveness_detection',
                    'results': {
                        'status': self.liveness_result.status.value,
                        'confidence': self.liveness_result.confidence,
                        'blink_count': self.liveness_result.blink_count,
                        'head_movement_score': self.liveness_result.head_movement_score,
                        'texture_score': self.liveness_result.texture_score,
                        'details': self.liveness_result.details,
                        'timestamp': self.liveness_result.timestamp
                    }
                }
                
                # Save to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo(self.lang_manager.get_text('success'), 
                                   f"{self.lang_manager.get_text('results_saved_to')}: {file_path}")
                self.status_var.set(f"{self.lang_manager.get_text('results_saved_to')}: {Path(file_path).name}")
                
        except Exception as e:
            messagebox.showerror(self.lang_manager.get_text('error'), 
                               f"{self.lang_manager.get_text('save_failed')}: {str(e)}")
    
    def add_to_history(self, detection_type, result, confidence, details):
        """Add detection result to history"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.history_tree.insert('', 0, values=(timestamp, detection_type, result, confidence, details))
    
    def clear_history(self):
        """Clear detection history"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
    
    def on_closing(self):
        """Handle window closing"""
        # Stop camera if active
        if self.camera_active:
            self.stop_camera()
        
        # Close window
        self.root.destroy()

def main():
    """Main function"""
    root = tk.Tk()
    app = FaceDetectionWithLivenessGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()