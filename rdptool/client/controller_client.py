#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程桌面工具 - 控制端客户端
负责显示远程屏幕和发送控制指令
"""

import asyncio
import json
import base64
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import websockets
import cv2
import numpy as np
from PIL import Image, ImageTk
import io
import socket
from loguru import logger

# 配置日志
logger.add("logs/controller_client.log", rotation="1 day", retention="7 days")

class RemoteScreen:
    """远程屏幕显示类"""
    
    def __init__(self, parent, controller_client):
        self.parent = parent
        self.controller_client = controller_client
        self.canvas = None
        self.current_image = None
        self.scale_factor = 1.0
        self.remote_resolution = {'width': 1920, 'height': 1080}
        self.setup_canvas()
        
    def setup_canvas(self):
        """设置画布"""
        # 创建滚动画布
        canvas_frame = ttk.Frame(self.parent)
        canvas_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 画布和滚动条
        self.canvas = tk.Canvas(canvas_frame, bg='black')
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 配置权重
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        
        # 绑定事件
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        self.canvas.bind("<Button-3>", self.on_mouse_right_click)
        self.canvas.bind("<Double-Button-1>", self.on_mouse_double_click)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<KeyPress>", self.on_key_press)
        self.canvas.focus_set()
        
    def update_screen(self, image_data, width, height, original_width, original_height):
        """更新屏幕显示"""
        try:
            # 解码图像
            img_bytes = base64.b64decode(image_data)
            img = Image.open(io.BytesIO(img_bytes))
            
            # 更新远程分辨率信息
            self.remote_resolution = {'width': original_width, 'height': original_height}
            
            # 应用缩放
            if self.scale_factor != 1.0:
                new_size = (int(width * self.scale_factor), int(height * self.scale_factor))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
            # 转换为Tkinter格式
            self.current_image = ImageTk.PhotoImage(img)
            
            # 更新画布
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)
            
            # 更新滚动区域
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        except Exception as e:
            logger.error(f"更新屏幕显示失败: {e}")
            
    def canvas_to_remote_coords(self, canvas_x, canvas_y):
        """将画布坐标转换为远程坐标"""
        # 考虑滚动偏移
        scroll_x = self.canvas.canvasx(canvas_x)
        scroll_y = self.canvas.canvasy(canvas_y)
        
        # 考虑缩放
        remote_x = int(scroll_x / self.scale_factor)
        remote_y = int(scroll_y / self.scale_factor)
        
        return remote_x, remote_y
        
    def on_mouse_click(self, event):
        """鼠标点击事件"""
        remote_x, remote_y = self.canvas_to_remote_coords(event.x, event.y)
        self.controller_client.send_mouse_event('click', remote_x, remote_y, 'left')
        
    def on_mouse_right_click(self, event):
        """鼠标右键点击事件"""
        remote_x, remote_y = self.canvas_to_remote_coords(event.x, event.y)
        self.controller_client.send_mouse_event('click', remote_x, remote_y, 'right')
        
    def on_mouse_double_click(self, event):
        """鼠标双击事件"""
        remote_x, remote_y = self.canvas_to_remote_coords(event.x, event.y)
        self.controller_client.send_mouse_event('double_click', remote_x, remote_y, 'left')
        
    def on_mouse_drag(self, event):
        """鼠标拖拽事件"""
        remote_x, remote_y = self.canvas_to_remote_coords(event.x, event.y)
        self.controller_client.send_mouse_event('move', remote_x, remote_y)
        
    def on_mouse_move(self, event):
        """鼠标移动事件"""
        remote_x, remote_y = self.canvas_to_remote_coords(event.x, event.y)
        self.controller_client.send_mouse_event('move', remote_x, remote_y)
        
    def on_mouse_wheel(self, event):
        """鼠标滚轮事件"""
        remote_x, remote_y = self.canvas_to_remote_coords(event.x, event.y)
        scroll_y = 1 if event.delta > 0 else -1
        self.controller_client.send_mouse_event('scroll', remote_x, remote_y, scroll_y=scroll_y)
        
    def on_key_press(self, event):
        """键盘按键事件"""
        key = event.keysym
        self.controller_client.send_keyboard_event('press', key)
        
    def set_scale(self, scale):
        """设置缩放比例"""
        self.scale_factor = scale

class ControllerClient:
    """控制端客户端主类"""
    
    def __init__(self):
        self.device_id = self.generate_device_id()
        self.device_name = socket.gethostname()
        self.server_url = "ws://localhost:8000"
        self.websocket = None
        self.running = False
        
        # 控制状态
        self.is_controlling = False
        self.controlled_device = None
        self.available_devices = {}
        
        # GUI
        self.root = None
        self.remote_screen = None
        self.setup_gui()
        
    def generate_device_id(self):
        """生成设备ID"""
        import uuid
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)][::-1])
        return f"controller_{mac.replace(':', '')}"
        
    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title(f"远程桌面控制端 - {self.device_name}")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 创建菜单栏
        self.create_menu()
        
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 工具栏
        self.create_toolbar(main_frame)
        
        # 内容区域
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # 左侧设备列表
        self.create_device_panel(content_frame)
        
        # 右侧远程屏幕
        self.create_screen_panel(content_frame)
        
        # 状态栏
        self.create_status_bar(main_frame)
        
        # 配置权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 连接菜单
        conn_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="连接", menu=conn_menu)
        conn_menu.add_command(label="连接服务器", command=self.toggle_connection)
        conn_menu.add_separator()
        conn_menu.add_command(label="退出", command=self.on_closing)
        
        # 控制菜单
        control_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="控制", menu=control_menu)
        control_menu.add_command(label="发送Ctrl+Alt+Del", command=lambda: self.send_key_combination(['ctrl', 'alt', 'del']))
        control_menu.add_command(label="发送Ctrl+C", command=lambda: self.send_key_combination(['ctrl', 'c']))
        control_menu.add_command(label="发送Ctrl+V", command=lambda: self.send_key_combination(['ctrl', 'v']))
        
        # 视图菜单
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="适应窗口", command=self.fit_to_window)
        view_menu.add_command(label="原始大小", command=lambda: self.set_scale(1.0))
        view_menu.add_command(label="50%", command=lambda: self.set_scale(0.5))
        view_menu.add_command(label="75%", command=lambda: self.set_scale(0.75))
        view_menu.add_command(label="125%", command=lambda: self.set_scale(1.25))
        view_menu.add_command(label="150%", command=lambda: self.set_scale(1.5))
        
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # 连接按钮
        self.connect_btn = ttk.Button(toolbar, text="连接服务器", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=0, padx=(0, 5))
        
        # 服务器地址
        ttk.Label(toolbar, text="服务器:").grid(row=0, column=1, padx=(10, 5))
        self.server_entry = ttk.Entry(toolbar, width=30)
        self.server_entry.insert(0, "localhost:8000")
        self.server_entry.grid(row=0, column=2, padx=(0, 10))
        
        # 控制按钮
        self.control_btn = ttk.Button(toolbar, text="开始控制", command=self.toggle_control, state="disabled")
        self.control_btn.grid(row=0, column=3, padx=(0, 5))
        
        # 缩放控制
        ttk.Label(toolbar, text="缩放:").grid(row=0, column=4, padx=(10, 5))
        self.scale_var = tk.StringVar(value="100%")
        scale_combo = ttk.Combobox(toolbar, textvariable=self.scale_var, values=["50%", "75%", "100%", "125%", "150%"], width=8)
        scale_combo.bind("<<ComboboxSelected>>", self.on_scale_changed)
        scale_combo.grid(row=0, column=5)
        
    def create_device_panel(self, parent):
        """创建设备面板"""
        device_frame = ttk.LabelFrame(parent, text="可用设备", padding="5")
        device_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # 设备列表
        self.device_tree = ttk.Treeview(device_frame, columns=('name', 'type', 'status'), show='tree headings', height=15)
        self.device_tree.heading('#0', text='设备ID')
        self.device_tree.heading('name', text='名称')
        self.device_tree.heading('type', text='类型')
        self.device_tree.heading('status', text='状态')
        
        self.device_tree.column('#0', width=150)
        self.device_tree.column('name', width=120)
        self.device_tree.column('type', width=80)
        self.device_tree.column('status', width=80)
        
        # 滚动条
        device_scrollbar = ttk.Scrollbar(device_frame, orient="vertical", command=self.device_tree.yview)
        self.device_tree.configure(yscrollcommand=device_scrollbar.set)
        
        self.device_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        device_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 双击事件
        self.device_tree.bind("<Double-1>", self.on_device_double_click)
        
        # 刷新按钮
        ttk.Button(device_frame, text="刷新", command=self.refresh_devices).grid(row=1, column=0, pady=(5, 0))
        
        device_frame.columnconfigure(0, weight=1)
        device_frame.rowconfigure(0, weight=1)
        
    def create_screen_panel(self, parent):
        """创建屏幕面板"""
        screen_frame = ttk.LabelFrame(parent, text="远程屏幕", padding="5")
        screen_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 远程屏幕
        self.remote_screen = RemoteScreen(screen_frame, self)
        
        screen_frame.columnconfigure(0, weight=1)
        screen_frame.rowconfigure(0, weight=1)
        
    def create_status_bar(self, parent):
        """创建状态栏"""
        self.status_var = tk.StringVar(value="未连接")
        status_bar = ttk.Label(parent, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
    def toggle_connection(self):
        """切换连接状态"""
        if self.running:
            self.disconnect()
        else:
            self.connect()
            
    def connect(self):
        """连接到服务器"""
        server_addr = self.server_entry.get().strip()
        if not server_addr.startswith("ws://") and not server_addr.startswith("wss://"):
            self.server_url = f"ws://{server_addr}/ws/{self.device_id}"
        else:
            self.server_url = f"{server_addr}/ws/{self.device_id}"
            
        self.running = True
        self.connect_btn.config(text="断开连接")
        self.server_entry.config(state="disabled")
        self.status_var.set("正在连接...")
        
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
        self.control_btn.config(state="disabled")
        self.status_var.set("未连接")
        
        # 清空设备列表
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)
            
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
            
    def run_client(self):
        """运行客户端"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.client_loop())
        except Exception as e:
            self.status_var.set(f"连接错误: {e}")
        finally:
            loop.close()
            
    async def client_loop(self):
        """客户端主循环"""
        while self.running:
            try:
                async with websockets.connect(self.server_url) as websocket:
                    self.websocket = websocket
                    self.status_var.set("已连接")
                    
                    # 发送设备信息
                    device_info = {
                        'type': 'device_info',
                        'name': self.device_name,
                        'device_type': 'controller',
                        'os': self.get_system_info()['os']
                    }
                    
                    await websocket.send(json.dumps(device_info))
                    
                    # 处理消息
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self.handle_message(data)
                        except json.JSONDecodeError:
                            logger.error("收到无效的JSON消息")
                        except Exception as e:
                            logger.error(f"处理消息时出错: {e}")
                            
            except websockets.exceptions.ConnectionClosed:
                self.status_var.set("连接已关闭")
            except Exception as e:
                self.status_var.set(f"连接错误: {e}")
                
            if self.running:
                await asyncio.sleep(5)
                
    async def handle_message(self, data):
        """处理收到的消息"""
        msg_type = data.get('type')
        
        if msg_type == 'device_list':
            # 更新设备列表
            devices = data.get('devices', {})
            self.root.after(0, lambda: self.update_device_list(devices))
            
        elif msg_type == 'control_request_result':
            # 控制请求结果
            success = data.get('success', False)
            message = data.get('message', '')
            self.root.after(0, lambda: self.handle_control_request_result(success, message))
            
        elif msg_type == 'control_response':
            # 控制响应
            accepted = data.get('accepted', False)
            if accepted:
                self.is_controlling = True
                self.root.after(0, lambda: self.control_btn.config(text="结束控制"))
                self.status_var.set("正在控制远程设备")
            else:
                self.status_var.set("控制请求被拒绝")
                
        elif msg_type == 'screen_data':
            # 屏幕数据
            if self.is_controlling:
                image_data = data.get('data')
                width = data.get('width')
                height = data.get('height')
                original_width = data.get('original_width')
                original_height = data.get('original_height')
                
                self.root.after(0, lambda: self.remote_screen.update_screen(
                    image_data, width, height, original_width, original_height
                ))
                
        elif msg_type == 'control_ended':
            # 控制结束
            self.is_controlling = False
            self.controlled_device = None
            self.root.after(0, lambda: self.control_btn.config(text="开始控制"))
            self.status_var.set("控制已结束")
            
    def update_device_list(self, devices):
        """更新设备列表"""
        # 清空现有列表
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)
            
        # 添加设备
        for device_id, device_info in devices.items():
            if device_info.get('device_type') == 'controlled':  # 只显示被控端设备
                self.device_tree.insert('', 'end', iid=device_id, text=device_id,
                                      values=(device_info.get('name', 'Unknown'),
                                             device_info.get('device_type', 'Unknown'),
                                             device_info.get('status', 'Unknown')))
                                             
        self.available_devices = devices
        
        # 更新控制按钮状态
        if devices:
            self.control_btn.config(state="normal")
        else:
            self.control_btn.config(state="disabled")
            
    def on_device_double_click(self, event):
        """设备双击事件"""
        selection = self.device_tree.selection()
        if selection and not self.is_controlling:
            device_id = selection[0]
            self.start_control(device_id)
            
    def toggle_control(self):
        """切换控制状态"""
        if self.is_controlling:
            self.end_control()
        else:
            selection = self.device_tree.selection()
            if selection:
                device_id = selection[0]
                self.start_control(device_id)
            else:
                messagebox.showwarning("警告", "请先选择要控制的设备")
                
    def start_control(self, device_id):
        """开始控制设备"""
        if device_id not in self.available_devices:
            messagebox.showerror("错误", "设备不可用")
            return
            
        # 可选：请求密码
        password = simpledialog.askstring("密码", "请输入连接密码（可选）:", show='*')
        
        # 发送控制请求
        control_request = {
            'type': 'control_request',
            'target_id': device_id,
            'password': password
        }
        
        if self.websocket:
            # 使用线程安全的方式发送消息
            threading.Thread(target=self._send_message_async, args=(control_request,), daemon=True).start()
            self.controlled_device = device_id
            self.status_var.set("正在请求控制...")
            
    def end_control(self):
        """结束控制"""
        if self.websocket and self.is_controlling:
            end_message = {'type': 'end_control'}
            threading.Thread(target=self._send_message_async, args=(end_message,), daemon=True).start()
            
        self.is_controlling = False
        self.controlled_device = None
        self.control_btn.config(text="开始控制")
        self.status_var.set("已连接")
        
    def handle_control_request_result(self, success, message):
        """处理控制请求结果"""
        if success:
            self.status_var.set(message)
        else:
            messagebox.showerror("控制请求失败", message)
            self.status_var.set("已连接")
            
    def send_mouse_event(self, event_type, x, y, button='left', **kwargs):
        """发送鼠标事件"""
        if self.websocket and self.is_controlling:
            event_data = {
                'type': 'mouse_event',
                'event_type': event_type,
                'x': x,
                'y': y,
                'button': button,
                **kwargs
            }
            threading.Thread(target=self._send_message_async, args=(event_data,), daemon=True).start()
            
    def send_keyboard_event(self, event_type, key, **kwargs):
        """发送键盘事件"""
        if self.websocket and self.is_controlling:
            event_data = {
                'type': 'keyboard_event',
                'event_type': event_type,
                'key': key,
                **kwargs
            }
            threading.Thread(target=self._send_message_async, args=(event_data,), daemon=True).start()
            
    def send_key_combination(self, keys):
        """发送组合键"""
        if self.websocket and self.is_controlling:
            event_data = {
                'type': 'keyboard_event',
                'event_type': 'press',
                'key': keys
            }
            threading.Thread(target=self._send_message_async, args=(event_data,), daemon=True).start()
            
    def refresh_devices(self):
        """刷新设备列表"""
        # 设备列表会通过WebSocket自动更新
        self.status_var.set("正在刷新设备列表...")
        
    def on_scale_changed(self, event):
        """缩放改变事件"""
        scale_text = self.scale_var.get()
        scale_value = float(scale_text.replace('%', '')) / 100
        self.set_scale(scale_value)
        
    def set_scale(self, scale):
        """设置缩放比例"""
        if self.remote_screen:
            self.remote_screen.set_scale(scale)
            self.scale_var.set(f"{int(scale * 100)}%")
            
    def fit_to_window(self):
        """适应窗口大小"""
        if self.remote_screen and self.remote_screen.remote_resolution:
            canvas_width = self.remote_screen.canvas.winfo_width()
            canvas_height = self.remote_screen.canvas.winfo_height()
            
            remote_width = self.remote_screen.remote_resolution['width']
            remote_height = self.remote_screen.remote_resolution['height']
            
            scale_x = canvas_width / remote_width
            scale_y = canvas_height / remote_height
            scale = min(scale_x, scale_y, 1.0)  # 不放大，只缩小
            
            self.set_scale(scale)
            
    def get_system_info(self):
        """获取系统信息"""
        import platform
        return {
            'os': platform.system(),
            'os_version': platform.version()
        }
        
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
    
    client = ControllerClient()
    client.run()

if __name__ == "__main__":
    main()