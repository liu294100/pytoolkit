import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import json
import os
import sys

# 尝试导入MediaPipe相关模块
try:
    from detect import main as detect_main
    MEDIAPIPE_AVAILABLE = True
except ImportError as e:
    MEDIAPIPE_AVAILABLE = False
    IMPORT_ERROR = str(e)

from resp_entity import ImageStatus


class FaceDetectGUILite:
    def __init__(self, root):
        self.root = root
        self.root.title("人脸检测工具 (轻量版)")
        self.root.geometry("1000x700")
        
        # 当前选择的图片路径
        self.current_image_path = None
        self.current_image = None
        
        self.setup_ui()
        
        # 检查MediaPipe可用性
        if not MEDIAPIPE_AVAILABLE:
            self.show_compatibility_warning()
    
    def show_compatibility_warning(self):
        """显示兼容性警告"""
        warning_msg = f"""⚠️ MediaPipe不可用

错误信息: {IMPORT_ERROR}

可能的原因：
1. Python版本不兼容（当前: {sys.version.split()[0]}）
2. MediaPipe未安装或安装失败

解决方案：
1. 使用Python 3.11或3.12
2. 安装MediaPipe: pip install mediapipe
3. 查看COMPATIBILITY.md获取详细说明

当前只能使用基础图片查看功能。"""
        
        messagebox.showwarning("兼容性警告", warning_msg)
    
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 左侧控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="10")
        control_frame.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 选择图片按钮
        ttk.Button(control_frame, text="选择图片", command=self.select_image).pack(pady=5, fill=tk.X)
        
        # 检测按钮
        self.detect_btn = ttk.Button(
            control_frame, 
            text="开始检测" if MEDIAPIPE_AVAILABLE else "检测不可用", 
            command=self.detect_face, 
            state=tk.DISABLED
        )
        self.detect_btn.pack(pady=5, fill=tk.X)
        
        # 兼容性信息按钮
        if not MEDIAPIPE_AVAILABLE:
            ttk.Button(
                control_frame, 
                text="查看兼容性说明", 
                command=self.show_compatibility_info
            ).pack(pady=5, fill=tk.X)
        
        # 分隔线
        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 系统信息
        info_frame = ttk.LabelFrame(control_frame, text="系统信息", padding="5")
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text=f"Python版本: {sys.version.split()[0]}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"MediaPipe: {'✅ 可用' if MEDIAPIPE_AVAILABLE else '❌ 不可用'}").pack(anchor=tk.W)
        
        try:
            import cv2
            ttk.Label(info_frame, text=f"OpenCV: ✅ {cv2.__version__}").pack(anchor=tk.W)
        except ImportError:
            ttk.Label(info_frame, text="OpenCV: ❌ 不可用").pack(anchor=tk.W)
        
        # 检测结果标签
        ttk.Label(control_frame, text="检测结果:", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(10, 0))
        
        # 结果显示区域
        result_frame = ttk.Frame(control_frame)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建滚动文本框显示结果
        self.result_text = tk.Text(result_frame, height=15, width=40, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右侧图片显示区域
        image_frame = ttk.LabelFrame(main_frame, text="图片预览", padding="10")
        image_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
        
        # 图片显示标签
        self.image_label = ttk.Label(image_frame, text="请选择图片", anchor=tk.CENTER)
        self.image_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)
        
        # 进度条
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 初始化结果显示
        if not MEDIAPIPE_AVAILABLE:
            self.result_text.insert(tk.END, "⚠️ MediaPipe不可用\n\n")
            self.result_text.insert(tk.END, "当前只能使用图片查看功能。\n\n")
            self.result_text.insert(tk.END, "要启用人脸检测功能，请：\n")
            self.result_text.insert(tk.END, "1. 使用Python 3.11或3.12\n")
            self.result_text.insert(tk.END, "2. 安装MediaPipe\n")
            self.result_text.insert(tk.END, "3. 查看COMPATIBILITY.md\n")
    
    def show_compatibility_info(self):
        """显示兼容性信息窗口"""
        info_window = tk.Toplevel(self.root)
        info_window.title("兼容性说明")
        info_window.geometry("600x500")
        info_window.transient(self.root)
        info_window.grab_set()
        
        # 创建滚动文本框
        text_frame = ttk.Frame(info_window, padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # 兼容性信息内容
        info_content = f"""Python版本兼容性说明
{'='*50}

当前环境：
- Python版本: {sys.version}
- MediaPipe状态: {'可用' if MEDIAPIPE_AVAILABLE else '不可用'}
- 错误信息: {IMPORT_ERROR if not MEDIAPIPE_AVAILABLE else '无'}

问题原因：
MediaPipe目前不支持Python 3.13，支持的版本为Python 3.8-3.12。

解决方案：

方案1：降级Python版本（推荐）
- 安装Python 3.11或3.12
- 重新安装依赖包

方案2：使用conda虚拟环境
conda create -n face_detect python=3.11
conda activate face_detect
pip install -r requirements.txt

方案3：使用pyenv（Linux/macOS）
pyenv install 3.11.0
pyenv local 3.11.0
pip install -r requirements.txt

安装验证：
安装完成后运行 test_gui.py 验证所有依赖是否正常。

更多信息：
请查看项目目录下的 COMPATIBILITY.md 文件获取详细说明。
"""
        
        text_widget.insert(tk.END, info_content)
        text_widget.config(state=tk.DISABLED)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 关闭按钮
        ttk.Button(info_window, text="关闭", command=info_window.destroy).pack(pady=10)
    
    def select_image(self):
        """选择图片文件"""
        file_types = [
            ('图片文件', '*.jpg *.jpeg *.png *.bmp *.tiff'),
            ('JPEG文件', '*.jpg *.jpeg'),
            ('PNG文件', '*.png'),
            ('所有文件', '*.*')
        ]
        
        file_path = filedialog.askopenfilename(
            title="选择图片文件",
            filetypes=file_types
        )
        
        if file_path:
            self.current_image_path = file_path
            self.load_and_display_image(file_path)
            
            if MEDIAPIPE_AVAILABLE:
                self.detect_btn.config(state=tk.NORMAL)
            
            self.status_label.config(text=f"已选择: {os.path.basename(file_path)}")
            
            # 显示图片基本信息
            self.show_image_info(file_path)
    
    def show_image_info(self, image_path):
        """显示图片基本信息"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                mode = img.mode
                format_name = img.format
            
            file_size = os.path.getsize(image_path) / 1024  # KB
            
            info_text = f"""图片信息：
{'='*20}
文件名: {os.path.basename(image_path)}
尺寸: {width} x {height}
颜色模式: {mode}
格式: {format_name}
文件大小: {file_size:.1f} KB

"""
            
            # 清空之前的结果并显示图片信息
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, info_text)
            
            if not MEDIAPIPE_AVAILABLE:
                self.result_text.insert(tk.END, "⚠️ 人脸检测功能不可用\n")
                self.result_text.insert(tk.END, "请查看兼容性说明解决依赖问题。\n")
            
        except Exception as e:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"读取图片信息失败: {str(e)}\n")
    
    def load_and_display_image(self, image_path):
        """加载并显示图片"""
        try:
            # 使用PIL加载图片
            pil_image = Image.open(image_path)
            
            # 计算缩放比例以适应显示区域
            display_width = 500
            display_height = 400
            
            # 保持宽高比缩放
            img_width, img_height = pil_image.size
            scale = min(display_width / img_width, display_height / img_height)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # 缩放图片
            resized_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 转换为tkinter可显示的格式
            self.current_image = ImageTk.PhotoImage(resized_image)
            
            # 显示图片
            self.image_label.config(image=self.current_image, text="")
            
        except Exception as e:
            messagebox.showerror("错误", f"无法加载图片: {str(e)}")
    
    def detect_face(self):
        """执行人脸检测"""
        if not MEDIAPIPE_AVAILABLE:
            messagebox.showerror("错误", "MediaPipe不可用，无法进行人脸检测。\n请查看兼容性说明解决依赖问题。")
            return
        
        if not self.current_image_path:
            messagebox.showwarning("警告", "请先选择图片")
            return
        
        try:
            # 显示进度条
            self.progress.start()
            self.status_label.config(text="正在检测...")
            self.detect_btn.config(state=tk.DISABLED)
            
            # 更新界面
            self.root.update()
            
            # 执行检测
            status, confidence = detect_main(self.current_image_path)
            
            # 停止进度条
            self.progress.stop()
            self.detect_btn.config(state=tk.NORMAL)
            
            # 显示结果
            self.display_results(status, confidence)
            
            # 更新状态
            if status.get('legal', False):
                self.status_label.config(text="检测完成 - 图片合规")
            else:
                self.status_label.config(text="检测完成 - 图片不合规")
                
        except Exception as e:
            self.progress.stop()
            self.detect_btn.config(state=tk.NORMAL)
            self.status_label.config(text="检测失败")
            messagebox.showerror("错误", f"检测过程中出现错误: {str(e)}")
    
    def display_results(self, status, confidence):
        """显示检测结果"""
        self.result_text.delete(1.0, tk.END)
        
        # 总体结果
        overall_result = "✅ 图片合规" if status.get('legal', False) else "❌ 图片不合规"
        self.result_text.insert(tk.END, f"总体结果: {overall_result}\n\n")
        
        # 详细检测项目
        checks = [
            ("人脸检测", "face_detect", "是否检测到人脸"),
            ("多人脸检测", "multiple_face", "是否检测到多张人脸"),
            ("亮度检测", "is_bright", "图片亮度是否合适"),
            ("模糊检测", "is_blur", "图片是否模糊"),
            ("完整度检测", "is_complete", "人脸是否完整"),
            ("墨镜检测", "has_sun_glass", "是否佩戴墨镜"),
            ("闭眼检测", "eye_close", "是否闭眼"),
            ("口罩检测", "has_mask", "是否佩戴口罩"),
            ("表情检测", "expression", "面部表情"),
            ("姿态检测", "pose", "头部姿态是否正确")
        ]
        
        self.result_text.insert(tk.END, "详细检测结果:\n")
        self.result_text.insert(tk.END, "-" * 30 + "\n")
        
        for name, key, desc in checks:
            value = status.get(key)
            if value is None:
                continue
                
            if key == "expression":
                # 表情特殊处理
                expr_map = {
                    "close": "闭嘴",
                    "smile": "微笑",
                    "laugh": "大笑",
                    "unknown": "未知"
                }
                result_text = f"{name}: {expr_map.get(value, value)}"
            elif key in ["multiple_face", "is_blur", "has_sun_glass", "eye_close", "has_mask"]:
                # 这些项目True表示有问题
                if value:
                    result_text = f"{name}: ❌ {desc}"
                else:
                    result_text = f"{name}: ✅ 正常"
            else:
                # 其他项目True表示正常
                if value:
                    result_text = f"{name}: ✅ 正常"
                else:
                    result_text = f"{name}: ❌ {desc}"
            
            self.result_text.insert(tk.END, result_text + "\n")
        
        # 显示置信度信息
        self.result_text.insert(tk.END, "\n置信度信息:\n")
        self.result_text.insert(tk.END, "-" * 30 + "\n")
        
        confidence_items = [
            ("人脸概率", "face_detect"),
            ("亮度值", "is_bright"),
            ("清晰度", "is_blur"),
            ("完整度", "is_complete")
        ]
        
        for name, key in confidence_items:
            value = confidence.get(key)
            if value is not None:
                if isinstance(value, float):
                    self.result_text.insert(tk.END, f"{name}: {value:.3f}\n")
                else:
                    self.result_text.insert(tk.END, f"{name}: {value}\n")


def main():
    root = tk.Tk()
    app = FaceDetectGUILite(root)
    root.mainloop()


if __name__ == "__main__":
    main()