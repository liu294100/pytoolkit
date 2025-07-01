#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
协议模块

支持多种网络协议：
- TCP/UDP 双向代理
- HTTP/HTTPS/HTTP2/HTTP3 通道
- Socks4/Socks5 代理
- Shadowsocks/SSR 协议
- Trojan 协议
- SSH tunnel
- WebSocket 通道
- Raw socket 通道
"""

from .tcp_udp import TCPProxy, UDPProxy, TCPUDPBridge
from .http_proxy import HTTPProxy, HTTPSProxy
from .socks_proxy import SocksProxy
from .ssh_tunnel import SSHTunnel
from .websocket_proxy import WebSocketProxy
from .raw_socket import RawSocketProxy
from .protocol_manager import ProtocolManager, ProtocolType

# 协议版本信息
PROTOCOL_VERSION = "1.0.0"

# 支持的协议列表
SUPPORTED_PROTOCOLS = [
    "tcp",
    "udp",
    "http",
    "https",
    "http2",
    "http3",
    "socks4",
    "socks5",
    "shadowsocks",
    "ssr",
    "trojan",
    "ssh",
    "websocket",
    "raw_socket"
]

# 协议默认端口
DEFAULT_PORTS = {
    "tcp": 8080,
    "udp": 8080,
    "http": 80,
    "https": 443,
    "http2": 443,
    "http3": 443,
    "socks4": 1080,
    "socks5": 1080,
    "shadowsocks": 8388,
    "ssr": 8388,
    "trojan": 443,
    "ssh": 22,
    "websocket": 8080,
    "raw_socket": 8080
}

# 协议描述
PROTOCOL_DESCRIPTIONS = {
    "tcp": "TCP 代理协议",
    "udp": "UDP 代理协议",
    "http": "HTTP 代理协议",
    "https": "HTTPS 代理协议",
    "http2": "HTTP/2 代理协议",
    "http3": "HTTP/3 (QUIC) 代理协议",
    "socks4": "SOCKS4 代理协议",
    "socks5": "SOCKS5 代理协议",
    "shadowsocks": "Shadowsocks 代理协议",
    "ssr": "ShadowsocksR 代理协议",
    "trojan": "Trojan 代理协议",
    "ssh": "SSH 隧道协议",
    "websocket": "WebSocket 代理协议",
    "raw_socket": "原始套接字协议"
}

def get_protocol_info(protocol_name: str) -> dict:
    """
    获取协议信息
    
    Args:
        protocol_name: 协议名称
    
    Returns:
        协议信息字典
    """
    if protocol_name not in SUPPORTED_PROTOCOLS:
        raise ValueError(f"不支持的协议: {protocol_name}")
    
    return {
        "name": protocol_name,
        "description": PROTOCOL_DESCRIPTIONS.get(protocol_name, ""),
        "default_port": DEFAULT_PORTS.get(protocol_name, 8080),
        "supported": True
    }

def list_supported_protocols() -> list:
    """
    列出所有支持的协议
    
    Returns:
        支持的协议列表
    """
    return SUPPORTED_PROTOCOLS.copy()

def create_protocol_proxy(protocol_type: str, **kwargs):
    """
    创建协议代理实例
    
    Args:
        protocol_type: 协议类型
        **kwargs: 协议参数
    
    Returns:
        协议代理实例
    """
    protocol_type = protocol_type.lower()
    
    if protocol_type == "tcp":
        return TCPProxy(**kwargs)
    elif protocol_type == "udp":
        return UDPProxy(**kwargs)
    elif protocol_type == "http":
        return HTTPProxy(**kwargs)
    elif protocol_type == "https":
        return HTTPSProxy(**kwargs)
    elif protocol_type == "http2":
        # HTTP2 暂未实现，使用 HTTPS 代理
        return HTTPSProxy(**kwargs)
    elif protocol_type == "http3":
        # HTTP3 暂未实现，使用 HTTPS 代理
        return HTTPSProxy(**kwargs)
    elif protocol_type == "socks4":
        return SocksProxy(version=4, **kwargs)
    elif protocol_type == "socks5":
        return SocksProxy(version=5, **kwargs)
    elif protocol_type == "shadowsocks":
        # Shadowsocks 暂未实现
        raise NotImplementedError(f"协议 {protocol_type} 暂未实现")
    elif protocol_type == "ssr":
        # SSR 暂未实现
        raise NotImplementedError(f"协议 {protocol_type} 暂未实现")
    elif protocol_type == "trojan":
        # Trojan 暂未实现
        raise NotImplementedError(f"协议 {protocol_type} 暂未实现")
    elif protocol_type == "ssh":
        return SSHTunnel(**kwargs)
    elif protocol_type == "websocket":
        return WebSocketProxy(**kwargs)
    elif protocol_type == "raw_socket":
        return RawSocketProxy(**kwargs)
    else:
        raise ValueError(f"不支持的协议类型: {protocol_type}")

# 导出所有协议类和函数
__all__ = [
    # 协议类
    "TCPProxy",
    "UDPProxy",
    "TCPUDPBridge",
    "HTTPProxy",
    "HTTPSProxy",
    "SocksProxy",
    "ShadowsocksProxy",
    "SSRProxy",
    "TrojanProxy",
    "TrojanServer",
    "SSHTunnel",
    "SSHClient",
    "WebSocketProxy",
    "WebSocketServer",
    "RawSocketProxy",
    "RawSocketServer",
    "ProtocolManager",
    "ProtocolType",
    
    # 常量
    "PROTOCOL_VERSION",
    "SUPPORTED_PROTOCOLS",
    "DEFAULT_PORTS",
    "PROTOCOL_DESCRIPTIONS",
    
    # 函数
    "get_protocol_info",
    "list_supported_protocols",
    "create_protocol_proxy"
]