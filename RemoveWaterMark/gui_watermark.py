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

class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title(" Watermark Tool")
        self.root.geometry("600x600")
        
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

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Add Watermark Tool", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Input Image
        ttk.Label(main_frame, text="Input Image:").pack(anchor=tk.W)
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(5, 15))
        
        ttk.Entry(input_frame, textvariable=self.input_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(input_frame, text="Browse...", command=self.browse_input).pack(side=tk.RIGHT)

        # Output Path
        ttk.Label(main_frame, text="Output Path:").pack(anchor=tk.W)
        ttk.Entry(main_frame, textvariable=self.output_path).pack(fill=tk.X, pady=(5, 15))

        # Watermark Text
        ttk.Label(main_frame, text="Watermark Text:").pack(anchor=tk.W)
        ttk.Entry(main_frame, textvariable=self.watermark_text).pack(fill=tk.X, pady=(5, 15))

        # Sliders Frame
        sliders_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        sliders_frame.pack(fill=tk.X, pady=10)

        # Font Size
        ttk.Label(sliders_frame, text="Font Size:").grid(row=0, column=0, sticky=tk.W, pady=5)
        scale_font = tk.Scale(sliders_frame, from_=10, to=200, orient=tk.HORIZONTAL, variable=self.font_size, showvalue=0)
        scale_font.grid(row=0, column=1, sticky=tk.EW, padx=10)
        ttk.Label(sliders_frame, textvariable=self.font_size, width=4).grid(row=0, column=2)

        # Opacity
        ttk.Label(sliders_frame, text="Opacity (0-255):").grid(row=1, column=0, sticky=tk.W, pady=5)
        scale_opacity = tk.Scale(sliders_frame, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.opacity, showvalue=0)
        scale_opacity.grid(row=1, column=1, sticky=tk.EW, padx=10)
        ttk.Label(sliders_frame, textvariable=self.opacity, width=4).grid(row=1, column=2)

        # Angle
        ttk.Label(sliders_frame, text="Angle (Deg):").grid(row=2, column=0, sticky=tk.W, pady=5)
        scale_angle = tk.Scale(sliders_frame, from_=0, to=360, orient=tk.HORIZONTAL, variable=self.angle, showvalue=0)
        scale_angle.grid(row=2, column=1, sticky=tk.EW, padx=10)
        ttk.Label(sliders_frame, textvariable=self.angle, width=4).grid(row=2, column=2)

        # Color
        ttk.Label(sliders_frame, text="Color:").grid(row=3, column=0, sticky=tk.W, pady=5)
        color_combo = ttk.Combobox(sliders_frame, textvariable=self.color_var, values=["Black", "Gray", "Red", "White"], state="readonly")
        color_combo.grid(row=3, column=1, sticky=tk.EW, padx=10)

        sliders_frame.columnconfigure(1, weight=1)

        # Action Button
        ttk.Button(main_frame, text="Generate Watermark", command=self.run_process).pack(pady=20, fill=tk.X)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        if filename:
            self.input_path.set(filename)
            directory = os.path.dirname(filename)
            name, ext = os.path.splitext(os.path.basename(filename))
            output_name = f"{name}_watermarked{ext}"
            self.output_path.set(os.path.join(directory, output_name))

    def run_process(self):
        inp = self.input_path.get()
        out = self.output_path.get()
        text = self.watermark_text.get()
        
        if not inp or not os.path.exists(inp):
            messagebox.showerror("Error", "Input file does not exist!")
            return
            
        if not out:
            messagebox.showerror("Error", "Output path cannot be empty!")
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
            self.status_var.set("Processing...")
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
            
            self.status_var.set(f"Saved to {out}")
            messagebox.showinfo("Success", f"Watermark added successfully!\nSaved to: {out}")
        except Exception as e:
            self.status_var.set("Error occurred")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkApp(root)
    root.mainloop()
