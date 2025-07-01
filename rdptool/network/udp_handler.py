#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UDP处理模块

实现UDP服务器和客户端的异步通信功能，包括：
- UDP服务器实现
- UDP客户端实现
- 会话管理
- 数据传输
- 可靠UDP实现
"""

import asyncio
import socket
import time
import uuid
import random
import struct
import logging
from typing import Optional, Dict, Any, Callable, Tuple, List, Set, Union
from dataclasses import dataclass, field
from enum import Enum

from .connection_manager import ConnectionInfo, ConnectionStatus, ConnectionType, NetworkEvent, NetworkEventType

class UDPSessionState(Enum):
    """UDP会话状态"""
    IDLE = "idle"
    ACTIVE = "active"
    STALE = "stale"  # 一段时间没有活动
    EXPIRED = "expired"  # 超时
    CLOSED = "closed"

class UDPPacketType(Enum):
    """UDP包类型（用于可靠UDP实现）"""
    DATA = 0  # 数据包
    ACK = 1   # 确认包
    SYN = 2   # 同步包（建立连接）
    FIN = 3   # 结束包（关闭连接）
    PING = 4  # 心跳包
    PONG = 5  # 心跳响应包

@dataclass
class UDPServerConfig:
    """UDP服务器配置"""
    host: str = '0.0.0.0'
    port: int = 3390
    buffer_size: int = 8192
    session_timeout: float = 120.0  # 会话超时时间（秒）
    cleanup_interval: float = 60.0  # 清理过期会话的间隔（秒）
    max_sessions: int = 1000
    reuse_address: bool = True
    reuse_port: bool = False
    recv_buffer_size: Optional[int] = None
    send_buffer_size: Optional[int] = None
    reliable_udp: bool = False  # 是否启用可靠UDP
    reliable_timeout: float = 5.0  # 可靠UDP超时时间
    reliable_retries: int = 3  # 可靠UDP重试次数
    reliable_window_size: int = 64  # 可靠UDP窗口大小

@dataclass
class UDPClientConfig:
    """UDP客户端配置"""
    host: str
    port: int
    buffer_size: int = 8192
    timeout: float = 30.0
    local_addr: Optional[Tuple[str, int]] = None
    recv_buffer_size: Optional[int] = None
    send_buffer_size: Optional[int] = None
    reliable_udp: bool = False  # 是否启用可靠UDP
    reliable_timeout: float = 5.0  # 可靠UDP超时时间
    reliable_retries: int = 3  # 可靠UDP重试次数
    reliable_window_size: int = 64  # 可靠UDP窗口大小

@dataclass
class UDPSessionInfo(ConnectionInfo):
    """UDP会话信息"""
    session_state: UDPSessionState = UDPSessionState.IDLE
    last_activity: float = field(default_factory=time.time)
    creation_time: float = field(default_factory=time.time)
    reliable: bool = False  # 是否为可靠UDP会话
    sequence_number: int = 0  # 当前序列号（可靠UDP）
    ack_number: int = 0  # 当前确认号（可靠UDP）
    unacked_packets: Dict[int, Any] = field(default_factory=dict)  # 未确认的数据包（可靠UDP）

@dataclass
class UDPPacket:
    """UDP数据包（用于可靠UDP实现）"""
    packet_type: UDPPacketType
    sequence_number: int
    ack_number: int
    data: bytes = b''
    timestamp: float = field(default_factory=time.time)
    retries: int = 0
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'UDPPacket':
        """从字节数据解析UDP数据包"""
        if len(data) < 9:  # 至少需要9字节的头部
            raise ValueError("数据包太短")
        
        # 解析头部
        header = data[:9]
        packet_type, seq_num, ack_num = struct.unpack("!BII", header)
        
        # 解析数据
        payload = data[9:]
        
        return cls(
            packet_type=UDPPacketType(packet_type),
            sequence_number=seq_num,
            ack_number=ack_num,
            data=payload
        )
    
    def to_bytes(self) -> bytes:
        """将UDP数据包转换为字节数据"""
        # 构建头部
        header = struct.pack("!BII", 
                           self.packet_type.value, 
                           self.sequence_number, 
                           self.ack_number)
        
        # 组合头部和数据
        return header + self.data

class UDPSession:
    """
    UDP会话
    
    表示与特定远程端点的UDP通信会话
    """
    
    def __init__(self, session_info: UDPSessionInfo, config: Dict[str, Any]):
        self.session_info = session_info
        self.config = config
        
        # 状态管理
        self._closed = False
        
        # 可靠UDP管理
        self._reliable = config.get('reliable_udp', False)
        self._window_size = config.get('reliable_window_size', 64)
        self._timeout = config.get('reliable_timeout', 5.0)
        self._retries = config.get('reliable_retries', 3)
        self._next_seq_num = random.randint(0, 0xFFFFFFFF) if self._reliable else 0
        self._next_ack_num = 0
        self._unacked_packets: Dict[int, Tuple[UDPPacket, asyncio.TimerHandle]] = {}
        self._received_packets: Set[int] = set()
        
        # 事件回调
        self.on_data_received: Optional[Callable] = None
        self.on_session_closed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 日志记录器
        self.logger = logging.getLogger(f"network.udp.session.{session_info.conn_id}")
        
        if self._reliable:
            self.session_info.reliable = True
    
    @property
    def is_active(self) -> bool:
        """检查会话是否活跃"""
        return not self._closed and self.session_info.session_state in (
            UDPSessionState.IDLE, UDPSessionState.ACTIVE)
    
    def update_activity(self):
        """更新会话活动时间"""
        self.session_info.last_activity = time.time()
        if self.session_info.session_state == UDPSessionState.IDLE:
            self.session_info.session_state = UDPSessionState.ACTIVE
    
    def is_expired(self, current_time: float, timeout: float) -> bool:
        """检查会话是否已过期"""
        return current_time - self.session_info.last_activity > timeout
    
    async def process_data(self, data: bytes, transport: asyncio.DatagramTransport) -> bool:
        """
        处理接收到的数据
        
        Args:
            data: 接收到的数据
            transport: UDP传输对象
        
        Returns:
            bool: 是否处理成功
        """
        self.update_activity()
        
        try:
            # 更新统计信息
            self.session_info.bytes_received += len(data)
            self.session_info.packets_received += 1
            
            # 可靠UDP处理
            if self._reliable:
                try:
                    packet = UDPPacket.from_bytes(data)
                    return await self._process_reliable_packet(packet, transport)
                except Exception as e:
                    self.logger.error(f"处理可靠UDP数据包失败: {e}")
                    return False
            
            # 普通UDP处理
            if self.on_data_received:
                try:
                    await self.on_data_received(data)
                except Exception as e:
                    self.logger.error(f"数据接收回调错误: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"处理数据失败: {e}")
            await self._handle_error(e)
            return False
    
    async def send_data(self, data: bytes, transport: asyncio.DatagramTransport) -> bool:
        """
        发送数据
        
        Args:
            data: 要发送的数据
            transport: UDP传输对象
        
        Returns:
            bool: 是否发送成功
        """
        if not self.is_active:
            return False
        
        try:
            # 可靠UDP发送
            if self._reliable:
                return await self._send_reliable_data(data, transport)
            
            # 普通UDP发送
            transport.sendto(data, self.session_info.remote_addr)
            
            # 更新统计信息
            self.session_info.bytes_sent += len(data)
            self.session_info.packets_sent += 1
            self.update_activity()
            
            self.logger.debug(f"发送数据: {len(data)} 字节")
            return True
            
        except Exception as e:
            self.logger.error(f"发送数据失败: {e}")
            await self._handle_error(e)
            return False
    
    async def close(self, reason: str = "normal"):
        """
        关闭会话
        
        Args:
            reason: 关闭原因
        """
        if self._closed:
            return
        
        self._closed = True
        self.session_info.session_state = UDPSessionState.CLOSED
        self.session_info.status = ConnectionStatus.DISCONNECTED
        
        # 取消所有未确认的数据包重传定时器
        for _, timer in self._unacked_packets.values():
            timer.cancel()
        
        self._unacked_packets.clear()
        
        self.logger.info(f"会话已关闭: {reason}")
        
        if self.on_session_closed:
            try:
                await self.on_session_closed()
            except Exception as e:
                self.logger.error(f"会话关闭回调错误: {e}")
    
    async def _handle_error(self, error: Exception):
        """
        处理错误
        
        Args:
            error: 错误对象
        """
        self.session_info.errors += 1
        self.session_info.status = ConnectionStatus.ERROR
        
        if self.on_error:
            try:
                await self.on_error(error)
            except Exception as e:
                self.logger.error(f"错误处理回调失败: {e}")
    
    async def _send_reliable_data(self, data: bytes, transport: asyncio.DatagramTransport) -> bool:
        """
        发送可靠UDP数据
        
        Args:
            data: 要发送的数据
            transport: UDP传输对象
        
        Returns:
            bool: 是否发送成功
        """
        # 检查窗口是否已满
        if len(self._unacked_packets) >= self._window_size:
            self.logger.warning("发送窗口已满，等待确认")
            return False
        
        # 创建数据包
        seq_num = self._next_seq_num
        self._next_seq_num = (self._next_seq_num + 1) & 0xFFFFFFFF
        
        packet = UDPPacket(
            packet_type=UDPPacketType.DATA,
            sequence_number=seq_num,
            ack_number=self._next_ack_num,
            data=data
        )
        
        # 发送数据包
        packet_data = packet.to_bytes()
        transport.sendto(packet_data, self.session_info.remote_addr)
        
        # 更新统计信息
        self.session_info.bytes_sent += len(packet_data)
        self.session_info.packets_sent += 1
        self.update_activity()
        
        # 设置重传定时器
        timer = asyncio.get_event_loop().call_later(
            self._timeout, 
            lambda: asyncio.create_task(self._retransmit(seq_num, transport))
        )
        
        # 保存未确认的数据包
        self._unacked_packets[seq_num] = (packet, timer)
        
        self.logger.debug(f"发送可靠数据包: SEQ={seq_num}, ACK={self._next_ack_num}, 大小={len(data)} 字节")
        return True
    
    async def _retransmit(self, seq_num: int, transport: asyncio.DatagramTransport):
        """
        重传数据包
        
        Args:
            seq_num: 序列号
            transport: UDP传输对象
        """
        if seq_num not in self._unacked_packets:
            return
        
        packet, _ = self._unacked_packets[seq_num]
        packet.retries += 1
        
        if packet.retries > self._retries:
            self.logger.warning(f"数据包 SEQ={seq_num} 重传次数超过限制，放弃")
            del self._unacked_packets[seq_num]
            return
        
        self.logger.debug(f"重传数据包: SEQ={seq_num}, 重试次数={packet.retries}")
        
        # 重新发送数据包
        packet_data = packet.to_bytes()
        transport.sendto(packet_data, self.session_info.remote_addr)
        
        # 更新统计信息
        self.session_info.bytes_sent += len(packet_data)
        self.session_info.packets_sent += 1
        
        # 设置新的重传定时器
        timer = asyncio.get_event_loop().call_later(
            self._timeout * (1.5 ** packet.retries),  # 指数退避
            lambda: asyncio.create_task(self._retransmit(seq_num, transport))
        )
        
        self._unacked_packets[seq_num] = (packet, timer)
    
    async def _process_reliable_packet(self, packet: UDPPacket, transport: asyncio.DatagramTransport) -> bool:
        """
        处理可靠UDP数据包
        
        Args:
            packet: UDP数据包
            transport: UDP传输对象
        
        Returns:
            bool: 是否处理成功
        """
        self.logger.debug(f"收到可靠数据包: 类型={packet.packet_type.name}, SEQ={packet.sequence_number}, ACK={packet.ack_number}")
        
        # 处理确认包
        if packet.packet_type == UDPPacketType.ACK:
            return self._process_ack(packet.ack_number)
        
        # 处理数据包
        elif packet.packet_type == UDPPacketType.DATA:
            # 发送确认包
            await self._send_ack(packet.sequence_number, transport)
            
            # 检查是否已经处理过这个数据包
            if packet.sequence_number in self._received_packets:
                self.logger.debug(f"数据包 SEQ={packet.sequence_number} 已处理过，忽略")
                return True
            
            # 记录已处理的数据包
            self._received_packets.add(packet.sequence_number)
            
            # 更新下一个期望的确认号
            self._next_ack_num = packet.sequence_number + 1
            
            # 清理已处理的数据包记录（保持集合大小合理）
            if len(self._received_packets) > self._window_size * 2:
                self._received_packets = set(sorted(self._received_packets)[-self._window_size:])
            
            # 处理数据
            if self.on_data_received and packet.data:
                try:
                    await self.on_data_received(packet.data)
                except Exception as e:
                    self.logger.error(f"数据接收回调错误: {e}")
            
            return True
        
        # 处理同步包（建立连接）
        elif packet.packet_type == UDPPacketType.SYN:
            # 发送确认包
            await self._send_ack(packet.sequence_number, transport)
            return True
        
        # 处理结束包（关闭连接）
        elif packet.packet_type == UDPPacketType.FIN:
            # 发送确认包
            await self._send_ack(packet.sequence_number, transport)
            # 关闭会话
            await self.close("received FIN")
            return True
        
        # 处理心跳包
        elif packet.packet_type == UDPPacketType.PING:
            # 发送心跳响应包
            await self._send_pong(packet.sequence_number, transport)
            return True
        
        # 处理心跳响应包
        elif packet.packet_type == UDPPacketType.PONG:
            # 不需要特殊处理，只是更新活动时间
            return True
        
        return False
    
    def _process_ack(self, ack_num: int) -> bool:
        """
        处理确认包
        
        Args:
            ack_num: 确认号
        
        Returns:
            bool: 是否处理成功
        """
        # 查找并移除已确认的数据包
        acked_packets = [seq for seq in self._unacked_packets.keys() if seq <= ack_num]
        
        for seq in acked_packets:
            if seq in self._unacked_packets:
                _, timer = self._unacked_packets[seq]
                timer.cancel()
                del self._unacked_packets[seq]
                self.logger.debug(f"数据包 SEQ={seq} 已确认")
        
        return True
    
    async def _send_ack(self, seq_num: int, transport: asyncio.DatagramTransport):
        """
        发送确认包
        
        Args:
            seq_num: 要确认的序列号
            transport: UDP传输对象
        """
        packet = UDPPacket(
            packet_type=UDPPacketType.ACK,
            sequence_number=0,  # ACK包的序列号不重要
            ack_number=seq_num,
            data=b''
        )
        
        packet_data = packet.to_bytes()
        transport.sendto(packet_data, self.session_info.remote_addr)
        
        # 更新统计信息
        self.session_info.bytes_sent += len(packet_data)
        self.session_info.packets_sent += 1
        
        self.logger.debug(f"发送确认包: ACK={seq_num}")
    
    async def _send_pong(self, seq_num: int, transport: asyncio.DatagramTransport):
        """
        发送心跳响应包
        
        Args:
            seq_num: 心跳包的序列号
            transport: UDP传输对象
        """
        packet = UDPPacket(
            packet_type=UDPPacketType.PONG,
            sequence_number=seq_num,
            ack_number=0,  # PONG包的确认号不重要
            data=b''
        )
        
        packet_data = packet.to_bytes()
        transport.sendto(packet_data, self.session_info.remote_addr)
        
        # 更新统计信息
        self.session_info.bytes_sent += len(packet_data)
        self.session_info.packets_sent += 1
        
        self.logger.debug(f"发送心跳响应包: SEQ={seq_num}")
    
    async def send_ping(self, transport: asyncio.DatagramTransport) -> bool:
        """
        发送心跳包
        
        Args:
            transport: UDP传输对象
        
        Returns:
            bool: 是否发送成功
        """
        if not self.is_active or not self._reliable:
            return False
        
        seq_num = random.randint(0, 0xFFFFFFFF)
        
        packet = UDPPacket(
            packet_type=UDPPacketType.PING,
            sequence_number=seq_num,
            ack_number=0,  # PING包的确认号不重要
            data=b''
        )
        
        packet_data = packet.to_bytes()
        transport.sendto(packet_data, self.session_info.remote_addr)
        
        # 更新统计信息
        self.session_info.bytes_sent += len(packet_data)
        self.session_info.packets_sent += 1
        self.update_activity()
        
        self.logger.debug(f"发送心跳包: SEQ={seq_num}")
        return True

class UDPServer(asyncio.DatagramProtocol):
    """
    UDP服务器
    
    异步UDP服务器实现
    """
    
    def __init__(self, config: UDPServerConfig):
        self.config = config
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.sessions: Dict[str, UDPSession] = {}
        
        # 事件回调
        self.on_session_created: Optional[Callable] = None
        self.on_session_closed: Optional[Callable] = None
        self.on_data_received: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 状态管理
        self._running = False
        self._start_time = 0.0
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # 统计信息
        self.stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0,
            'total_errors': 0
        }
        
        # 日志记录器
        self.logger = logging.getLogger("network.udp.server")
    
    async def start(self) -> bool:
        """
        启动UDP服务器
        
        Returns:
            bool: 是否启动成功
        """
        if self._running:
            return True
        
        try:
            # 创建UDP传输
            loop = asyncio.get_event_loop()
            transport, _ = await loop.create_datagram_endpoint(
                lambda: self,
                local_addr=(self.config.host, self.config.port),
                reuse_address=self.config.reuse_address,
                reuse_port=self.config.reuse_port,
                allow_broadcast=True
            )
            
            self.transport = transport
            self._running = True
            self._start_time = time.time()
            
            # 配置套接字选项
            sock = transport.get_extra_info('socket')
            if sock:
                self._configure_socket(sock)
            
            # 启动会话清理任务
            self._cleanup_task = asyncio.create_task(self._cleanup_sessions_loop())
            
            self.logger.info(f"UDP服务器已启动: {self.config.host}:{self.config.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动UDP服务器失败: {e}")
            return False
    
    async def stop(self):
        """
        停止UDP服务器
        """
        if not self._running:
            return
        
        self._running = False
        
        try:
            # 停止会话清理任务
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭所有会话
            for session in list(self.sessions.values()):
                await session.close("server shutdown")
            
            # 关闭传输
            if self.transport:
                self.transport.close()
                self.transport = None
            
            self.logger.info("UDP服务器已停止")
            
        except Exception as e:
            self.logger.error(f"停止UDP服务器时发生错误: {e}")
    
    def _configure_socket(self, sock: socket.socket):
        """
        配置套接字选项
        
        Args:
            sock: 套接字对象
        """
        try:
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
    
    def connection_made(self, transport: asyncio.DatagramTransport):
        """
        连接建立回调
        
        Args:
            transport: UDP传输对象
        """
        self.transport = transport
        self.logger.debug("UDP传输已建立")
    
    def connection_lost(self, exc: Optional[Exception]):
        """
        连接丢失回调
        
        Args:
            exc: 异常对象
        """
        self.transport = None
        self._running = False
        
        if exc:
            self.logger.error(f"UDP传输丢失: {exc}")
        else:
            self.logger.info("UDP传输已关闭")
    
    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        """
        数据报接收回调
        
        Args:
            data: 接收到的数据
            addr: 发送方地址
        """
        asyncio.create_task(self._handle_datagram(data, addr))
    
    def error_received(self, exc: Exception):
        """
        错误接收回调
        
        Args:
            exc: 异常对象
        """
        self.logger.error(f"UDP错误: {exc}")
        self.stats['total_errors'] += 1
        
        if self.on_error:
            try:
                asyncio.create_task(self.on_error(exc))
            except Exception as e:
                self.logger.error(f"错误回调失败: {e}")
    
    async def _handle_datagram(self, data: bytes, addr: Tuple[str, int]):
        """
        处理接收到的数据报
        
        Args:
            data: 接收到的数据
            addr: 发送方地址
        """
        # 更新统计信息
        self.stats['total_bytes_received'] += len(data)
        
        # 获取或创建会话
        session_key = f"{addr[0]}:{addr[1]}"
        session = self.sessions.get(session_key)
        
        if not session:
            # 检查会话数限制
            if len(self.sessions) >= self.config.max_sessions:
                self.logger.warning(f"会话数已达到最大限制，忽略来自 {addr} 的数据")
                return
            
            # 创建新会话
            session = await self._create_session(addr)
        
        # 处理数据
        if session:
            await session.process_data(data, self.transport)
    
    async def _create_session(self, addr: Tuple[str, int]) -> Optional[UDPSession]:
        """
        创建新会话
        
        Args:
            addr: 远程地址
        
        Returns:
            UDPSession: 会话对象
        """
        session_key = f"{addr[0]}:{addr[1]}"
        conn_id = str(uuid.uuid4())
        
        # 创建会话信息
        session_info = UDPSessionInfo(
            conn_id=conn_id,
            conn_type=ConnectionType.UDP,
            status=ConnectionStatus.CONNECTED,
            local_addr=(self.config.host, self.config.port),
            remote_addr=addr,
            session_state=UDPSessionState.ACTIVE,
            reliable=self.config.reliable_udp
        )
        
        # 创建会话对象
        session = UDPSession(session_info, self.config.__dict__)
        session.on_data_received = self._on_data_received
        session.on_session_closed = lambda: self._on_session_closed(session_key)
        session.on_error = lambda error: self._on_error(session_key, error)
        
        self.sessions[session_key] = session
        self.stats['total_sessions'] += 1
        self.stats['active_sessions'] = len(self.sessions)
        
        self.logger.info(f"新会话创建: {addr} (ID: {conn_id})")
        
        # 调用会话创建回调
        if self.on_session_created:
            try:
                await self.on_session_created(session)
            except Exception as e:
                self.logger.error(f"会话创建回调错误: {e}")
        
        return session
    
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
    
    async def _on_session_closed(self, session_key: str):
        """
        会话关闭回调
        
        Args:
            session_key: 会话键
        """
        session = self.sessions.pop(session_key, None)
        if session and self.on_session_closed:
            try:
                await self.on_session_closed(session)
            except Exception as e:
                self.logger.error(f"会话关闭回调错误: {e}")
        
        self.stats['active_sessions'] = len(self.sessions)
    
    async def _on_error(self, session_key: str, error: Exception):
        """
        错误回调
        
        Args:
            session_key: 会话键
            error: 错误对象
        """
        self.stats['total_errors'] += 1
        
        if self.on_error:
            try:
                await self.on_error(error)
            except Exception as e:
                self.logger.error(f"错误回调失败: {e}")
    
    async def _cleanup_sessions_loop(self):
        """
        会话清理循环
        """
        try:
            while self._running:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_expired_sessions()
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"会话清理循环错误: {e}")
    
    async def _cleanup_expired_sessions(self):
        """
        清理过期会话
        """
        current_time = time.time()
        expired_keys = []
        
        for key, session in self.sessions.items():
            if session.is_expired(current_time, self.config.session_timeout):
                expired_keys.append(key)
                session.session_info.session_state = UDPSessionState.EXPIRED
        
        for key in expired_keys:
            session = self.sessions.get(key)
            if session:
                self.logger.info(f"会话已过期: {session.session_info.remote_addr} (ID: {session.session_info.conn_id})")
                await session.close("expired")
                self.sessions.pop(key, None)
        
        if expired_keys:
            self.stats['active_sessions'] = len(self.sessions)
            self.logger.info(f"已清理 {len(expired_keys)} 个过期会话")
    
    async def send_to(self, addr: Tuple[str, int], data: bytes) -> bool:
        """
        发送数据到指定地址
        
        Args:
            addr: 目标地址
            data: 要发送的数据
        
        Returns:
            bool: 是否发送成功
        """
        if not self._running or not self.transport:
            return False
        
        try:
            # 获取或创建会话
            session_key = f"{addr[0]}:{addr[1]}"
            session = self.sessions.get(session_key)
            
            if not session:
                session = await self._create_session(addr)
            
            if session:
                return await session.send_data(data, self.transport)
            
            return False
            
        except Exception as e:
            self.logger.error(f"发送数据到 {addr} 失败: {e}")
            self.stats['total_errors'] += 1
            return False
    
    async def broadcast(self, data: bytes, exclude_addrs: Optional[List[Tuple[str, int]]] = None) -> int:
        """
        广播数据到所有会话
        
        Args:
            data: 要广播的数据
            exclude_addrs: 要排除的地址列表
        
        Returns:
            int: 成功发送的会话数
        """
        if not self._running or not self.transport:
            return 0
        
        exclude_addrs = exclude_addrs or []
        sent_count = 0
        
        for session in self.sessions.values():
            if session.is_active and session.session_info.remote_addr not in exclude_addrs:
                if await session.send_data(data, self.transport):
                    sent_count += 1
        
        self.stats['total_bytes_sent'] += len(data) * sent_count
        return sent_count
    
    def get_session(self, addr: Tuple[str, int]) -> Optional[UDPSession]:
        """
        获取会话对象
        
        Args:
            addr: 远程地址
        
        Returns:
            UDPSession: 会话对象
        """
        session_key = f"{addr[0]}:{addr[1]}"
        return self.sessions.get(session_key)
    
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
            'reliable_udp': self.config.reliable_udp,
            'max_sessions': self.config.max_sessions
        }

class UDPClient(asyncio.DatagramProtocol):
    """
    UDP客户端
    
    异步UDP客户端实现
    """
    
    def __init__(self, config: UDPClientConfig):
        self.config = config
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.session: Optional[UDPSession] = None
        
        # 事件回调
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_data_received: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 状态管理
        self._connected = False
        self._connecting = False
        
        # 统计信息
        self.stats = {
            'connection_attempts': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0,
            'total_errors': 0,
            'last_connect_time': 0.0
        }
        
        # 日志记录器
        self.logger = logging.getLogger("network.udp.client")
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.transport is not None
    
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
            
            # 创建UDP传输
            loop = asyncio.get_event_loop()
            transport, _ = await loop.create_datagram_endpoint(
                lambda: self,
                remote_addr=(self.config.host, self.config.port),
                local_addr=self.config.local_addr,
                allow_broadcast=True
            )
            
            self.transport = transport
            
            # 配置套接字
            sock = transport.get_extra_info('socket')
            if sock:
                self._configure_socket(sock)
            
            # 创建会话信息
            conn_id = str(uuid.uuid4())
            session_info = UDPSessionInfo(
                conn_id=conn_id,
                conn_type=ConnectionType.UDP,
                status=ConnectionStatus.CONNECTED,
                local_addr=transport.get_extra_info('sockname'),
                remote_addr=(self.config.host, self.config.port),
                session_state=UDPSessionState.ACTIVE,
                reliable=self.config.reliable_udp
            )
            
            # 创建会话对象
            self.session = UDPSession(session_info, self.config.__dict__)
            self.session.on_data_received = self._on_data_received
            self.session.on_session_closed = self._on_session_closed
            self.session.on_error = self._on_error
            
            self._connected = True
            self.stats['last_connect_time'] = time.time()
            
            self.logger.info(f"已连接到 {self.config.host}:{self.config.port}")
            
            # 调用连接回调
            if self.on_connected:
                await self.on_connected()
            
            # 如果是可靠UDP，发送SYN包建立连接
            if self.config.reliable_udp:
                await self._send_syn()
            
            return True
            
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            self.stats['total_errors'] += 1
            return False
        
        finally:
            self._connecting = False
    
    async def disconnect(self):
        """
        断开连接
        """
        if not self.is_connected:
            return
        
        try:
            # 如果是可靠UDP，发送FIN包关闭连接
            if self.config.reliable_udp and self.session:
                await self._send_fin()
            
            # 关闭会话
            if self.session:
                await self.session.close("user disconnect")
                self.session = None
            
            # 关闭传输
            if self.transport:
                self.transport.close()
                self.transport = None
            
            self._connected = False
            
            self.logger.info("已断开连接")
            
        except Exception as e:
            self.logger.error(f"断开连接失败: {e}")
    
    def _configure_socket(self, sock: socket.socket):
        """
        配置套接字选项
        
        Args:
            sock: 套接字对象
        """
        try:
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
    
    def connection_made(self, transport: asyncio.DatagramTransport):
        """
        连接建立回调
        
        Args:
            transport: UDP传输对象
        """
        self.transport = transport
        self.logger.debug("UDP传输已建立")
    
    def connection_lost(self, exc: Optional[Exception]):
        """
        连接丢失回调
        
        Args:
            exc: 异常对象
        """
        self.transport = None
        self._connected = False
        
        if exc:
            self.logger.error(f"UDP传输丢失: {exc}")
        else:
            self.logger.info("UDP传输已关闭")
        
        # 调用断开连接回调
        if self.on_disconnected:
            try:
                asyncio.create_task(self.on_disconnected())
            except Exception as e:
                self.logger.error(f"断开连接回调错误: {e}")
    
    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        """
        数据报接收回调
        
        Args:
            data: 接收到的数据
            addr: 发送方地址
        """
        # 检查地址是否匹配
        expected_addr = (self.config.host, self.config.port)
        if addr[0] != expected_addr[0] or addr[1] != expected_addr[1]:
            self.logger.warning(f"收到来自意外地址的数据: {addr}，期望: {expected_addr}")
            return
        
        # 更新统计信息
        self.stats['total_bytes_received'] += len(data)
        
        # 处理数据
        if self.session:
            asyncio.create_task(self.session.process_data(data, self.transport))
    
    def error_received(self, exc: Exception):
        """
        错误接收回调
        
        Args:
            exc: 异常对象
        """
        self.logger.error(f"UDP错误: {exc}")
        self.stats['total_errors'] += 1
        
        if self.on_error:
            try:
                asyncio.create_task(self.on_error(exc))
            except Exception as e:
                self.logger.error(f"错误回调失败: {e}")
    
    async def send_data(self, data: bytes) -> bool:
        """
        发送数据
        
        Args:
            data: 要发送的数据
        
        Returns:
            bool: 是否发送成功
        """
        if not self.is_connected or not self.session:
            return False
        
        if await self.session.send_data(data, self.transport):
            self.stats['total_bytes_sent'] += len(data)
            return True
        
        return False
    
    async def _send_syn(self):
        """
        发送SYN包建立连接
        """
        if not self.is_connected or not self.session:
            return
        
        seq_num = random.randint(0, 0xFFFFFFFF)
        
        packet = UDPPacket(
            packet_type=UDPPacketType.SYN,
            sequence_number=seq_num,
            ack_number=0,
            data=b''
        )
        
        packet_data = packet.to_bytes()
        self.transport.sendto(packet_data, (self.config.host, self.config.port))
        
        # 更新统计信息
        self.stats['total_bytes_sent'] += len(packet_data)
        
        self.logger.debug(f"发送SYN包: SEQ={seq_num}")
    
    async def _send_fin(self):
        """
        发送FIN包关闭连接
        """
        if not self.is_connected or not self.session:
            return
        
        seq_num = random.randint(0, 0xFFFFFFFF)
        
        packet = UDPPacket(
            packet_type=UDPPacketType.FIN,
            sequence_number=seq_num,
            ack_number=0,
            data=b''
        )
        
        packet_data = packet.to_bytes()
        self.transport.sendto(packet_data, (self.config.host, self.config.port))
        
        # 更新统计信息
        self.stats['total_bytes_sent'] += len(packet_data)
        
        self.logger.debug(f"发送FIN包: SEQ={seq_num}")
    
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
    
    async def _on_session_closed(self):
        """
        会话关闭回调
        """
        self._connected = False
        
        # 关闭传输
        if self.transport:
            self.transport.close()
            self.transport = None
        
        if self.on_disconnected:
            try:
                await self.on_disconnected()
            except Exception as e:
                self.logger.error(f"断开连接回调错误: {e}")
    
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
                self.logger.error(f"错误回调错误: {e}")
    
    async def send_ping(self) -> bool:
        """
        发送心跳包
        
        Returns:
            bool: 是否发送成功
        """
        if not self.is_connected or not self.session:
            return False
        
        return await self.session.send_ping(self.transport)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取客户端统计信息
        
        Returns:
            dict: 统计信息
        """
        return {
            **self.stats,
            'connected': self.is_connected,
            'server_address': f"{self.config.host}:{self.config.port}",
            'reliable_udp': self.config.reliable_udp
        }

# 导出功能
__all__ = [
    'UDPSessionState',
    'UDPPacketType',
    'UDPServerConfig',
    'UDPClientConfig',
    'UDPSessionInfo',
    'UDPPacket',
    'UDPSession',
    'UDPServer',
    'UDPClient'
]