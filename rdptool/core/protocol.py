#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
协议处理模块

定义和处理远程桌面通信协议：
- 消息类型和格式
- 数据包编码/解码
- 协议版本管理
- 压缩和优化
"""

import json
import zlib
import base64
import struct
import logging
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict
from enum import Enum
import time

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """消息类型"""
    # 连接管理
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    AUTH = "auth"
    
    # 屏幕相关
    SCREEN_FRAME = "screen_frame"
    SCREEN_INFO = "screen_info"
    SCREEN_REGION = "screen_region"
    
    # 输入控制
    MOUSE_EVENT = "mouse_event"
    KEYBOARD_EVENT = "keyboard_event"
    
    # 文件传输
    FILE_TRANSFER = "file_transfer"
    FILE_LIST = "file_list"
    
    # 系统控制
    SYSTEM_INFO = "system_info"
    SYSTEM_COMMAND = "system_command"
    
    # 错误和状态
    ERROR = "error"
    STATUS = "status"
    ACK = "ack"

class CompressionType(Enum):
    """压缩类型"""
    NONE = "none"
    ZLIB = "zlib"
    GZIP = "gzip"
    LZ4 = "lz4"  # 可选

@dataclass
class ProtocolHeader:
    """协议头"""
    version: str = "1.0"
    message_type: MessageType = MessageType.HEARTBEAT
    message_id: str = ""
    timestamp: float = 0.0
    compression: CompressionType = CompressionType.NONE
    data_length: int = 0
    checksum: str = ""
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if not self.message_id:
            self.message_id = f"{int(self.timestamp * 1000000)}"

@dataclass
class ProtocolMessage:
    """协议消息"""
    header: ProtocolHeader
    payload: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'header': asdict(self.header),
            'payload': self.payload
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProtocolMessage':
        """从字典创建"""
        header_data = data.get('header', {})
        header = ProtocolHeader(
            version=header_data.get('version', '1.0'),
            message_type=MessageType(header_data.get('message_type', 'heartbeat')),
            message_id=header_data.get('message_id', ''),
            timestamp=header_data.get('timestamp', 0.0),
            compression=CompressionType(header_data.get('compression', 'none')),
            data_length=header_data.get('data_length', 0),
            checksum=header_data.get('checksum', '')
        )
        
        return cls(
            header=header,
            payload=data.get('payload', {})
        )

class ProtocolHandler:
    """协议处理器"""
    
    def __init__(self, version: str = "1.0", enable_compression: bool = True):
        self.version = version
        self.enable_compression = enable_compression
        self.default_compression = CompressionType.ZLIB
        self.max_payload_size = 10 * 1024 * 1024  # 10MB
        
    def create_message(self, 
                      message_type: MessageType, 
                      payload: Dict[str, Any],
                      compression: Optional[CompressionType] = None) -> ProtocolMessage:
        """创建消息"""
        if compression is None and self.enable_compression:
            compression = self.default_compression
        elif compression is None:
            compression = CompressionType.NONE
        
        header = ProtocolHeader(
            version=self.version,
            message_type=message_type,
            compression=compression
        )
        
        return ProtocolMessage(header=header, payload=payload)
    
    def encode_message(self, message: ProtocolMessage) -> bytes:
        """编码消息"""
        try:
            # 序列化payload
            payload_json = json.dumps(message.payload, ensure_ascii=False)
            payload_bytes = payload_json.encode('utf-8')
            
            # 压缩payload
            if message.header.compression == CompressionType.ZLIB:
                payload_bytes = zlib.compress(payload_bytes)
            elif message.header.compression == CompressionType.GZIP:
                import gzip
                payload_bytes = gzip.compress(payload_bytes)
            
            # 更新header信息
            message.header.data_length = len(payload_bytes)
            message.header.checksum = self._calculate_checksum(payload_bytes)
            
            # 序列化header
            header_dict = asdict(message.header)
            # 转换枚举为字符串
            header_dict['message_type'] = message.header.message_type.value
            header_dict['compression'] = message.header.compression.value
            
            header_json = json.dumps(header_dict, ensure_ascii=False)
            header_bytes = header_json.encode('utf-8')
            
            # 构建最终数据包
            # 格式: [header_length(4字节)] [header] [payload]
            header_length = len(header_bytes)
            packet = struct.pack('>I', header_length) + header_bytes + payload_bytes
            
            return packet
            
        except Exception as e:
            logger.error(f"编码消息失败: {e}")
            raise
    
    def decode_message(self, data: bytes) -> Optional[ProtocolMessage]:
        """解码消息"""
        try:
            if len(data) < 4:
                logger.error("数据包太短")
                return None
            
            # 读取header长度
            header_length = struct.unpack('>I', data[:4])[0]
            
            if len(data) < 4 + header_length:
                logger.error("数据包不完整")
                return None
            
            # 读取header
            header_bytes = data[4:4 + header_length]
            header_json = header_bytes.decode('utf-8')
            header_dict = json.loads(header_json)
            
            # 读取payload
            payload_bytes = data[4 + header_length:]
            
            # 验证数据长度
            expected_length = header_dict.get('data_length', 0)
            if len(payload_bytes) != expected_length:
                logger.error(f"数据长度不匹配: 期望{expected_length}, 实际{len(payload_bytes)}")
                return None
            
            # 验证校验和
            expected_checksum = header_dict.get('checksum', '')
            actual_checksum = self._calculate_checksum(payload_bytes)
            if expected_checksum != actual_checksum:
                logger.error("校验和验证失败")
                return None
            
            # 解压缩payload
            compression = CompressionType(header_dict.get('compression', 'none'))
            if compression == CompressionType.ZLIB:
                payload_bytes = zlib.decompress(payload_bytes)
            elif compression == CompressionType.GZIP:
                import gzip
                payload_bytes = gzip.decompress(payload_bytes)
            
            # 解析payload
            payload_json = payload_bytes.decode('utf-8')
            payload = json.loads(payload_json)
            
            # 创建消息对象
            message = ProtocolMessage.from_dict({
                'header': header_dict,
                'payload': payload
            })
            
            return message
            
        except Exception as e:
            logger.error(f"解码消息失败: {e}")
            return None
    
    def _calculate_checksum(self, data: bytes) -> str:
        """计算校验和"""
        import hashlib
        return hashlib.md5(data).hexdigest()
    
    # 便捷方法
    def create_connect_message(self, client_info: Dict[str, Any]) -> ProtocolMessage:
        """创建连接消息"""
        return self.create_message(MessageType.CONNECT, {
            'client_info': client_info,
            'protocol_version': self.version
        })
    
    def create_auth_message(self, username: str, password: str, token: str = "") -> ProtocolMessage:
        """创建认证消息"""
        return self.create_message(MessageType.AUTH, {
            'username': username,
            'password': password,
            'token': token
        })
    
    def create_screen_frame_message(self, frame_data: bytes, 
                                   frame_info: Dict[str, Any]) -> ProtocolMessage:
        """创建屏幕帧消息"""
        # 将二进制数据编码为base64
        frame_b64 = base64.b64encode(frame_data).decode('ascii')
        
        return self.create_message(MessageType.SCREEN_FRAME, {
            'frame_data': frame_b64,
            'frame_info': frame_info
        })
    
    def create_mouse_event_message(self, event_type: str, 
                                  x: int, y: int, 
                                  button: str = "", 
                                  clicks: int = 1) -> ProtocolMessage:
        """创建鼠标事件消息"""
        return self.create_message(MessageType.MOUSE_EVENT, {
            'event_type': event_type,
            'x': x,
            'y': y,
            'button': button,
            'clicks': clicks
        })
    
    def create_keyboard_event_message(self, event_type: str, 
                                     key: str, 
                                     text: str = "") -> ProtocolMessage:
        """创建键盘事件消息"""
        return self.create_message(MessageType.KEYBOARD_EVENT, {
            'event_type': event_type,
            'key': key,
            'text': text
        })
    
    def create_heartbeat_message(self) -> ProtocolMessage:
        """创建心跳消息"""
        return self.create_message(MessageType.HEARTBEAT, {
            'timestamp': time.time()
        })
    
    def create_error_message(self, error_code: str, error_message: str) -> ProtocolMessage:
        """创建错误消息"""
        return self.create_message(MessageType.ERROR, {
            'error_code': error_code,
            'error_message': error_message
        })
    
    def create_ack_message(self, message_id: str, status: str = "ok") -> ProtocolMessage:
        """创建确认消息"""
        return self.create_message(MessageType.ACK, {
            'message_id': message_id,
            'status': status
        })
    
    def extract_screen_frame(self, message: ProtocolMessage) -> Optional[bytes]:
        """提取屏幕帧数据"""
        if message.header.message_type != MessageType.SCREEN_FRAME:
            return None
        
        try:
            frame_b64 = message.payload.get('frame_data', '')
            if frame_b64:
                return base64.b64decode(frame_b64)
        except Exception as e:
            logger.error(f"提取屏幕帧失败: {e}")
        
        return None
    
    def get_compression_ratio(self, original_size: int, compressed_size: int) -> float:
        """获取压缩比"""
        if original_size == 0:
            return 0.0
        return (original_size - compressed_size) / original_size
    
    def validate_message(self, message: ProtocolMessage) -> bool:
        """验证消息"""
        try:
            # 检查版本
            if message.header.version != self.version:
                logger.warning(f"协议版本不匹配: {message.header.version} != {self.version}")
            
            # 检查消息类型
            if not isinstance(message.header.message_type, MessageType):
                logger.error("无效的消息类型")
                return False
            
            # 检查payload大小
            payload_size = len(json.dumps(message.payload).encode('utf-8'))
            if payload_size > self.max_payload_size:
                logger.error(f"Payload太大: {payload_size} > {self.max_payload_size}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证消息失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'version': self.version,
            'enable_compression': self.enable_compression,
            'default_compression': self.default_compression.value,
            'max_payload_size': self.max_payload_size
        }

# 工具函数
def create_protocol_handler(version: str = "1.0", **kwargs) -> ProtocolHandler:
    """创建协议处理器"""
    return ProtocolHandler(version=version, **kwargs)

def message_type_from_string(type_str: str) -> Optional[MessageType]:
    """从字符串获取消息类型"""
    try:
        return MessageType(type_str)
    except ValueError:
        return None

def compression_type_from_string(comp_str: str) -> Optional[CompressionType]:
    """从字符串获取压缩类型"""
    try:
        return CompressionType(comp_str)
    except ValueError:
        return None