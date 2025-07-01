#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
远程桌面客户端

提供远程桌面客户端功能：
- 连接远程服务器
- 接收屏幕数据
- 发送控制指令
- 用户界面
"""

import asyncio
import argparse
import logging
import signal
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from PIL import Image, ImageTk
import io
import threading

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.network import NetworkManager, ConnectionConfig, ProtocolType
from core.protocol import ProtocolHandler, MessageType, ProtocolMessage
from core.security import SecurityManager, SecurityConfig, EncryptionType, AuthMethod
from utils.logger import setup_logger
from utils.config import load_config, save_config

logger = logging.getLogger(__name__)

class RDPClientGUI:
    """远程桌面客户端GUI"""
    
    def __init__(self, client):
        self.client = client
        self.root = tk.Tk()
        self.root.title("远程桌面客户端")
        self.root.geometry("1024x768")
        
        # 界面组件
        self.canvas = None
        self.status_label = None
        self.connect_button = None
        self.disconnect_button = None
        
        # 状态
        self.is_connected = False
        self.current_image = None
        self.scale_factor = 1.0
        
        self._setup_ui()
        self._setup_events()
    
    def _setup_ui(self):
        """设置用户界面"""
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 连接菜单
        connect_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="连接", menu=connect_menu)
        connect_menu.add_command(label="连接服务器", command=self._show_connect_dialog)
        connect_menu.add_command(label="断开连接", command=self._disconnect)
        connect_menu.add_separator()
        connect_menu.add_command(label="退出", command=self.root.quit)
        
        # 视图菜单
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="适应窗口", command=self._fit_to_window)
        view_menu.add_command(label="原始大小", command=self._original_size)
        view_menu.add_command(label="全屏", command=self._toggle_fullscreen)
        
        # 工具栏
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        self.connect_button = ttk.Button(toolbar, text="连接", command=self._show_connect_dialog)
        self.connect_button.pack(side=tk.LEFT, padx=2)
        
        self.disconnect_button = ttk.Button(toolbar, text="断开", command=self._disconnect, state=tk.DISABLED)
        self.disconnect_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Label(toolbar, text="缩放:").pack(side=tk.LEFT, padx=2)
        self.scale_var = tk.StringVar(value="100%")
        scale_combo = ttk.Combobox(toolbar, textvariable=self.scale_var, width=8, state="readonly")
        scale_combo['values'] = ('50%', '75%', '100%', '125%', '150%', '200%')
        scale_combo.pack(side=tk.LEFT, padx=2)
        scale_combo.bind('<<ComboboxSelected>>', self._on_scale_changed)
        
        # 状态栏
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, text="未连接")
        self.status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        # 主显示区域
        main_frame = ttk.Frame(self.root)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建滚动画布
        self.canvas_frame = ttk.Frame(main_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg='black')
        
        # 滚动条
        v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 布局滚动条和画布
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
    
    def _setup_events(self):
        """设置事件处理"""
        # 鼠标事件
        self.canvas.bind("<Button-1>", self._on_mouse_click)
        self.canvas.bind("<Button-2>", self._on_mouse_click)
        self.canvas.bind("<Button-3>", self._on_mouse_click)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        
        # 键盘事件
        self.canvas.bind("<KeyPress>", self._on_key_press)
        self.canvas.bind("<KeyRelease>", self._on_key_release)
        self.canvas.focus_set()
        
        # 窗口事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self._exit_fullscreen())
    
    def _show_connect_dialog(self):
        """显示连接对话框"""
        dialog = ConnectionDialog(self.root)
        if dialog.result:
            host, port, username, password = dialog.result
            asyncio.create_task(self.client.connect(host, port, username, password))
    
    def _disconnect(self):
        """断开连接"""
        asyncio.create_task(self.client.disconnect())
    
    def _on_scale_changed(self, event):
        """缩放改变"""
        scale_text = self.scale_var.get()
        self.scale_factor = float(scale_text.rstrip('%')) / 100.0
        self._update_display()
    
    def _fit_to_window(self):
        """适应窗口大小"""
        if self.current_image:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            image_width, image_height = self.current_image.size
            
            scale_x = canvas_width / image_width
            scale_y = canvas_height / image_height
            self.scale_factor = min(scale_x, scale_y)
            
            self.scale_var.set(f"{int(self.scale_factor * 100)}%")
            self._update_display()
    
    def _original_size(self):
        """原始大小"""
        self.scale_factor = 1.0
        self.scale_var.set("100%")
        self._update_display()
    
    def _toggle_fullscreen(self):
        """切换全屏"""
        self.root.attributes('-fullscreen', not self.root.attributes('-fullscreen'))
    
    def _exit_fullscreen(self):
        """退出全屏"""
        self.root.attributes('-fullscreen', False)
    
    def _on_mouse_click(self, event):
        """鼠标点击事件"""
        if not self.is_connected:
            return
        
        # 转换坐标
        x, y = self._canvas_to_remote_coords(event.x, event.y)
        
        button_map = {1: 'left', 2: 'middle', 3: 'right'}
        button = button_map.get(event.num, 'left')
        
        asyncio.create_task(self.client.send_mouse_event('click', x, y, button=button))
    
    def _on_mouse_move(self, event):
        """鼠标移动事件"""
        if not self.is_connected:
            return
        
        # 转换坐标
        x, y = self._canvas_to_remote_coords(event.x, event.y)
        
        asyncio.create_task(self.client.send_mouse_event('move', x, y))
    
    def _on_mouse_wheel(self, event):
        """鼠标滚轮事件"""
        if not self.is_connected:
            return
        
        x, y = self._canvas_to_remote_coords(event.x, event.y)
        dy = event.delta // 120  # Windows标准
        
        asyncio.create_task(self.client.send_mouse_event('scroll', x, y, dx=0, dy=dy))
    
    def _on_key_press(self, event):
        """按键按下事件"""
        if not self.is_connected:
            return
        
        key = event.keysym
        asyncio.create_task(self.client.send_keyboard_event('press', key))
    
    def _on_key_release(self, event):
        """按键释放事件"""
        if not self.is_connected:
            return
        
        key = event.keysym
        asyncio.create_task(self.client.send_keyboard_event('release', key))
    
    def _canvas_to_remote_coords(self, canvas_x, canvas_y):
        """将画布坐标转换为远程坐标"""
        if not self.current_image:
            return canvas_x, canvas_y
        
        # 考虑缩放因子
        remote_x = int(canvas_x / self.scale_factor)
        remote_y = int(canvas_y / self.scale_factor)
        
        return remote_x, remote_y
    
    def _on_closing(self):
        """窗口关闭事件"""
        if self.is_connected:
            asyncio.create_task(self.client.disconnect())
        self.root.quit()
    
    def update_status(self, status: str):
        """更新状态"""
        self.status_label.config(text=status)
    
    def set_connected(self, connected: bool):
        """设置连接状态"""
        self.is_connected = connected
        
        if connected:
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            self.update_status("已连接")
        else:
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            self.update_status("未连接")
            self.canvas.delete("all")
            self.current_image = None
    
    def display_frame(self, image_data: bytes):
        """显示屏幕帧"""
        try:
            # 从字节数据创建图像
            image = Image.open(io.BytesIO(image_data))
            self.current_image = image
            
            self._update_display()
            
        except Exception as e:
            logger.error(f"显示屏幕帧失败: {e}")
    
    def _update_display(self):
        """更新显示"""
        if not self.current_image:
            return
        
        try:
            # 应用缩放
            if self.scale_factor != 1.0:
                new_size = (
                    int(self.current_image.width * self.scale_factor),
                    int(self.current_image.height * self.scale_factor)
                )
                display_image = self.current_image.resize(new_size, Image.Resampling.LANCZOS)
            else:
                display_image = self.current_image
            
            # 转换为Tkinter格式
            photo = ImageTk.PhotoImage(display_image)
            
            # 更新画布
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # 保持引用防止垃圾回收
            self.canvas.image = photo
            
        except Exception as e:
            logger.error(f"更新显示失败: {e}")
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()

class ConnectionDialog:
    """连接对话框"""
    
    def __init__(self, parent):
        self.result = None
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("连接到服务器")
        self.dialog.geometry("300x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self._setup_ui()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def _setup_ui(self):
        """设置对话框界面"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 服务器地址
        ttk.Label(main_frame, text="服务器地址:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.host_var = tk.StringVar(value="localhost")
        ttk.Entry(main_frame, textvariable=self.host_var, width=20).grid(row=0, column=1, pady=2, padx=(5, 0))
        
        # 端口
        ttk.Label(main_frame, text="端口:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.port_var = tk.StringVar(value="8888")
        ttk.Entry(main_frame, textvariable=self.port_var, width=20).grid(row=1, column=1, pady=2, padx=(5, 0))
        
        # 用户名
        ttk.Label(main_frame, text="用户名:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.username_var = tk.StringVar(value="admin")
        ttk.Entry(main_frame, textvariable=self.username_var, width=20).grid(row=2, column=1, pady=2, padx=(5, 0))
        
        # 密码
        ttk.Label(main_frame, text="密码:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.password_var = tk.StringVar(value="password")
        ttk.Entry(main_frame, textvariable=self.password_var, width=20, show="*").grid(row=3, column=1, pady=2, padx=(5, 0))
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="连接", command=self._connect).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self._cancel).pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        self.dialog.bind('<Return>', lambda e: self._connect())
        self.dialog.bind('<Escape>', lambda e: self._cancel())
    
    def _connect(self):
        """连接"""
        try:
            host = self.host_var.get().strip()
            port = int(self.port_var.get().strip())
            username = self.username_var.get().strip()
            password = self.password_var.get()
            
            if not host or not username:
                messagebox.showerror("错误", "请填写服务器地址和用户名")
                return
            
            self.result = (host, port, username, password)
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("错误", "端口必须是数字")
    
    def _cancel(self):
        """取消"""
        self.dialog.destroy()

class RDPClient:
    """远程桌面客户端"""
    
    def __init__(self, config_file: Optional[str] = None):
        # 加载配置
        self.config = self._load_client_config(config_file)
        
        # 初始化组件
        self.network_manager = None
        self.protocol_handler = None
        self.security_manager = None
        self.gui = None
        
        # 连接状态
        self.is_connected = False
        self.connection_id = None
        self.session_id = None
        
        # 初始化组件
        self._init_components()
    
    def _load_client_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """加载客户端配置"""
        default_config = {
            'client': {
                'auto_reconnect': True,
                'reconnect_interval': 5,
                'heartbeat_interval': 30
            },
            'display': {
                'auto_scale': True,
                'quality': 'high',
                'color_depth': 24
            },
            'input': {
                'mouse_sensitivity': 1.0,
                'keyboard_layout': 'auto'
            },
            'security': {
                'encryption_type': 'aes_256_cbc',
                'verify_certificate': True
            },
            'logging': {
                'level': 'INFO',
                'file': 'rdp_client.log'
            }
        }
        
        if config_file and Path(config_file).exists():
            try:
                user_config = load_config(config_file)
                # 合并配置
                for section, values in user_config.items():
                    if section in default_config:
                        default_config[section].update(values)
                    else:
                        default_config[section] = values
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认配置")
        
        return default_config
    
    def _init_components(self):
        """初始化组件"""
        try:
            # 初始化日志
            setup_logger(
                level=self.config['logging']['level'],
                log_file=self.config['logging']['file']
            )
            
            # 初始化安全管理器
            security_config = SecurityConfig(
                encryption_type=EncryptionType(self.config['security']['encryption_type']),
                auth_method=AuthMethod.PASSWORD,
                require_encryption=True
            )
            self.security_manager = SecurityManager(security_config)
            
            # 初始化协议处理器
            self.protocol_handler = ProtocolHandler()
            
            # 初始化GUI
            self.gui = RDPClientGUI(self)
            
            logger.info("客户端组件初始化完成")
            
        except Exception as e:
            logger.error(f"组件初始化失败: {e}")
            raise
    
    async def connect(self, host: str, port: int, username: str, password: str):
        """连接到服务器"""
        try:
            logger.info(f"正在连接到服务器: {host}:{port}")
            self.gui.update_status("正在连接...")
            
            # 创建网络管理器
            network_config = ConnectionConfig(
                host=host,
                port=port,
                protocol=ProtocolType.TCP
            )
            self.network_manager = NetworkManager(network_config)
            
            # 注册消息处理器
            self.network_manager.register_message_handler('default', self._handle_server_message)
            
            # 连接到服务器
            self.connection_id = await self.network_manager.connect_to_server()
            
            if self.connection_id:
                # 发送连接请求
                connect_message = self.protocol_handler.create_message(
                    MessageType.CONNECT,
                    {
                        'client_info': {
                            'version': '1.0',
                            'platform': sys.platform,
                            'capabilities': ['screen_view', 'remote_control']
                        }
                    }
                )
                
                await self.network_manager.send_message(connect_message.to_dict(), self.connection_id)
                
                # 等待连接确认
                await asyncio.sleep(1)
                
                # 发送认证请求
                auth_message = self.protocol_handler.create_message(
                    MessageType.AUTH,
                    {
                        'username': username,
                        'password': password
                    }
                )
                
                await self.network_manager.send_message(auth_message.to_dict(), self.connection_id)
                
                logger.info("连接请求已发送")
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
            self.gui.update_status(f"连接失败: {e}")
            await self.disconnect()
    
    async def disconnect(self):
        """断开连接"""
        try:
            if self.is_connected and self.connection_id:
                # 发送断开连接消息
                disconnect_message = self.protocol_handler.create_message(
                    MessageType.DISCONNECT,
                    {'reason': 'user_request'}
                )
                
                await self.network_manager.send_message(disconnect_message.to_dict(), self.connection_id)
            
            # 清理状态
            self.is_connected = False
            self.connection_id = None
            self.session_id = None
            
            # 停止网络管理器
            if self.network_manager:
                await self.network_manager.stop()
                self.network_manager = None
            
            # 更新GUI
            self.gui.set_connected(False)
            
            logger.info("已断开连接")
            
        except Exception as e:
            logger.error(f"断开连接失败: {e}")
    
    async def _handle_server_message(self, message_dict: Dict[str, Any], connection_id: str):
        """处理服务器消息"""
        try:
            # 解析协议消息
            message = ProtocolMessage.from_dict(message_dict)
            
            if not self.protocol_handler.validate_message(message):
                logger.warning("收到无效消息")
                return
            
            # 处理不同类型的消息
            if message.header.message_type == MessageType.ACK:
                await self._handle_ack(message)
            elif message.header.message_type == MessageType.SCREEN_FRAME:
                await self._handle_screen_frame(message)
            elif message.header.message_type == MessageType.ERROR:
                await self._handle_error(message)
            elif message.header.message_type == MessageType.HEARTBEAT:
                await self._handle_heartbeat(message)
            else:
                logger.warning(f"未知消息类型: {message.header.message_type}")
            
        except Exception as e:
            logger.error(f"处理服务器消息失败: {e}")
    
    async def _handle_ack(self, message: ProtocolMessage):
        """处理确认消息"""
        try:
            status = message.payload.get('status', '')
            
            if status == 'connected':
                logger.info("服务器连接确认")
                self.gui.update_status("已连接，等待认证...")
            
            elif status == 'authenticated':
                self.session_id = message.payload.get('session_id')
                self.is_connected = True
                
                logger.info("认证成功")
                self.gui.set_connected(True)
                
                # 开始心跳
                asyncio.create_task(self._start_heartbeat())
            
        except Exception as e:
            logger.error(f"处理确认消息失败: {e}")
    
    async def _handle_screen_frame(self, message: ProtocolMessage):
        """处理屏幕帧"""
        try:
            frame_data = message.payload.get('frame_data', b'')
            
            if frame_data:
                # 在主线程中更新GUI
                self.gui.root.after(0, lambda: self.gui.display_frame(frame_data))
            
        except Exception as e:
            logger.error(f"处理屏幕帧失败: {e}")
    
    async def _handle_error(self, message: ProtocolMessage):
        """处理错误消息"""
        try:
            error_code = message.payload.get('error_code', '')
            error_message = message.payload.get('message', '')
            
            logger.error(f"服务器错误: {error_code} - {error_message}")
            self.gui.update_status(f"错误: {error_message}")
            
            if error_code == 'AUTH_FAILED':
                await self.disconnect()
                messagebox.showerror("认证失败", error_message)
            
        except Exception as e:
            logger.error(f"处理错误消息失败: {e}")
    
    async def _handle_heartbeat(self, message: ProtocolMessage):
        """处理心跳"""
        # 心跳响应，保持连接活跃
        pass
    
    async def _start_heartbeat(self):
        """开始心跳"""
        try:
            interval = self.config['client']['heartbeat_interval']
            
            while self.is_connected:
                await asyncio.sleep(interval)
                
                if self.is_connected and self.connection_id:
                    heartbeat_message = self.protocol_handler.create_heartbeat_message()
                    await self.network_manager.send_message(heartbeat_message.to_dict(), self.connection_id)
            
        except Exception as e:
            logger.error(f"心跳失败: {e}")
    
    async def send_mouse_event(self, event_type: str, x: int, y: int, **kwargs):
        """发送鼠标事件"""
        try:
            if not self.is_connected or not self.connection_id:
                return
            
            payload = {
                'event_type': event_type,
                'x': x,
                'y': y
            }
            payload.update(kwargs)
            
            message = self.protocol_handler.create_message(MessageType.MOUSE_EVENT, payload)
            await self.network_manager.send_message(message.to_dict(), self.connection_id)
            
        except Exception as e:
            logger.error(f"发送鼠标事件失败: {e}")
    
    async def send_keyboard_event(self, event_type: str, key: str, **kwargs):
        """发送键盘事件"""
        try:
            if not self.is_connected or not self.connection_id:
                return
            
            payload = {
                'event_type': event_type,
                'key': key
            }
            payload.update(kwargs)
            
            message = self.protocol_handler.create_message(MessageType.KEYBOARD_EVENT, payload)
            await self.network_manager.send_message(message.to_dict(), self.connection_id)
            
        except Exception as e:
            logger.error(f"发送键盘事件失败: {e}")
    
    def start_gui(self):
        """启动GUI界面"""
        self.run()
    
    def run(self):
        """运行客户端"""
        # 在单独线程中运行asyncio事件循环
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_forever()
        
        async_thread = threading.Thread(target=run_async_loop, daemon=True)
        async_thread.start()
        
        # 运行GUI主循环
        self.gui.run()

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='远程桌面客户端')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--host', help='服务器地址')
    parser.add_argument('--port', type=int, help='服务器端口')
    parser.add_argument('--username', help='用户名')
    parser.add_argument('--password', help='密码')
    
    args = parser.parse_args()
    
    # 创建客户端
    client = RDPClient(args.config)
    
    # 如果提供了命令行参数，直接连接
    if args.host and args.username:
        port = args.port or 8888
        password = args.password or ''
        
        # 在后台连接
        asyncio.create_task(client.connect(args.host, port, args.username, password))
    
    # 运行客户端
    client.run()

if __name__ == '__main__':
    # 对于GUI应用，直接运行
    client = RDPClient()
    client.run()