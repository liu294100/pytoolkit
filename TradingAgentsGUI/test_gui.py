#!/usr/bin/env python3
"""
Simple GUI test script to diagnose display issues
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_basic_gui():
    """Test basic GUI functionality"""
    try:
        # Create root window
        root = tk.Tk()
        root.title("GUI Test - TradingAgents")
        root.geometry("800x600")
        root.configure(bg='#f0f0f0')
        
        # Create main frame
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Add title
        title_label = ttk.Label(main_frame, text="TradingAgents GUI Test", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Add status info
        status_frame = ttk.LabelFrame(main_frame, text="System Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(status_frame, text=f"Python Version: {sys.version}").pack(anchor=tk.W)
        ttk.Label(status_frame, text=f"Tkinter Version: {tk.TkVersion}").pack(anchor=tk.W)
        ttk.Label(status_frame, text=f"Working Directory: {os.getcwd()}").pack(anchor=tk.W)
        
        # Test imports
        import_frame = ttk.LabelFrame(main_frame, text="Module Import Test", padding=10)
        import_frame.pack(fill=tk.X, pady=(0, 20))
        
        modules_to_test = [
            'config',
            'utils', 
            'performance_optimizer',
            'technical_indicators',
            'api_integration',
            'strategy_customization'
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
                status = "✓ OK"
                color = 'green'
            except ImportError as e:
                status = f"✗ FAILED: {e}"
                color = 'red'
            except Exception as e:
                status = f"✗ ERROR: {e}"
                color = 'red'
                
            label = ttk.Label(import_frame, text=f"{module_name}: {status}")
            label.pack(anchor=tk.W)
        
        # Test button
        def test_main_app():
            try:
                # Try to import and create main app
                from main import TradingAgentsGUI
                messagebox.showinfo("Test", "Main app import successful! Attempting to create GUI...")
                
                # Create new window for main app
                app = TradingAgentsGUI()
                messagebox.showinfo("Success", "Main GUI created successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create main GUI: {e}")
        
        test_button = ttk.Button(main_frame, text="Test Main Application", 
                                command=test_main_app)
        test_button.pack(pady=20)
        
        # Instructions
        instructions = ttk.Label(main_frame, 
                                text="If you can see this window, basic GUI is working.\n"
                                     "Click 'Test Main Application' to test the full app.",
                                justify=tk.CENTER)
        instructions.pack(pady=20)
        
        # Show window
        root.update_idletasks()
        root.deiconify()
        
        print("GUI test window created successfully")
        print("If you see a blank window, there may be a display driver issue")
        
        # Start main loop
        root.mainloop()
        
    except Exception as e:
        print(f"Failed to create test GUI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting GUI test...")
    test_basic_gui()