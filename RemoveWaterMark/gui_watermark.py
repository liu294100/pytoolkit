import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys

# Ensure we can import the module from the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from addwatermarrk import add_watermark
except ImportError:
    # Handle case where script is run from project root
    sys.path.append(os.path.join(current_dir, 'RemoveWaterMark'))
    try:
        from addwatermarrk import add_watermark
    except ImportError:
        # Last resort: try relative import if run as module (though unlikely for direct execution)
        try:
            from .addwatermarrk import add_watermark
        except ImportError:
            pass

# Translations
TRANSLATIONS = {
    "zh": {
        "title": "图片水印工具",
        "window_title": "图片水印工具",
        "language_label": "语言 / Language:",
        "input_label": "输入图片:",
        "browse": "浏览...",
        "output_label": "输出路径:",
        "watermark_text_label": "水印文字:",
        "settings_group": "设置",
        "font_size": "字体大小:",
        "opacity": "透明度 (0-255):",
        "angle": "角度 (度):",
        "color": "颜色:",
        "generate_btn": "生成水印",
        "status_ready": "就绪",
        "status_processing": "处理中...",
        "status_saved": "已保存至 {}",
        "status_error": "发生错误",
        "msg_error_input": "输入文件不存在!",
        "msg_error_output": "输出路径不能为空!",
        "msg_success_title": "成功",
        "msg_success_content": "水印添加成功!\n保存至: {}",
        "msg_error_title": "错误",
        "msg_error_content": "发生错误:\n{}"
    },
    "en": {
        "title": "Picture Watermark Tool",
        "window_title": "Picture Watermark Tool",
        "language_label": "Language / 语言:",
        "input_label": "Input Image:",
        "browse": "Browse...",
        "output_label": "Output Path:",
        "watermark_text_label": "Watermark Text:",
        "settings_group": "Settings",
        "font_size": "Font Size:",
        "opacity": "Opacity (0-255):",
        "angle": "Angle (Deg):",
        "color": "Color:",
        "generate_btn": "Generate Watermark",
        "status_ready": "Ready",
        "status_processing": "Processing...",
        "status_saved": "Saved to {}",
        "status_error": "Error occurred",
        "msg_error_input": "Input file does not exist!",
        "msg_error_output": "Output path cannot be empty!",
        "msg_success_title": "Success",
        "msg_success_content": "Watermark added successfully!\nSaved to: {}",
        "msg_error_title": "Error",
        "msg_error_content": "An error occurred:\n{}"
    },
    "ja": {
        "title": "画像透かしツール",
        "window_title": "画像透かしツール",
        "language_label": "言語 / Language:",
        "input_label": "入力画像:",
        "browse": "参照...",
        "output_label": "出力パス:",
        "watermark_text_label": "透かし文字:",
        "settings_group": "設定",
        "font_size": "フォントサイズ:",
        "opacity": "不透明度 (0-255):",
        "angle": "角度 (度):",
        "color": "色:",
        "generate_btn": "透かしを作成",
        "status_ready": "準備完了",
        "status_processing": "処理中...",
        "status_saved": "保存しました: {}",
        "status_error": "エラーが発生しました",
        "msg_error_input": "入力ファイルが存在しません!",
        "msg_error_output": "出力パスを空にすることはできません!",
        "msg_success_title": "成功",
        "msg_success_content": "透かしを追加しました!\n保存先: {}",
        "msg_error_title": "エラー",
        "msg_error_content": "エラーが発生しました:\n{}"
    }
}

class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.current_lang = "zh" # Default to Chinese
        
        # Apply a theme if possible, otherwise standard
        try:
            style = ttk.Style()
            style.theme_use('clam')
        except:
            pass

        # Variables
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.watermark_text = tk.StringVar(value="仅供XXXX使用")
        self.font_size = tk.IntVar(value=50) # Increased default size
        self.opacity = tk.IntVar(value=150)  # Increased default opacity
        self.angle = tk.IntVar(value=30)
        self.color_var = tk.StringVar(value="Black") # Default to Black for better visibility
        self.lang_var = tk.StringVar(value="中文")

        # UI Element References (for dynamic text update)
        self.ui_elements = {}

        self.create_widgets()
        self.update_ui_text()

    def create_widgets(self):
        self.root.geometry("600x650") # Slightly taller for language selection

        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Language Selection
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.ui_elements['language_label'] = ttk.Label(lang_frame, text="")
        self.ui_elements['language_label'].pack(side=tk.LEFT, padx=(0, 10))
        
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=["中文", "English", "日本語"], state="readonly", width=10)
        lang_combo.pack(side=tk.LEFT)
        lang_combo.bind("<<ComboboxSelected>>", self.on_language_change)

        # Title
        self.ui_elements['title_label'] = ttk.Label(main_frame, text="", font=("Helvetica", 16, "bold"))
        self.ui_elements['title_label'].pack(pady=(0, 20))

        # Input Image
        self.ui_elements['input_label'] = ttk.Label(main_frame, text="")
        self.ui_elements['input_label'].pack(anchor=tk.W)
        
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(5, 15))
        
        ttk.Entry(input_frame, textvariable=self.input_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.ui_elements['browse_btn_in'] = ttk.Button(input_frame, text="", command=self.browse_input)
        self.ui_elements['browse_btn_in'].pack(side=tk.RIGHT)

        # Output Path
        self.ui_elements['output_label'] = ttk.Label(main_frame, text="")
        self.ui_elements['output_label'].pack(anchor=tk.W)
        ttk.Entry(main_frame, textvariable=self.output_path).pack(fill=tk.X, pady=(5, 15))

        # Watermark Text
        self.ui_elements['watermark_text_label'] = ttk.Label(main_frame, text="")
        self.ui_elements['watermark_text_label'].pack(anchor=tk.W)
        ttk.Entry(main_frame, textvariable=self.watermark_text).pack(fill=tk.X, pady=(5, 15))

        # Sliders Frame
        self.sliders_frame = ttk.LabelFrame(main_frame, text="", padding="10")
        self.sliders_frame.pack(fill=tk.X, pady=10)

        # Font Size
        self.ui_elements['font_size_label'] = ttk.Label(self.sliders_frame, text="")
        self.ui_elements['font_size_label'].grid(row=0, column=0, sticky=tk.W, pady=5)
        
        scale_font = tk.Scale(self.sliders_frame, from_=10, to=200, orient=tk.HORIZONTAL, variable=self.font_size, showvalue=0)
        scale_font.grid(row=0, column=1, sticky=tk.EW, padx=10)
        ttk.Label(self.sliders_frame, textvariable=self.font_size, width=4).grid(row=0, column=2)

        # Opacity
        self.ui_elements['opacity_label'] = ttk.Label(self.sliders_frame, text="")
        self.ui_elements['opacity_label'].grid(row=1, column=0, sticky=tk.W, pady=5)
        
        scale_opacity = tk.Scale(self.sliders_frame, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.opacity, showvalue=0)
        scale_opacity.grid(row=1, column=1, sticky=tk.EW, padx=10)
        ttk.Label(self.sliders_frame, textvariable=self.opacity, width=4).grid(row=1, column=2)

        # Angle
        self.ui_elements['angle_label'] = ttk.Label(self.sliders_frame, text="")
        self.ui_elements['angle_label'].grid(row=2, column=0, sticky=tk.W, pady=5)
        
        scale_angle = tk.Scale(self.sliders_frame, from_=0, to=360, orient=tk.HORIZONTAL, variable=self.angle, showvalue=0)
        scale_angle.grid(row=2, column=1, sticky=tk.EW, padx=10)
        ttk.Label(self.sliders_frame, textvariable=self.angle, width=4).grid(row=2, column=2)

        # Color
        self.ui_elements['color_label'] = ttk.Label(self.sliders_frame, text="")
        self.ui_elements['color_label'].grid(row=3, column=0, sticky=tk.W, pady=5)
        
        color_combo = ttk.Combobox(self.sliders_frame, textvariable=self.color_var, values=["Black", "Gray", "Red", "White"], state="readonly")
        color_combo.grid(row=3, column=1, sticky=tk.EW, padx=10)

        self.sliders_frame.columnconfigure(1, weight=1)

        # Action Button
        self.ui_elements['generate_btn'] = ttk.Button(main_frame, text="", command=self.run_process)
        self.ui_elements['generate_btn'].pack(pady=20, fill=tk.X)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def on_language_change(self, event=None):
        selection = self.lang_var.get()
        if selection == "中文":
            self.current_lang = "zh"
        elif selection == "English":
            self.current_lang = "en"
        elif selection == "日本語":
            self.current_lang = "ja"
        self.update_ui_text()

    def update_ui_text(self):
        t = TRANSLATIONS[self.current_lang]
        
        self.root.title(t['window_title'])
        self.ui_elements['language_label'].config(text=t['language_label'])
        self.ui_elements['title_label'].config(text=t['title'])
        self.ui_elements['input_label'].config(text=t['input_label'])
        self.ui_elements['browse_btn_in'].config(text=t['browse'])
        self.ui_elements['output_label'].config(text=t['output_label'])
        self.ui_elements['watermark_text_label'].config(text=t['watermark_text_label'])
        self.sliders_frame.config(text=t['settings_group'])
        self.ui_elements['font_size_label'].config(text=t['font_size'])
        self.ui_elements['opacity_label'].config(text=t['opacity'])
        self.ui_elements['angle_label'].config(text=t['angle'])
        self.ui_elements['color_label'].config(text=t['color'])
        self.ui_elements['generate_btn'].config(text=t['generate_btn'])
        
        # Reset status if it's the "Ready" message
        current_status = self.status_var.get()
        if current_status in ["Ready", "就绪", "準備完了"]:
            self.status_var.set(t['status_ready'])

    def browse_input(self):
        t = TRANSLATIONS[self.current_lang]
        filename = filedialog.askopenfilename(
            title=t['browse'], # Reuse browse or define title
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        if filename:
            self.input_path.set(filename)
            directory = os.path.dirname(filename)
            name, ext = os.path.splitext(os.path.basename(filename))
            output_name = f"{name}_watermarked{ext}"
            self.output_path.set(os.path.join(directory, output_name))

    def run_process(self):
        t = TRANSLATIONS[self.current_lang]
        inp = self.input_path.get()
        out = self.output_path.get()
        text = self.watermark_text.get()
        
        if not inp or not os.path.exists(inp):
            messagebox.showerror(t['msg_error_title'], t['msg_error_input'])
            return
            
        if not out:
            messagebox.showerror(t['msg_error_title'], t['msg_error_output'])
            return

        # Map color name to tuple
        color_map = {
            "Black": (0, 0, 0),
            "Gray": (100, 100, 100),
            "Red": (255, 0, 0),
            "White": (255, 255, 255)
        }
        selected_color = color_map.get(self.color_var.get(), (100, 100, 100))

        try:
            self.status_var.set(t['status_processing'])
            self.root.update_idletasks()
            
            # Check if add_watermark is imported
            if 'add_watermark' not in globals():
                 raise ImportError("Could not import add_watermark function. Please ensure addwatermarrk.py is in the same directory.")

            add_watermark(
                image_path=inp,
                output_path=out,
                text=text,
                font_size=self.font_size.get(),
                opacity=self.opacity.get(),
                angle=self.angle.get(),
                color=selected_color,
                space=None # Auto spacing for full fill
            )
            
            self.status_var.set(t['status_saved'].format(out))
            messagebox.showinfo(t['msg_success_title'], t['msg_success_content'].format(out))
        except Exception as e:
            self.status_var.set(t['status_error'])
            messagebox.showerror(t['msg_error_title'], t['msg_error_content'].format(str(e)))

if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkApp(root)
    root.mainloop()
