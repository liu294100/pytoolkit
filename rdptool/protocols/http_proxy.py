#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTTP/HTTPS 代理协议模块

实现HTTP/HTTPS通道代理功能
"""

import asyncio
import ssl
import base64
import urllib.parse
import time
import uuid
import re
from typing import Optional, Dict, Any, Tuple, List
import logging
from dataclasses import dataclass
from enum import Enum

from .protocol_manager import BaseProtocol, ProtocolConfig, ProtocolStatus, ProtocolType

class HTTPMethod(Enum):
    """HTTP方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"
    CONNECT = "CONNECT"

@dataclass
class HTTPRequest:
    """HTTP请求"""
    method: str
    path: str
    version: str
    headers: Dict[str, str]
    body: bytes
    raw_data: bytes

@dataclass
class HTTPResponse:
    """HTTP响应"""
    version: str
    status_code: int
    reason: str
    headers: Dict[str, str]
    body: bytes

@dataclass
class HTTPConnectionInfo:
    """HTTP连接信息"""
    conn_id: str
    client_addr: Tuple[str, int]
    target_host: str
    target_port: int
    is_https: bool
    start_time: float
    last_activity: float
    requests_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0

class HTTPParser:
    """
    HTTP协议解析器
    """
    
    @staticmethod
    def parse_request(data: bytes) -> Optional[HTTPRequest]:
        """
        解析HTTP请求
        """
        try:
            # 分离头部和主体
            if b'\r\n\r\n' in data:
                header_data, body = data.split(b'\r\n\r\n', 1)
            else:
                header_data = data
                body = b''
            
            # 解析请求行和头部
            lines = header_data.decode('utf-8', errors='ignore').split('\r\n')
            if not lines:
                return None
            
            # 解析请求行
            request_line = lines[0]
            parts = request_line.split(' ', 2)
            if len(parts) != 3:
                return None
            
            method, path, version = parts
            
            # 解析头部
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            return HTTPRequest(
                method=method,
                path=path,
                version=version,
                headers=headers,
                body=body,
                raw_data=data
            )
            
        except Exception:
            return None
    
    @staticmethod
    def parse_response(data: bytes) -> Optional[HTTPResponse]:
        """
        解析HTTP响应
        """
        try:
            # 分离头部和主体
            if b'\r\n\r\n' in data:
                header_data, body = data.split(b'\r\n\r\n', 1)
            else:
                header_data = data
                body = b''
            
            # 解析状态行和头部
            lines = header_data.decode('utf-8', errors='ignore').split('\r\n')
            if not lines:
                return None
            
            # 解析状态行
            status_line = lines[0]
            parts = status_line.split(' ', 2)
            if len(parts) < 2:
                return None
            
            version = parts[0]
            status_code = int(parts[1])
            reason = parts[2] if len(parts) > 2 else ''
            
            # 解析头部
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            return HTTPResponse(
                version=version,
                status_code=status_code,
                reason=reason,
                headers=headers,
                body=body
            )
            
        except Exception:
            return None
    
    @staticmethod
    def build_response(status_code: int, reason: str = '', headers: Dict[str, str] = None, body: bytes = b'') -> bytes:
        """
        构建HTTP响应
        """
        if headers is None:
            headers = {}
        
        # 默认响应原因
        if not reason:
            reason_map = {
                200: 'OK',
                400: 'Bad Request',
                401: 'Unauthorized',
                403: 'Forbidden',
                404: 'Not Found',
                407: 'Proxy Authentication Required',
                500: 'Internal Server Error',
                502: 'Bad Gateway',
                503: 'Service Unavailable'
            }
            reason = reason_map.get(status_code, 'Unknown')
        
        # 设置默认头部
        if 'content-length' not in headers:
            headers['content-length'] = str(len(body))
        if 'connection' not in headers:
            headers['connection'] = 'close'
        
        # 构建响应
        response_lines = [f'HTTP/1.1 {status_code} {reason}']
        for key, value in headers.items():
            response_lines.append(f'{key}: {value}')
        response_lines.append('')
        response_lines.append('')
        
        response_data = '\r\n'.join(response_lines).encode('utf-8') + body
        return response_data

class HTTPProxy(BaseProtocol):
    """
    HTTP代理服务器
    
    支持HTTP和HTTPS代理
    """
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.server: Optional[asyncio.Server] = None
        self.connections: Dict[str, HTTPConnectionInfo] = {}
        self.auth_required = config.auth_required if hasattr(config, 'auth_required') else False
        self.auth_users = getattr(config, 'auth_users', {})
    
    async def start(self) -> bool:
        """
        启动HTTP代理服务器
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
            self.logger.info(f"HTTP代理服务器启动成功: {self.config.host}:{self.config.port}")
            
            if self.auth_required:
                self.logger.info("已启用代理认证")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"启动HTTP代理服务器失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        停止HTTP代理服务器
        """
        try:
            self.status = ProtocolStatus.STOPPING
            
            # 关闭服务器
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.status = ProtocolStatus.STOPPED
            self.stats.stop_time = time.time()
            self.logger.info("HTTP代理服务器已停止")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"停止HTTP代理服务器失败: {e}")
            return False
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理HTTP连接
        """
        conn_id = str(uuid.uuid4())
        client_addr = writer.get_extra_info('peername')
        
        # 创建连接信息
        conn_info = HTTPConnectionInfo(
            conn_id=conn_id,
            client_addr=client_addr,
            target_host='',
            target_port=0,
            is_https=False,
            start_time=time.time(),
            last_activity=time.time()
        )
        
        self.connections[conn_id] = conn_info
        self.add_connection(conn_id, conn_info)
        
        try:
            self.logger.info(f"新HTTP连接: {client_addr}")
            
            # 处理HTTP请求
            await self._handle_http_requests(conn_id, reader, writer)
            
        except Exception as e:
            self.logger.error(f"处理HTTP连接 {conn_id} 时发生错误: {e}")
            self.stats.errors += 1
        finally:
            # 清理连接
            self._cleanup_connection(conn_id, writer)
    
    async def _handle_http_requests(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理HTTP请求
        """
        while True:
            try:
                # 读取请求数据
                data = await self._read_http_request(reader)
                if not data:
                    break
                
                # 解析HTTP请求
                request = HTTPParser.parse_request(data)
                if not request:
                    await self._send_error_response(writer, 400, "Bad Request")
                    break
                
                # 更新连接信息
                conn_info = self.connections[conn_id]
                conn_info.requests_count += 1
                conn_info.bytes_received += len(data)
                conn_info.last_activity = time.time()
                self.stats.bytes_received += len(data)
                
                # 检查认证
                if self.auth_required and not self._check_auth(request):
                    await self._send_auth_required_response(writer)
                    continue
                
                # 处理不同类型的请求
                if request.method == HTTPMethod.CONNECT.value:
                    # HTTPS隧道
                    await self._handle_connect_request(conn_id, request, reader, writer)
                    break  # CONNECT后不再处理其他请求
                else:
                    # 普通HTTP请求
                    await self._handle_http_request(conn_id, request, writer)
                
            except Exception as e:
                self.logger.error(f"处理HTTP请求错误: {e}")
                break
    
    async def _read_http_request(self, reader: asyncio.StreamReader) -> bytes:
        """
        读取HTTP请求数据
        """
        try:
            # 读取请求头
            header_data = b''
            while b'\r\n\r\n' not in header_data:
                chunk = await reader.read(1024)
                if not chunk:
                    return b''
                header_data += chunk
            
            # 分离头部和可能的主体数据
            header_part, body_part = header_data.split(b'\r\n\r\n', 1)
            
            # 解析Content-Length
            header_text = header_part.decode('utf-8', errors='ignore')
            content_length = 0
            for line in header_text.split('\r\n'):
                if line.lower().startswith('content-length:'):
                    content_length = int(line.split(':', 1)[1].strip())
                    break
            
            # 读取剩余的主体数据
            remaining = content_length - len(body_part)
            if remaining > 0:
                body_part += await reader.read(remaining)
            
            return header_part + b'\r\n\r\n' + body_part
            
        except Exception:
            return b''
    
    def _check_auth(self, request: HTTPRequest) -> bool:
        """
        检查代理认证
        """
        if not self.auth_required:
            return True
        
        auth_header = request.headers.get('proxy-authorization', '')
        if not auth_header.startswith('Basic '):
            return False
        
        try:
            # 解码认证信息
            auth_data = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = auth_data.split(':', 1)
            
            # 验证用户名和密码
            return self.auth_users.get(username) == password
            
        except Exception:
            return False
    
    async def _send_auth_required_response(self, writer: asyncio.StreamWriter):
        """
        发送认证要求响应
        """
        headers = {
            'proxy-authenticate': 'Basic realm="Proxy"',
            'content-type': 'text/html'
        }
        body = b'<html><body><h1>407 Proxy Authentication Required</h1></body></html>'
        
        response = HTTPParser.build_response(407, 'Proxy Authentication Required', headers, body)
        writer.write(response)
        await writer.drain()
    
    async def _send_error_response(self, writer: asyncio.StreamWriter, status_code: int, reason: str):
        """
        发送错误响应
        """
        headers = {'content-type': 'text/html'}
        body = f'<html><body><h1>{status_code} {reason}</h1></body></html>'.encode('utf-8')
        
        response = HTTPParser.build_response(status_code, reason, headers, body)
        writer.write(response)
        await writer.drain()
    
    async def _handle_connect_request(self, conn_id: str, request: HTTPRequest, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理CONNECT请求（HTTPS隧道）
        """
        try:
            # 解析目标地址
            target_host, target_port = self._parse_connect_target(request.path)
            if not target_host:
                await self._send_error_response(writer, 400, "Bad Request")
                return
            
            # 更新连接信息
            conn_info = self.connections[conn_id]
            conn_info.target_host = target_host
            conn_info.target_port = target_port
            conn_info.is_https = True
            
            self.logger.info(f"HTTPS隧道: {conn_info.client_addr} -> {target_host}:{target_port}")
            
            # 连接到目标服务器
            target_reader, target_writer = await asyncio.open_connection(target_host, target_port)
            
            # 发送连接成功响应
            response = b'HTTP/1.1 200 Connection Established\r\n\r\n'
            writer.write(response)
            await writer.drain()
            
            # 更新统计信息
            conn_info.bytes_sent += len(response)
            self.stats.bytes_sent += len(response)
            
            # 开始双向数据转发
            await self._tunnel_data(conn_id, reader, writer, target_reader, target_writer)
            
        except Exception as e:
            self.logger.error(f"处理CONNECT请求错误: {e}")
            await self._send_error_response(writer, 502, "Bad Gateway")
    
    def _parse_connect_target(self, path: str) -> Tuple[str, int]:
        """
        解析CONNECT目标地址
        """
        try:
            if ':' in path:
                host, port_str = path.rsplit(':', 1)
                port = int(port_str)
                return host, port
            else:
                return path, 443  # 默认HTTPS端口
        except Exception:
            return '', 0
    
    async def _handle_http_request(self, conn_id: str, request: HTTPRequest, writer: asyncio.StreamWriter):
        """
        处理普通HTTP请求
        """
        try:
            # 解析目标URL
            target_host, target_port, target_path = self._parse_http_url(request.path)
            if not target_host:
                await self._send_error_response(writer, 400, "Bad Request")
                return
            
            # 更新连接信息
            conn_info = self.connections[conn_id]
            conn_info.target_host = target_host
            conn_info.target_port = target_port
            
            self.logger.debug(f"HTTP请求: {request.method} {target_host}:{target_port}{target_path}")
            
            # 连接到目标服务器
            target_reader, target_writer = await asyncio.open_connection(target_host, target_port)
            
            try:
                # 修改请求路径
                modified_request = self._modify_request(request, target_path)
                
                # 发送请求到目标服务器
                target_writer.write(modified_request)
                await target_writer.drain()
                
                # 读取响应
                response_data = await self._read_http_response(target_reader)
                if response_data:
                    # 发送响应到客户端
                    writer.write(response_data)
                    await writer.drain()
                    
                    # 更新统计信息
                    conn_info.bytes_sent += len(response_data)
                    self.stats.bytes_sent += len(response_data)
                
            finally:
                target_writer.close()
                await target_writer.wait_closed()
            
        except Exception as e:
            self.logger.error(f"处理HTTP请求错误: {e}")
            await self._send_error_response(writer, 502, "Bad Gateway")
    
    def _parse_http_url(self, url: str) -> Tuple[str, int, str]:
        """
        解析HTTP URL
        """
        try:
            parsed = urllib.parse.urlparse(url)
            
            if parsed.hostname:
                host = parsed.hostname
                port = parsed.port or (443 if parsed.scheme == 'https' else 80)
                path = parsed.path or '/'
                if parsed.query:
                    path += '?' + parsed.query
                return host, port, path
            else:
                # 相对路径，使用Host头
                return '', 0, url
                
        except Exception:
            return '', 0, ''
    
    def _modify_request(self, request: HTTPRequest, target_path: str) -> bytes:
        """
        修改HTTP请求
        """
        # 构建新的请求行
        request_line = f"{request.method} {target_path} {request.version}\r\n"
        
        # 移除代理相关头部
        headers = request.headers.copy()
        headers.pop('proxy-authorization', None)
        headers.pop('proxy-connection', None)
        
        # 构建头部
        header_lines = []
        for key, value in headers.items():
            header_lines.append(f"{key}: {value}")
        
        # 组合请求
        request_data = request_line + '\r\n'.join(header_lines) + '\r\n\r\n'
        return request_data.encode('utf-8') + request.body
    
    async def _read_http_response(self, reader: asyncio.StreamReader) -> bytes:
        """
        读取HTTP响应
        """
        try:
            # 读取响应头
            header_data = b''
            while b'\r\n\r\n' not in header_data:
                chunk = await reader.read(1024)
                if not chunk:
                    return header_data
                header_data += chunk
            
            # 分离头部和主体
            header_part, body_part = header_data.split(b'\r\n\r\n', 1)
            
            # 解析Content-Length
            header_text = header_part.decode('utf-8', errors='ignore')
            content_length = None
            transfer_encoding = None
            
            for line in header_text.split('\r\n'):
                line_lower = line.lower()
                if line_lower.startswith('content-length:'):
                    content_length = int(line.split(':', 1)[1].strip())
                elif line_lower.startswith('transfer-encoding:'):
                    transfer_encoding = line.split(':', 1)[1].strip().lower()
            
            # 读取主体数据
            if content_length is not None:
                # 固定长度
                remaining = content_length - len(body_part)
                if remaining > 0:
                    body_part += await reader.read(remaining)
            elif transfer_encoding == 'chunked':
                # 分块传输
                body_part += await self._read_chunked_body(reader)
            else:
                # 读取到连接关闭
                while True:
                    chunk = await reader.read(8192)
                    if not chunk:
                        break
                    body_part += chunk
            
            return header_part + b'\r\n\r\n' + body_part
            
        except Exception:
            return b''
    
    async def _read_chunked_body(self, reader: asyncio.StreamReader) -> bytes:
        """
        读取分块传输的主体
        """
        body = b''
        
        while True:
            # 读取块大小行
            size_line = await reader.readline()
            if not size_line:
                break
            
            # 解析块大小
            try:
                chunk_size = int(size_line.strip().split(b';')[0], 16)
            except ValueError:
                break
            
            if chunk_size == 0:
                # 最后一块
                await reader.readline()  # 读取结束行
                break
            
            # 读取块数据
            chunk_data = await reader.read(chunk_size)
            await reader.readline()  # 读取块结束行
            
            body += chunk_data
        
        return body
    
    async def _tunnel_data(self, conn_id: str, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter,
                          target_reader: asyncio.StreamReader, target_writer: asyncio.StreamWriter):
        """
        隧道数据转发
        """
        try:
            # 创建双向转发任务
            client_to_target = asyncio.create_task(
                self._forward_tunnel_data(conn_id, client_reader, target_writer, "client->target")
            )
            target_to_client = asyncio.create_task(
                self._forward_tunnel_data(conn_id, target_reader, client_writer, "target->client")
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
    
    async def _forward_tunnel_data(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str):
        """
        转发隧道数据
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
            self.logger.debug(f"隧道数据转发 {direction} 结束: {e}")
    
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
        self.logger.info(f"HTTP连接 {conn_id} 已关闭")

class HTTPSProxy(HTTPProxy):
    """
    HTTPS代理服务器
    
    基于SSL/TLS的HTTP代理
    """
    
    def __init__(self, config: ProtocolConfig, ssl_context: Optional[ssl.SSLContext] = None):
        super().__init__(config)
        self.ssl_context = ssl_context or self._create_ssl_context()
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """
        创建SSL上下文
        """
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        # 如果有证书文件，加载它们
        cert_file = getattr(self.config, 'cert_file', None)
        key_file = getattr(self.config, 'key_file', None)
        
        if cert_file and key_file:
            context.load_cert_chain(cert_file, key_file)
        else:
            # 创建自签名证书（仅用于测试）
            self.logger.warning("使用自签名证书，仅适用于测试环境")
        
        return context
    
    async def start(self) -> bool:
        """
        启动HTTPS代理服务器
        """
        try:
            self.status = ProtocolStatus.STARTING
            self.stats.start_time = time.time()
            
            # 创建SSL服务器
            self.server = await asyncio.start_server(
                self.handle_connection,
                self.config.host,
                self.config.port,
                ssl=self.ssl_context,
                limit=self.config.buffer_size
            )
            
            self.status = ProtocolStatus.RUNNING
            self.logger.info(f"HTTPS代理服务器启动成功: {self.config.host}:{self.config.port}")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"启动HTTPS代理服务器失败: {e}")
            return False

# 导出功能
__all__ = [
    'HTTPMethod',
    'HTTPRequest',
    'HTTPResponse',
    'HTTPConnectionInfo',
    'HTTPParser',
    'HTTPProxy',
    'HTTPSProxy'
]