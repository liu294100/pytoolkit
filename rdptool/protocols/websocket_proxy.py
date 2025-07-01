#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket 代理协议模块

实现WebSocket通道代理功能
"""

import asyncio
import base64
import hashlib
import struct
import time
import uuid
import json
from typing import Optional, Dict, Any, Tuple, List, Union
import logging
from dataclasses import dataclass
from enum import Enum

from .protocol_manager import BaseProtocol, ProtocolConfig, ProtocolStatus, ProtocolType

class WebSocketOpcode(Enum):
    """WebSocket操作码"""
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xa

class WebSocketState(Enum):
    """WebSocket连接状态"""
    CONNECTING = "connecting"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"

@dataclass
class WebSocketFrame:
    """WebSocket帧"""
    fin: bool
    rsv1: bool
    rsv2: bool
    rsv3: bool
    opcode: int
    masked: bool
    payload_length: int
    mask_key: Optional[bytes]
    payload: bytes

@dataclass
class WebSocketHandshake:
    """WebSocket握手信息"""
    method: str
    path: str
    version: str
    headers: Dict[str, str]
    key: str
    protocol: Optional[str] = None
    extensions: List[str] = None

@dataclass
class WebSocketConnectionInfo:
    """WebSocket连接信息"""
    conn_id: str
    client_addr: Tuple[str, int]
    target_addr: Tuple[str, int]
    state: WebSocketState
    start_time: float
    last_activity: float
    frames_sent: int = 0
    frames_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    protocol: Optional[str] = None
    extensions: List[str] = None

class WebSocketParser:
    """
    WebSocket协议解析器
    """
    
    WEBSOCKET_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    
    @staticmethod
    def parse_handshake(data: bytes) -> Optional[WebSocketHandshake]:
        """
        解析WebSocket握手请求
        """
        try:
            # 解析HTTP请求
            lines = data.decode('utf-8', errors='ignore').split('\r\n')
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
            
            # 检查WebSocket必需的头部
            if (headers.get('upgrade', '').lower() != 'websocket' or
                headers.get('connection', '').lower() != 'upgrade' or
                'sec-websocket-key' not in headers):
                return None
            
            # 提取WebSocket信息
            key = headers['sec-websocket-key']
            protocol = headers.get('sec-websocket-protocol')
            extensions_str = headers.get('sec-websocket-extensions', '')
            extensions = [ext.strip() for ext in extensions_str.split(',') if ext.strip()]
            
            return WebSocketHandshake(
                method=method,
                path=path,
                version=version,
                headers=headers,
                key=key,
                protocol=protocol,
                extensions=extensions
            )
            
        except Exception:
            return None
    
    @staticmethod
    def build_handshake_response(handshake: WebSocketHandshake, accept_protocol: Optional[str] = None) -> bytes:
        """
        构建WebSocket握手响应
        """
        # 计算Sec-WebSocket-Accept
        accept_key = base64.b64encode(
            hashlib.sha1((handshake.key + WebSocketParser.WEBSOCKET_MAGIC).encode()).digest()
        ).decode()
        
        # 构建响应头
        response_lines = [
            'HTTP/1.1 101 Switching Protocols',
            'Upgrade: websocket',
            'Connection: Upgrade',
            f'Sec-WebSocket-Accept: {accept_key}'
        ]
        
        # 添加协议
        if accept_protocol:
            response_lines.append(f'Sec-WebSocket-Protocol: {accept_protocol}')
        
        response_lines.extend(['', ''])
        return '\r\n'.join(response_lines).encode('utf-8')
    
    @staticmethod
    def parse_frame(data: bytes) -> Tuple[Optional[WebSocketFrame], int]:
        """
        解析WebSocket帧
        
        返回: (帧对象, 消耗的字节数)
        """
        try:
            if len(data) < 2:
                return None, 0
            
            # 解析第一个字节
            first_byte = data[0]
            fin = bool(first_byte & 0x80)
            rsv1 = bool(first_byte & 0x40)
            rsv2 = bool(first_byte & 0x20)
            rsv3 = bool(first_byte & 0x10)
            opcode = first_byte & 0x0f
            
            # 解析第二个字节
            second_byte = data[1]
            masked = bool(second_byte & 0x80)
            payload_length = second_byte & 0x7f
            
            offset = 2
            
            # 解析扩展载荷长度
            if payload_length == 126:
                if len(data) < offset + 2:
                    return None, 0
                payload_length = struct.unpack('!H', data[offset:offset+2])[0]
                offset += 2
            elif payload_length == 127:
                if len(data) < offset + 8:
                    return None, 0
                payload_length = struct.unpack('!Q', data[offset:offset+8])[0]
                offset += 8
            
            # 解析掩码
            mask_key = None
            if masked:
                if len(data) < offset + 4:
                    return None, 0
                mask_key = data[offset:offset+4]
                offset += 4
            
            # 检查是否有足够的载荷数据
            if len(data) < offset + payload_length:
                return None, 0
            
            # 提取载荷
            payload = data[offset:offset+payload_length]
            
            # 解除掩码
            if masked and mask_key:
                payload = bytes(payload[i] ^ mask_key[i % 4] for i in range(len(payload)))
            
            frame = WebSocketFrame(
                fin=fin,
                rsv1=rsv1,
                rsv2=rsv2,
                rsv3=rsv3,
                opcode=opcode,
                masked=masked,
                payload_length=payload_length,
                mask_key=mask_key,
                payload=payload
            )
            
            return frame, offset + payload_length
            
        except Exception:
            return None, 0
    
    @staticmethod
    def build_frame(opcode: int, payload: bytes, masked: bool = False, fin: bool = True) -> bytes:
        """
        构建WebSocket帧
        """
        # 第一个字节
        first_byte = 0x80 if fin else 0x00  # FIN位
        first_byte |= opcode & 0x0f
        
        # 第二个字节和载荷长度
        payload_length = len(payload)
        if payload_length < 126:
            length_bytes = struct.pack('!B', payload_length)
        elif payload_length < 65536:
            length_bytes = struct.pack('!BH', 126, payload_length)
        else:
            length_bytes = struct.pack('!BQ', 127, payload_length)
        
        # 设置掩码位
        if masked:
            length_bytes = bytes([length_bytes[0] | 0x80]) + length_bytes[1:]
        
        # 构建帧
        frame = struct.pack('!B', first_byte) + length_bytes
        
        # 添加掩码
        if masked:
            import os
            mask_key = os.urandom(4)
            frame += mask_key
            # 应用掩码
            masked_payload = bytes(payload[i] ^ mask_key[i % 4] for i in range(len(payload)))
            frame += masked_payload
        else:
            frame += payload
        
        return frame
    
    @staticmethod
    def build_close_frame(code: int = 1000, reason: str = '') -> bytes:
        """
        构建关闭帧
        """
        payload = struct.pack('!H', code) + reason.encode('utf-8')
        return WebSocketParser.build_frame(WebSocketOpcode.CLOSE.value, payload)
    
    @staticmethod
    def build_ping_frame(data: bytes = b'') -> bytes:
        """
        构建Ping帧
        """
        return WebSocketParser.build_frame(WebSocketOpcode.PING.value, data)
    
    @staticmethod
    def build_pong_frame(data: bytes = b'') -> bytes:
        """
        构建Pong帧
        """
        return WebSocketParser.build_frame(WebSocketOpcode.PONG.value, data)

class WebSocketProxy(BaseProtocol):
    """
    WebSocket代理服务器
    
    支持WebSocket协议的代理和隧道功能
    """
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.server: Optional[asyncio.Server] = None
        self.connections: Dict[str, WebSocketConnectionInfo] = {}
        self.supported_protocols = getattr(config, 'supported_protocols', [])
        self.ping_interval = getattr(config, 'ping_interval', 30)  # 心跳间隔
        self.ping_timeout = getattr(config, 'ping_timeout', 10)   # 心跳超时
    
    async def start(self) -> bool:
        """
        启动WebSocket代理服务器
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
            self.logger.info(f"WebSocket代理服务器启动成功: {self.config.host}:{self.config.port}")
            
            if self.supported_protocols:
                self.logger.info(f"支持的子协议: {self.supported_protocols}")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"启动WebSocket代理服务器失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        停止WebSocket代理服务器
        """
        try:
            self.status = ProtocolStatus.STOPPING
            
            # 关闭所有连接
            for conn_info in list(self.connections.values()):
                conn_info.state = WebSocketState.CLOSING
            
            # 关闭服务器
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.status = ProtocolStatus.STOPPED
            self.stats.stop_time = time.time()
            self.logger.info("WebSocket代理服务器已停止")
            
            return True
            
        except Exception as e:
            self.status = ProtocolStatus.ERROR
            self.stats.last_error = str(e)
            self.logger.error(f"停止WebSocket代理服务器失败: {e}")
            return False
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理WebSocket连接
        """
        conn_id = str(uuid.uuid4())
        client_addr = writer.get_extra_info('peername')
        
        # 创建连接信息
        conn_info = WebSocketConnectionInfo(
            conn_id=conn_id,
            client_addr=client_addr,
            target_addr=('', 0),
            state=WebSocketState.CONNECTING,
            start_time=time.time(),
            last_activity=time.time()
        )
        
        self.connections[conn_id] = conn_info
        self.add_connection(conn_id, conn_info)
        
        try:
            self.logger.info(f"新WebSocket连接: {client_addr}")
            
            # 处理WebSocket握手
            if await self._handle_handshake(conn_id, reader, writer):
                # 握手成功，开始处理WebSocket通信
                await self._handle_websocket_communication(conn_id, reader, writer)
            
        except Exception as e:
            self.logger.error(f"处理WebSocket连接 {conn_id} 时发生错误: {e}")
            self.stats.errors += 1
        finally:
            # 清理连接
            self._cleanup_connection(conn_id, writer)
    
    async def _handle_handshake(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        """
        处理WebSocket握手
        """
        try:
            # 读取握手请求
            handshake_data = await self._read_http_request(reader)
            if not handshake_data:
                return False
            
            # 解析握手请求
            handshake = WebSocketParser.parse_handshake(handshake_data)
            if not handshake:
                await self._send_http_error(writer, 400, "Bad Request")
                return False
            
            # 检查WebSocket版本
            ws_version = handshake.headers.get('sec-websocket-version')
            if ws_version != '13':
                await self._send_http_error(writer, 426, "Upgrade Required", {
                    'Sec-WebSocket-Version': '13'
                })
                return False
            
            # 选择子协议
            selected_protocol = self._select_protocol(handshake.protocol)
            
            # 更新连接信息
            conn_info = self.connections[conn_id]
            conn_info.protocol = selected_protocol
            conn_info.extensions = handshake.extensions
            
            # 如果配置了目标地址，建立到目标的WebSocket连接
            if self.config.target_host and self.config.target_port:
                target_success = await self._connect_to_target(conn_id, handshake)
                if not target_success:
                    await self._send_http_error(writer, 502, "Bad Gateway")
                    return False
            
            # 发送握手响应
            response = WebSocketParser.build_handshake_response(handshake, selected_protocol)
            writer.write(response)
            await writer.drain()
            
            # 更新连接状态
            conn_info.state = WebSocketState.OPEN
            conn_info.last_activity = time.time()
            
            self.logger.info(f"WebSocket握手成功: {conn_id}")
            if selected_protocol:
                self.logger.info(f"选择的子协议: {selected_protocol}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"WebSocket握手失败: {e}")
            return False
    
    async def _read_http_request(self, reader: asyncio.StreamReader) -> bytes:
        """
        读取HTTP请求
        """
        try:
            data = b''
            while b'\r\n\r\n' not in data:
                chunk = await reader.read(1024)
                if not chunk:
                    break
                data += chunk
            return data
        except Exception:
            return b''
    
    async def _send_http_error(self, writer: asyncio.StreamWriter, status_code: int, reason: str, headers: Dict[str, str] = None):
        """
        发送HTTP错误响应
        """
        if headers is None:
            headers = {}
        
        response_lines = [f'HTTP/1.1 {status_code} {reason}']
        headers['Content-Type'] = 'text/html'
        headers['Content-Length'] = str(len(reason))
        
        for key, value in headers.items():
            response_lines.append(f'{key}: {value}')
        
        response_lines.extend(['', reason])
        response = '\r\n'.join(response_lines).encode('utf-8')
        
        writer.write(response)
        await writer.drain()
    
    def _select_protocol(self, requested_protocol: Optional[str]) -> Optional[str]:
        """
        选择WebSocket子协议
        """
        if not requested_protocol or not self.supported_protocols:
            return None
        
        # 检查请求的协议是否在支持列表中
        requested_protocols = [p.strip() for p in requested_protocol.split(',')]
        for protocol in requested_protocols:
            if protocol in self.supported_protocols:
                return protocol
        
        return None
    
    async def _connect_to_target(self, conn_id: str, handshake: WebSocketHandshake) -> bool:
        """
        连接到目标WebSocket服务器
        """
        try:
            # 建立TCP连接
            target_reader, target_writer = await asyncio.open_connection(
                self.config.target_host,
                self.config.target_port
            )
            
            # 发送WebSocket握手请求到目标服务器
            target_handshake = self._build_target_handshake(handshake)
            target_writer.write(target_handshake)
            await target_writer.drain()
            
            # 读取目标服务器的握手响应
            target_response = await self._read_http_request(target_reader)
            if not target_response or b'101 Switching Protocols' not in target_response:
                target_writer.close()
                return False
            
            # 保存目标连接
            conn_info = self.connections[conn_id]
            conn_info.target_addr = (self.config.target_host, self.config.target_port)
            
            # 存储目标连接（这里简化处理，实际应该存储在连接信息中）
            setattr(conn_info, '_target_reader', target_reader)
            setattr(conn_info, '_target_writer', target_writer)
            
            return True
            
        except Exception as e:
            self.logger.error(f"连接到目标WebSocket服务器失败: {e}")
            return False
    
    def _build_target_handshake(self, handshake: WebSocketHandshake) -> bytes:
        """
        构建发送到目标服务器的握手请求
        """
        # 生成新的WebSocket key
        import os
        new_key = base64.b64encode(os.urandom(16)).decode()
        
        # 构建请求行
        request_lines = [f'{handshake.method} {handshake.path} {handshake.version}']
        
        # 添加必要的头部
        headers = handshake.headers.copy()
        headers['sec-websocket-key'] = new_key
        headers['host'] = f'{self.config.target_host}:{self.config.target_port}'
        
        for key, value in headers.items():
            request_lines.append(f'{key}: {value}')
        
        request_lines.extend(['', ''])
        return '\r\n'.join(request_lines).encode('utf-8')
    
    async def _handle_websocket_communication(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理WebSocket通信
        """
        conn_info = self.connections[conn_id]
        
        # 如果有目标连接，启动代理模式
        if hasattr(conn_info, '_target_reader'):
            await self._handle_proxy_mode(conn_id, reader, writer)
        else:
            # 直接模式，处理WebSocket消息
            await self._handle_direct_mode(conn_id, reader, writer)
    
    async def _handle_proxy_mode(self, conn_id: str, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """
        处理代理模式的WebSocket通信
        """
        conn_info = self.connections[conn_id]
        target_reader = getattr(conn_info, '_target_reader')
        target_writer = getattr(conn_info, '_target_writer')
        
        try:
            # 创建双向转发任务
            client_to_target = asyncio.create_task(
                self._forward_websocket_data(conn_id, client_reader, target_writer, "client->target")
            )
            target_to_client = asyncio.create_task(
                self._forward_websocket_data(conn_id, target_reader, client_writer, "target->client")
            )
            
            # 创建心跳任务
            ping_task = asyncio.create_task(self._ping_loop(conn_id, client_writer))
            
            # 等待任一任务完成
            done, pending = await asyncio.wait(
                [client_to_target, target_to_client, ping_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 取消剩余任务
            for task in pending:
                task.cancel()
            
        except Exception as e:
            self.logger.error(f"WebSocket代理通信错误: {e}")
        finally:
            # 关闭目标连接
            target_writer.close()
            await target_writer.wait_closed()
    
    async def _handle_direct_mode(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理直接模式的WebSocket通信
        """
        try:
            # 创建消息处理任务
            message_task = asyncio.create_task(
                self._handle_websocket_messages(conn_id, reader, writer)
            )
            
            # 创建心跳任务
            ping_task = asyncio.create_task(self._ping_loop(conn_id, writer))
            
            # 等待任一任务完成
            done, pending = await asyncio.wait(
                [message_task, ping_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 取消剩余任务
            for task in pending:
                task.cancel()
            
        except Exception as e:
            self.logger.error(f"WebSocket直接通信错误: {e}")
    
    async def _forward_websocket_data(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str):
        """
        转发WebSocket数据
        """
        buffer = b''
        
        try:
            while True:
                # 读取数据
                data = await reader.read(self.config.buffer_size)
                if not data:
                    break
                
                buffer += data
                
                # 解析并转发完整的帧
                while buffer:
                    frame, consumed = WebSocketParser.parse_frame(buffer)
                    if not frame:
                        break  # 需要更多数据
                    
                    buffer = buffer[consumed:]
                    
                    # 转发帧
                    frame_data = WebSocketParser.build_frame(
                        frame.opcode,
                        frame.payload,
                        masked=False,  # 服务器到客户端不需要掩码
                        fin=frame.fin
                    )
                    
                    writer.write(frame_data)
                    await writer.drain()
                    
                    # 更新统计信息
                    conn_info = self.connections[conn_id]
                    if direction.startswith("client"):
                        conn_info.frames_sent += 1
                        conn_info.bytes_sent += len(frame_data)
                        self.stats.bytes_sent += len(frame_data)
                    else:
                        conn_info.frames_received += 1
                        conn_info.bytes_received += len(frame_data)
                        self.stats.bytes_received += len(frame_data)
                    
                    conn_info.last_activity = time.time()
                    
                    # 处理控制帧
                    if frame.opcode == WebSocketOpcode.CLOSE.value:
                        return
                    elif frame.opcode == WebSocketOpcode.PING.value:
                        # 发送Pong响应
                        pong_frame = WebSocketParser.build_pong_frame(frame.payload)
                        writer.write(pong_frame)
                        await writer.drain()
                
        except Exception as e:
            self.logger.debug(f"WebSocket数据转发 {direction} 结束: {e}")
    
    async def _handle_websocket_messages(self, conn_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理WebSocket消息（直接模式）
        """
        buffer = b''
        
        try:
            while True:
                # 读取数据
                data = await reader.read(self.config.buffer_size)
                if not data:
                    break
                
                buffer += data
                
                # 解析并处理完整的帧
                while buffer:
                    frame, consumed = WebSocketParser.parse_frame(buffer)
                    if not frame:
                        break  # 需要更多数据
                    
                    buffer = buffer[consumed:]
                    
                    # 处理帧
                    await self._process_websocket_frame(conn_id, frame, writer)
                    
                    # 更新统计信息
                    conn_info = self.connections[conn_id]
                    conn_info.frames_received += 1
                    conn_info.bytes_received += len(frame.payload)
                    conn_info.last_activity = time.time()
                    self.stats.bytes_received += len(frame.payload)
                    
                    # 检查是否为关闭帧
                    if frame.opcode == WebSocketOpcode.CLOSE.value:
                        return
                
        except Exception as e:
            self.logger.debug(f"WebSocket消息处理结束: {e}")
    
    async def _process_websocket_frame(self, conn_id: str, frame: WebSocketFrame, writer: asyncio.StreamWriter):
        """
        处理WebSocket帧
        """
        try:
            if frame.opcode == WebSocketOpcode.TEXT.value:
                # 文本消息
                message = frame.payload.decode('utf-8')
                response = await self._handle_text_message(conn_id, message)
                if response:
                    await self._send_text_message(writer, response)
                    
            elif frame.opcode == WebSocketOpcode.BINARY.value:
                # 二进制消息
                response = await self._handle_binary_message(conn_id, frame.payload)
                if response:
                    await self._send_binary_message(writer, response)
                    
            elif frame.opcode == WebSocketOpcode.PING.value:
                # Ping帧，发送Pong响应
                pong_frame = WebSocketParser.build_pong_frame(frame.payload)
                writer.write(pong_frame)
                await writer.drain()
                
            elif frame.opcode == WebSocketOpcode.PONG.value:
                # Pong帧，更新心跳状态
                conn_info = self.connections[conn_id]
                conn_info.last_activity = time.time()
                
            elif frame.opcode == WebSocketOpcode.CLOSE.value:
                # 关闭帧
                close_code = 1000
                close_reason = ''
                if len(frame.payload) >= 2:
                    close_code = struct.unpack('!H', frame.payload[:2])[0]
                    if len(frame.payload) > 2:
                        close_reason = frame.payload[2:].decode('utf-8', errors='ignore')
                
                self.logger.info(f"WebSocket连接关闭: {conn_id}, 代码: {close_code}, 原因: {close_reason}")
                
                # 发送关闭响应
                close_frame = WebSocketParser.build_close_frame(close_code, close_reason)
                writer.write(close_frame)
                await writer.drain()
                
                # 更新连接状态
                self.connections[conn_id].state = WebSocketState.CLOSING
                
        except Exception as e:
            self.logger.error(f"处理WebSocket帧错误: {e}")
    
    async def _handle_text_message(self, conn_id: str, message: str) -> Optional[str]:
        """
        处理文本消息
        
        子类可以重写此方法来实现自定义消息处理逻辑
        """
        # 默认回显消息
        return f"Echo: {message}"
    
    async def _handle_binary_message(self, conn_id: str, data: bytes) -> Optional[bytes]:
        """
        处理二进制消息
        
        子类可以重写此方法来实现自定义消息处理逻辑
        """
        # 默认回显数据
        return data
    
    async def _send_text_message(self, writer: asyncio.StreamWriter, message: str):
        """
        发送文本消息
        """
        frame = WebSocketParser.build_frame(
            WebSocketOpcode.TEXT.value,
            message.encode('utf-8')
        )
        writer.write(frame)
        await writer.drain()
    
    async def _send_binary_message(self, writer: asyncio.StreamWriter, data: bytes):
        """
        发送二进制消息
        """
        frame = WebSocketParser.build_frame(
            WebSocketOpcode.BINARY.value,
            data
        )
        writer.write(frame)
        await writer.drain()
    
    async def _ping_loop(self, conn_id: str, writer: asyncio.StreamWriter):
        """
        心跳循环
        """
        try:
            while True:
                await asyncio.sleep(self.ping_interval)
                
                # 检查连接状态
                if conn_id not in self.connections:
                    break
                
                conn_info = self.connections[conn_id]
                if conn_info.state != WebSocketState.OPEN:
                    break
                
                # 检查是否超时
                if time.time() - conn_info.last_activity > self.ping_timeout:
                    self.logger.warning(f"WebSocket连接超时: {conn_id}")
                    break
                
                # 发送Ping帧
                ping_frame = WebSocketParser.build_ping_frame()
                writer.write(ping_frame)
                await writer.drain()
                
        except Exception as e:
            self.logger.debug(f"心跳循环结束: {e}")
    
    def _cleanup_connection(self, conn_id: str, writer: asyncio.StreamWriter):
        """
        清理连接
        """
        try:
            # 发送关闭帧
            if conn_id in self.connections:
                conn_info = self.connections[conn_id]
                if conn_info.state == WebSocketState.OPEN:
                    close_frame = WebSocketParser.build_close_frame(1001, "Going Away")
                    writer.write(close_frame)
            
            writer.close()
        except Exception:
            pass
        
        if conn_id in self.connections:
            del self.connections[conn_id]
        
        self.remove_connection(conn_id)
        self.logger.info(f"WebSocket连接 {conn_id} 已关闭")

class WebSocketTunnelProxy(WebSocketProxy):
    """
    WebSocket隧道代理
    
    将任意TCP流量通过WebSocket隧道传输
    """
    
    async def _handle_text_message(self, conn_id: str, message: str) -> Optional[str]:
        """
        处理隧道控制消息
        """
        try:
            # 解析JSON控制消息
            control_msg = json.loads(message)
            
            if control_msg.get('type') == 'connect':
                # 建立隧道连接
                target_host = control_msg.get('host')
                target_port = control_msg.get('port')
                
                if target_host and target_port:
                    success = await self._establish_tunnel(conn_id, target_host, target_port)
                    return json.dumps({
                        'type': 'connect_response',
                        'success': success,
                        'message': 'Connected' if success else 'Connection failed'
                    })
            
            elif control_msg.get('type') == 'disconnect':
                # 断开隧道连接
                await self._close_tunnel(conn_id)
                return json.dumps({
                    'type': 'disconnect_response',
                    'success': True,
                    'message': 'Disconnected'
                })
            
        except Exception as e:
            self.logger.error(f"处理隧道控制消息错误: {e}")
        
        return None
    
    async def _handle_binary_message(self, conn_id: str, data: bytes) -> Optional[bytes]:
        """
        处理隧道数据
        """
        # 转发数据到目标连接
        if hasattr(self.connections[conn_id], '_tunnel_writer'):
            tunnel_writer = getattr(self.connections[conn_id], '_tunnel_writer')
            try:
                tunnel_writer.write(data)
                await tunnel_writer.drain()
            except Exception as e:
                self.logger.error(f"转发隧道数据失败: {e}")
        
        return None
    
    async def _establish_tunnel(self, conn_id: str, target_host: str, target_port: int) -> bool:
        """
        建立隧道连接
        """
        try:
            # 连接到目标服务器
            tunnel_reader, tunnel_writer = await asyncio.open_connection(target_host, target_port)
            
            # 保存隧道连接
            conn_info = self.connections[conn_id]
            setattr(conn_info, '_tunnel_reader', tunnel_reader)
            setattr(conn_info, '_tunnel_writer', tunnel_writer)
            
            # 启动数据转发任务
            asyncio.create_task(self._tunnel_data_forward(conn_id))
            
            self.logger.info(f"隧道连接建立: {conn_id} -> {target_host}:{target_port}")
            return True
            
        except Exception as e:
            self.logger.error(f"建立隧道连接失败: {e}")
            return False
    
    async def _close_tunnel(self, conn_id: str):
        """
        关闭隧道连接
        """
        if conn_id in self.connections:
            conn_info = self.connections[conn_id]
            if hasattr(conn_info, '_tunnel_writer'):
                tunnel_writer = getattr(conn_info, '_tunnel_writer')
                tunnel_writer.close()
                await tunnel_writer.wait_closed()
                delattr(conn_info, '_tunnel_reader')
                delattr(conn_info, '_tunnel_writer')
    
    async def _tunnel_data_forward(self, conn_id: str):
        """
        隧道数据转发（从目标到WebSocket）
        """
        try:
            conn_info = self.connections[conn_id]
            tunnel_reader = getattr(conn_info, '_tunnel_reader')
            
            # 这里需要获取WebSocket writer，简化处理
            # 实际实现中需要更复杂的连接管理
            
            while True:
                data = await tunnel_reader.read(self.config.buffer_size)
                if not data:
                    break
                
                # 通过WebSocket发送二进制数据
                # 这里需要访问WebSocket writer，实际实现需要重构
                
        except Exception as e:
            self.logger.debug(f"隧道数据转发结束: {e}")

# 导出功能
__all__ = [
    'WebSocketOpcode',
    'WebSocketState',
    'WebSocketFrame',
    'WebSocketHandshake',
    'WebSocketConnectionInfo',
    'WebSocketParser',
    'WebSocketProxy',
    'WebSocketTunnelProxy'
]