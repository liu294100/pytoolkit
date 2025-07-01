#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网络通信模块

支持多种协议的网络通信管理：
- TCP/UDP 双向代理
- HTTP/HTTPS/WebSocket 通道
- SOCKS4/SOCKS5 代理
- 异步IO和连接池管理
"""

import asyncio
import socket
import ssl
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ProtocolType(Enum):
    """支持的协议类型"""
    TCP = "tcp"
    UDP = "udp"
    HTTP = "http"
    HTTPS = "https"
    WEBSOCKET = "websocket"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

@dataclass
class ConnectionConfig:
    """连接配置"""
    host: str
    port: int
    protocol: ProtocolType
    ssl_context: Optional[ssl.SSLContext] = None
    timeout: float = 30.0
    max_connections: int = 100
    buffer_size: int = 8192
    
class NetworkManager:
    """网络管理器"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.connections: Dict[str, Any] = {}
        self.server = None
        self.is_running = False
        self.message_handlers: Dict[str, Callable] = {}
        
    async def start_server(self, message_handler: Optional[Callable] = None):
        """启动服务器"""
        try:
            if self.config.protocol == ProtocolType.TCP:
                self.server = await asyncio.start_server(
                    self._handle_tcp_client,
                    self.config.host,
                    self.config.port,
                    ssl=self.config.ssl_context
                )
            elif self.config.protocol == ProtocolType.UDP:
                await self._start_udp_server()
            elif self.config.protocol == ProtocolType.WEBSOCKET:
                await self._start_websocket_server()
            
            self.is_running = True
            if message_handler:
                self.message_handlers['default'] = message_handler
                
            logger.info(f"服务器启动成功: {self.config.protocol.value}://{self.config.host}:{self.config.port}")
            
            if self.server:
                await self.server.serve_forever()
                
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            raise
    
    async def connect_to_server(self) -> bool:
        """连接到服务器"""
        try:
            if self.config.protocol == ProtocolType.TCP:
                reader, writer = await asyncio.open_connection(
                    self.config.host,
                    self.config.port,
                    ssl=self.config.ssl_context
                )
                self.connections['main'] = {'reader': reader, 'writer': writer}
                
            elif self.config.protocol == ProtocolType.WEBSOCKET:
                await self._connect_websocket()
                
            logger.info(f"连接服务器成功: {self.config.host}:{self.config.port}")
            return True
            
        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            return False
    
    async def send_message(self, message: Dict[str, Any], connection_id: str = 'main'):
        """发送消息"""
        try:
            data = json.dumps(message).encode('utf-8')
            
            if connection_id in self.connections:
                conn = self.connections[connection_id]
                
                if 'writer' in conn:
                    # TCP连接
                    writer = conn['writer']
                    # 发送消息长度前缀
                    length = len(data)
                    writer.write(length.to_bytes(4, byteorder='big'))
                    writer.write(data)
                    await writer.drain()
                    
                elif 'websocket' in conn:
                    # WebSocket连接
                    await conn['websocket'].send(data)
                    
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
    
    async def receive_message(self, connection_id: str = 'main') -> Optional[Dict[str, Any]]:
        """接收消息"""
        try:
            if connection_id in self.connections:
                conn = self.connections[connection_id]
                
                if 'reader' in conn:
                    # TCP连接
                    reader = conn['reader']
                    # 读取消息长度
                    length_data = await reader.read(4)
                    if not length_data:
                        return None
                    
                    length = int.from_bytes(length_data, byteorder='big')
                    # 读取消息内容
                    data = await reader.read(length)
                    if data:
                        return json.loads(data.decode('utf-8'))
                        
                elif 'websocket' in conn:
                    # WebSocket连接
                    data = await conn['websocket'].recv()
                    return json.loads(data.decode('utf-8'))
                    
        except Exception as e:
            logger.error(f"接收消息失败: {e}")
        
        return None
    
    async def _handle_tcp_client(self, reader, writer):
        """处理TCP客户端连接"""
        client_addr = writer.get_extra_info('peername')
        connection_id = f"client_{client_addr[0]}_{client_addr[1]}"
        
        self.connections[connection_id] = {
            'reader': reader,
            'writer': writer,
            'address': client_addr
        }
        
        logger.info(f"客户端连接: {client_addr}")
        
        try:
            while True:
                message = await self.receive_message(connection_id)
                if message is None:
                    break
                    
                # 处理消息
                if 'default' in self.message_handlers:
                    await self.message_handlers['default'](message, connection_id)
                    
        except Exception as e:
            logger.error(f"处理客户端连接错误: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            if connection_id in self.connections:
                del self.connections[connection_id]
            logger.info(f"客户端断开: {client_addr}")
    
    async def _start_udp_server(self):
        """启动UDP服务器"""
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPProtocol(self),
            local_addr=(self.config.host, self.config.port)
        )
        self.server = transport
    
    async def _start_websocket_server(self):
        """启动WebSocket服务器"""
        try:
            import websockets
            
            async def websocket_handler(websocket, path):
                connection_id = f"ws_{websocket.remote_address[0]}_{websocket.remote_address[1]}"
                self.connections[connection_id] = {'websocket': websocket}
                
                try:
                    async for message in websocket:
                        data = json.loads(message)
                        if 'default' in self.message_handlers:
                            await self.message_handlers['default'](data, connection_id)
                except Exception as e:
                    logger.error(f"WebSocket处理错误: {e}")
                finally:
                    if connection_id in self.connections:
                        del self.connections[connection_id]
            
            self.server = await websockets.serve(
                websocket_handler,
                self.config.host,
                self.config.port,
                ssl=self.config.ssl_context
            )
            
        except ImportError:
            logger.error("WebSocket支持需要安装websockets库")
            raise
    
    async def _connect_websocket(self):
        """连接WebSocket服务器"""
        try:
            import websockets
            
            uri = f"ws://{self.config.host}:{self.config.port}"
            if self.config.ssl_context:
                uri = f"wss://{self.config.host}:{self.config.port}"
            
            websocket = await websockets.connect(uri, ssl=self.config.ssl_context)
            self.connections['main'] = {'websocket': websocket}
            
        except ImportError:
            logger.error("WebSocket支持需要安装websockets库")
            raise
    
    async def stop(self):
        """停止网络服务"""
        self.is_running = False
        
        # 关闭所有连接
        for conn_id, conn in list(self.connections.items()):
            try:
                if 'writer' in conn:
                    conn['writer'].close()
                    await conn['writer'].wait_closed()
                elif 'websocket' in conn:
                    await conn['websocket'].close()
            except Exception as e:
                logger.error(f"关闭连接错误: {e}")
        
        self.connections.clear()
        
        # 关闭服务器
        if self.server:
            if hasattr(self.server, 'close'):
                self.server.close()
                if hasattr(self.server, 'wait_closed'):
                    await self.server.wait_closed()
        
        logger.info("网络服务已停止")
    
    def register_message_handler(self, handler_name: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[handler_name] = handler
    
    def get_connection_count(self) -> int:
        """获取连接数量"""
        return len(self.connections)
    
    def get_connection_info(self) -> List[Dict[str, Any]]:
        """获取连接信息"""
        info = []
        for conn_id, conn in self.connections.items():
            conn_info = {
                'id': conn_id,
                'type': 'tcp' if 'writer' in conn else 'websocket',
                'address': conn.get('address', 'unknown')
            }
            info.append(conn_info)
        return info

class UDPProtocol(asyncio.DatagramProtocol):
    """UDP协议处理器"""
    
    def __init__(self, network_manager: NetworkManager):
        self.network_manager = network_manager
        self.transport = None
    
    def connection_made(self, transport):
        self.transport = transport
        logger.info("UDP服务器启动")
    
    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode('utf-8'))
            connection_id = f"udp_{addr[0]}_{addr[1]}"
            
            # 存储UDP连接信息
            self.network_manager.connections[connection_id] = {
                'transport': self.transport,
                'address': addr
            }
            
            # 处理消息
            if 'default' in self.network_manager.message_handlers:
                asyncio.create_task(
                    self.network_manager.message_handlers['default'](message, connection_id)
                )
                
        except Exception as e:
            logger.error(f"UDP消息处理错误: {e}")
    
    def error_received(self, exc):
        logger.error(f"UDP错误: {exc}")