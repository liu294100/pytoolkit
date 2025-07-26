#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程桌面工具 - 被控端客户端
负责屏幕捕获、接收控制指令并执行
"""

import asyncio
import json
import base64
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import websockets
import cv2
import numpy as np
from mss import mss
import pyautogui
from pynput import mouse, keyboard
import psutil
import socket
from loguru import logger
from PIL import Image, ImageTk
import io

# 配置日志
logger.add("logs/controlled_client.log", rotation="1 day", retention="7 days")

class ScreenCapture:
    """屏幕捕获类"""
    
    def __init__(self, quality=80, scale=0.8):
        self.quality = quality
        self.scale = scale
        self.running = False
        
    def capture_screen(self):
        """捕获屏幕并压缩"""
        try:
            # 为每次捕获创建新的mss实例，避免线程本地存储问题
            with mss() as sct:
                # 获取主显示器
                monitor = sct.monitors[1]
                
                # 捕获屏幕
                screenshot = sct.grab(monitor)
                
                # 转换为PIL图像
                img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                
                # 缩放图像
                if self.scale != 1.0:
                    new_size = (int(img.width * self.scale), int(img.height * self.scale))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # 压缩为JPEG
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=self.quality, optimize=True)
                
                # 转换为base64
                img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                return {
                    'data': img_data,
                    'width': img.width,
                    'height': img.height,
                    'original_width': screenshot.width,
                    'original_height': screenshot.height
                }
            
        except Exception as e:
            logger.error(f"屏幕捕获失败: {e}")
            return None

class InputController:
    """输入控制类"""
    
    def __init__(self):
        # 禁用pyautogui的安全检查
        pyautogui.FAILSAFE = False
        
    def handle_mouse_event(self, event_data):
        """处理鼠标事件"""
        try:
            event_type = event_data.get('event_type')
            x = event_data.get('x', 0)
            y = event_data.get('y', 0)
            button = event_data.get('button', 'left')
            
            if event_type == 'move':
                pyautogui.moveTo(x, y)
            elif event_type == 'click':
                pyautogui.click(x, y, button=button)
            elif event_type == 'double_click':
                pyautogui.doubleClick(x, y, button=button)
            elif event_type == 'drag':
                to_x = event_data.get('to_x', x)
                to_y = event_data.get('to_y', y)
                pyautogui.drag(to_x - x, to_y - y, duration=0.1, button=button)
            elif event_type == 'scroll':
                scroll_y = event_data.get('scroll_y', 0)
                pyautogui.scroll(scroll_y, x, y)
                
        except Exception as e:
            logger.error(f"处理鼠标事件失败: {e}")
            
    def handle_keyboard_event(self, event_data):
        """处理键盘事件"""
        try:
            event_type = event_data.get('event_type')
            key = event_data.get('key')
            
            if event_type == 'press':
                if isinstance(key, list):  # 组合键
                    pyautogui.hotkey(*key)
                else:
                    pyautogui.press(key)
            elif event_type == 'type':
                text = event_data.get('text', '')
                pyautogui.typewrite(text)
                
        except Exception as e:
            logger.error(f"处理键盘事件失败: {e}")

class ControlledClient:
    """被控端客户端主类"""
    
    def __init__(self):
        self.device_id = self.generate_device_id()
        self.device_name = socket.gethostname()
        self.server_url = "ws://localhost:8000"
        self.websocket = None
        self.running = False
        
        # 组件
        self.screen_capture = ScreenCapture()
        self.input_controller = InputController()
        
        # 控制状态
        self.is_being_controlled = False
        self.controller_info = None
        
        # GUI
        self.root = None
        self.setup_gui()
        
    def generate_device_id(self):
        """生成设备ID"""
        import uuid
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)][::-1])
        return f"controlled_{mac.replace(':', '')}"
        
    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title(f"远程桌面被控端 - {self.device_name}")
        self.root.geometry("500x400")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 设备信息
        info_frame = ttk.LabelFrame(main_frame, text="设备信息", padding="10")
        info_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(info_frame, text=f"设备名称: {self.device_name}").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=f"设备ID: {self.device_id}").grid(row=1, column=0, sticky=tk.W)
        
        # 连接设置
        conn_frame = ttk.LabelFrame(main_frame, text="连接设置", padding="10")
        conn_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(conn_frame, text="服务器地址:").grid(row=0, column=0, sticky=tk.W)
        self.server_entry = ttk.Entry(conn_frame, width=40)
        self.server_entry.insert(0, "ws://localhost:8000")
        self.server_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # 控制按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        self.connect_btn = ttk.Button(btn_frame, text="连接服务器", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.settings_btn = ttk.Button(btn_frame, text="设置", command=self.show_settings)
        self.settings_btn.grid(row=0, column=1)
        
        # 状态显示
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding="10")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.status_text = tk.Text(status_frame, height=15, width=60)
        scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 配置权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        self.log_message("被控端客户端已启动")
        
        # 自动连接到服务器
        self.root.after(1000, self.connect)  # 1秒后自动连接
        
    def _send_message_async(self, message):
        """异步发送消息的辅助方法"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.websocket.send(json.dumps(message)))
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
        finally:
            loop.close()
        
    def log_message(self, message):
        """记录日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        
        if self.root:
            self.status_text.insert(tk.END, log_msg)
            self.status_text.see(tk.END)
            
        logger.info(message)
        
    def toggle_connection(self):
        """切换连接状态"""
        if self.running:
            self.disconnect()
        else:
            self.connect()
            
    def connect(self):
        """连接到服务器"""
        self.server_url = self.server_entry.get().strip()
        if not self.server_url.startswith("ws://") and not self.server_url.startswith("wss://"):
            self.server_url = f"ws://{self.server_url}"
            
        if not self.server_url.endswith("/ws/" + self.device_id):
            if self.server_url.endswith("/"):
                self.server_url += f"ws/{self.device_id}"
            else:
                self.server_url += f"/ws/{self.device_id}"
                
        self.running = True
        self.connect_btn.config(text="断开连接")
        self.server_entry.config(state="disabled")
        
        # 启动连接线程
        threading.Thread(target=self.run_client, daemon=True).start()
        
    def disconnect(self):
        """断开连接"""
        self.running = False
        if self.websocket:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.websocket.close())
                else:
                    loop.run_until_complete(self.websocket.close())
            except Exception as e:
                logger.error(f"关闭WebSocket连接时出错: {e}")
            
        self.connect_btn.config(text="连接服务器")
        self.server_entry.config(state="normal")
        self.log_message("已断开连接")
        
    def run_client(self):
        """运行客户端"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.client_loop())
        except Exception as e:
            self.log_message(f"客户端运行错误: {e}")
        finally:
            loop.close()
            
    async def client_loop(self):
        """客户端主循环"""
        while self.running:
            try:
                self.log_message(f"正在连接服务器: {self.server_url}")
                
                async with websockets.connect(self.server_url) as websocket:
                    self.websocket = websocket
                    self.log_message("已连接到服务器")
                    
                    # 发送设备信息
                    device_info = {
                        'type': 'device_info',
                        'name': self.device_name,
                        'device_type': 'controlled',
                        'os': self.get_system_info()['os'],
                        'resolution': self.get_screen_resolution()
                    }
                    
                    await websocket.send(json.dumps(device_info))
                    
                    # 启动屏幕捕获任务
                    screen_task = asyncio.create_task(self.screen_capture_loop())
                    
                    # 处理消息
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self.handle_message(data)
                        except json.JSONDecodeError:
                            logger.error("收到无效的JSON消息")
                        except Exception as e:
                            logger.error(f"处理消息时出错: {e}")
                            
                    screen_task.cancel()
                    
            except websockets.exceptions.ConnectionClosed:
                self.log_message("连接已关闭")
            except Exception as e:
                self.log_message(f"连接错误: {e}")
                
            if self.running:
                self.log_message("5秒后重新连接...")
                await asyncio.sleep(5)
                
    async def handle_message(self, data):
        """处理收到的消息"""
        msg_type = data.get('type')
        
        if msg_type == 'control_request':
            # 收到控制请求
            controller_id = data.get('controller_id')
            controller_name = data.get('controller_name', 'Unknown')
            
            # 显示确认对话框
            self.root.after(0, lambda: self.show_control_request_dialog(controller_id, controller_name))
            
        elif msg_type == 'mouse_event':
            if self.is_being_controlled:
                self.input_controller.handle_mouse_event(data)
                
        elif msg_type == 'keyboard_event':
            if self.is_being_controlled:
                self.input_controller.handle_keyboard_event(data)
                
        elif msg_type == 'control_ended':
            self.is_being_controlled = False
            self.controller_info = None
            self.log_message("远程控制已结束")
            
    def show_control_request_dialog(self, controller_id, controller_name):
        """显示控制请求对话框"""
        result = messagebox.askyesno(
            "远程控制请求",
            f"用户 '{controller_name}' 请求控制您的桌面。\n\n是否允许？",
            parent=self.root
        )
        
        # 发送响应
        response = {
            'type': 'control_response',
            'controller_id': controller_id,
            'accepted': result
        }
        
        if result:
            self.is_being_controlled = True
            self.controller_info = {'id': controller_id, 'name': controller_name}
            self.log_message(f"已接受来自 '{controller_name}' 的控制请求")
        else:
            self.log_message(f"已拒绝来自 '{controller_name}' 的控制请求")
            
        if self.websocket:
            # 使用线程安全的方式发送消息
            threading.Thread(target=self._send_message_async, args=(response,), daemon=True).start()
            
    async def screen_capture_loop(self):
        """屏幕捕获循环"""
        while self.running:
            try:
                # 只有在被控制时才发送屏幕数据
                if self.is_being_controlled:
                    screen_data = self.screen_capture.capture_screen()
                    if screen_data:
                        message = {
                            'type': 'screen_data',
                            **screen_data
                        }
                        
                        if self.websocket:
                            await self.websocket.send(json.dumps(message))
                            
                    # 控制帧率
                    await asyncio.sleep(1/30)  # 30 FPS
                else:
                    # 未被控制时，降低检查频率
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"屏幕捕获循环错误: {e}")
                await asyncio.sleep(1)
                
    def get_system_info(self):
        """获取系统信息"""
        import platform
        return {
            'os': platform.system(),
            'os_version': platform.version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total
        }
        
    def get_screen_resolution(self):
        """获取屏幕分辨率"""
        try:
            with mss() as sct:
                monitor = sct.monitors[1]
                return {'width': monitor['width'], 'height': monitor['height']}
        except:
            return {'width': 1920, 'height': 1080}
            
    def show_settings(self):
        """显示设置对话框"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        settings_window.geometry("400x300")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # 设置内容
        frame = ttk.Frame(settings_window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 图像质量设置
        ttk.Label(frame, text="图像质量 (1-100):").grid(row=0, column=0, sticky=tk.W)
        quality_var = tk.IntVar(value=self.screen_capture.quality)
        quality_scale = ttk.Scale(frame, from_=1, to=100, variable=quality_var, orient=tk.HORIZONTAL)
        quality_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # 缩放比例设置
        ttk.Label(frame, text="缩放比例:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        scale_var = tk.DoubleVar(value=self.screen_capture.scale)
        scale_combo = ttk.Combobox(frame, textvariable=scale_var, values=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        scale_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(10, 0))
        
        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0))
        
        def apply_settings():
            self.screen_capture.quality = quality_var.get()
            self.screen_capture.scale = scale_var.get()
            settings_window.destroy()
            
        ttk.Button(btn_frame, text="应用", command=apply_settings).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(btn_frame, text="取消", command=settings_window.destroy).grid(row=0, column=1)
        
        frame.columnconfigure(1, weight=1)
        settings_window.columnconfigure(0, weight=1)
        settings_window.rowconfigure(0, weight=1)
        
    def on_closing(self):
        """窗口关闭事件"""
        if self.running:
            self.disconnect()
        self.root.destroy()
        
    def run(self):
        """运行GUI"""
        self.root.mainloop()

def main():
    """主函数"""
    import os
    os.makedirs("logs", exist_ok=True)
    
    client = ControlledClient()
    client.run()

if __name__ == "__main__":
    main()