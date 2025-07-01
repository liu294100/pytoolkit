#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
远程桌面服务端

提供远程桌面服务功能：
- 屏幕共享服务
- 远程控制接收
- 多客户端管理
- 安全认证
"""

import asyncio
import argparse
import logging
import signal
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.network import NetworkManager, ConnectionConfig, ProtocolType
from core.screen import ScreenCapture, CaptureConfig, CaptureMethod, CompressionFormat
from core.input import InputController, InputConfig, InputEvent, InputType
from core.protocol import ProtocolHandler, MessageType, ProtocolMessage
from core.security import SecurityManager, SecurityConfig, EncryptionType, AuthMethod
from utils.logger import setup_logger
from utils.config import load_config, save_config

logger = logging.getLogger(__name__)

class RDPServer:
    """远程桌面服务器"""
    
    def __init__(self, config_file: Optional[str] = None):
        # 加载配置
        self.config = self._load_server_config(config_file)
        
        # 初始化组件
        self.network_manager = None
        self.screen_capture = None
        self.input_controller = None
        self.protocol_handler = None
        self.security_manager = None
        
        # 运行状态
        self.is_running = False
        self.clients: Dict[str, Dict[str, Any]] = {}  # 连接的客户端
        
        # 初始化所有组件
        self._init_components()
    
    def _load_server_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """加载服务器配置"""
        default_config = {
            'server': {
                'host': '0.0.0.0',
                'port': 8888,
                'protocol': 'tcp',
                'max_clients': 10
            },
            'screen': {
                'method': 'pil',
                'format': 'jpeg',
                'quality': 80,
                'fps': 30,
                'scale_factor': 1.0
            },
            'input': {
                'enable_mouse': True,
                'enable_keyboard': True,
                'security_enabled': True
            },
            'security': {
                'encryption_type': 'aes_256_cbc',
                'auth_method': 'password',
                'require_encryption': True,
                'session_timeout': 3600
            },
            'logging': {
                'level': 'INFO',
                'file': 'rdp_server.log'
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
        """初始化所有组件"""
        try:
            # 初始化日志
            setup_logger(
                level=self.config['logging']['level'],
                log_file=self.config['logging']['file']
            )
            
            # 初始化安全管理器
            security_config = SecurityConfig(
                encryption_type=EncryptionType(self.config['security']['encryption_type']),
                auth_method=AuthMethod(self.config['security']['auth_method']),
                require_encryption=self.config['security']['require_encryption'],
                session_timeout=self.config['security']['session_timeout']
            )
            self.security_manager = SecurityManager(security_config)
            
            # 初始化协议处理器
            self.protocol_handler = ProtocolHandler()
            
            # 初始化网络管理器
            network_config = ConnectionConfig(
                host=self.config['server']['host'],
                port=self.config['server']['port'],
                protocol=ProtocolType(self.config['server']['protocol']),
                max_connections=self.config['server']['max_clients']
            )
            self.network_manager = NetworkManager(network_config)
            
            # 初始化屏幕捕获
            capture_config = CaptureConfig(
                method=CaptureMethod(self.config['screen']['method']),
                format=CompressionFormat(self.config['screen']['format']),
                quality=self.config['screen']['quality'],
                fps=self.config['screen']['fps'],
                scale_factor=self.config['screen']['scale_factor']
            )
            self.screen_capture = ScreenCapture(capture_config)
            
            # 初始化输入控制器
            input_config = InputConfig(
                enable_mouse=self.config['input']['enable_mouse'],
                enable_keyboard=self.config['input']['enable_keyboard'],
                security_enabled=self.config['input']['security_enabled']
            )
            self.input_controller = InputController(input_config)
            
            logger.info("服务器组件初始化完成")
            
        except Exception as e:
            logger.error(f"组件初始化失败: {e}")
            raise
    
    async def start(self):
        """启动服务器"""
        try:
            logger.info("正在启动远程桌面服务器...")
            
            # 注册消息处理器
            self.network_manager.register_message_handler('default', self._handle_client_message)
            
            # 启动输入控制器
            self.input_controller.start_processing()
            
            # 启动网络服务
            self.is_running = True
            
            logger.info(f"服务器启动成功: {self.config['server']['protocol']}://{self.config['server']['host']}:{self.config['server']['port']}")
            
            # 启动网络服务器（这会阻塞）
            await self.network_manager.start_server()
            
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """停止服务器"""
        logger.info("正在停止服务器...")
        
        self.is_running = False
        
        # 停止屏幕捕获
        if self.screen_capture:
            self.screen_capture.stop_capture_stream()
        
        # 停止输入控制器
        if self.input_controller:
            self.input_controller.stop_processing()
        
        # 停止网络服务
        if self.network_manager:
            await self.network_manager.stop()
        
        # 清理客户端
        self.clients.clear()
        
        logger.info("服务器已停止")
    
    async def _handle_client_message(self, message_dict: Dict[str, Any], connection_id: str):
        """处理客户端消息"""
        try:
            # 解析协议消息
            message = ProtocolMessage.from_dict(message_dict)
            
            if not self.protocol_handler.validate_message(message):
                logger.warning(f"无效消息: {connection_id}")
                return
            
            # 处理不同类型的消息
            if message.header.message_type == MessageType.CONNECT:
                await self._handle_connect(message, connection_id)
            elif message.header.message_type == MessageType.AUTH:
                await self._handle_auth(message, connection_id)
            elif message.header.message_type == MessageType.MOUSE_EVENT:
                await self._handle_mouse_event(message, connection_id)
            elif message.header.message_type == MessageType.KEYBOARD_EVENT:
                await self._handle_keyboard_event(message, connection_id)
            elif message.header.message_type == MessageType.HEARTBEAT:
                await self._handle_heartbeat(message, connection_id)
            elif message.header.message_type == MessageType.DISCONNECT:
                await self._handle_disconnect(message, connection_id)
            else:
                logger.warning(f"未知消息类型: {message.header.message_type}")
            
        except Exception as e:
            logger.error(f"处理客户端消息失败: {e}")
    
    async def _handle_connect(self, message: ProtocolMessage, connection_id: str):
        """处理连接请求"""
        try:
            client_info = message.payload.get('client_info', {})
            
            # 记录客户端信息
            self.clients[connection_id] = {
                'client_info': client_info,
                'connected_time': message.header.timestamp,
                'last_activity': message.header.timestamp,
                'session_id': None,
                'is_authenticated': False,
                'is_streaming': False
            }
            
            # 发送连接确认
            response = self.protocol_handler.create_message(
                MessageType.ACK,
                {
                    'status': 'connected',
                    'server_info': {
                        'version': '1.0',
                        'capabilities': ['screen_share', 'remote_control'],
                        'encryption_required': self.security_manager.config.require_encryption
                    }
                }
            )
            
            await self.network_manager.send_message(response.to_dict(), connection_id)
            
            logger.info(f"客户端连接: {connection_id}")
            
        except Exception as e:
            logger.error(f"处理连接请求失败: {e}")
    
    async def _handle_auth(self, message: ProtocolMessage, connection_id: str):
        """处理认证请求"""
        try:
            username = message.payload.get('username', '')
            password = message.payload.get('password', '')
            
            # 进行认证
            session_id = self.security_manager.authenticate(username, password)
            
            if session_id:
                # 认证成功
                self.clients[connection_id]['session_id'] = session_id
                self.clients[connection_id]['is_authenticated'] = True
                
                response = self.protocol_handler.create_message(
                    MessageType.ACK,
                    {
                        'status': 'authenticated',
                        'session_id': session_id,
                        'permissions': self.security_manager.get_session_info(session_id).get('permissions', [])
                    }
                )
                
                logger.info(f"客户端认证成功: {connection_id}, 用户: {username}")
                
                # 开始屏幕共享
                await self._start_screen_sharing(connection_id)
                
            else:
                # 认证失败
                response = self.protocol_handler.create_error_message(
                    'AUTH_FAILED',
                    '用户名或密码错误'
                )
                
                logger.warning(f"客户端认证失败: {connection_id}, 用户: {username}")
            
            await self.network_manager.send_message(response.to_dict(), connection_id)
            
        except Exception as e:
            logger.error(f"处理认证请求失败: {e}")
    
    async def _start_screen_sharing(self, connection_id: str):
        """开始屏幕共享"""
        try:
            if connection_id not in self.clients:
                return
            
            client = self.clients[connection_id]
            if not client['is_authenticated']:
                return
            
            # 添加帧回调
            def frame_callback(frame_data: bytes):
                asyncio.create_task(self._send_screen_frame(frame_data, connection_id))
            
            self.screen_capture.add_frame_callback(frame_callback)
            
            # 如果还没有开始捕获，则开始
            if not self.screen_capture.is_capturing:
                self.screen_capture.start_capture_stream(frame_callback)
            
            client['is_streaming'] = True
            
            logger.info(f"开始屏幕共享: {connection_id}")
            
        except Exception as e:
            logger.error(f"开始屏幕共享失败: {e}")
    
    async def _send_screen_frame(self, frame_data: bytes, connection_id: str):
        """发送屏幕帧"""
        try:
            if connection_id not in self.clients:
                return
            
            client = self.clients[connection_id]
            if not client['is_streaming']:
                return
            
            # 创建屏幕帧消息
            frame_info = {
                'timestamp': message.header.timestamp,
                'format': self.screen_capture.config.format.value,
                'quality': self.screen_capture.config.quality,
                'size': len(frame_data)
            }
            
            message = self.protocol_handler.create_screen_frame_message(frame_data, frame_info)
            
            # 加密数据（如果需要）
            session_id = client.get('session_id')
            if session_id and self.security_manager.config.require_encryption:
                # 这里可以对整个消息进行加密
                pass
            
            await self.network_manager.send_message(message.to_dict(), connection_id)
            
        except Exception as e:
            logger.error(f"发送屏幕帧失败: {e}")
    
    async def _handle_mouse_event(self, message: ProtocolMessage, connection_id: str):
        """处理鼠标事件"""
        try:
            if not self._is_client_authorized(connection_id, 'control'):
                return
            
            event_type = message.payload.get('event_type', '')
            x = message.payload.get('x', 0)
            y = message.payload.get('y', 0)
            button = message.payload.get('button', 'left')
            clicks = message.payload.get('clicks', 1)
            
            if event_type == 'move':
                self.input_controller.mouse_move(x, y)
            elif event_type == 'click':
                self.input_controller.mouse_click(button, clicks)
            elif event_type == 'scroll':
                dx = message.payload.get('dx', 0)
                dy = message.payload.get('dy', 0)
                self.input_controller.mouse_scroll(dx, dy)
            
            # 更新客户端活动时间
            self.clients[connection_id]['last_activity'] = message.header.timestamp
            
        except Exception as e:
            logger.error(f"处理鼠标事件失败: {e}")
    
    async def _handle_keyboard_event(self, message: ProtocolMessage, connection_id: str):
        """处理键盘事件"""
        try:
            if not self._is_client_authorized(connection_id, 'control'):
                return
            
            event_type = message.payload.get('event_type', '')
            key = message.payload.get('key', '')
            text = message.payload.get('text', '')
            
            if event_type == 'press':
                self.input_controller.key_press(key)
            elif event_type == 'release':
                self.input_controller.key_release(key)
            elif event_type == 'type':
                self.input_controller.key_type(text)
            
            # 更新客户端活动时间
            self.clients[connection_id]['last_activity'] = message.header.timestamp
            
        except Exception as e:
            logger.error(f"处理键盘事件失败: {e}")
    
    async def _handle_heartbeat(self, message: ProtocolMessage, connection_id: str):
        """处理心跳"""
        try:
            if connection_id in self.clients:
                self.clients[connection_id]['last_activity'] = message.header.timestamp
            
            # 发送心跳响应
            response = self.protocol_handler.create_heartbeat_message()
            await self.network_manager.send_message(response.to_dict(), connection_id)
            
        except Exception as e:
            logger.error(f"处理心跳失败: {e}")
    
    async def _handle_disconnect(self, message: ProtocolMessage, connection_id: str):
        """处理断开连接"""
        try:
            if connection_id in self.clients:
                client = self.clients[connection_id]
                session_id = client.get('session_id')
                
                # 登出会话
                if session_id:
                    self.security_manager.logout(session_id)
                
                # 移除客户端
                del self.clients[connection_id]
                
                logger.info(f"客户端断开连接: {connection_id}")
            
        except Exception as e:
            logger.error(f"处理断开连接失败: {e}")
    
    def _is_client_authorized(self, connection_id: str, permission: str) -> bool:
        """检查客户端权限"""
        if connection_id not in self.clients:
            return False
        
        client = self.clients[connection_id]
        if not client['is_authenticated']:
            return False
        
        session_id = client.get('session_id')
        if not session_id:
            return False
        
        # 验证会话
        if not self.security_manager.validate_session(session_id):
            return False
        
        # 检查权限
        session_info = self.security_manager.get_session_info(session_id)
        if session_info:
            permissions = session_info.get('permissions', [])
            return permission in permissions or 'all' in permissions
        
        return False
    
    def get_server_stats(self) -> Dict[str, Any]:
        """获取服务器统计信息"""
        return {
            'is_running': self.is_running,
            'connected_clients': len(self.clients),
            'authenticated_clients': sum(1 for c in self.clients.values() if c['is_authenticated']),
            'streaming_clients': sum(1 for c in self.clients.values() if c['is_streaming']),
            'network_stats': self.network_manager.get_connection_info() if self.network_manager else [],
            'screen_stats': self.screen_capture.get_stats() if self.screen_capture else {},
            'input_stats': self.input_controller.get_stats() if self.input_controller else {},
            'security_stats': self.security_manager.get_stats() if self.security_manager else {}
        }

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='远程桌面服务器')
    parser.add_argument('--host', default='0.0.0.0', help='服务器地址')
    parser.add_argument('--port', type=int, default=8888, help='服务器端口')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--protocol', choices=['tcp', 'udp', 'websocket'], default='tcp', help='网络协议')
    
    args = parser.parse_args()
    
    # 创建服务器
    server = RDPServer(args.config)
    
    # 覆盖命令行参数
    if args.host != '0.0.0.0':
        server.config['server']['host'] = args.host
    if args.port != 8888:
        server.config['server']['port'] = args.port
    if args.protocol != 'tcp':
        server.config['server']['protocol'] = args.protocol
    
    # 重新初始化网络组件
    network_config = ConnectionConfig(
        host=server.config['server']['host'],
        port=server.config['server']['port'],
        protocol=ProtocolType(server.config['server']['protocol'])
    )
    server.network_manager = NetworkManager(network_config)
    
    # 信号处理
    def signal_handler(signum, frame):
        logger.info("收到停止信号，正在关闭服务器...")
        asyncio.create_task(server.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动服务器
        await server.start()
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器运行错误: {e}")
    finally:
        await server.stop()

if __name__ == '__main__':
    asyncio.run(main())