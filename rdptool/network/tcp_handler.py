#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TCP处理模块

实现TCP服务器和客户端的异步通信功能，包括：
- TCP服务器实现
- TCP客户端实现
- 连接管理
- 数据传输
- 心跳检测
- 重连机制
"""

import asyncio
import socket
import ssl
import time
import uuid
from typing import Optional, Dict, Any, Callable, Tuple, List
from dataclasses import dataclass, field
import logging
import weakref
from enum import Enum

from .connection_manager import ConnectionInfo, ConnectionStatus, ConnectionType, NetworkEvent, NetworkEventType

class TCPConnectionState(Enum):
    """TCP连接状态"""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    TRANSFERRING = "transferring"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"

@dataclass
class TCPServerConfig:
    """TCP服务器配置"""
    host: str = '0.0.0.0'
    port: int = 3389
    backlog: int = 100
    buffer_size: int = 8192
    timeout: float = 30.0
    keepalive_interval: float = 60.0
    max_connections: int = 100
    ssl_context: Optional[ssl.SSLContext] = None
    reuse_address: bool = True
    reuse_port: bool = False
    nodelay: bool = True
    linger: Optional[Tuple[int, int]] = None
    recv_buffer_size: Optional[int] = None
    send_buffer_size: Optional[int] = None
    auth_required: bool = False
    auth_timeout: float = 10.0
    compression: bool = False
    encryption: bool = False

@dataclass
class TCPClientConfig:
    """TCP客户端配置"""
    host: str
    port: int
    buffer_size: int = 8192
    timeout: float = 30.0
    keepalive_interval: float = 60.0
    ssl_context: Optional[ssl.SSLContext] = None
    local_addr: Optional[Tuple[str, int]] = None
    nodelay: bool = True
    linger: Optional[Tuple[int, int]] = None
    recv_buffer_size: Optional[int] = None
    send_buffer_size: Optional[int] = None
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 3
    reconnect_delay: float = 5.0
    auth_data: Optional[Dict[str, Any]] = None
    compression: bool = False
    encryption: bool = False

@dataclass
class TCPConnectionInfo(ConnectionInfo):
    """TCP连接信息"""
    tcp_state: TCPConnectionState = TCPConnectionState.IDLE
    ssl_enabled: bool = False
    compression_enabled: bool = False
    encryption_enabled: bool = False
    auth_status: str = "none"
    keepalive_count: int = 0
    last_keepalive: float = 0.0
    socket_info: Optional[Dict[str, Any]] = None

class TCPConnection:
    """
    TCP连接封装
    
    封装asyncio的StreamReader和StreamWriter
    """
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                 conn_info: TCPConnectionInfo, config: Dict[str, Any]):
        self.reader = reader
        self.writer = writer
        self.conn_info = conn_info
        self.config = config
        
        # 状态管理
        self._closed = False
        self._closing = False
        
        # 心跳管理
        self._keepalive_task: Optional[asyncio.Task] = None
        self._last_activity = time.time()
        
        # 事件回调
        self.on_data_received: Optional[Callable] = None
        self.on_connection_lost: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 日志记录器
        self.logger = logging.getLogger(f"network.tcp.connection.{conn_info.conn_id}")
        
        # 启动心跳
        if config.get('keepalive_interval', 0) > 0:
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
    
    @property
    def is_connected(self) -> bool:
        """检查连接是否有效"""
        return not self._closed and not self.writer.is_closing()
    
    @property
    def remote_address(self) -> Optional[Tuple[str, int]]:
        """获取远程地址"""
        try:
            return self.writer.get_extra_info('peername')
        except Exception:
            return None
    
    @property
    def local_address(self) -> Optional[Tuple[str, int]]:
        """获取本地地址"""
        try:
            return self.writer.get_extra_info('sockname')
        except Exception:
            return None
    
    async def send_data(self, data: bytes) -> bool:
        """
        发送数据
        
        Args:
            data: 要发送的数据
        
        Returns:
            bool: 是否发送成功
        """
        if not self.is_connected:
            return False
        
        try:
            self.writer.write(data)
            await self.writer.drain()
            
            # 更新统计信息
            self.conn_info.bytes_sent += len(data)
            self.conn_info.packets_sent += 1
            self.conn_info.last_activity = time.time()
            self._last_activity = time.time()
            
            self.logger.debug(f"发送数据: {len(data)} 字节")
            return True
            
        except Exception as e:
            self.logger.error(f"发送数据失败: {e}")
            await self._handle_error(e)
            return False
    
    async def receive_data(self, size: int = -1) -> Optional[bytes]:
        """
        接收数据
        
        Args:
            size: 要接收的字节数，-1表示接收所有可用数据
        
        Returns:
            bytes: 接收到的数据，None表示连接已关闭
        """
        if not self.is_connected:
            return None
        
        try:
            if size == -1:
                data = await self.reader.read(self.config.get('buffer_size', 8192))
            else:
                data = await self.reader.read(size)
            
            if not data:
                # 连接已关闭
                await self._handle_connection_lost()
                return None
            
            # 更新统计信息
            self.conn_info.bytes_received += len(data)
            self.conn_info.packets_received += 1
            self.conn_info.last_activity = time.time()
            self._last_activity = time.time()
            
            self.logger.debug(f"接收数据: {len(data)} 字节")
            
            # 调用数据接收回调
            if self.on_data_received:
                try:
                    await self.on_data_received(data)
                except Exception as e:
                    self.logger.error(f"数据接收回调错误: {e}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"接收数据失败: {e}")
            await self._handle_error(e)
            return None
    
    async def send_keepalive(self) -> bool:
        """
        发送心跳包
        
        Returns:
            bool: 是否发送成功
        """
        # 简单的心跳包（可以根据协议自定义）
        keepalive_data = b'\x00\x00\x00\x00'  # 4字节的心跳包
        
        if await self.send_data(keepalive_data):
            self.conn_info.keepalive_count += 1
            self.conn_info.last_keepalive = time.time()
            self.logger.debug("心跳包已发送")
            return True
        
        return False
    
    async def close(self, reason: str = "normal"):
        """
        关闭连接
        
        Args:
            reason: 关闭原因
        """
        if self._closed or self._closing:
            return
        
        self._closing = True
        self.conn_info.tcp_state = TCPConnectionState.CLOSING
        
        try:
            # 停止心跳任务
            if self._keepalive_task:
                self._keepalive_task.cancel()
                try:
                    await self._keepalive_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭写入端
            if not self.writer.is_closing():
                self.writer.close()
                await self.writer.wait_closed()
            
            self._closed = True
            self.conn_info.tcp_state = TCPConnectionState.CLOSED
            self.conn_info.status = ConnectionStatus.DISCONNECTED
            
            self.logger.info(f"连接已关闭: {reason}")
            
        except Exception as e:
            self.logger.error(f"关闭连接时发生错误: {e}")
        
        finally:
            self._closed = True
            self._closing = False
    
    async def _keepalive_loop(self):
        """
        心跳循环
        """
        interval = self.config.get('keepalive_interval', 60.0)
        
        try:
            while self.is_connected:
                await asyncio.sleep(interval)
                
                if not self.is_connected:
                    break
                
                # 检查是否需要发送心跳
                current_time = time.time()
                if current_time - self._last_activity >= interval:
                    if not await self.send_keepalive():
                        break
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"心跳循环错误: {e}")
    
    async def _handle_error(self, error: Exception):
        """
        处理错误
        
        Args:
            error: 错误对象
        """
        self.conn_info.errors += 1
        self.conn_info.tcp_state = TCPConnectionState.ERROR
        self.conn_info.status = ConnectionStatus.ERROR
        
        if self.on_error:
            try:
                await self.on_error(error)
            except Exception as e:
                self.logger.error(f"错误处理回调失败: {e}")
        
        # 关闭连接
        await self.close(f"error: {error}")
    
    async def _handle_connection_lost(self):
        """
        处理连接丢失
        """
        self.conn_info.tcp_state = TCPConnectionState.CLOSED
        self.conn_info.status = ConnectionStatus.DISCONNECTED
        
        if self.on_connection_lost:
            try:
                await self.on_connection_lost()
            except Exception as e:
                self.logger.error(f"连接丢失回调失败: {e}")
        
        await self.close("connection lost")

class TCPServer:
    """
    TCP服务器
    
    异步TCP服务器实现
    """
    
    def __init__(self, config: TCPServerConfig):
        self.config = config
        self.server: Optional[asyncio.Server] = None
        self.connections: Dict[str, TCPConnection] = {}
        
        # 事件回调
        self.on_client_connected: Optional[Callable] = None
        self.on_client_disconnected: Optional[Callable] = None
        self.on_data_received: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 状态管理
        self._running = False
        self._start_time = 0.0
        
        # 统计信息
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0,
            'total_errors': 0
        }
        
        # 日志记录器
        self.logger = logging.getLogger("network.tcp.server")
    
    async def start(self) -> bool:
        """
        启动TCP服务器
        
        Returns:
            bool: 是否启动成功
        """
        if self._running:
            return True
        
        try:
            # 创建服务器
            self.server = await asyncio.start_server(
                self._handle_client,
                self.config.host,
                self.config.port,
                backlog=self.config.backlog,
                ssl=self.config.ssl_context,
                reuse_address=self.config.reuse_address,
                reuse_port=self.config.reuse_port,
                limit=self.config.buffer_size
            )
            
            self._running = True
            self._start_time = time.time()
            
            # 配置套接字选项
            for sock in self.server.sockets:
                self._configure_socket(sock)
            
            self.logger.info(f"TCP服务器已启动: {self.config.host}:{self.config.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动TCP服务器失败: {e}")
            return False
    
    async def stop(self):
        """
        停止TCP服务器
        """
        if not self._running:
            return
        
        self._running = False
        
        try:
            # 关闭所有客户端连接
            for conn in list(self.connections.values()):
                await conn.close("server shutdown")
            
            # 关闭服务器
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.logger.info("TCP服务器已停止")
            
        except Exception as e:
            self.logger.error(f"停止TCP服务器时发生错误: {e}")
    
    def _configure_socket(self, sock: socket.socket):
        """
        配置套接字选项
        
        Args:
            sock: 套接字对象
        """
        try:
            # 设置TCP_NODELAY
            if self.config.nodelay:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # 设置SO_LINGER
            if self.config.linger:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, 
                              struct.pack('ii', *self.config.linger))
            
            # 设置接收缓冲区大小
            if self.config.recv_buffer_size:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 
                              self.config.recv_buffer_size)
            
            # 设置发送缓冲区大小
            if self.config.send_buffer_size:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 
                              self.config.send_buffer_size)
            
        except Exception as e:
            self.logger.warning(f"配置套接字选项失败: {e}")
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理客户端连接
        
        Args:
            reader: 流读取器
            writer: 流写入器
        """
        conn_id = str(uuid.uuid4())
        client_addr = writer.get_extra_info('peername')
        
        # 检查连接数限制
        if len(self.connections) >= self.config.max_connections:
            self.logger.warning(f"连接数已达到最大限制，拒绝连接: {client_addr}")
            writer.close()
            await writer.wait_closed()
            return
        
        # 创建连接信息
        conn_info = TCPConnectionInfo(
            conn_id=conn_id,
            conn_type=ConnectionType.TCP,
            status=ConnectionStatus.CONNECTED,
            local_addr=writer.get_extra_info('sockname'),
            remote_addr=client_addr,
            tcp_state=TCPConnectionState.CONNECTED,
            ssl_enabled=self.config.ssl_context is not None
        )
        
        # 创建连接对象
        connection = TCPConnection(reader, writer, conn_info, self.config.__dict__)
        connection.on_data_received = self._on_data_received
        connection.on_connection_lost = lambda: self._on_client_disconnected(conn_id)
        connection.on_error = lambda error: self._on_error(conn_id, error)
        
        self.connections[conn_id] = connection
        self.stats['total_connections'] += 1
        self.stats['active_connections'] = len(self.connections)
        
        try:
            self.logger.info(f"新客户端连接: {client_addr} (ID: {conn_id})")
            
            # 调用连接回调
            if self.on_client_connected:
                await self.on_client_connected(connection)
            
            # 处理客户端数据
            await self._process_client_data(connection)
            
        except Exception as e:
            self.logger.error(f"处理客户端 {conn_id} 时发生错误: {e}")
        finally:
            # 清理连接
            await self._cleanup_connection(conn_id)
    
    async def _process_client_data(self, connection: TCPConnection):
        """
        处理客户端数据
        
        Args:
            connection: TCP连接对象
        """
        try:
            while connection.is_connected:
                # 接收数据
                data = await connection.receive_data()
                if data is None:
                    break
                
                # 更新统计信息
                self.stats['total_bytes_received'] += len(data)
                
        except Exception as e:
            self.logger.error(f"处理客户端数据时发生错误: {e}")
            await connection._handle_error(e)
    
    async def _on_data_received(self, data: bytes):
        """
        数据接收回调
        
        Args:
            data: 接收到的数据
        """
        if self.on_data_received:
            try:
                await self.on_data_received(data)
            except Exception as e:
                self.logger.error(f"数据接收回调错误: {e}")
    
    async def _on_client_disconnected(self, conn_id: str):
        """
        客户端断开连接回调
        
        Args:
            conn_id: 连接ID
        """
        connection = self.connections.get(conn_id)
        if connection and self.on_client_disconnected:
            try:
                await self.on_client_disconnected(connection)
            except Exception as e:
                self.logger.error(f"客户端断开连接回调错误: {e}")
    
    async def _on_error(self, conn_id: str, error: Exception):
        """
        错误回调
        
        Args:
            conn_id: 连接ID
            error: 错误对象
        """
        self.stats['total_errors'] += 1
        
        if self.on_error:
            try:
                await self.on_error(conn_id, error)
            except Exception as e:
                self.logger.error(f"错误回调失败: {e}")
    
    async def _cleanup_connection(self, conn_id: str):
        """
        清理连接
        
        Args:
            conn_id: 连接ID
        """
        connection = self.connections.pop(conn_id, None)
        if connection:
            await connection.close("cleanup")
            self.stats['active_connections'] = len(self.connections)
            self.logger.debug(f"连接 {conn_id} 已清理")
    
    async def broadcast(self, data: bytes, exclude_conn_ids: Optional[List[str]] = None) -> int:
        """
        广播数据到所有连接
        
        Args:
            data: 要广播的数据
            exclude_conn_ids: 要排除的连接ID列表
        
        Returns:
            int: 成功发送的连接数
        """
        exclude_conn_ids = exclude_conn_ids or []
        sent_count = 0
        
        for conn_id, connection in self.connections.items():
            if conn_id not in exclude_conn_ids and connection.is_connected:
                if await connection.send_data(data):
                    sent_count += 1
        
        self.stats['total_bytes_sent'] += len(data) * sent_count
        return sent_count
    
    async def send_to_connection(self, conn_id: str, data: bytes) -> bool:
        """
        发送数据到指定连接
        
        Args:
            conn_id: 连接ID
            data: 要发送的数据
        
        Returns:
            bool: 是否发送成功
        """
        connection = self.connections.get(conn_id)
        if connection and connection.is_connected:
            if await connection.send_data(data):
                self.stats['total_bytes_sent'] += len(data)
                return True
        
        return False
    
    def get_connection(self, conn_id: str) -> Optional[TCPConnection]:
        """
        获取连接对象
        
        Args:
            conn_id: 连接ID
        
        Returns:
            TCPConnection: 连接对象
        """
        return self.connections.get(conn_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取服务器统计信息
        
        Returns:
            dict: 统计信息
        """
        uptime = time.time() - self._start_time if self._running else 0
        
        return {
            **self.stats,
            'uptime': uptime,
            'running': self._running,
            'server_address': f"{self.config.host}:{self.config.port}",
            'ssl_enabled': self.config.ssl_context is not None,
            'max_connections': self.config.max_connections
        }

class TCPClient:
    """
    TCP客户端
    
    异步TCP客户端实现
    """
    
    def __init__(self, config: TCPClientConfig):
        self.config = config
        self.connection: Optional[TCPConnection] = None
        
        # 重连管理
        self._reconnect_attempts = 0
        self._reconnect_task: Optional[asyncio.Task] = None
        
        # 事件回调
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_data_received: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 状态管理
        self._connecting = False
        self._connected = False
        
        # 统计信息
        self.stats = {
            'connection_attempts': 0,
            'successful_connections': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0,
            'total_errors': 0,
            'last_connect_time': 0.0
        }
        
        # 日志记录器
        self.logger = logging.getLogger("network.tcp.client")
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.connection and self.connection.is_connected
    
    async def connect(self) -> bool:
        """
        连接到服务器
        
        Returns:
            bool: 是否连接成功
        """
        if self._connecting or self.is_connected:
            return self.is_connected
        
        self._connecting = True
        self.stats['connection_attempts'] += 1
        
        try:
            self.logger.info(f"正在连接到 {self.config.host}:{self.config.port}")
            
            # 建立连接
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.config.host,
                    self.config.port,
                    ssl=self.config.ssl_context,
                    local_addr=self.config.local_addr,
                    limit=self.config.buffer_size
                ),
                timeout=self.config.timeout
            )
            
            # 配置套接字
            sock = writer.get_extra_info('socket')
            if sock:
                self._configure_socket(sock)
            
            # 创建连接信息
            conn_id = str(uuid.uuid4())
            conn_info = TCPConnectionInfo(
                conn_id=conn_id,
                conn_type=ConnectionType.TCP,
                status=ConnectionStatus.CONNECTED,
                local_addr=writer.get_extra_info('sockname'),
                remote_addr=writer.get_extra_info('peername'),
                tcp_state=TCPConnectionState.CONNECTED,
                ssl_enabled=self.config.ssl_context is not None
            )
            
            # 创建连接对象
            self.connection = TCPConnection(reader, writer, conn_info, self.config.__dict__)
            self.connection.on_data_received = self._on_data_received
            self.connection.on_connection_lost = self._on_connection_lost
            self.connection.on_error = self._on_error
            
            self._connected = True
            self._reconnect_attempts = 0
            self.stats['successful_connections'] += 1
            self.stats['last_connect_time'] = time.time()
            
            self.logger.info(f"已连接到 {self.config.host}:{self.config.port}")
            
            # 调用连接回调
            if self.on_connected:
                await self.on_connected()
            
            return True
            
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            self.stats['total_errors'] += 1
            
            # 自动重连
            if self.config.auto_reconnect and self._reconnect_attempts < self.config.max_reconnect_attempts:
                self._schedule_reconnect()
            
            return False
        
        finally:
            self._connecting = False
    
    async def disconnect(self):
        """
        断开连接
        """
        if self.connection:
            await self.connection.close("user disconnect")
            self.connection = None
        
        self._connected = False
        
        # 取消重连任务
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None
        
        self.logger.info("已断开连接")
    
    def _configure_socket(self, sock: socket.socket):
        """
        配置套接字选项
        
        Args:
            sock: 套接字对象
        """
        try:
            # 设置TCP_NODELAY
            if self.config.nodelay:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # 设置SO_LINGER
            if self.config.linger:
                import struct
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, 
                              struct.pack('ii', *self.config.linger))
            
            # 设置接收缓冲区大小
            if self.config.recv_buffer_size:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 
                              self.config.recv_buffer_size)
            
            # 设置发送缓冲区大小
            if self.config.send_buffer_size:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 
                              self.config.send_buffer_size)
            
        except Exception as e:
            self.logger.warning(f"配置套接字选项失败: {e}")
    
    async def send_data(self, data: bytes) -> bool:
        """
        发送数据
        
        Args:
            data: 要发送的数据
        
        Returns:
            bool: 是否发送成功
        """
        if not self.is_connected:
            return False
        
        if await self.connection.send_data(data):
            self.stats['total_bytes_sent'] += len(data)
            return True
        
        return False
    
    async def receive_data(self, size: int = -1) -> Optional[bytes]:
        """
        接收数据
        
        Args:
            size: 要接收的字节数
        
        Returns:
            bytes: 接收到的数据
        """
        if not self.is_connected:
            return None
        
        data = await self.connection.receive_data(size)
        if data:
            self.stats['total_bytes_received'] += len(data)
        
        return data
    
    def _schedule_reconnect(self):
        """
        安排重连
        """
        if self._reconnect_task:
            return
        
        self._reconnect_attempts += 1
        delay = self.config.reconnect_delay * self._reconnect_attempts
        
        self.logger.info(f"将在 {delay} 秒后尝试重连 (第 {self._reconnect_attempts} 次)")
        self._reconnect_task = asyncio.create_task(self._reconnect_after_delay(delay))
    
    async def _reconnect_after_delay(self, delay: float):
        """
        延迟重连
        
        Args:
            delay: 延迟时间（秒）
        """
        try:
            await asyncio.sleep(delay)
            await self.connect()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"重连失败: {e}")
        finally:
            self._reconnect_task = None
    
    async def _on_data_received(self, data: bytes):
        """
        数据接收回调
        
        Args:
            data: 接收到的数据
        """
        if self.on_data_received:
            try:
                await self.on_data_received(data)
            except Exception as e:
                self.logger.error(f"数据接收回调错误: {e}")
    
    async def _on_connection_lost(self):
        """
        连接丢失回调
        """
        self._connected = False
        
        if self.on_disconnected:
            try:
                await self.on_disconnected()
            except Exception as e:
                self.logger.error(f"断开连接回调错误: {e}")
        
        # 自动重连
        if self.config.auto_reconnect and self._reconnect_attempts < self.config.max_reconnect_attempts:
            self._schedule_reconnect()
    
    async def _on_error(self, error: Exception):
        """
        错误回调
        
        Args:
            error: 错误对象
        """
        self.stats['total_errors'] += 1
        
        if self.on_error:
            try:
                await self.on_error(error)
            except Exception as e:
                self.logger.error(f"错误回调失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取客户端统计信息
        
        Returns:
            dict: 统计信息
        """
        return {
            **self.stats,
            'connected': self.is_connected,
            'reconnect_attempts': self._reconnect_attempts,
            'server_address': f"{self.config.host}:{self.config.port}",
            'ssl_enabled': self.config.ssl_context is not None,
            'auto_reconnect': self.config.auto_reconnect
        }

# 导出功能
__all__ = [
    'TCPConnectionState',
    'TCPServerConfig',
    'TCPClientConfig',
    'TCPConnectionInfo',
    'TCPConnection',
    'TCPServer',
    'TCPClient'
]