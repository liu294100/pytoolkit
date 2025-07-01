#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Raw Socket 协议模块

实现原始套接字通道功能
"""

import asyncio
import socket
import struct
import time
import uuid
import os
from typing import Optional, Dict, Any, Tuple, List, Union, Callable
import logging
from dataclasses import dataclass
from enum import Enum

from .protocol_manager import BaseProtocol, ProtocolConfig, ProtocolStatus, ProtocolType

class SocketType(Enum):
    """套接字类型"""
    TCP = socket.SOCK_STREAM
    UDP = socket.SOCK_DGRAM
    RAW = socket.SOCK_RAW
    ICMP = socket.IPPROTO_ICMP
    TCP_RAW = socket.IPPROTO_TCP
    UDP_RAW = socket.IPPROTO_UDP

class AddressFamily(Enum):
    """地址族"""
    IPv4 = socket.AF_INET
    IPv6 = socket.AF_INET6
    UNIX = getattr(socket, 'AF_UNIX', None)  # Unix/Linux only
    PACKET = getattr(socket, 'AF_PACKET', None)  # Linux only

class SocketMode(Enum):
    """套接字模式"""
    SERVER = "server"
    CLIENT = "client"
    BRIDGE = "bridge"
    SNIFFER = "sniffer"
    INJECTOR = "injector"

@dataclass
class RawSocketConfig:
    """原始套接字配置"""
    socket_type: SocketType
    address_family: AddressFamily
    mode: SocketMode
    bind_address: Optional[str] = None
    bind_port: Optional[int] = None
    target_address: Optional[str] = None
    target_port: Optional[int] = None
    interface: Optional[str] = None
    promiscuous: bool = False
    include_ip_header: bool = False
    custom_headers: bool = False
    packet_filter: Optional[str] = None
    buffer_size: int = 65536
    timeout: float = 30.0

@dataclass
class PacketInfo:
    """数据包信息"""
    timestamp: float
    source_addr: Tuple[str, int]
    dest_addr: Tuple[str, int]
    protocol: int
    data: bytes
    size: int
    direction: str  # 'in', 'out', 'forward'
    interface: Optional[str] = None
    packet_id: Optional[str] = None

@dataclass
class RawSocketConnectionInfo:
    """原始套接字连接信息"""
    conn_id: str
    socket_config: RawSocketConfig
    local_addr: Optional[Tuple[str, int]]
    remote_addr: Optional[Tuple[str, int]]
    start_time: float
    last_activity: float
    packets_sent: int = 0
    packets_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors: int = 0
    socket_fd: Optional[int] = None

class PacketParser:
    """
    数据包解析器
    
    解析各种网络协议的数据包
    """
    
    @staticmethod
    def parse_ip_header(data: bytes) -> Dict[str, Any]:
        """
        解析IP头部
        """
        if len(data) < 20:
            return {}
        
        try:
            # 解析IPv4头部
            version_ihl = data[0]
            version = (version_ihl >> 4) & 0xF
            ihl = version_ihl & 0xF
            
            if version == 4:
                # IPv4
                tos = data[1]
                total_length = struct.unpack('!H', data[2:4])[0]
                identification = struct.unpack('!H', data[4:6])[0]
                flags_fragment = struct.unpack('!H', data[6:8])[0]
                flags = (flags_fragment >> 13) & 0x7
                fragment_offset = flags_fragment & 0x1FFF
                ttl = data[8]
                protocol = data[9]
                checksum = struct.unpack('!H', data[10:12])[0]
                source_ip = socket.inet_ntoa(data[12:16])
                dest_ip = socket.inet_ntoa(data[16:20])
                
                header_length = ihl * 4
                options = data[20:header_length] if header_length > 20 else b''
                
                return {
                    'version': version,
                    'header_length': header_length,
                    'tos': tos,
                    'total_length': total_length,
                    'identification': identification,
                    'flags': flags,
                    'fragment_offset': fragment_offset,
                    'ttl': ttl,
                    'protocol': protocol,
                    'checksum': checksum,
                    'source_ip': source_ip,
                    'dest_ip': dest_ip,
                    'options': options,
                    'payload': data[header_length:]
                }
            
            elif version == 6:
                # IPv6 (简化版本)
                traffic_class = ((data[0] & 0x0F) << 4) | ((data[1] & 0xF0) >> 4)
                flow_label = struct.unpack('!I', b'\x00' + data[1:4])[0] & 0xFFFFF
                payload_length = struct.unpack('!H', data[4:6])[0]
                next_header = data[6]
                hop_limit = data[7]
                source_ip = socket.inet_ntop(socket.AF_INET6, data[8:24])
                dest_ip = socket.inet_ntop(socket.AF_INET6, data[24:40])
                
                return {
                    'version': version,
                    'traffic_class': traffic_class,
                    'flow_label': flow_label,
                    'payload_length': payload_length,
                    'next_header': next_header,
                    'hop_limit': hop_limit,
                    'source_ip': source_ip,
                    'dest_ip': dest_ip,
                    'payload': data[40:]
                }
        
        except Exception:
            pass
        
        return {}
    
    @staticmethod
    def parse_tcp_header(data: bytes) -> Dict[str, Any]:
        """
        解析TCP头部
        """
        if len(data) < 20:
            return {}
        
        try:
            source_port = struct.unpack('!H', data[0:2])[0]
            dest_port = struct.unpack('!H', data[2:4])[0]
            sequence_number = struct.unpack('!I', data[4:8])[0]
            ack_number = struct.unpack('!I', data[8:12])[0]
            
            data_offset_flags = struct.unpack('!H', data[12:14])[0]
            data_offset = (data_offset_flags >> 12) & 0xF
            flags = data_offset_flags & 0x1FF
            
            window_size = struct.unpack('!H', data[14:16])[0]
            checksum = struct.unpack('!H', data[16:18])[0]
            urgent_pointer = struct.unpack('!H', data[18:20])[0]
            
            header_length = data_offset * 4
            options = data[20:header_length] if header_length > 20 else b''
            
            return {
                'source_port': source_port,
                'dest_port': dest_port,
                'sequence_number': sequence_number,
                'ack_number': ack_number,
                'data_offset': data_offset,
                'flags': {
                    'fin': bool(flags & 0x01),
                    'syn': bool(flags & 0x02),
                    'rst': bool(flags & 0x04),
                    'psh': bool(flags & 0x08),
                    'ack': bool(flags & 0x10),
                    'urg': bool(flags & 0x20),
                    'ece': bool(flags & 0x40),
                    'cwr': bool(flags & 0x80),
                    'ns': bool(flags & 0x100)
                },
                'window_size': window_size,
                'checksum': checksum,
                'urgent_pointer': urgent_pointer,
                'options': options,
                'payload': data[header_length:]
            }
        
        except Exception:
            pass
        
        return {}
    
    @staticmethod
    def parse_udp_header(data: bytes) -> Dict[str, Any]:
        """
        解析UDP头部
        """
        if len(data) < 8:
            return {}
        
        try:
            source_port = struct.unpack('!H', data[0:2])[0]
            dest_port = struct.unpack('!H', data[2:4])[0]
            length = struct.unpack('!H', data[4:6])[0]
            checksum = struct.unpack('!H', data[6:8])[0]
            
            return {
                'source_port': source_port,
                'dest_port': dest_port,
                'length': length,
                'checksum': checksum,
                'payload': data[8:]
            }
        
        except Exception:
            pass
        
        return {}
    
    @staticmethod
    def parse_icmp_header(data: bytes) -> Dict[str, Any]:
        """
        解析ICMP头部
        """
        if len(data) < 8:
            return {}
        
        try:
            icmp_type = data[0]
            code = data[1]
            checksum = struct.unpack('!H', data[2:4])[0]
            identifier = struct.unpack('!H', data[4:6])[0]
            sequence = struct.unpack('!H', data[6:8])[0]
            
            return {
                'type': icmp_type,
                'code': code,
                'checksum': checksum,
                'identifier': identifier,
                'sequence': sequence,
                'payload': data[8:]
            }
        
        except Exception:
            pass
        
        return {}
    
    @staticmethod
    def build_ip_header(source_ip: str, dest_ip: str, protocol: int, payload_length: int, **kwargs) -> bytes:
        """
        构建IP头部
        """
        try:
            version = kwargs.get('version', 4)
            
            if version == 4:
                # IPv4头部
                ihl = 5  # 20字节头部
                tos = kwargs.get('tos', 0)
                total_length = 20 + payload_length
                identification = kwargs.get('identification', 0)
                flags = kwargs.get('flags', 0x2)  # Don't Fragment
                fragment_offset = kwargs.get('fragment_offset', 0)
                ttl = kwargs.get('ttl', 64)
                checksum = 0  # 先设为0，后面计算
                
                # 构建头部
                header = struct.pack('!BBHHHBBH4s4s',
                    (version << 4) | ihl,
                    tos,
                    total_length,
                    identification,
                    (flags << 13) | fragment_offset,
                    ttl,
                    protocol,
                    checksum,
                    socket.inet_aton(source_ip),
                    socket.inet_aton(dest_ip)
                )
                
                # 计算校验和
                checksum = PacketParser._calculate_checksum(header)
                
                # 重新构建头部
                header = struct.pack('!BBHHHBBH4s4s',
                    (version << 4) | ihl,
                    tos,
                    total_length,
                    identification,
                    (flags << 13) | fragment_offset,
                    ttl,
                    protocol,
                    checksum,
                    socket.inet_aton(source_ip),
                    socket.inet_aton(dest_ip)
                )
                
                return header
        
        except Exception:
            pass
        
        return b''
    
    @staticmethod
    def build_tcp_header(source_port: int, dest_port: int, seq: int, ack: int, flags: int, **kwargs) -> bytes:
        """
        构建TCP头部
        """
        try:
            data_offset = 5  # 20字节头部
            window_size = kwargs.get('window_size', 8192)
            checksum = 0  # 先设为0
            urgent_pointer = kwargs.get('urgent_pointer', 0)
            
            header = struct.pack('!HHIIBBHHH',
                source_port,
                dest_port,
                seq,
                ack,
                (data_offset << 4),
                flags,
                window_size,
                checksum,
                urgent_pointer
            )
            
            return header
        
        except Exception:
            pass
        
        return b''
    
    @staticmethod
    def build_udp_header(source_port: int, dest_port: int, payload_length: int) -> bytes:
        """
        构建UDP头部
        """
        try:
            length = 8 + payload_length
            checksum = 0  # 简化处理，不计算校验和
            
            header = struct.pack('!HHHH',
                source_port,
                dest_port,
                length,
                checksum
            )
            
            return header
        
        except Exception:
            pass
        
        return b''
    
    @staticmethod
    def _calculate_checksum(data: bytes) -> int:
        """
        计算校验和
        """
        try:
            # 简化的校验和计算
            checksum = 0
            
            # 按16位分组求和
            for i in range(0, len(data), 2):
                if i + 1 < len(data):
                    word = (data[i] << 8) + data[i + 1]
                else:
                    word = data[i] << 8
                checksum += word
            
            # 处理进位
            while checksum >> 16:
                checksum = (checksum & 0xFFFF) + (checksum >> 16)
            
            # 取反
            checksum = ~checksum & 0xFFFF
            
            return checksum
        
        except Exception:
            return 0

class RawSocketProxy(BaseProtocol):
    """
    原始套接字代理
    
    实现原始套接字通道功能
    """
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.server: Optional[asyncio.Server] = None
        self.connections: Dict[str, RawSocketConnectionInfo] = {}
        self.raw_sockets: Dict[str, socket.socket] = {}
        self.packet_parser = PacketParser()
        
        # 原始套接字配置
        self.socket_configs: List[RawSocketConfig] = getattr(config, 'socket_configs', [])
        self.default_socket_config = getattr(config, 'default_socket_config', None)
        
        # 数据包处理回调
        self.packet_handlers: Dict[str, Callable] = {}
        self.packet_filters: List[Callable] = []
    
    async def start(self) -> bool:
        """
        启动原始套接字代理
        """
        try:
            self.status = ProtocolStatus.STARTING
            self.stats.start_time = time.time()
            
            # 检查权限
            if not self._check_permissions():
                raise PermissionError("需要管理员权限才能使用原始套接字")
            
            # 创建原始套接字
            for socket_config in self.socket_configs:
                await self._create_raw_socket(socket_config)
            
            # 如果配置了服务器模式，启动服务器
            if any(sc.mode == SocketMode.SERVER for sc in self.socket_configs):
                self.server = await asyncio.start_server(
                    self.handle_connection,
                    self.config.host,
                    self.config.port,
                    limit=self.config.buffer_size
                )
            
            self.status = ProtocolStatus.RUNNING
            self.logger.info(f"原始套接字代理启动成功: {self.config.host}:{self.config.port}")
            
            if self.socket_configs:
                self.logger.info(f"配置了 {len(self.socket_configs)} 个原始套接字")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"启动原始套接字代理失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        停止原始套接字代理
        """
        try:
            self.status = ProtocolStatus.STOPPING
            
            # 关闭所有连接
            for conn_info in list(self.connections.values()):
                await self._close_connection(conn_info.conn_id)
            
            # 关闭原始套接字
            for sock in self.raw_sockets.values():
                sock.close()
            self.raw_sockets.clear()
            
            # 关闭服务器
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.status = ProtocolStatus.STOPPED
            self.stats.stop_time = time.time()
            self.logger.info("原始套接字代理已停止")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"停止原始套接字代理失败: {e}")
            return False
    
    def _check_permissions(self) -> bool:
        """
        检查权限
        """
        try:
            # 尝试创建原始套接字来检查权限
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            test_socket.close()
            return True
        except PermissionError:
            return False
        except Exception:
            # 其他错误可能是因为平台不支持
            return True
    
    async def _create_raw_socket(self, socket_config: RawSocketConfig) -> bool:
        """
        创建原始套接字
        """
        try:
            # 创建套接字
            if socket_config.socket_type == SocketType.RAW:
                sock = socket.socket(
                    socket_config.address_family.value,
                    socket.SOCK_RAW,
                    socket.IPPROTO_IP if socket_config.address_family == AddressFamily.IPv4 else socket.IPPROTO_IPV6
                )
            else:
                sock = socket.socket(
                    socket_config.address_family.value,
                    socket_config.socket_type.value
                )
            
            # 设置套接字选项
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            if socket_config.socket_type == SocketType.RAW:
                # 原始套接字特殊设置
                if socket_config.include_ip_header:
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                
                if socket_config.promiscuous and hasattr(socket, 'SO_BINDTODEVICE'):
                    if socket_config.interface:
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, 
                                      socket_config.interface.encode())
            
            # 绑定地址
            if socket_config.bind_address and socket_config.bind_port:
                sock.bind((socket_config.bind_address, socket_config.bind_port))
            elif socket_config.bind_address:
                sock.bind((socket_config.bind_address, 0))
            
            # 设置非阻塞
            sock.setblocking(False)
            
            # 保存套接字
            sock_id = str(uuid.uuid4())
            self.raw_sockets[sock_id] = sock
            
            # 创建连接信息
            conn_info = RawSocketConnectionInfo(
                conn_id=sock_id,
                socket_config=socket_config,
                local_addr=sock.getsockname() if socket_config.bind_address else None,
                remote_addr=None,
                start_time=time.time(),
                last_activity=time.time(),
                socket_fd=sock.fileno()
            )
            
            self.connections[sock_id] = conn_info
            self.add_connection(sock_id, conn_info)
            
            # 启动数据包处理任务
            if socket_config.mode in [SocketMode.SNIFFER, SocketMode.BRIDGE]:
                asyncio.create_task(self._packet_sniffer_loop(sock_id))
            
            self.logger.info(f"原始套接字创建成功: {socket_config.socket_type.name} - {sock_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建原始套接字失败: {e}")
            return False
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理客户端连接
        """
        conn_id = str(uuid.uuid4())
        client_addr = writer.get_extra_info('peername')
        
        # 选择套接字配置
        socket_config = self._select_socket_config(client_addr)
        if not socket_config:
            self.logger.error(f"未找到适合的套接字配置: {client_addr}")
            writer.close()
            return
        
        # 创建连接信息
        conn_info = RawSocketConnectionInfo(
            conn_id=conn_id,
            socket_config=socket_config,
            local_addr=None,
            remote_addr=client_addr,
            start_time=time.time(),
            last_activity=time.time()
        )
        
        self.connections[conn_id] = conn_info
        self.add_connection(conn_id, conn_info)
        
        try:
            self.logger.info(f"新原始套接字连接: {client_addr}")
            
            # 处理连接
            if socket_config.mode == SocketMode.CLIENT:
                await self._handle_client_mode(conn_id, reader, writer)
            elif socket_config.mode == SocketMode.BRIDGE:
                await self._handle_bridge_mode(conn_id, reader, writer)
            elif socket_config.mode == SocketMode.INJECTOR:
                await self._handle_injector_mode(conn_id, reader, writer)
            else:
                await self._handle_server_mode(conn_id, reader, writer)
            
        except Exception as e:
            self.logger.error(f"处理原始套接字连接 {conn_id} 时发生错误: {e}")
            self.stats.errors += 1
        finally:
            # 清理连接
            await self._cleanup_connection(conn_id, writer)
    
    def _select_socket_config(self, client_addr: Tuple[str, int]) -> Optional[RawSocketConfig]:
        """
        选择套接字配置
        """
        # 简化版本：返回默认配置或第一个配置
        if self.default_socket_config:
            return self.default_socket_config
        elif self.socket_configs:
            return self.socket_configs[0]
        else:
            # 创建默认配置
            return RawSocketConfig(
                socket_type=SocketType.TCP,
                address_family=AddressFamily.IPv4,
                mode=SocketMode.SERVER
            )
    
    async def _handle_client_mode(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理客户端模式
        """
        conn_info = self.connections[conn_id]
        socket_config = conn_info.socket_config
        
        try:
            # 连接到目标
            if socket_config.target_address and socket_config.target_port:
                target_reader, target_writer = await asyncio.open_connection(
                    socket_config.target_address,
                    socket_config.target_port
                )
                
                # 双向转发
                client_to_target = asyncio.create_task(
                    self._forward_data(conn_id, reader, target_writer, "client->target")
                )
                target_to_client = asyncio.create_task(
                    self._forward_data(conn_id, target_reader, writer, "target->client")
                )
                
                # 等待任一任务完成
                done, pending = await asyncio.wait(
                    [client_to_target, target_to_client],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # 取消剩余任务
                for task in pending:
                    task.cancel()
                
                # 关闭目标连接
                target_writer.close()
                await target_writer.wait_closed()
            
        except Exception as e:
            self.logger.error(f"客户端模式处理错误: {e}")
    
    async def _handle_bridge_mode(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理桥接模式
        """
        conn_info = self.connections[conn_id]
        
        try:
            # 桥接模式：在客户端和原始套接字之间转发数据
            # 这里需要根据具体需求实现
            
            # 读取客户端数据并通过原始套接字发送
            while True:
                data = await reader.read(self.config.buffer_size)
                if not data:
                    break
                
                # 解析数据包
                packet_info = await self._parse_packet(data)
                if packet_info:
                    # 通过原始套接字发送
                    await self._send_raw_packet(conn_id, packet_info)
                
                conn_info.packets_received += 1
                conn_info.bytes_received += len(data)
                conn_info.last_activity = time.time()
                self.stats.bytes_received += len(data)
            
        except Exception as e:
            self.logger.error(f"桥接模式处理错误: {e}")
    
    async def _handle_injector_mode(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理注入模式
        """
        conn_info = self.connections[conn_id]
        
        try:
            # 注入模式：接收数据包描述并构造发送
            while True:
                data = await reader.read(self.config.buffer_size)
                if not data:
                    break
                
                try:
                    # 假设接收JSON格式的数据包描述
                    import json
                    packet_desc = json.loads(data.decode('utf-8'))
                    
                    # 构造数据包
                    packet = await self._build_packet(packet_desc)
                    if packet:
                        # 发送数据包
                        await self._inject_packet(conn_id, packet)
                        
                        # 发送确认
                        response = json.dumps({'status': 'sent', 'size': len(packet)})
                        writer.write(response.encode('utf-8'))
                        await writer.drain()
                
                except Exception as e:
                    # 发送错误响应
                    error_response = json.dumps({'status': 'error', 'message': str(e)})
                    writer.write(error_response.encode('utf-8'))
                    await writer.drain()
                
                conn_info.last_activity = time.time()
            
        except Exception as e:
            self.logger.error(f"注入模式处理错误: {e}")
    
    async def _handle_server_mode(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理服务器模式
        """
        conn_info = self.connections[conn_id]
        
        try:
            # 服务器模式：提供原始套接字服务
            while True:
                data = await reader.read(self.config.buffer_size)
                if not data:
                    break
                
                # 处理客户端请求
                response = await self._process_raw_request(conn_id, data)
                if response:
                    writer.write(response)
                    await writer.drain()
                
                conn_info.packets_received += 1
                conn_info.bytes_received += len(data)
                conn_info.last_activity = time.time()
                self.stats.bytes_received += len(data)
            
        except Exception as e:
            self.logger.error(f"服务器模式处理错误: {e}")
    
    async def _packet_sniffer_loop(self, sock_id: str):
        """
        数据包嗅探循环
        """
        try:
            sock = self.raw_sockets[sock_id]
            conn_info = self.connections[sock_id]
            
            while sock_id in self.raw_sockets:
                try:
                    # 接收数据包
                    data, addr = await asyncio.get_event_loop().sock_recvfrom(sock, 65536)
                    
                    if data:
                        # 解析数据包
                        packet_info = await self._parse_packet(data, addr)
                        if packet_info:
                            # 应用过滤器
                            if self._apply_packet_filters(packet_info):
                                # 处理数据包
                                await self._handle_captured_packet(sock_id, packet_info)
                        
                        # 更新统计信息
                        conn_info.packets_received += 1
                        conn_info.bytes_received += len(data)
                        conn_info.last_activity = time.time()
                        self.stats.bytes_received += len(data)
                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.debug(f"数据包嗅探错误: {e}")
                    await asyncio.sleep(0.1)
            
        except Exception as e:
            self.logger.error(f"数据包嗅探循环错误: {e}")
    
    async def _parse_packet(self, data: bytes, addr: Optional[Tuple] = None) -> Optional[PacketInfo]:
        """
        解析数据包
        """
        try:
            timestamp = time.time()
            packet_id = str(uuid.uuid4())
            
            # 解析IP头部
            ip_info = self.packet_parser.parse_ip_header(data)
            if not ip_info:
                return None
            
            source_addr = (ip_info.get('source_ip', ''), 0)
            dest_addr = (ip_info.get('dest_ip', ''), 0)
            protocol = ip_info.get('protocol', 0)
            
            # 解析传输层协议
            payload = ip_info.get('payload', b'')
            if protocol == socket.IPPROTO_TCP:
                tcp_info = self.packet_parser.parse_tcp_header(payload)
                if tcp_info:
                    source_addr = (ip_info.get('source_ip', ''), tcp_info.get('source_port', 0))
                    dest_addr = (ip_info.get('dest_ip', ''), tcp_info.get('dest_port', 0))
            elif protocol == socket.IPPROTO_UDP:
                udp_info = self.packet_parser.parse_udp_header(payload)
                if udp_info:
                    source_addr = (ip_info.get('source_ip', ''), udp_info.get('source_port', 0))
                    dest_addr = (ip_info.get('dest_ip', ''), udp_info.get('dest_port', 0))
            
            return PacketInfo(
                timestamp=timestamp,
                source_addr=source_addr,
                dest_addr=dest_addr,
                protocol=protocol,
                data=data,
                size=len(data),
                direction='in',
                packet_id=packet_id
            )
            
        except Exception as e:
            self.logger.debug(f"解析数据包失败: {e}")
            return None
    
    def _apply_packet_filters(self, packet_info: PacketInfo) -> bool:
        """
        应用数据包过滤器
        """
        try:
            for filter_func in self.packet_filters:
                if not filter_func(packet_info):
                    return False
            return True
        except Exception:
            return True
    
    async def _handle_captured_packet(self, sock_id: str, packet_info: PacketInfo):
        """
        处理捕获的数据包
        """
        try:
            # 调用注册的处理器
            for handler_name, handler_func in self.packet_handlers.items():
                try:
                    await handler_func(sock_id, packet_info)
                except Exception as e:
                    self.logger.debug(f"数据包处理器 {handler_name} 错误: {e}")
            
            # 记录数据包信息
            self.logger.debug(
                f"捕获数据包: {packet_info.source_addr} -> {packet_info.dest_addr}, "
                f"协议: {packet_info.protocol}, 大小: {packet_info.size}"
            )
            
        except Exception as e:
            self.logger.error(f"处理捕获数据包错误: {e}")
    
    async def _send_raw_packet(self, conn_id: str, packet_info: PacketInfo):
        """
        发送原始数据包
        """
        try:
            # 查找合适的原始套接字
            for sock_id, sock in self.raw_sockets.items():
                conn_info = self.connections.get(sock_id)
                if conn_info and conn_info.socket_config.socket_type == SocketType.RAW:
                    # 发送数据包
                    await asyncio.get_event_loop().sock_sendto(
                        sock, packet_info.data, packet_info.dest_addr
                    )
                    
                    # 更新统计信息
                    conn_info.packets_sent += 1
                    conn_info.bytes_sent += packet_info.size
                    conn_info.last_activity = time.time()
                    self.stats.bytes_sent += packet_info.size
                    
                    break
            
        except Exception as e:
            self.logger.error(f"发送原始数据包失败: {e}")
    
    async def _build_packet(self, packet_desc: Dict[str, Any]) -> Optional[bytes]:
        """
        根据描述构造数据包
        """
        try:
            # 提取数据包信息
            source_ip = packet_desc.get('source_ip')
            dest_ip = packet_desc.get('dest_ip')
            protocol = packet_desc.get('protocol')
            payload = packet_desc.get('payload', b'')
            
            if isinstance(payload, str):
                payload = payload.encode('utf-8')
            
            if not all([source_ip, dest_ip, protocol]):
                return None
            
            # 构造IP头部
            ip_header = self.packet_parser.build_ip_header(
                source_ip, dest_ip, protocol, len(payload)
            )
            
            # 构造传输层头部
            transport_header = b''
            if protocol == socket.IPPROTO_TCP:
                tcp_info = packet_desc.get('tcp', {})
                transport_header = self.packet_parser.build_tcp_header(
                    tcp_info.get('source_port', 0),
                    tcp_info.get('dest_port', 0),
                    tcp_info.get('seq', 0),
                    tcp_info.get('ack', 0),
                    tcp_info.get('flags', 0)
                )
            elif protocol == socket.IPPROTO_UDP:
                udp_info = packet_desc.get('udp', {})
                transport_header = self.packet_parser.build_udp_header(
                    udp_info.get('source_port', 0),
                    udp_info.get('dest_port', 0),
                    len(payload)
                )
            
            # 组合数据包
            packet = ip_header + transport_header + payload
            return packet
            
        except Exception as e:
            self.logger.error(f"构造数据包失败: {e}")
            return None
    
    async def _inject_packet(self, conn_id: str, packet: bytes):
        """
        注入数据包
        """
        try:
            # 解析数据包以获取目标地址
            packet_info = await self._parse_packet(packet)
            if packet_info:
                await self._send_raw_packet(conn_id, packet_info)
            
        except Exception as e:
            self.logger.error(f"注入数据包失败: {e}")
    
    async def _process_raw_request(self, conn_id: str, data: bytes) -> Optional[bytes]:
        """
        处理原始套接字请求
        """
        try:
            # 简化的请求处理
            # 实际实现应该根据具体协议处理
            
            # 回显数据
            return data
            
        except Exception as e:
            self.logger.error(f"处理原始套接字请求失败: {e}")
            return None
    
    async def _forward_data(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str):
        """
        转发数据
        """
        try:
            conn_info = self.connections[conn_id]
            
            while True:
                data = await reader.read(self.config.buffer_size)
                if not data:
                    break
                
                writer.write(data)
                await writer.drain()
                
                # 更新统计信息
                if direction.startswith("client"):
                    conn_info.bytes_sent += len(data)
                    self.stats.bytes_sent += len(data)
                else:
                    conn_info.bytes_received += len(data)
                    self.stats.bytes_received += len(data)
                
                conn_info.last_activity = time.time()
            
        except Exception as e:
            self.logger.debug(f"数据转发 {direction} 结束: {e}")
    
    async def _close_connection(self, conn_id: str):
        """
        关闭连接
        """
        try:
            if conn_id in self.raw_sockets:
                sock = self.raw_sockets[conn_id]
                sock.close()
                del self.raw_sockets[conn_id]
            
        except Exception as e:
            self.logger.error(f"关闭原始套接字失败: {e}")
    
    async def _cleanup_connection(self, conn_id: str, writer: asyncio.StreamWriter):
        """
        清理连接
        """
        try:
            # 关闭原始套接字
            await self._close_connection(conn_id)
            
            # 关闭客户端连接
            writer.close()
            await writer.wait_closed()
            
        except Exception:
            pass
        
        if conn_id in self.connections:
            del self.connections[conn_id]
        
        self.remove_connection(conn_id)
        self.logger.info(f"原始套接字连接 {conn_id} 已清理")
    
    def add_packet_handler(self, name: str, handler: Callable):
        """
        添加数据包处理器
        """
        self.packet_handlers[name] = handler
    
    def remove_packet_handler(self, name: str):
        """
        移除数据包处理器
        """
        if name in self.packet_handlers:
            del self.packet_handlers[name]
    
    def add_packet_filter(self, filter_func: Callable):
        """
        添加数据包过滤器
        """
        self.packet_filters.append(filter_func)
    
    def clear_packet_filters(self):
        """
        清除所有数据包过滤器
        """
        self.packet_filters.clear()

# 导出功能
__all__ = [
    'SocketType',
    'AddressFamily',
    'SocketMode',
    'RawSocketConfig',
    'PacketInfo',
    'RawSocketConnectionInfo',
    'PacketParser',
    'RawSocketProxy'
]