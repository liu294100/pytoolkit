#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Socks 代理协议模块

实现Socks4和Socks5代理功能
"""

import asyncio
import socket
import struct
import time
import uuid
from typing import Optional, Dict, Any, Tuple, List
import logging
from dataclasses import dataclass
from enum import Enum

from .protocol_manager import BaseProtocol, ProtocolConfig, ProtocolStatus, ProtocolType

class SocksVersion(Enum):
    """Socks版本"""
    SOCKS4 = 4
    SOCKS5 = 5

class SocksCommand(Enum):
    """Socks命令"""
    CONNECT = 1
    BIND = 2
    UDP_ASSOCIATE = 3

class SocksAddressType(Enum):
    """Socks地址类型"""
    IPV4 = 1
    DOMAIN = 3
    IPV6 = 4

class SocksAuthMethod(Enum):
    """Socks认证方法"""
    NO_AUTH = 0
    GSSAPI = 1
    USERNAME_PASSWORD = 2
    NO_ACCEPTABLE = 255

class SocksReplyCode(Enum):
    """Socks回复代码"""
    SUCCESS = 0
    GENERAL_FAILURE = 1
    CONNECTION_NOT_ALLOWED = 2
    NETWORK_UNREACHABLE = 3
    HOST_UNREACHABLE = 4
    CONNECTION_REFUSED = 5
    TTL_EXPIRED = 6
    COMMAND_NOT_SUPPORTED = 7
    ADDRESS_TYPE_NOT_SUPPORTED = 8

@dataclass
class SocksRequest:
    """Socks请求"""
    version: int
    command: int
    address_type: int
    address: str
    port: int
    user_id: str = ''  # Socks4使用
    username: str = ''  # Socks5认证使用
    password: str = ''  # Socks5认证使用

@dataclass
class SocksConnectionInfo:
    """Socks连接信息"""
    conn_id: str
    client_addr: Tuple[str, int]
    target_addr: Tuple[str, int]
    socks_version: int
    command: int
    start_time: float
    last_activity: float
    bytes_sent: int = 0
    bytes_received: int = 0
    authenticated: bool = False

class SocksParser:
    """
    Socks协议解析器
    """
    
    @staticmethod
    def parse_socks4_request(data: bytes) -> Optional[SocksRequest]:
        """
        解析Socks4请求
        """
        try:
            if len(data) < 8:
                return None
            
            # 解析固定部分
            version, command, port, ip = struct.unpack('!BBHI', data[:8])
            
            if version != 4:
                return None
            
            # 解析用户ID
            user_id_end = data.find(b'\x00', 8)
            if user_id_end == -1:
                return None
            
            user_id = data[8:user_id_end].decode('utf-8', errors='ignore')
            
            # 检查是否为Socks4a（域名）
            if ip < 256:
                # Socks4a，域名在用户ID后面
                domain_start = user_id_end + 1
                domain_end = data.find(b'\x00', domain_start)
                if domain_end == -1:
                    return None
                address = data[domain_start:domain_end].decode('utf-8', errors='ignore')
                address_type = SocksAddressType.DOMAIN.value
            else:
                # 普通Socks4，IP地址
                address = socket.inet_ntoa(struct.pack('!I', ip))
                address_type = SocksAddressType.IPV4.value
            
            return SocksRequest(
                version=version,
                command=command,
                address_type=address_type,
                address=address,
                port=port,
                user_id=user_id
            )
            
        except Exception:
            return None
    
    @staticmethod
    def parse_socks5_auth_request(data: bytes) -> Optional[List[int]]:
        """
        解析Socks5认证请求
        """
        try:
            if len(data) < 3:
                return None
            
            version, nmethods = struct.unpack('!BB', data[:2])
            if version != 5 or nmethods == 0:
                return None
            
            if len(data) < 2 + nmethods:
                return None
            
            methods = list(struct.unpack(f'!{nmethods}B', data[2:2+nmethods]))
            return methods
            
        except Exception:
            return None
    
    @staticmethod
    def parse_socks5_request(data: bytes) -> Optional[SocksRequest]:
        """
        解析Socks5请求
        """
        try:
            if len(data) < 4:
                return None
            
            version, command, reserved, address_type = struct.unpack('!BBBB', data[:4])
            
            if version != 5:
                return None
            
            offset = 4
            
            # 解析地址
            if address_type == SocksAddressType.IPV4.value:
                if len(data) < offset + 4:
                    return None
                ip_bytes = data[offset:offset+4]
                address = socket.inet_ntoa(ip_bytes)
                offset += 4
            elif address_type == SocksAddressType.IPV6.value:
                if len(data) < offset + 16:
                    return None
                ip_bytes = data[offset:offset+16]
                address = socket.inet_ntop(socket.AF_INET6, ip_bytes)
                offset += 16
            elif address_type == SocksAddressType.DOMAIN.value:
                if len(data) < offset + 1:
                    return None
                domain_len = data[offset]
                offset += 1
                if len(data) < offset + domain_len:
                    return None
                address = data[offset:offset+domain_len].decode('utf-8', errors='ignore')
                offset += domain_len
            else:
                return None
            
            # 解析端口
            if len(data) < offset + 2:
                return None
            port = struct.unpack('!H', data[offset:offset+2])[0]
            
            return SocksRequest(
                version=version,
                command=command,
                address_type=address_type,
                address=address,
                port=port
            )
            
        except Exception:
            return None
    
    @staticmethod
    def parse_socks5_auth_data(data: bytes) -> Optional[Tuple[str, str]]:
        """
        解析Socks5用户名密码认证数据
        """
        try:
            if len(data) < 3:
                return None
            
            version = data[0]
            if version != 1:
                return None
            
            username_len = data[1]
            if len(data) < 2 + username_len + 1:
                return None
            
            username = data[2:2+username_len].decode('utf-8', errors='ignore')
            
            password_len = data[2+username_len]
            if len(data) < 2 + username_len + 1 + password_len:
                return None
            
            password = data[2+username_len+1:2+username_len+1+password_len].decode('utf-8', errors='ignore')
            
            return username, password
            
        except Exception:
            return None
    
    @staticmethod
    def build_socks4_response(reply_code: int, port: int = 0, ip: str = '0.0.0.0') -> bytes:
        """
        构建Socks4响应
        """
        try:
            ip_int = struct.unpack('!I', socket.inet_aton(ip))[0]
            return struct.pack('!BBHI', 0, reply_code, port, ip_int)
        except Exception:
            return struct.pack('!BBHI', 0, 91, 0, 0)  # 91 = request rejected or failed
    
    @staticmethod
    def build_socks5_auth_response(method: int) -> bytes:
        """
        构建Socks5认证响应
        """
        return struct.pack('!BB', 5, method)
    
    @staticmethod
    def build_socks5_auth_result(success: bool) -> bytes:
        """
        构建Socks5认证结果
        """
        return struct.pack('!BB', 1, 0 if success else 1)
    
    @staticmethod
    def build_socks5_response(reply_code: int, address_type: int = 1, address: str = '0.0.0.0', port: int = 0) -> bytes:
        """
        构建Socks5响应
        """
        try:
            response = struct.pack('!BBBB', 5, reply_code, 0, address_type)
            
            if address_type == SocksAddressType.IPV4.value:
                response += socket.inet_aton(address)
            elif address_type == SocksAddressType.IPV6.value:
                response += socket.inet_pton(socket.AF_INET6, address)
            elif address_type == SocksAddressType.DOMAIN.value:
                address_bytes = address.encode('utf-8')
                response += struct.pack('!B', len(address_bytes)) + address_bytes
            
            response += struct.pack('!H', port)
            return response
            
        except Exception:
            return struct.pack('!BBBBIH', 5, 1, 0, 1, 0, 0)  # 1 = general SOCKS server failure

class SocksProxy(BaseProtocol):
    """
    Socks代理服务器
    
    支持Socks4、Socks4a和Socks5协议
    """
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.server: Optional[asyncio.Server] = None
        self.connections: Dict[str, SocksConnectionInfo] = {}
        self.auth_required = getattr(config, 'auth_required', False)
        self.auth_users = getattr(config, 'auth_users', {})
        self.supported_versions = getattr(config, 'supported_versions', [4, 5])
    
    async def start(self) -> bool:
        """
        启动Socks代理服务器
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
            self.logger.info(f"Socks代理服务器启动成功: {self.config.host}:{self.config.port}")
            self.logger.info(f"支持的版本: {self.supported_versions}")
            
            if self.auth_required:
                self.logger.info("已启用代理认证")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"启动Socks代理服务器失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        停止Socks代理服务器
        """
        try:
            self.status = ProtocolStatus.STOPPING
            
            # 关闭服务器
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.status = ProtocolStatus.STOPPED
            self.stats.stop_time = time.time()
            self.logger.info("Socks代理服务器已停止")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"停止Socks代理服务器失败: {e}")
            return False
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理Socks连接
        """
        conn_id = str(uuid.uuid4())
        client_addr = writer.get_extra_info('peername')
        
        # 创建连接信息
        conn_info = SocksConnectionInfo(
            conn_id=conn_id,
            client_addr=client_addr,
            target_addr=('', 0),
            socks_version=0,
            command=0,
            start_time=time.time(),
            last_activity=time.time()
        )
        
        self.connections[conn_id] = conn_info
        self.add_connection(conn_id, conn_info)
        
        try:
            self.logger.info(f"新Socks连接: {client_addr}")
            
            # 检测Socks版本
            first_byte = await reader.read(1)
            if not first_byte:
                return
            
            version = first_byte[0]
            conn_info.socks_version = version
            
            if version == 4 and 4 in self.supported_versions:
                await self._handle_socks4(conn_id, reader, writer, first_byte)
            elif version == 5 and 5 in self.supported_versions:
                await self._handle_socks5(conn_id, reader, writer, first_byte)
            else:
                self.logger.warning(f"不支持的Socks版本: {version}")
                
        except Exception as e:
            self.logger.error(f"处理Socks连接 {conn_id} 时发生错误: {e}")
            self.stats.errors += 1
        finally:
            # 清理连接
            self._cleanup_connection(conn_id, writer)
    
    async def _handle_socks4(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, first_byte: bytes):
        """
        处理Socks4连接
        """
        try:
            # 读取剩余的请求数据
            remaining_data = await reader.read(1024)
            if not remaining_data:
                return
            
            request_data = first_byte + remaining_data
            
            # 解析请求
            request = SocksParser.parse_socks4_request(request_data)
            if not request:
                # 发送错误响应
                response = SocksParser.build_socks4_response(91)  # request rejected or failed
                writer.write(response)
                await writer.drain()
                return
            
            # 更新连接信息
            conn_info = self.connections[conn_id]
            conn_info.command = request.command
            conn_info.target_addr = (request.address, request.port)
            
            self.logger.info(f"Socks4请求: {request.command} -> {request.address}:{request.port}")
            
            # 只支持CONNECT命令
            if request.command != SocksCommand.CONNECT.value:
                response = SocksParser.build_socks4_response(91)  # request rejected or failed
                writer.write(response)
                await writer.drain()
                return
            
            # 连接到目标服务器
            try:
                target_reader, target_writer = await asyncio.open_connection(request.address, request.port)
                
                # 发送成功响应
                response = SocksParser.build_socks4_response(90)  # request granted
                writer.write(response)
                await writer.drain()
                
                # 开始数据转发
                await self._tunnel_data(conn_id, reader, writer, target_reader, target_writer)
                
            except Exception as e:
                self.logger.error(f"连接目标服务器失败: {e}")
                response = SocksParser.build_socks4_response(91)  # request rejected or failed
                writer.write(response)
                await writer.drain()
                
        except Exception as e:
            self.logger.error(f"处理Socks4请求错误: {e}")
    
    async def _handle_socks5(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, first_byte: bytes):
        """
        处理Socks5连接
        """
        try:
            # 读取认证方法请求
            nmethods_data = await reader.read(1)
            if not nmethods_data:
                return
            
            nmethods = nmethods_data[0]
            if nmethods == 0:
                return
            
            methods_data = await reader.read(nmethods)
            if len(methods_data) != nmethods:
                return
            
            auth_data = first_byte + nmethods_data + methods_data
            methods = SocksParser.parse_socks5_auth_request(auth_data)
            if not methods:
                return
            
            # 选择认证方法
            selected_method = self._select_auth_method(methods)
            
            # 发送认证方法响应
            auth_response = SocksParser.build_socks5_auth_response(selected_method)
            writer.write(auth_response)
            await writer.drain()
            
            if selected_method == SocksAuthMethod.NO_ACCEPTABLE.value:
                return
            
            # 处理认证
            if selected_method == SocksAuthMethod.USERNAME_PASSWORD.value:
                if not await self._handle_socks5_auth(conn_id, reader, writer):
                    return
            
            # 读取连接请求
            request_data = await reader.read(1024)
            if not request_data:
                return
            
            request = SocksParser.parse_socks5_request(request_data)
            if not request:
                response = SocksParser.build_socks5_response(SocksReplyCode.GENERAL_FAILURE.value)
                writer.write(response)
                await writer.drain()
                return
            
            # 更新连接信息
            conn_info = self.connections[conn_id]
            conn_info.command = request.command
            conn_info.target_addr = (request.address, request.port)
            
            self.logger.info(f"Socks5请求: {request.command} -> {request.address}:{request.port}")
            
            # 处理不同的命令
            if request.command == SocksCommand.CONNECT.value:
                await self._handle_socks5_connect(conn_id, request, reader, writer)
            elif request.command == SocksCommand.UDP_ASSOCIATE.value:
                await self._handle_socks5_udp_associate(conn_id, request, reader, writer)
            else:
                response = SocksParser.build_socks5_response(SocksReplyCode.COMMAND_NOT_SUPPORTED.value)
                writer.write(response)
                await writer.drain()
                
        except Exception as e:
            self.logger.error(f"处理Socks5请求错误: {e}")
    
    def _select_auth_method(self, methods: List[int]) -> int:
        """
        选择认证方法
        """
        if self.auth_required:
            if SocksAuthMethod.USERNAME_PASSWORD.value in methods:
                return SocksAuthMethod.USERNAME_PASSWORD.value
            else:
                return SocksAuthMethod.NO_ACCEPTABLE.value
        else:
            if SocksAuthMethod.NO_AUTH.value in methods:
                return SocksAuthMethod.NO_AUTH.value
            else:
                return SocksAuthMethod.NO_ACCEPTABLE.value
    
    async def _handle_socks5_auth(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        """
        处理Socks5用户名密码认证
        """
        try:
            # 读取认证数据
            auth_data = await reader.read(1024)
            if not auth_data:
                return False
            
            auth_info = SocksParser.parse_socks5_auth_data(auth_data)
            if not auth_info:
                response = SocksParser.build_socks5_auth_result(False)
                writer.write(response)
                await writer.drain()
                return False
            
            username, password = auth_info
            
            # 验证用户名和密码
            if self.auth_users.get(username) == password:
                response = SocksParser.build_socks5_auth_result(True)
                writer.write(response)
                await writer.drain()
                
                # 更新连接信息
                self.connections[conn_id].authenticated = True
                self.logger.info(f"用户 {username} 认证成功")
                return True
            else:
                response = SocksParser.build_socks5_auth_result(False)
                writer.write(response)
                await writer.drain()
                self.logger.warning(f"用户 {username} 认证失败")
                return False
                
        except Exception as e:
            self.logger.error(f"处理Socks5认证错误: {e}")
            return False
    
    async def _handle_socks5_connect(self, conn_id: str, request: SocksRequest, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理Socks5 CONNECT命令
        """
        try:
            # 连接到目标服务器
            target_reader, target_writer = await asyncio.open_connection(request.address, request.port)
            
            # 获取本地绑定地址
            local_addr = target_writer.get_extra_info('sockname')
            bind_addr = local_addr[0] if local_addr else '0.0.0.0'
            bind_port = local_addr[1] if local_addr else 0
            
            # 发送成功响应
            response = SocksParser.build_socks5_response(
                SocksReplyCode.SUCCESS.value,
                SocksAddressType.IPV4.value,
                bind_addr,
                bind_port
            )
            writer.write(response)
            await writer.drain()
            
            # 开始数据转发
            await self._tunnel_data(conn_id, reader, writer, target_reader, target_writer)
            
        except Exception as e:
            self.logger.error(f"连接目标服务器失败: {e}")
            
            # 确定错误类型
            if "Name or service not known" in str(e) or "nodename nor servname provided" in str(e):
                reply_code = SocksReplyCode.HOST_UNREACHABLE.value
            elif "Connection refused" in str(e):
                reply_code = SocksReplyCode.CONNECTION_REFUSED.value
            elif "Network is unreachable" in str(e):
                reply_code = SocksReplyCode.NETWORK_UNREACHABLE.value
            else:
                reply_code = SocksReplyCode.GENERAL_FAILURE.value
            
            response = SocksParser.build_socks5_response(reply_code)
            writer.write(response)
            await writer.drain()
    
    async def _handle_socks5_udp_associate(self, conn_id: str, request: SocksRequest, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理Socks5 UDP ASSOCIATE命令
        """
        try:
            # 创建UDP服务器
            loop = asyncio.get_event_loop()
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: SocksUDPProtocol(self, conn_id),
                local_addr=(self.config.host, 0)  # 使用随机端口
            )
            
            # 获取UDP服务器地址
            udp_addr = transport.get_extra_info('sockname')
            udp_host = udp_addr[0]
            udp_port = udp_addr[1]
            
            # 发送成功响应
            response = SocksParser.build_socks5_response(
                SocksReplyCode.SUCCESS.value,
                SocksAddressType.IPV4.value,
                udp_host,
                udp_port
            )
            writer.write(response)
            await writer.drain()
            
            self.logger.info(f"UDP关联建立: {udp_host}:{udp_port}")
            
            # 保持TCP连接活跃
            try:
                while True:
                    data = await reader.read(1024)
                    if not data:
                        break
            finally:
                transport.close()
                
        except Exception as e:
            self.logger.error(f"处理UDP关联失败: {e}")
            response = SocksParser.build_socks5_response(SocksReplyCode.GENERAL_FAILURE.value)
            writer.write(response)
            await writer.drain()
    
    async def _tunnel_data(self, conn_id: str, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter,
                          target_reader: asyncio.StreamReader, target_writer: asyncio.StreamWriter):
        """
        隧道数据转发
        """
        try:
            # 创建双向转发任务
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
            self.logger.error(f"隧道数据转发错误: {e}")
        finally:
            # 关闭目标连接
            target_writer.close()
            await target_writer.wait_closed()
    
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
                conn_info = self.connections[conn_id]
                if direction.startswith("client"):
                    conn_info.bytes_sent += len(data)
                    self.stats.bytes_sent += len(data)
                else:
                    conn_info.bytes_received += len(data)
                    self.stats.bytes_received += len(data)
                
                conn_info.last_activity = time.time()
                
        except Exception as e:
            self.logger.debug(f"数据转发 {direction} 结束: {e}")
    
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
        
        self.remove_connection(conn_id)
        self.logger.info(f"Socks连接 {conn_id} 已关闭")

class SocksUDPProtocol(asyncio.DatagramProtocol):
    """
    Socks UDP协议处理器
    """
    
    def __init__(self, proxy: SocksProxy, conn_id: str):
        self.proxy = proxy
        self.conn_id = conn_id
        self.logger = proxy.logger
    
    def connection_made(self, transport):
        self.transport = transport
        self.logger.info(f"UDP协议连接建立: {self.conn_id}")
    
    def datagram_received(self, data, addr):
        """
        处理UDP数据包
        """
        try:
            # 解析Socks5 UDP请求
            if len(data) < 10:  # 最小UDP请求长度
                return
            
            # Socks5 UDP请求格式: RSV(2) + FRAG(1) + ATYP(1) + DST.ADDR + DST.PORT + DATA
            rsv, frag, atyp = struct.unpack('!HBB', data[:4])
            
            if rsv != 0 or frag != 0:  # 不支持分片
                return
            
            offset = 4
            
            # 解析目标地址
            if atyp == SocksAddressType.IPV4.value:
                if len(data) < offset + 6:
                    return
                dst_addr = socket.inet_ntoa(data[offset:offset+4])
                dst_port = struct.unpack('!H', data[offset+4:offset+6])[0]
                offset += 6
            elif atyp == SocksAddressType.DOMAIN.value:
                if len(data) < offset + 1:
                    return
                addr_len = data[offset]
                offset += 1
                if len(data) < offset + addr_len + 2:
                    return
                dst_addr = data[offset:offset+addr_len].decode('utf-8', errors='ignore')
                dst_port = struct.unpack('!H', data[offset+addr_len:offset+addr_len+2])[0]
                offset += addr_len + 2
            else:
                return  # 不支持的地址类型
            
            # 提取实际数据
            udp_data = data[offset:]
            
            # 转发到目标服务器
            asyncio.create_task(self._forward_udp_data(dst_addr, dst_port, udp_data, addr))
            
        except Exception as e:
            self.logger.error(f"处理UDP数据包错误: {e}")
    
    async def _forward_udp_data(self, dst_addr: str, dst_port: int, data: bytes, client_addr: Tuple[str, int]):
        """
        转发UDP数据到目标服务器
        """
        try:
            # 创建到目标的UDP连接
            loop = asyncio.get_event_loop()
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: SocksUDPTargetProtocol(self, client_addr, dst_addr, dst_port),
                remote_addr=(dst_addr, dst_port)
            )
            
            # 发送数据
            transport.sendto(data)
            
        except Exception as e:
            self.logger.error(f"转发UDP数据失败: {e}")
    
    def send_udp_response(self, data: bytes, dst_addr: str, dst_port: int, client_addr: Tuple[str, int]):
        """
        发送UDP响应到客户端
        """
        try:
            # 构建Socks5 UDP响应
            response = struct.pack('!HBB', 0, 0, SocksAddressType.IPV4.value)
            response += socket.inet_aton(dst_addr)
            response += struct.pack('!H', dst_port)
            response += data
            
            # 发送到客户端
            self.transport.sendto(response, client_addr)
            
        except Exception as e:
            self.logger.error(f"发送UDP响应失败: {e}")
    
    def error_received(self, exc):
        self.logger.error(f"UDP协议错误: {exc}")

class SocksUDPTargetProtocol(asyncio.DatagramProtocol):
    """
    Socks UDP目标协议处理器
    """
    
    def __init__(self, udp_protocol: SocksUDPProtocol, client_addr: Tuple[str, int], dst_addr: str, dst_port: int):
        self.udp_protocol = udp_protocol
        self.client_addr = client_addr
        self.dst_addr = dst_addr
        self.dst_port = dst_port
    
    def connection_made(self, transport):
        self.transport = transport
    
    def datagram_received(self, data, addr):
        """
        接收目标服务器的UDP响应
        """
        # 转发响应到客户端
        self.udp_protocol.send_udp_response(data, self.dst_addr, self.dst_port, self.client_addr)
    
    def error_received(self, exc):
        self.udp_protocol.logger.error(f"UDP目标协议错误: {exc}")

# 导出功能
__all__ = [
    'SocksVersion',
    'SocksCommand',
    'SocksAddressType',
    'SocksAuthMethod',
    'SocksReplyCode',
    'SocksRequest',
    'SocksConnectionInfo',
    'SocksParser',
    'SocksProxy',
    'SocksUDPProtocol',
    'SocksUDPTargetProtocol'
]