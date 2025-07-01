#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SSH隧道协议模块

实现SSH tunnel通道功能
"""

import asyncio
import socket
import struct
import time
import uuid
import base64
import hashlib
import hmac
import os
from typing import Optional, Dict, Any, Tuple, List, Union, Callable
import logging
from dataclasses import dataclass
from enum import Enum

from .protocol_manager import BaseProtocol, ProtocolConfig, ProtocolStatus, ProtocolType

class SSHMessageType(Enum):
    """SSH消息类型"""
    SSH_MSG_DISCONNECT = 1
    SSH_MSG_IGNORE = 2
    SSH_MSG_UNIMPLEMENTED = 3
    SSH_MSG_DEBUG = 4
    SSH_MSG_SERVICE_REQUEST = 5
    SSH_MSG_SERVICE_ACCEPT = 6
    SSH_MSG_KEXINIT = 20
    SSH_MSG_NEWKEYS = 21
    SSH_MSG_KEXDH_INIT = 30
    SSH_MSG_KEXDH_REPLY = 31
    SSH_MSG_USERAUTH_REQUEST = 50
    SSH_MSG_USERAUTH_FAILURE = 51
    SSH_MSG_USERAUTH_SUCCESS = 52
    SSH_MSG_USERAUTH_BANNER = 53
    SSH_MSG_GLOBAL_REQUEST = 80
    SSH_MSG_REQUEST_SUCCESS = 81
    SSH_MSG_REQUEST_FAILURE = 82
    SSH_MSG_CHANNEL_OPEN = 90
    SSH_MSG_CHANNEL_OPEN_CONFIRMATION = 91
    SSH_MSG_CHANNEL_OPEN_FAILURE = 92
    SSH_MSG_CHANNEL_WINDOW_ADJUST = 93
    SSH_MSG_CHANNEL_DATA = 94
    SSH_MSG_CHANNEL_EXTENDED_DATA = 95
    SSH_MSG_CHANNEL_EOF = 96
    SSH_MSG_CHANNEL_CLOSE = 97
    SSH_MSG_CHANNEL_REQUEST = 98
    SSH_MSG_CHANNEL_SUCCESS = 99
    SSH_MSG_CHANNEL_FAILURE = 100

class SSHChannelType(Enum):
    """SSH通道类型"""
    SESSION = "session"
    DIRECT_TCPIP = "direct-tcpip"
    FORWARDED_TCPIP = "forwarded-tcpip"
    X11 = "x11"

class SSHTunnelType(Enum):
    """SSH隧道类型"""
    LOCAL_FORWARD = "local_forward"    # 本地端口转发
    REMOTE_FORWARD = "remote_forward"  # 远程端口转发
    DYNAMIC_FORWARD = "dynamic_forward" # 动态端口转发(SOCKS)
    REVERSE_TUNNEL = "reverse_tunnel"  # 反向隧道

@dataclass
class SSHPacket:
    """SSH数据包"""
    packet_length: int
    padding_length: int
    payload: bytes
    padding: bytes
    mac: Optional[bytes] = None

@dataclass
class SSHChannel:
    """SSH通道"""
    channel_id: int
    remote_channel_id: int
    channel_type: str
    window_size: int
    max_packet_size: int
    connected: bool = False
    eof_sent: bool = False
    eof_received: bool = False
    closed: bool = False
    data_buffer: bytes = b''

@dataclass
class SSHTunnelConfig:
    """SSH隧道配置"""
    tunnel_type: SSHTunnelType
    local_host: str
    local_port: int
    remote_host: str
    remote_port: int
    ssh_host: str
    ssh_port: int
    username: str
    password: Optional[str] = None
    private_key: Optional[str] = None
    private_key_password: Optional[str] = None
    host_key_verify: bool = True
    compression: bool = False
    keepalive_interval: int = 30

@dataclass
class SSHConnectionInfo:
    """SSH连接信息"""
    conn_id: str
    client_addr: Tuple[str, int]
    ssh_addr: Tuple[str, int]
    tunnel_config: SSHTunnelConfig
    start_time: float
    last_activity: float
    authenticated: bool = False
    channels: Dict[int, SSHChannel] = None
    next_channel_id: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = {}

class SSHProtocolHandler:
    """
    SSH协议处理器
    
    实现SSH协议的基本功能
    """
    
    def __init__(self):
        self.sequence_number_in = 0
        self.sequence_number_out = 0
        self.session_id: Optional[bytes] = None
        self.encryption_key_c2s: Optional[bytes] = None
        self.encryption_key_s2c: Optional[bytes] = None
        self.mac_key_c2s: Optional[bytes] = None
        self.mac_key_s2c: Optional[bytes] = None
        self.block_size_in = 8
        self.block_size_out = 8
        self.mac_size_in = 0
        self.mac_size_out = 0
    
    def pack_packet(self, payload: bytes) -> bytes:
        """
        打包SSH数据包
        """
        # 计算填充长度
        packet_length = 4 + 1 + len(payload)  # packet_length + padding_length + payload
        padding_length = self.block_size_out - (packet_length % self.block_size_out)
        if padding_length < 4:
            padding_length += self.block_size_out
        
        # 生成随机填充
        padding = os.urandom(padding_length)
        
        # 构建数据包
        packet_length = 1 + len(payload) + padding_length
        packet = struct.pack('!I', packet_length)
        packet += struct.pack('!B', padding_length)
        packet += payload
        packet += padding
        
        # 计算MAC（如果启用）
        if self.mac_size_out > 0 and self.mac_key_s2c:
            mac_data = struct.pack('!I', self.sequence_number_out) + packet
            mac = hmac.new(self.mac_key_s2c, mac_data, hashlib.sha1).digest()[:self.mac_size_out]
            packet += mac
        
        self.sequence_number_out += 1
        return packet
    
    def unpack_packet(self, data: bytes) -> Tuple[Optional[SSHPacket], int]:
        """
        解包SSH数据包
        
        返回: (数据包对象, 消耗的字节数)
        """
        if len(data) < 4:
            return None, 0
        
        # 读取数据包长度
        packet_length = struct.unpack('!I', data[:4])[0]
        
        # 检查数据包完整性
        total_length = 4 + packet_length + self.mac_size_in
        if len(data) < total_length:
            return None, 0
        
        # 提取数据包内容
        packet_data = data[4:4+packet_length]
        
        if len(packet_data) < 1:
            return None, total_length
        
        padding_length = packet_data[0]
        payload_length = packet_length - 1 - padding_length
        
        if payload_length < 0 or len(packet_data) < 1 + payload_length + padding_length:
            return None, total_length
        
        payload = packet_data[1:1+payload_length]
        padding = packet_data[1+payload_length:1+payload_length+padding_length]
        
        # 提取MAC（如果有）
        mac = None
        if self.mac_size_in > 0:
            mac = data[4+packet_length:4+packet_length+self.mac_size_in]
        
        packet = SSHPacket(
            packet_length=packet_length,
            padding_length=padding_length,
            payload=payload,
            padding=padding,
            mac=mac
        )
        
        self.sequence_number_in += 1
        return packet, total_length
    
    def build_version_string(self) -> bytes:
        """
        构建SSH版本字符串
        """
        return b"SSH-2.0-PySSHTunnel_1.0\r\n"
    
    def parse_version_string(self, data: bytes) -> Optional[str]:
        """
        解析SSH版本字符串
        """
        try:
            version_line = data.split(b'\r\n')[0].decode('ascii')
            if version_line.startswith('SSH-'):
                return version_line
        except Exception:
            pass
        return None
    
    def build_kexinit(self) -> bytes:
        """
        构建密钥交换初始化消息
        """
        # 生成随机cookie
        cookie = os.urandom(16)
        
        # 算法列表（简化版本）
        kex_algorithms = b"diffie-hellman-group14-sha256"
        server_host_key_algorithms = b"ssh-rsa"
        encryption_algorithms_c2s = b"aes128-ctr"
        encryption_algorithms_s2c = b"aes128-ctr"
        mac_algorithms_c2s = b"hmac-sha1"
        mac_algorithms_s2c = b"hmac-sha1"
        compression_algorithms_c2s = b"none"
        compression_algorithms_s2c = b"none"
        languages_c2s = b""
        languages_s2c = b""
        
        # 构建消息
        payload = struct.pack('!B', SSHMessageType.SSH_MSG_KEXINIT.value)
        payload += cookie
        
        # 添加算法列表
        for alg_list in [kex_algorithms, server_host_key_algorithms,
                        encryption_algorithms_c2s, encryption_algorithms_s2c,
                        mac_algorithms_c2s, mac_algorithms_s2c,
                        compression_algorithms_c2s, compression_algorithms_s2c,
                        languages_c2s, languages_s2c]:
            payload += struct.pack('!I', len(alg_list)) + alg_list
        
        # 添加标志
        payload += struct.pack('!B', 0)  # first_kex_packet_follows
        payload += struct.pack('!I', 0)  # reserved
        
        return payload
    
    def build_service_request(self, service_name: str) -> bytes:
        """
        构建服务请求消息
        """
        service_bytes = service_name.encode('utf-8')
        payload = struct.pack('!B', SSHMessageType.SSH_MSG_SERVICE_REQUEST.value)
        payload += struct.pack('!I', len(service_bytes)) + service_bytes
        return payload
    
    def build_userauth_request(self, username: str, service: str, method: str, **kwargs) -> bytes:
        """
        构建用户认证请求消息
        """
        username_bytes = username.encode('utf-8')
        service_bytes = service.encode('utf-8')
        method_bytes = method.encode('utf-8')
        
        payload = struct.pack('!B', SSHMessageType.SSH_MSG_USERAUTH_REQUEST.value)
        payload += struct.pack('!I', len(username_bytes)) + username_bytes
        payload += struct.pack('!I', len(service_bytes)) + service_bytes
        payload += struct.pack('!I', len(method_bytes)) + method_bytes
        
        if method == 'password':
            payload += struct.pack('!B', 0)  # password change flag
            password = kwargs.get('password', '').encode('utf-8')
            payload += struct.pack('!I', len(password)) + password
        elif method == 'publickey':
            # 简化的公钥认证
            payload += struct.pack('!B', 0)  # signature flag
            algorithm = b'ssh-rsa'
            payload += struct.pack('!I', len(algorithm)) + algorithm
            # 这里应该添加公钥数据，简化处理
            public_key = b''
            payload += struct.pack('!I', len(public_key)) + public_key
        
        return payload
    
    def build_channel_open(self, channel_type: str, sender_channel: int, 
                          initial_window_size: int, maximum_packet_size: int,
                          **kwargs) -> bytes:
        """
        构建通道打开消息
        """
        channel_type_bytes = channel_type.encode('utf-8')
        
        payload = struct.pack('!B', SSHMessageType.SSH_MSG_CHANNEL_OPEN.value)
        payload += struct.pack('!I', len(channel_type_bytes)) + channel_type_bytes
        payload += struct.pack('!I', sender_channel)
        payload += struct.pack('!I', initial_window_size)
        payload += struct.pack('!I', maximum_packet_size)
        
        # 添加通道特定数据
        if channel_type == 'direct-tcpip':
            host = kwargs.get('host', '').encode('utf-8')
            port = kwargs.get('port', 0)
            originator_ip = kwargs.get('originator_ip', '').encode('utf-8')
            originator_port = kwargs.get('originator_port', 0)
            
            payload += struct.pack('!I', len(host)) + host
            payload += struct.pack('!I', port)
            payload += struct.pack('!I', len(originator_ip)) + originator_ip
            payload += struct.pack('!I', originator_port)
        
        return payload
    
    def build_channel_data(self, recipient_channel: int, data: bytes) -> bytes:
        """
        构建通道数据消息
        """
        payload = struct.pack('!B', SSHMessageType.SSH_MSG_CHANNEL_DATA.value)
        payload += struct.pack('!I', recipient_channel)
        payload += struct.pack('!I', len(data)) + data
        return payload
    
    def build_channel_close(self, recipient_channel: int) -> bytes:
        """
        构建通道关闭消息
        """
        payload = struct.pack('!B', SSHMessageType.SSH_MSG_CHANNEL_CLOSE.value)
        payload += struct.pack('!I', recipient_channel)
        return payload
    
    def parse_message(self, payload: bytes) -> Dict[str, Any]:
        """
        解析SSH消息
        """
        if not payload:
            return {}
        
        message_type = payload[0]
        data = payload[1:]
        
        result = {'type': message_type}
        
        try:
            if message_type == SSHMessageType.SSH_MSG_CHANNEL_OPEN_CONFIRMATION.value:
                if len(data) >= 16:
                    recipient_channel = struct.unpack('!I', data[0:4])[0]
                    sender_channel = struct.unpack('!I', data[4:8])[0]
                    initial_window_size = struct.unpack('!I', data[8:12])[0]
                    maximum_packet_size = struct.unpack('!I', data[12:16])[0]
                    
                    result.update({
                        'recipient_channel': recipient_channel,
                        'sender_channel': sender_channel,
                        'initial_window_size': initial_window_size,
                        'maximum_packet_size': maximum_packet_size
                    })
            
            elif message_type == SSHMessageType.SSH_MSG_CHANNEL_DATA.value:
                if len(data) >= 8:
                    recipient_channel = struct.unpack('!I', data[0:4])[0]
                    data_length = struct.unpack('!I', data[4:8])[0]
                    channel_data = data[8:8+data_length]
                    
                    result.update({
                        'recipient_channel': recipient_channel,
                        'data': channel_data
                    })
            
            elif message_type == SSHMessageType.SSH_MSG_CHANNEL_CLOSE.value:
                if len(data) >= 4:
                    recipient_channel = struct.unpack('!I', data[0:4])[0]
                    result['recipient_channel'] = recipient_channel
            
            elif message_type == SSHMessageType.SSH_MSG_SERVICE_ACCEPT.value:
                if len(data) >= 4:
                    service_length = struct.unpack('!I', data[0:4])[0]
                    service_name = data[4:4+service_length].decode('utf-8')
                    result['service'] = service_name
            
            elif message_type == SSHMessageType.SSH_MSG_USERAUTH_SUCCESS.value:
                result['authenticated'] = True
            
            elif message_type == SSHMessageType.SSH_MSG_USERAUTH_FAILURE.value:
                # 解析认证失败信息
                if len(data) >= 4:
                    methods_length = struct.unpack('!I', data[0:4])[0]
                    methods = data[4:4+methods_length].decode('utf-8')
                    partial_success = data[4+methods_length] if len(data) > 4+methods_length else 0
                    result.update({
                        'methods': methods.split(','),
                        'partial_success': bool(partial_success)
                    })
        
        except Exception as e:
            result['parse_error'] = str(e)
        
        return result

class SSHTunnel(BaseProtocol):
    """
    SSH隧道代理
    
    实现SSH tunnel通道功能
    """
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.server: Optional[asyncio.Server] = None
        self.connections: Dict[str, SSHConnectionInfo] = {}
        self.ssh_handler = SSHProtocolHandler()
        
        # SSH隧道配置
        self.tunnel_configs: List[SSHTunnelConfig] = getattr(config, 'tunnel_configs', [])
        self.default_tunnel_config = getattr(config, 'default_tunnel_config', None)
    
    async def start(self) -> bool:
        """
        启动SSH隧道服务器
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
            self.logger.info(f"SSH隧道服务器启动成功: {self.config.host}:{self.config.port}")
            
            if self.tunnel_configs:
                self.logger.info(f"配置了 {len(self.tunnel_configs)} 个隧道")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"启动SSH隧道服务器失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        停止SSH隧道服务器
        """
        try:
            self.status = ProtocolStatus.STOPPING
            
            # 关闭所有连接
            for conn_info in list(self.connections.values()):
                await self._close_ssh_connection(conn_info.conn_id)
            
            # 关闭服务器
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.status = ProtocolStatus.STOPPED
            self.stats.stop_time = time.time()
            self.logger.info("SSH隧道服务器已停止")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"停止SSH隧道服务器失败: {e}")
            return False
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理SSH隧道连接
        """
        conn_id = str(uuid.uuid4())
        client_addr = writer.get_extra_info('peername')
        
        # 选择隧道配置
        tunnel_config = self._select_tunnel_config(client_addr)
        if not tunnel_config:
            self.logger.error(f"未找到适合的隧道配置: {client_addr}")
            writer.close()
            return
        
        # 创建连接信息
        conn_info = SSHConnectionInfo(
            conn_id=conn_id,
            client_addr=client_addr,
            ssh_addr=(tunnel_config.ssh_host, tunnel_config.ssh_port),
            tunnel_config=tunnel_config,
            start_time=time.time(),
            last_activity=time.time()
        )
        
        self.connections[conn_id] = conn_info
        self.add_connection(conn_id, conn_info)
        
        try:
            self.logger.info(f"新SSH隧道连接: {client_addr} -> {tunnel_config.ssh_host}:{tunnel_config.ssh_port}")
            
            # 建立SSH连接
            if await self._establish_ssh_connection(conn_id):
                # SSH连接成功，开始处理隧道通信
                await self._handle_tunnel_communication(conn_id, reader, writer)
            
        except Exception as e:
            self.logger.error(f"处理SSH隧道连接 {conn_id} 时发生错误: {e}")
            self.stats.errors += 1
        finally:
            # 清理连接
            await self._cleanup_connection(conn_id, writer)
    
    def _select_tunnel_config(self, client_addr: Tuple[str, int]) -> Optional[SSHTunnelConfig]:
        """
        选择隧道配置
        """
        # 简化版本：返回默认配置或第一个配置
        if self.default_tunnel_config:
            return self.default_tunnel_config
        elif self.tunnel_configs:
            return self.tunnel_configs[0]
        else:
            # 使用协议配置创建默认隧道配置
            return SSHTunnelConfig(
                tunnel_type=SSHTunnelType.LOCAL_FORWARD,
                local_host=self.config.host,
                local_port=self.config.port,
                remote_host=getattr(self.config, 'target_host', 'localhost'),
                remote_port=getattr(self.config, 'target_port', 22),
                ssh_host=getattr(self.config, 'ssh_host', 'localhost'),
                ssh_port=getattr(self.config, 'ssh_port', 22),
                username=getattr(self.config, 'username', 'user'),
                password=getattr(self.config, 'password', None)
            )
    
    async def _establish_ssh_connection(self, conn_id: str) -> bool:
        """
        建立SSH连接
        """
        try:
            conn_info = self.connections[conn_id]
            tunnel_config = conn_info.tunnel_config
            
            # 连接到SSH服务器
            ssh_reader, ssh_writer = await asyncio.open_connection(
                tunnel_config.ssh_host,
                tunnel_config.ssh_port
            )
            
            # 保存SSH连接
            setattr(conn_info, '_ssh_reader', ssh_reader)
            setattr(conn_info, '_ssh_writer', ssh_writer)
            
            # 执行SSH握手
            if await self._ssh_handshake(conn_id):
                # 认证
                if await self._ssh_authenticate(conn_id):
                    self.logger.info(f"SSH连接建立成功: {conn_id}")
                    return True
            
            # 连接失败，关闭SSH连接
            ssh_writer.close()
            await ssh_writer.wait_closed()
            return False
            
        except Exception as e:
            self.logger.error(f"建立SSH连接失败: {e}")
            return False
    
    async def _ssh_handshake(self, conn_id: str) -> bool:
        """
        执行SSH握手
        """
        try:
            conn_info = self.connections[conn_id]
            ssh_reader = getattr(conn_info, '_ssh_reader')
            ssh_writer = getattr(conn_info, '_ssh_writer')
            
            # 发送版本字符串
            version_string = self.ssh_handler.build_version_string()
            ssh_writer.write(version_string)
            await ssh_writer.drain()
            
            # 读取服务器版本字符串
            server_version_data = await ssh_reader.readuntil(b'\n')
            server_version = self.ssh_handler.parse_version_string(server_version_data)
            if not server_version:
                self.logger.error("无效的SSH服务器版本")
                return False
            
            self.logger.info(f"SSH服务器版本: {server_version}")
            
            # 发送KEXINIT消息
            kexinit_payload = self.ssh_handler.build_kexinit()
            kexinit_packet = self.ssh_handler.pack_packet(kexinit_payload)
            ssh_writer.write(kexinit_packet)
            await ssh_writer.drain()
            
            # 读取服务器KEXINIT消息
            server_kexinit_data = await self._read_ssh_packet(ssh_reader)
            if not server_kexinit_data:
                self.logger.error("读取服务器KEXINIT失败")
                return False
            
            # 简化密钥交换过程（实际实现需要完整的DH密钥交换）
            # 这里假设密钥交换成功
            
            self.logger.info(f"SSH握手完成: {conn_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"SSH握手失败: {e}")
            return False
    
    async def _ssh_authenticate(self, conn_id: str) -> bool:
        """
        SSH认证
        """
        try:
            conn_info = self.connections[conn_id]
            tunnel_config = conn_info.tunnel_config
            ssh_reader = getattr(conn_info, '_ssh_reader')
            ssh_writer = getattr(conn_info, '_ssh_writer')
            
            # 请求ssh-connection服务
            service_request = self.ssh_handler.build_service_request("ssh-connection")
            service_packet = self.ssh_handler.pack_packet(service_request)
            ssh_writer.write(service_packet)
            await ssh_writer.drain()
            
            # 读取服务接受消息
            service_response = await self._read_ssh_packet(ssh_reader)
            if not service_response:
                return False
            
            service_msg = self.ssh_handler.parse_message(service_response.payload)
            if service_msg.get('type') != SSHMessageType.SSH_MSG_SERVICE_ACCEPT.value:
                self.logger.error("SSH服务请求被拒绝")
                return False
            
            # 用户认证
            if tunnel_config.password:
                # 密码认证
                auth_request = self.ssh_handler.build_userauth_request(
                    tunnel_config.username,
                    "ssh-connection",
                    "password",
                    password=tunnel_config.password
                )
            else:
                # 公钥认证（简化版本）
                auth_request = self.ssh_handler.build_userauth_request(
                    tunnel_config.username,
                    "ssh-connection",
                    "publickey"
                )
            
            auth_packet = self.ssh_handler.pack_packet(auth_request)
            ssh_writer.write(auth_packet)
            await ssh_writer.drain()
            
            # 读取认证响应
            auth_response = await self._read_ssh_packet(ssh_reader)
            if not auth_response:
                return False
            
            auth_msg = self.ssh_handler.parse_message(auth_response.payload)
            if auth_msg.get('type') == SSHMessageType.SSH_MSG_USERAUTH_SUCCESS.value:
                conn_info.authenticated = True
                self.logger.info(f"SSH认证成功: {conn_id}")
                return True
            else:
                self.logger.error(f"SSH认证失败: {auth_msg}")
                return False
            
        except Exception as e:
            self.logger.error(f"SSH认证失败: {e}")
            return False
    
    async def _read_ssh_packet(self, reader: asyncio.StreamReader) -> Optional[SSHPacket]:
        """
        读取SSH数据包
        """
        try:
            # 读取数据包长度
            length_data = await reader.readexactly(4)
            packet_length = struct.unpack('!I', length_data)[0]
            
            # 读取剩余数据
            remaining_data = await reader.readexactly(packet_length + self.ssh_handler.mac_size_in)
            
            # 解包数据
            full_data = length_data + remaining_data
            packet, _ = self.ssh_handler.unpack_packet(full_data)
            
            return packet
            
        except Exception as e:
            self.logger.debug(f"读取SSH数据包失败: {e}")
            return None
    
    async def _handle_tunnel_communication(self, conn_id: str, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """
        处理隧道通信
        """
        conn_info = self.connections[conn_id]
        tunnel_config = conn_info.tunnel_config
        
        try:
            if tunnel_config.tunnel_type == SSHTunnelType.LOCAL_FORWARD:
                await self._handle_local_forward(conn_id, client_reader, client_writer)
            elif tunnel_config.tunnel_type == SSHTunnelType.REMOTE_FORWARD:
                await self._handle_remote_forward(conn_id, client_reader, client_writer)
            elif tunnel_config.tunnel_type == SSHTunnelType.DYNAMIC_FORWARD:
                await self._handle_dynamic_forward(conn_id, client_reader, client_writer)
            else:
                self.logger.error(f"不支持的隧道类型: {tunnel_config.tunnel_type}")
                
        except Exception as e:
            self.logger.error(f"隧道通信错误: {e}")
    
    async def _handle_local_forward(self, conn_id: str, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """
        处理本地端口转发
        """
        conn_info = self.connections[conn_id]
        tunnel_config = conn_info.tunnel_config
        ssh_reader = getattr(conn_info, '_ssh_reader')
        ssh_writer = getattr(conn_info, '_ssh_writer')
        
        try:
            # 打开SSH通道
            channel_id = conn_info.next_channel_id
            conn_info.next_channel_id += 1
            
            channel_open = self.ssh_handler.build_channel_open(
                "direct-tcpip",
                channel_id,
                32768,  # initial window size
                32768,  # max packet size
                host=tunnel_config.remote_host,
                port=tunnel_config.remote_port,
                originator_ip=conn_info.client_addr[0],
                originator_port=conn_info.client_addr[1]
            )
            
            channel_packet = self.ssh_handler.pack_packet(channel_open)
            ssh_writer.write(channel_packet)
            await ssh_writer.drain()
            
            # 读取通道打开确认
            channel_response = await self._read_ssh_packet(ssh_reader)
            if not channel_response:
                return
            
            channel_msg = self.ssh_handler.parse_message(channel_response.payload)
            if channel_msg.get('type') != SSHMessageType.SSH_MSG_CHANNEL_OPEN_CONFIRMATION.value:
                self.logger.error(f"SSH通道打开失败: {channel_msg}")
                return
            
            remote_channel_id = channel_msg.get('sender_channel')
            
            # 创建通道对象
            channel = SSHChannel(
                channel_id=channel_id,
                remote_channel_id=remote_channel_id,
                channel_type="direct-tcpip",
                window_size=channel_msg.get('initial_window_size', 32768),
                max_packet_size=channel_msg.get('maximum_packet_size', 32768),
                connected=True
            )
            
            conn_info.channels[channel_id] = channel
            
            self.logger.info(f"SSH通道建立: {channel_id} -> {remote_channel_id}")
            
            # 开始数据转发
            client_to_ssh = asyncio.create_task(
                self._forward_client_to_ssh(conn_id, channel_id, client_reader)
            )
            ssh_to_client = asyncio.create_task(
                self._forward_ssh_to_client(conn_id, channel_id, client_writer)
            )
            
            # 等待任一任务完成
            done, pending = await asyncio.wait(
                [client_to_ssh, ssh_to_client],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 取消剩余任务
            for task in pending:
                task.cancel()
            
            # 关闭通道
            await self._close_ssh_channel(conn_id, channel_id)
            
        except Exception as e:
            self.logger.error(f"本地端口转发错误: {e}")
    
    async def _handle_remote_forward(self, conn_id: str, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """
        处理远程端口转发
        """
        # 远程端口转发的实现较为复杂，需要在SSH服务器上监听端口
        # 这里提供简化的框架
        self.logger.info(f"远程端口转发暂未完全实现: {conn_id}")
    
    async def _handle_dynamic_forward(self, conn_id: str, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """
        处理动态端口转发（SOCKS代理）
        """
        # 动态端口转发需要实现SOCKS协议
        # 这里提供简化的框架
        self.logger.info(f"动态端口转发暂未完全实现: {conn_id}")
    
    async def _forward_client_to_ssh(self, conn_id: str, channel_id: int, client_reader: asyncio.StreamReader):
        """
        转发客户端数据到SSH
        """
        try:
            conn_info = self.connections[conn_id]
            ssh_writer = getattr(conn_info, '_ssh_writer')
            channel = conn_info.channels[channel_id]
            
            while channel.connected and not channel.eof_sent:
                data = await client_reader.read(self.config.buffer_size)
                if not data:
                    break
                
                # 发送数据到SSH通道
                channel_data = self.ssh_handler.build_channel_data(channel.remote_channel_id, data)
                channel_packet = self.ssh_handler.pack_packet(channel_data)
                ssh_writer.write(channel_packet)
                await ssh_writer.drain()
                
                # 更新统计信息
                conn_info.bytes_sent += len(data)
                conn_info.last_activity = time.time()
                self.stats.bytes_sent += len(data)
            
            # 发送EOF
            channel.eof_sent = True
            
        except Exception as e:
            self.logger.debug(f"客户端到SSH转发结束: {e}")
    
    async def _forward_ssh_to_client(self, conn_id: str, channel_id: int, client_writer: asyncio.StreamWriter):
        """
        转发SSH数据到客户端
        """
        try:
            conn_info = self.connections[conn_id]
            ssh_reader = getattr(conn_info, '_ssh_reader')
            channel = conn_info.channels[channel_id]
            
            while channel.connected and not channel.eof_received:
                # 读取SSH数据包
                packet = await self._read_ssh_packet(ssh_reader)
                if not packet:
                    break
                
                # 解析消息
                msg = self.ssh_handler.parse_message(packet.payload)
                
                if msg.get('type') == SSHMessageType.SSH_MSG_CHANNEL_DATA.value:
                    if msg.get('recipient_channel') == channel_id:
                        # 转发数据到客户端
                        data = msg.get('data', b'')
                        client_writer.write(data)
                        await client_writer.drain()
                        
                        # 更新统计信息
                        conn_info.bytes_received += len(data)
                        conn_info.last_activity = time.time()
                        self.stats.bytes_received += len(data)
                
                elif msg.get('type') == SSHMessageType.SSH_MSG_CHANNEL_EOF.value:
                    if msg.get('recipient_channel') == channel_id:
                        channel.eof_received = True
                        break
                
                elif msg.get('type') == SSHMessageType.SSH_MSG_CHANNEL_CLOSE.value:
                    if msg.get('recipient_channel') == channel_id:
                        channel.connected = False
                        break
            
        except Exception as e:
            self.logger.debug(f"SSH到客户端转发结束: {e}")
    
    async def _close_ssh_channel(self, conn_id: str, channel_id: int):
        """
        关闭SSH通道
        """
        try:
            conn_info = self.connections[conn_id]
            if channel_id in conn_info.channels:
                channel = conn_info.channels[channel_id]
                ssh_writer = getattr(conn_info, '_ssh_writer')
                
                # 发送通道关闭消息
                channel_close = self.ssh_handler.build_channel_close(channel.remote_channel_id)
                channel_packet = self.ssh_handler.pack_packet(channel_close)
                ssh_writer.write(channel_packet)
                await ssh_writer.drain()
                
                # 标记通道为已关闭
                channel.connected = False
                channel.closed = True
                
                self.logger.info(f"SSH通道已关闭: {channel_id}")
                
        except Exception as e:
            self.logger.error(f"关闭SSH通道失败: {e}")
    
    async def _close_ssh_connection(self, conn_id: str):
        """
        关闭SSH连接
        """
        try:
            if conn_id in self.connections:
                conn_info = self.connections[conn_id]
                
                # 关闭所有通道
                for channel_id in list(conn_info.channels.keys()):
                    await self._close_ssh_channel(conn_id, channel_id)
                
                # 关闭SSH连接
                if hasattr(conn_info, '_ssh_writer'):
                    ssh_writer = getattr(conn_info, '_ssh_writer')
                    ssh_writer.close()
                    await ssh_writer.wait_closed()
                
        except Exception as e:
            self.logger.error(f"关闭SSH连接失败: {e}")
    
    async def _cleanup_connection(self, conn_id: str, client_writer: asyncio.StreamWriter):
        """
        清理连接
        """
        try:
            # 关闭SSH连接
            await self._close_ssh_connection(conn_id)
            
            # 关闭客户端连接
            client_writer.close()
            await client_writer.wait_closed()
            
        except Exception:
            pass
        
        if conn_id in self.connections:
            del self.connections[conn_id]
        
        self.remove_connection(conn_id)
        self.logger.info(f"SSH隧道连接 {conn_id} 已清理")

# 导出功能
__all__ = [
    'SSHMessageType',
    'SSHChannelType',
    'SSHTunnelType',
    'SSHPacket',
    'SSHChannel',
    'SSHTunnelConfig',
    'SSHConnectionInfo',
    'SSHProtocolHandler',
    'SSHTunnel'
]