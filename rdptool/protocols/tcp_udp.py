#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TCP/UDP 代理协议模块

实现TCP和UDP的双向代理功能
"""

import asyncio
import socket
import struct
import time
import uuid
from typing import Optional, Dict, Any, Tuple, Callable
import logging
from dataclasses import dataclass

from .protocol_manager import BaseProtocol, ProtocolConfig, ProtocolStatus, ProtocolType

@dataclass
class TCPConnectionInfo:
    """TCP连接信息"""
    conn_id: str
    client_addr: Tuple[str, int]
    target_addr: Tuple[str, int]
    start_time: float
    bytes_sent: int = 0
    bytes_received: int = 0
    last_activity: float = 0.0

@dataclass
class UDPSessionInfo:
    """UDP会话信息"""
    session_id: str
    client_addr: Tuple[str, int]
    target_addr: Tuple[str, int]
    start_time: float
    last_activity: float
    bytes_sent: int = 0
    bytes_received: int = 0

class TCPProxy(BaseProtocol):
    """
    TCP代理服务器
    
    提供TCP连接的双向代理功能
    """
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.server: Optional[asyncio.Server] = None
        self.connections: Dict[str, TCPConnectionInfo] = {}
        self.connection_handlers: Dict[str, asyncio.Task] = {}
    
    async def start(self) -> bool:
        """
        启动TCP代理服务器
        """
        try:
            self.status = ProtocolStatus.STARTING
            self.stats.start_time = time.time()
            
            # 创建服务器
            self.server = await asyncio.start_server(
                self.handle_connection,
                self.config.host,
                self.config.port,
                limit=self.config.buffer_size
            )
            
            self.status = ProtocolStatus.RUNNING
            self.logger.info(f"TCP代理服务器启动成功: {self.config.host}:{self.config.port}")
            
            # 如果有目标地址，记录日志
            if self.config.target_host and self.config.target_port:
                self.logger.info(f"目标地址: {self.config.target_host}:{self.config.target_port}")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"启动TCP代理服务器失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        停止TCP代理服务器
        """
        try:
            self.status = ProtocolStatus.STOPPING
            
            # 关闭所有连接
            for task in self.connection_handlers.values():
                task.cancel()
            
            # 等待所有任务完成
            if self.connection_handlers:
                await asyncio.gather(*self.connection_handlers.values(), return_exceptions=True)
            
            # 关闭服务器
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.status = ProtocolStatus.STOPPED
            self.stats.stop_time = time.time()
            self.logger.info("TCP代理服务器已停止")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"停止TCP代理服务器失败: {e}")
            return False
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理TCP连接
        """
        conn_id = str(uuid.uuid4())
        client_addr = writer.get_extra_info('peername')
        
        # 创建连接信息
        conn_info = TCPConnectionInfo(
            conn_id=conn_id,
            client_addr=client_addr,
            target_addr=(self.config.target_host or '', self.config.target_port or 0),
            start_time=time.time(),
            last_activity=time.time()
        )
        
        self.connections[conn_id] = conn_info
        self.add_connection(conn_id, conn_info)
        
        try:
            self.logger.info(f"新TCP连接: {client_addr} -> {conn_info.target_addr}")
            
            # 如果配置了目标地址，建立到目标的连接
            if self.config.target_host and self.config.target_port:
                await self._handle_proxy_connection(conn_id, reader, writer)
            else:
                # 否则处理为普通TCP服务
                await self._handle_direct_connection(conn_id, reader, writer)
                
        except Exception as e:
            self.logger.error(f"处理TCP连接 {conn_id} 时发生错误: {e}")
            self.stats.errors += 1
        finally:
            # 清理连接
            self._cleanup_connection(conn_id, writer)
    
    async def _handle_proxy_connection(self, conn_id: str, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """
        处理代理连接
        """
        target_reader = None
        target_writer = None
        
        try:
            # 连接到目标服务器
            target_reader, target_writer = await asyncio.open_connection(
                self.config.target_host,
                self.config.target_port
            )
            
            # 创建双向数据转发任务
            client_to_target = asyncio.create_task(
                self._forward_data(conn_id, client_reader, target_writer, "client->target")
            )
            target_to_client = asyncio.create_task(
                self._forward_data(conn_id, target_reader, client_writer, "target->client")
            )
            
            # 等待任一方向的连接关闭
            done, pending = await asyncio.wait(
                [client_to_target, target_to_client],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 取消剩余任务
            for task in pending:
                task.cancel()
            
        except Exception as e:
            self.logger.error(f"代理连接 {conn_id} 错误: {e}")
        finally:
            # 关闭目标连接
            if target_writer:
                target_writer.close()
                await target_writer.wait_closed()
    
    async def _handle_direct_connection(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理直接连接（非代理模式）
        """
        try:
            while True:
                # 读取数据
                data = await reader.read(self.config.buffer_size)
                if not data:
                    break
                
                # 更新统计信息
                self.connections[conn_id].bytes_received += len(data)
                self.connections[conn_id].last_activity = time.time()
                self.stats.bytes_received += len(data)
                
                # 处理数据（这里可以添加自定义逻辑）
                response = await self._process_data(conn_id, data)
                
                if response:
                    # 发送响应
                    writer.write(response)
                    await writer.drain()
                    
                    # 更新统计信息
                    self.connections[conn_id].bytes_sent += len(response)
                    self.stats.bytes_sent += len(response)
                
        except Exception as e:
            self.logger.error(f"处理直接连接 {conn_id} 错误: {e}")
    
    async def _forward_data(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str):
        """
        转发数据
        """
        try:
            while True:
                data = await reader.read(self.config.buffer_size)
                if not data:
                    break
                
                writer.write(data)
                await writer.drain()
                
                # 更新统计信息
                if direction.startswith("client"):
                    self.connections[conn_id].bytes_sent += len(data)
                    self.stats.bytes_sent += len(data)
                else:
                    self.connections[conn_id].bytes_received += len(data)
                    self.stats.bytes_received += len(data)
                
                self.connections[conn_id].last_activity = time.time()
                
        except Exception as e:
            self.logger.debug(f"数据转发 {direction} 结束: {e}")
    
    async def _process_data(self, conn_id: str, data: bytes) -> Optional[bytes]:
        """
        处理接收到的数据
        
        子类可以重写此方法来实现自定义数据处理逻辑
        """
        # 默认回显数据
        return data
    
    def _cleanup_connection(self, conn_id: str, writer: asyncio.StreamWriter):
        """
        清理连接
        """
        try:
            writer.close()
        except Exception:
            pass
        
        if conn_id in self.connections:
            del self.connections[conn_id]
        
        if conn_id in self.connection_handlers:
            del self.connection_handlers[conn_id]
        
        self.remove_connection(conn_id)
        self.logger.info(f"TCP连接 {conn_id} 已关闭")

class UDPProxy(BaseProtocol):
    """
    UDP代理服务器
    
    提供UDP数据包的双向代理功能
    """
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional['UDPProtocolHandler'] = None
        self.sessions: Dict[Tuple[str, int], UDPSessionInfo] = {}
        self.target_transports: Dict[str, asyncio.DatagramTransport] = {}
    
    async def start(self) -> bool:
        """
        启动UDP代理服务器
        """
        try:
            self.status = ProtocolStatus.STARTING
            self.stats.start_time = time.time()
            
            # 创建UDP服务器
            loop = asyncio.get_event_loop()
            self.transport, self.protocol = await loop.create_datagram_endpoint(
                lambda: UDPProtocolHandler(self),
                local_addr=(self.config.host, self.config.port)
            )
            
            self.status = ProtocolStatus.RUNNING
            self.logger.info(f"UDP代理服务器启动成功: {self.config.host}:{self.config.port}")
            
            if self.config.target_host and self.config.target_port:
                self.logger.info(f"目标地址: {self.config.target_host}:{self.config.target_port}")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"启动UDP代理服务器失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        停止UDP代理服务器
        """
        try:
            self.status = ProtocolStatus.STOPPING
            
            # 关闭所有目标传输
            for transport in self.target_transports.values():
                transport.close()
            
            # 关闭主传输
            if self.transport:
                self.transport.close()
            
            self.status = ProtocolStatus.STOPPED
            self.stats.stop_time = time.time()
            self.logger.info("UDP代理服务器已停止")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"停止UDP代理服务器失败: {e}")
            return False
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        UDP不使用此方法
        """
        pass
    
    def handle_datagram(self, data: bytes, addr: Tuple[str, int]):
        """
        处理UDP数据包
        """
        try:
            # 获取或创建会话
            session = self._get_or_create_session(addr)
            
            # 更新统计信息
            session.bytes_received += len(data)
            session.last_activity = time.time()
            self.stats.bytes_received += len(data)
            
            # 如果配置了目标地址，转发数据
            if self.config.target_host and self.config.target_port:
                asyncio.create_task(self._forward_to_target(session, data))
            else:
                # 否则处理为普通UDP服务
                response = self._process_udp_data(session, data)
                if response:
                    self._send_to_client(session, response)
                    
        except Exception as e:
            self.logger.error(f"处理UDP数据包错误: {e}")
            self.stats.errors += 1
    
    def _get_or_create_session(self, addr: Tuple[str, int]) -> UDPSessionInfo:
        """
        获取或创建UDP会话
        """
        if addr not in self.sessions:
            session_id = str(uuid.uuid4())
            session = UDPSessionInfo(
                session_id=session_id,
                client_addr=addr,
                target_addr=(self.config.target_host or '', self.config.target_port or 0),
                start_time=time.time(),
                last_activity=time.time()
            )
            self.sessions[addr] = session
            self.add_connection(session_id, session)
            self.logger.info(f"新UDP会话: {addr} -> {session.target_addr}")
        
        return self.sessions[addr]
    
    async def _forward_to_target(self, session: UDPSessionInfo, data: bytes):
        """
        转发数据到目标服务器
        """
        try:
            # 获取或创建到目标的传输
            if session.session_id not in self.target_transports:
                loop = asyncio.get_event_loop()
                transport, protocol = await loop.create_datagram_endpoint(
                    lambda: UDPTargetProtocolHandler(self, session),
                    remote_addr=(self.config.target_host, self.config.target_port)
                )
                self.target_transports[session.session_id] = transport
            
            # 发送数据到目标
            transport = self.target_transports[session.session_id]
            transport.sendto(data)
            
            # 更新统计信息
            session.bytes_sent += len(data)
            self.stats.bytes_sent += len(data)
            
        except Exception as e:
            self.logger.error(f"转发UDP数据到目标失败: {e}")
    
    def _process_udp_data(self, session: UDPSessionInfo, data: bytes) -> Optional[bytes]:
        """
        处理UDP数据
        
        子类可以重写此方法来实现自定义数据处理逻辑
        """
        # 默认回显数据
        return data
    
    def _send_to_client(self, session: UDPSessionInfo, data: bytes):
        """
        发送数据到客户端
        """
        if self.transport:
            self.transport.sendto(data, session.client_addr)
            
            # 更新统计信息
            session.bytes_sent += len(data)
            self.stats.bytes_sent += len(data)
    
    def handle_target_response(self, session: UDPSessionInfo, data: bytes):
        """
        处理目标服务器的响应
        """
        self._send_to_client(session, data)
        
        # 更新统计信息
        session.bytes_received += len(data)
        session.last_activity = time.time()
        self.stats.bytes_received += len(data)

class UDPProtocolHandler(asyncio.DatagramProtocol):
    """
    UDP协议处理器
    """
    
    def __init__(self, proxy: UDPProxy):
        self.proxy = proxy
    
    def connection_made(self, transport):
        self.transport = transport
    
    def datagram_received(self, data, addr):
        self.proxy.handle_datagram(data, addr)
    
    def error_received(self, exc):
        self.proxy.logger.error(f"UDP协议错误: {exc}")

class UDPTargetProtocolHandler(asyncio.DatagramProtocol):
    """
    UDP目标协议处理器
    """
    
    def __init__(self, proxy: UDPProxy, session: UDPSessionInfo):
        self.proxy = proxy
        self.session = session
    
    def connection_made(self, transport):
        self.transport = transport
    
    def datagram_received(self, data, addr):
        self.proxy.handle_target_response(self.session, data)
    
    def error_received(self, exc):
        self.proxy.logger.error(f"UDP目标协议错误: {exc}")

class TCPUDPBridge:
    """
    TCP/UDP桥接器
    
    在TCP和UDP协议之间进行数据转换
    """
    
    def __init__(self, tcp_config: ProtocolConfig, udp_config: ProtocolConfig):
        self.tcp_proxy = TCPProxy(tcp_config)
        self.udp_proxy = UDPProxy(udp_config)
        self.logger = logging.getLogger("tcp_udp_bridge")
        self.running = False
    
    async def start(self) -> bool:
        """
        启动桥接器
        """
        try:
            # 启动TCP和UDP代理
            tcp_success = await self.tcp_proxy.start()
            udp_success = await self.udp_proxy.start()
            
            if tcp_success and udp_success:
                self.running = True
                self.logger.info("TCP/UDP桥接器启动成功")
                return True
            else:
                # 如果任一启动失败，停止已启动的服务
                if tcp_success:
                    await self.tcp_proxy.stop()
                if udp_success:
                    await self.udp_proxy.stop()
                return False
                
        except Exception as e:
            self.logger.error(f"启动TCP/UDP桥接器失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        停止桥接器
        """
        try:
            tcp_success = await self.tcp_proxy.stop()
            udp_success = await self.udp_proxy.stop()
            
            self.running = False
            self.logger.info("TCP/UDP桥接器已停止")
            
            return tcp_success and udp_success
            
        except Exception as e:
            self.logger.error(f"停止TCP/UDP桥接器失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取桥接器统计信息
        """
        tcp_stats = self.tcp_proxy.get_stats()
        udp_stats = self.udp_proxy.get_stats()
        
        return {
            'running': self.running,
            'tcp': {
                'status': tcp_stats.status.value,
                'connections': tcp_stats.active_connections,
                'bytes_sent': tcp_stats.bytes_sent,
                'bytes_received': tcp_stats.bytes_received,
                'errors': tcp_stats.errors
            },
            'udp': {
                'status': udp_stats.status.value,
                'sessions': udp_stats.active_connections,
                'bytes_sent': udp_stats.bytes_sent,
                'bytes_received': udp_stats.bytes_received,
                'errors': udp_stats.errors
            },
            'total': {
                'bytes_sent': tcp_stats.bytes_sent + udp_stats.bytes_sent,
                'bytes_received': tcp_stats.bytes_received + udp_stats.bytes_received,
                'errors': tcp_stats.errors + udp_stats.errors
            }
        }

# 导出功能
__all__ = [
    'TCPConnectionInfo',
    'UDPSessionInfo',
    'TCPProxy',
    'UDPProxy',
    'TCPUDPBridge',
    'UDPProtocolHandler',
    'UDPTargetProtocolHandler'
]