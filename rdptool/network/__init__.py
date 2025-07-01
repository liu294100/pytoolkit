#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网络通信模块

提供远程桌面工具的网络通信功能，包括：
- TCP/UDP 连接管理
- 异步网络通信
- 连接池管理
- 网络事件处理
- 数据传输优化
- 网络监控和统计
"""

from .connection_manager import (
    ConnectionManager,
    ConnectionPool,
    ConnectionInfo,
    ConnectionStatus,
    ConnectionType,
    NetworkEvent,
    NetworkEventType
)

from .tcp_handler import (
    TCPServer,
    TCPClient,
    TCPConnection,
    TCPConnectionInfo,
    TCPServerConfig,
    TCPClientConfig
)

from .udp_handler import (
    UDPServer,
    UDPClient,
    UDPSessionInfo,
    UDPServerConfig,
    UDPClientConfig,
    UDPSession
)

from .network_monitor import (
    NetworkMonitor,
    NetworkStatus,
    NetworkInterface,
    NetworkTraffic,
    NetworkQualityMetrics
)

# Data transfer module not implemented yet
# from .data_transfer import (
#     DataTransfer,
#     TransferManager,
#     TransferSession,
#     TransferConfig,
#     TransferStats,
#     TransferMode,
#     CompressionType,
#     EncryptionType
# )

# 版本信息
__version__ = "1.0.0"
__author__ = "RDP Tool Team"

# 网络配置常量
DEFAULT_TCP_PORT = 3389
DEFAULT_UDP_PORT = 3390
DEFAULT_BUFFER_SIZE = 8192
DEFAULT_TIMEOUT = 30.0
DEFAULT_KEEPALIVE_INTERVAL = 60.0
DEFAULT_MAX_CONNECTIONS = 100
DEFAULT_CONNECTION_POOL_SIZE = 10

# 支持的网络协议
SUPPORTED_PROTOCOLS = [
    'TCP',
    'UDP',
    'WebSocket',
    'HTTP',
    'HTTPS',
    'SOCKS4',
    'SOCKS5'
]

# 网络质量等级
NETWORK_QUALITY_LEVELS = {
    'EXCELLENT': {'latency': 50, 'packet_loss': 0.1, 'bandwidth': 100},
    'GOOD': {'latency': 100, 'packet_loss': 0.5, 'bandwidth': 50},
    'FAIR': {'latency': 200, 'packet_loss': 1.0, 'bandwidth': 20},
    'POOR': {'latency': 500, 'packet_loss': 3.0, 'bandwidth': 5},
    'BAD': {'latency': 1000, 'packet_loss': 10.0, 'bandwidth': 1}
}

# 全局网络管理器实例
_global_connection_manager = None
_global_network_monitor = None
_global_transfer_manager = None

def get_connection_manager() -> ConnectionManager:
    """
    获取全局连接管理器
    
    Returns:
        ConnectionManager: 连接管理器实例
    """
    global _global_connection_manager
    if _global_connection_manager is None:
        _global_connection_manager = ConnectionManager()
    return _global_connection_manager

def get_network_monitor() -> NetworkMonitor:
    """
    获取全局网络监控器
    
    Returns:
        NetworkMonitor: 网络监控器实例
    """
    global _global_network_monitor
    if _global_network_monitor is None:
        _global_network_monitor = NetworkMonitor()
    return _global_network_monitor

# def get_transfer_manager() -> TransferManager:
#     """
#     获取全局传输管理器
#     
#     Returns:
#         TransferManager: 传输管理器实例
#     """
#     global _global_transfer_manager
#     if _global_transfer_manager is None:
#         _global_transfer_manager = TransferManager()
#     return _global_transfer_manager

def create_tcp_server(host: str = '0.0.0.0', port: int = DEFAULT_TCP_PORT, **kwargs) -> TCPServer:
    """
    创建TCP服务器
    
    Args:
        host: 绑定地址
        port: 绑定端口
        **kwargs: 其他配置参数
    
    Returns:
        TCPServer: TCP服务器实例
    """
    config = TCPServerConfig(
        host=host,
        port=port,
        buffer_size=kwargs.get('buffer_size', DEFAULT_BUFFER_SIZE),
        timeout=kwargs.get('timeout', DEFAULT_TIMEOUT),
        max_connections=kwargs.get('max_connections', DEFAULT_MAX_CONNECTIONS),
        keepalive_interval=kwargs.get('keepalive_interval', DEFAULT_KEEPALIVE_INTERVAL),
        **kwargs
    )
    return TCPServer(config)

def create_tcp_client(host: str, port: int, **kwargs) -> TCPClient:
    """
    创建TCP客户端
    
    Args:
        host: 服务器地址
        port: 服务器端口
        **kwargs: 其他配置参数
    
    Returns:
        TCPClient: TCP客户端实例
    """
    config = TCPClientConfig(
        host=host,
        port=port,
        buffer_size=kwargs.get('buffer_size', DEFAULT_BUFFER_SIZE),
        timeout=kwargs.get('timeout', DEFAULT_TIMEOUT),
        keepalive_interval=kwargs.get('keepalive_interval', DEFAULT_KEEPALIVE_INTERVAL),
        **kwargs
    )
    return TCPClient(config)

def create_udp_server(host: str = '0.0.0.0', port: int = DEFAULT_UDP_PORT, **kwargs) -> UDPServer:
    """
    创建UDP服务器
    
    Args:
        host: 绑定地址
        port: 绑定端口
        **kwargs: 其他配置参数
    
    Returns:
        UDPServer: UDP服务器实例
    """
    config = UDPServerConfig(
        host=host,
        port=port,
        buffer_size=kwargs.get('buffer_size', DEFAULT_BUFFER_SIZE),
        timeout=kwargs.get('timeout', DEFAULT_TIMEOUT),
        max_sessions=kwargs.get('max_sessions', DEFAULT_MAX_CONNECTIONS),
        session_timeout=kwargs.get('session_timeout', 300.0),
        **kwargs
    )
    return UDPServer(config)

def create_udp_client(host: str, port: int, **kwargs) -> UDPClient:
    """
    创建UDP客户端
    
    Args:
        host: 服务器地址
        port: 服务器端口
        **kwargs: 其他配置参数
    
    Returns:
        UDPClient: UDP客户端实例
    """
    config = UDPClientConfig(
        host=host,
        port=port,
        buffer_size=kwargs.get('buffer_size', DEFAULT_BUFFER_SIZE),
        timeout=kwargs.get('timeout', DEFAULT_TIMEOUT),
        **kwargs
    )
    return UDPClient(config)

def get_network_info() -> dict:
    """
    获取网络信息
    
    Returns:
        dict: 网络信息字典
    """
    import socket
    import platform
    
    info = {
        'hostname': socket.gethostname(),
        'platform': platform.system(),
        'python_version': platform.python_version(),
        'supported_protocols': SUPPORTED_PROTOCOLS.copy(),
        'default_ports': {
            'tcp': DEFAULT_TCP_PORT,
            'udp': DEFAULT_UDP_PORT
        },
        'network_quality_levels': NETWORK_QUALITY_LEVELS.copy()
    }
    
    try:
        # 获取本地IP地址
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            info['local_ip'] = s.getsockname()[0]
    except Exception:
        info['local_ip'] = '127.0.0.1'
    
    return info

def test_network_connectivity(host: str, port: int, timeout: float = 5.0) -> bool:
    """
    测试网络连通性
    
    Args:
        host: 目标主机
        port: 目标端口
        timeout: 超时时间
    
    Returns:
        bool: 连通性测试结果
    """
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False

def measure_network_latency(host: str, port: int, count: int = 3) -> dict:
    """
    测量网络延迟
    
    Args:
        host: 目标主机
        port: 目标端口
        count: 测试次数
    
    Returns:
        dict: 延迟测量结果
    """
    import socket
    import time
    
    latencies = []
    
    for _ in range(count):
        try:
            start_time = time.time()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((host, port))
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # 转换为毫秒
            latencies.append(latency)
        except Exception:
            continue
    
    if not latencies:
        return {'min': None, 'max': None, 'avg': None, 'count': 0}
    
    return {
        'min': min(latencies),
        'max': max(latencies),
        'avg': sum(latencies) / len(latencies),
        'count': len(latencies),
        'raw_data': latencies
    }

def get_network_quality(host: str, port: int) -> str:
    """
    评估网络质量
    
    Args:
        host: 目标主机
        port: 目标端口
    
    Returns:
        str: 网络质量等级
    """
    # 测试连通性
    if not test_network_connectivity(host, port):
        return 'BAD'
    
    # 测量延迟
    latency_result = measure_network_latency(host, port)
    if latency_result['avg'] is None:
        return 'BAD'
    
    avg_latency = latency_result['avg']
    
    # 根据延迟判断网络质量
    for quality, thresholds in NETWORK_QUALITY_LEVELS.items():
        if avg_latency <= thresholds['latency']:
            return quality
    
    return 'BAD'

def cleanup_network_resources():
    """
    清理网络资源
    """
    global _global_connection_manager, _global_network_monitor, _global_transfer_manager
    
    try:
        if _global_connection_manager:
            _global_connection_manager.cleanup()
            _global_connection_manager = None
        
        if _global_network_monitor:
            _global_network_monitor.stop()
            _global_network_monitor = None
        
        if _global_transfer_manager:
            _global_transfer_manager.cleanup()
            _global_transfer_manager = None
    
    except Exception:
        pass

# 导出所有公共接口
__all__ = [
    # 连接管理
    'ConnectionManager',
    'ConnectionPool',
    'ConnectionInfo',
    'ConnectionStatus',
    'ConnectionType',
    'NetworkEvent',
    'NetworkEventType',
    
    # TCP处理
    'TCPServer',
    'TCPClient',
    'TCPConnection',
    'TCPConnectionInfo',
    'TCPServerConfig',
    'TCPClientConfig',
    
    # UDP处理
    'UDPServer',
    'UDPClient',
    'UDPConnection',
    'UDPConnectionInfo',
    'UDPServerConfig',
    'UDPClientConfig',
    'UDPSession',
    
    # 网络监控
    'NetworkMonitor',
    'NetworkStats',
    'BandwidthMonitor',
    'LatencyMonitor',
    'PacketLossMonitor',
    'NetworkQualityMetrics',
    
    # 数据传输
    'DataTransfer',
    'TransferManager',
    'TransferSession',
    'TransferConfig',
    'TransferStats',
    'TransferMode',
    'CompressionType',
    'EncryptionType',
    
    # 工具函数
    'get_connection_manager',
    'get_network_monitor',
    'get_transfer_manager',
    'create_tcp_server',
    'create_tcp_client',
    'create_udp_server',
    'create_udp_client',
    'get_network_info',
    'test_network_connectivity',
    'measure_network_latency',
    'get_network_quality',
    'cleanup_network_resources',
    
    # 常量
    'DEFAULT_TCP_PORT',
    'DEFAULT_UDP_PORT',
    'DEFAULT_BUFFER_SIZE',
    'DEFAULT_TIMEOUT',
    'DEFAULT_KEEPALIVE_INTERVAL',
    'DEFAULT_MAX_CONNECTIONS',
    'DEFAULT_CONNECTION_POOL_SIZE',
    'SUPPORTED_PROTOCOLS',
    'NETWORK_QUALITY_LEVELS'
]