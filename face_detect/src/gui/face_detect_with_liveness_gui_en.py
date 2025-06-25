#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Face Detection and Liveness Detection Integrated GUI Application
Combines static image face detection and real-time liveness detection
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
    from core.detect import main as detect_faces
    from core.resp_entity import ImageStatus
    from core.liveness_detection import LivenessDetector, LivenessStatus
except ImportError as e:
    print(f"Module import failed: {e}")
    print("Please ensure all dependency modules are in the same directory")

class FaceDetectionWithLivenessGUI:
    """Face Detection and Liveness Detection Integrated GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Face Detection and Liveness Detection System")
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
        
        # Create tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Static image detection tab
        self.create_static_detection_tab()
        
        # Liveness detection tab
        self.create_liveness_detection_tab()
        
        # Results comparison tab
        self.create_comparison_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def create_static_detection_tab(self):
        """Create static image detection tab"""
        static_frame = ttk.Frame(self.notebook)
        self.notebook.add(static_frame, text="Static Image Detection")
        
        # Left control panel
        control_frame = ttk.LabelFrame(static_frame, text="Control Panel", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Image selection
        ttk.Button(control_frame, text="Select Image", command=self.select_image).grid(row=0, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Detection button
        self.detect_btn = ttk.Button(control_frame, text="Start Detection", command=self.detect_faces_static, state=tk.DISABLED)
        self.detect_btn.grid(row=1, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Save results button
        self.save_btn = ttk.Button(control_frame, text="Save Results", command=self.save_results, state=tk.DISABLED)
        self.save_btn.grid(row=2, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Image information
        info_frame = ttk.LabelFrame(control_frame, text="Image Information", padding="5")
        info_frame.grid(row=3, column=0, pady=10, sticky=tk.W+tk.E)
        
        self.image_info = tk.Text(info_frame, height=8, width=30)
        self.image_info.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Detection results
        result_frame = ttk.LabelFrame(control_frame, text="Detection Results", padding="5")
        result_frame.grid(row=4, column=0, pady=10, sticky=tk.W+tk.E)
        
        self.result_text = tk.Text(result_frame, height=10, width=30)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right image display area
        image_frame = ttk.LabelFrame(static_frame, text="Image Preview", padding="10")
        image_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.image_label = ttk.Label(image_frame, text="Please select an image")
        self.image_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        static_frame.columnconfigure(1, weight=1)
        static_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
    
    def create_liveness_detection_tab(self):
        """Create liveness detection tab"""
        liveness_frame = ttk.Frame(self.notebook)
        self.notebook.add(liveness_frame, text="Liveness Detection")
        
        # Left control panel
        liveness_control_frame = ttk.LabelFrame(liveness_frame, text="Liveness Detection Control", padding="10")
        liveness_control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Camera control
        self.camera_btn = ttk.Button(liveness_control_frame, text="Start Camera", command=self.toggle_camera)
        self.camera_btn.grid(row=0, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Start liveness detection
        self.liveness_btn = ttk.Button(liveness_control_frame, text="Start Liveness Detection", 
                                     command=self.start_liveness_detection, state=tk.DISABLED)
        self.liveness_btn.grid(row=1, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Reset detection
        self.reset_btn = ttk.Button(liveness_control_frame, text="Reset Detection", 
                                  command=self.reset_liveness_detection, state=tk.DISABLED)
        self.reset_btn.grid(row=2, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Save liveness detection results
        self.save_liveness_btn = ttk.Button(liveness_control_frame, text="Save Liveness Results", 
                                          command=self.save_liveness_results, state=tk.DISABLED)
        self.save_liveness_btn.grid(row=3, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Detection instructions
        instruction_frame = ttk.LabelFrame(liveness_control_frame, text="Detection Instructions", padding="5")
        instruction_frame.grid(row=4, column=0, pady=10, sticky=tk.W+tk.E)
        
        instructions = (
            "Liveness Detection Steps:\n\n"
            "1. Click 'Start Camera'\n"
            "2. Click 'Start Liveness Detection'\n"
            "3. Complete the following actions within 5 seconds:\n"
            "   • Blink 3 times\n"
            "   • Turn head slightly\n"
            "4. Wait for detection results\n\n"
            "Note: Keep your face within the\n"
            "camera view with sufficient lighting"
        )
        
        instruction_label = ttk.Label(instruction_frame, text=instructions, justify=tk.LEFT)
        instruction_label.grid(row=0, column=0, sticky=tk.W)
        
        # Liveness detection results
        liveness_result_frame = ttk.LabelFrame(liveness_control_frame, text="Liveness Detection Results", padding="5")
        liveness_result_frame.grid(row=5, column=0, pady=10, sticky=tk.W+tk.E)
        
        self.liveness_result_text = tk.Text(liveness_result_frame, height=8, width=30)
        self.liveness_result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right camera display area
        camera_frame = ttk.LabelFrame(liveness_frame, text="Camera Preview", padding="10")
        camera_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.camera_label = ttk.Label(camera_frame, text="Camera not started")
        self.camera_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        liveness_frame.columnconfigure(1, weight=1)
        liveness_frame.rowconfigure(0, weight=1)
        camera_frame.columnconfigure(0, weight=1)
        camera_frame.rowconfigure(0, weight=1)
    
    def create_comparison_tab(self):
        """Create results comparison tab"""
        comparison_frame = ttk.Frame(self.notebook)
        self.notebook.add(comparison_frame, text="Results Comparison")
        
        # Comparison instructions
        instruction_frame = ttk.LabelFrame(comparison_frame, text="Feature Comparison", padding="10")
        instruction_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        comparison_text = (
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
        )
        
        comparison_label = ttk.Label(instruction_frame, text=comparison_text, justify=tk.LEFT)
        comparison_label.grid(row=0, column=0, sticky=tk.W)
        
        # History records
        history_frame = ttk.LabelFrame(comparison_frame, text="Detection History", padding="10")
        history_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create table to display history records
        columns = ('Time', 'Type', 'Result', 'Confidence', 'Details')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=120)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Clear history button
        ttk.Button(history_frame, text="Clear History", command=self.clear_history).grid(row=1, column=0, pady=5, sticky=tk.W)
        
        # Configure grid weights
        comparison_frame.columnconfigure(0, weight=1)
        comparison_frame.rowconfigure(1, weight=1)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
    
    def select_image(self):
        """Select image file"""
        file_types = [
            ('Image files', '*.jpg *.jpeg *.png *.bmp *.tiff *.webp'),
            ('JPEG files', '*.jpg *.jpeg'),
            ('PNG files', '*.png'),
            ('All files', '*.*')
        ]
        
        file_path = filedialog.askopenfilename(
            title="Select Image File",
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
            
            self.status_var.set(f"Image loaded: {Path(file_path).name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
            self.status_var.set("Failed to load image")
    
    def resize_image_for_display(self, image, max_size):
        """Resize image for display"""
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    
    def show_image_info(self, image, file_path):
        """Show image information"""
        file_size = Path(file_path).stat().st_size
        
        info = f"File path: {file_path}\n"
        info += f"File size: {file_size / 1024:.1f} KB\n"
        info += f"Image dimensions: {image.size[0]} x {image.size[1]}\n"
        info += f"Image mode: {image.mode}\n"
        info += f"Image format: {image.format}\n"
        
        self.image_info.delete(1.0, tk.END)
        self.image_info.insert(1.0, info)
    
    def detect_faces_static(self):
        """Execute static image face detection"""
        if not self.current_image_path:
            messagebox.showwarning("Warning", "Please select an image first")
            return
        
        try:
            self.status_var.set("Detecting faces...")
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
                result_text = f"Detection completed!\n\n"
                result_text += f"Number of faces detected: {len(result.faces)}\n\n"
                
                for i, face in enumerate(result.faces, 1):
                    result_text += f"Face {i}:\n"
                    result_text += f"  Position: ({face.x}, {face.y})\n"
                    result_text += f"  Size: {face.width} x {face.height}\n"
                    result_text += f"  Confidence: {face.confidence:.3f}\n\n"
                
                # Load and display annotated image
                if result.output_path and Path(result.output_path).exists():
                    annotated_image = Image.open(result.output_path)
                    display_image = self.resize_image_for_display(annotated_image, max_size=(600, 400))
                    photo = ImageTk.PhotoImage(display_image)
                    self.image_label.configure(image=photo)
                    self.image_label.image = photo
            else:
                result_text = f"Detection result: {str(result)}"
            
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, result_text)
            
            # Add to history
            self.add_to_history('Static Detection', 'Success', len(result.faces) if hasattr(result, 'faces') else 0, 'See results')
            
            # Enable save button
            self.save_btn.configure(state=tk.NORMAL)
            self.detect_btn.configure(state=tk.NORMAL)
            
            self.status_var.set("Detection completed")
            
        except Exception as e:
            self.on_detection_error(str(e))
    
    def on_detection_error(self, error_msg):
        """Detection error callback"""
        messagebox.showerror("Detection Error", f"Face detection failed: {error_msg}")
        self.detect_btn.configure(state=tk.NORMAL)
        self.status_var.set("Detection failed")
        
        # Add to history
        self.add_to_history('Static Detection', 'Failed', 0, error_msg)
    
    def save_results(self):
        """Save detection results"""
        if not self.detection_results:
            messagebox.showwarning("Warning", "No detection results to save")
            return
        
        try:
            # Select save location
            file_path = filedialog.asksaveasfilename(
                title="Save Detection Results",
                defaultextension=".json",
                filetypes=[('JSON files', '*.json'), ('All files', '*.*')]
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
                
                messagebox.showinfo("Success", f"Results saved to: {file_path}")
                self.status_var.set(f"Results saved: {Path(file_path).name}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {str(e)}")
    
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
                messagebox.showerror("Error", "Cannot open camera")
                return
            
            self.camera_active = True
            self.camera_btn.configure(text="Stop Camera")
            self.liveness_btn.configure(state=tk.NORMAL)
            
            # Start camera display thread
            self.start_camera_thread()
            
            self.status_var.set("Camera started")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start camera: {str(e)}")
    
    def stop_camera(self):
        """Stop camera"""
        self.camera_active = False
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.camera_btn.configure(text="Start Camera")
        self.liveness_btn.configure(state=tk.DISABLED)
        self.reset_btn.configure(state=tk.DISABLED)
        
        # Clear camera display
        self.camera_label.configure(image="", text="Camera not started")
        
        self.status_var.set("Camera stopped")
    
    def start_camera_thread(self):
        """Start camera display thread"""
        def camera_loop():
            while self.camera_active and self.cap:
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame = frame.copy()
                    
                    # If liveness detection is running, add detection info
                    if self.liveness_detector and self.liveness_result:
                        frame = self.liveness_detector.draw_liveness_info(frame, self.liveness_result)
                    
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
                    
                    # Update display in main thread
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
        if not self.camera_active or not self.current_frame is not None:
            messagebox.showwarning("Warning", "Please start camera first")
            return
        
        try:
            # Initialize liveness detector
            if not self.liveness_detector:
                self.liveness_detector = LivenessDetector()
            
            self.liveness_btn.configure(state=tk.DISABLED)
            self.reset_btn.configure(state=tk.NORMAL)
            
            # Start liveness detection in new thread
            def liveness_thread():
                try:
                    self.status_var.set("Starting liveness detection...")
                    
                    # Collect frames for 5 seconds
                    frames = []
                    start_time = time.time()
                    
                    while time.time() - start_time < 5.0 and self.camera_active:
                        if self.current_frame is not None:
                            frames.append(self.current_frame.copy())
                        time.sleep(0.1)
                    
                    if frames:
                        # Perform liveness detection
                        result = self.liveness_detector.detect_liveness(frames)
                        
                        # Update UI in main thread
                        self.root.after(0, lambda: self.on_liveness_complete(result))
                    else:
                        self.root.after(0, lambda: self.on_liveness_error("No frames captured"))
                        
                except Exception as e:
                    self.root.after(0, lambda: self.on_liveness_error(str(e)))
            
            self.liveness_thread = threading.Thread(target=liveness_thread, daemon=True)
            self.liveness_thread.start()
            
        except Exception as e:
            self.on_liveness_error(str(e))
    
    def on_liveness_complete(self, result):
        """Liveness detection complete callback"""
        try:
            self.liveness_result = result
            
            # Show liveness results
            if isinstance(result, LivenessStatus):
                result_text = f"Liveness Detection Completed!\n\n"
                result_text += f"Is Live: {result.is_live}\n"
                result_text += f"Overall Score: {result.overall_score:.3f}\n\n"
                result_text += f"Blink Detection:\n"
                result_text += f"  Blinks: {result.blink_count}\n"
                result_text += f"  Score: {result.blink_score:.3f}\n\n"
                result_text += f"Head Movement:\n"
                result_text += f"  Score: {result.head_movement_score:.3f}\n\n"
                result_text += f"Face Texture:\n"
                result_text += f"  Score: {result.texture_score:.3f}\n\n"
                result_text += f"Confidence: {result.confidence:.3f}\n"
            else:
                result_text = f"Liveness result: {str(result)}"
            
            self.liveness_result_text.delete(1.0, tk.END)
            self.liveness_result_text.insert(1.0, result_text)
            
            # Add to history
            is_live = result.is_live if hasattr(result, 'is_live') else False
            confidence = result.confidence if hasattr(result, 'confidence') else 0
            self.add_to_history('Liveness Detection', 'Live' if is_live else 'Not Live', confidence, 'See results')
            
            # Enable save button
            self.save_liveness_btn.configure(state=tk.NORMAL)
            self.liveness_btn.configure(state=tk.NORMAL)
            
            self.status_var.set("Liveness detection completed")
            
        except Exception as e:
            self.on_liveness_error(str(e))
    
    def on_liveness_error(self, error_msg):
        """Liveness detection error callback"""
        messagebox.showerror("Liveness Detection Error", f"Liveness detection failed: {error_msg}")
        self.liveness_btn.configure(state=tk.NORMAL)
        self.status_var.set("Liveness detection failed")
        
        # Add to history
        self.add_to_history('Liveness Detection', 'Failed', 0, error_msg)
    
    def reset_liveness_detection(self):
        """Reset liveness detection"""
        self.liveness_result = None
        self.liveness_result_text.delete(1.0, tk.END)
        self.save_liveness_btn.configure(state=tk.DISABLED)
        self.reset_btn.configure(state=tk.DISABLED)
        self.liveness_btn.configure(state=tk.NORMAL)
        
        self.status_var.set("Liveness detection reset")
    
    def save_liveness_results(self):
        """Save liveness detection results"""
        if not self.liveness_result:
            messagebox.showwarning("Warning", "No liveness results to save")
            return
        
        try:
            # Select save location
            file_path = filedialog.asksaveasfilename(
                title="Save Liveness Results",
                defaultextension=".json",
                filetypes=[('JSON files', '*.json'), ('All files', '*.*')]
            )
            
            if file_path:
                # Prepare save data
                save_data = {
                    'timestamp': datetime.now().isoformat(),
                    'detection_type': 'liveness_detection',
                    'results': self.liveness_result.__dict__ if hasattr(self.liveness_result, '__dict__') else str(self.liveness_result)
                }
                
                # Save to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("Success", f"Liveness results saved to: {file_path}")
                self.status_var.set(f"Liveness results saved: {Path(file_path).name}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {str(e)}")
    
    def add_to_history(self, detection_type, result, confidence, details):
        """Add record to history"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.history_tree.insert('', 'end', values=(timestamp, detection_type, result, confidence, details))
    
    def clear_history(self):
        """Clear history records"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        self.status_var.set("History cleared")
    
    def on_closing(self):
        """Handle window closing"""
        # Stop camera
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