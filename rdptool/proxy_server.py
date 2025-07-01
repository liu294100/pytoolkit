#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多协议代理服务器

整合多种代理协议：
- HTTP/HTTPS代理
- SOCKS4/SOCKS5代理
- WebSocket隧道
- SSH隧道
- 原始套接字代理
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from protocols.http_proxy import HTTPProxy, HTTPSProxy
from protocols.socks_proxy import SocksProxy
from protocols.websocket_proxy import WebSocketProxy, WebSocketTunnelProxy
from protocols.ssh_tunnel import SSHTunnel
from protocols.raw_socket import RawSocketProxy
from network.connection_manager import ConnectionManager
from network.tcp_handler import TCPServer
from network.udp_handler import UDPServer
from utils.logger import setup_logger
from utils.config import load_config

logger = logging.getLogger(__name__)

class ProxyProtocol(Enum):
    """代理协议类型"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    WEBSOCKET = "websocket"
    SSH = "ssh"
    RAW_SOCKET = "raw_socket"

@dataclass
class ProxyConfig:
    """代理配置"""
    protocol: ProxyProtocol
    host: str = "0.0.0.0"
    port: int = 1080
    enabled: bool = True
    auth_required: bool = False
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    max_connections: int = 1000
    buffer_size: int = 8192
    timeout: int = 30

class ProxyServer:
    """
    多协议代理服务器
    
    支持多种代理协议的统一服务器
    """
    
    def __init__(self, config_file: Optional[str] = None):
        # 加载配置
        self.config = self._load_config(config_file)
        
        # 初始化组件
        self.connection_manager = ConnectionManager()
        self.proxy_instances: Dict[str, Any] = {}
        self.tcp_servers: Dict[str, TCPServer] = {}
        self.udp_servers: Dict[str, UDPServer] = {}
        
        # 运行状态
        self.is_running = False
        self.tasks: List[asyncio.Task] = []
        
        # 统计信息
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'bytes_transferred': 0,
            'protocols_stats': {}
        }
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            'proxy': {
                'host': '0.0.0.0',
                'protocols': {
                    'http': {
                        'enabled': True,
                        'port': 8080,
                        'auth_required': False
                    },
                    'https': {
                        'enabled': True,
                        'port': 8443,
                        'auth_required': False,
                        'ssl_cert': None,
                        'ssl_key': None
                    },
                    'socks4': {
                        'enabled': True,
                        'port': 1080,
                        'auth_required': False
                    },
                    'socks5': {
                        'enabled': True,
                        'port': 1081,
                        'auth_required': False,
                        'username': None,
                        'password': None
                    },
                    'websocket': {
                        'enabled': True,
                        'port': 8888,
                        'path': '/ws',
                        'auth_required': False
                    },
                    'ssh': {
                        'enabled': False,
                        'port': 2222,
                        'host_key': None,
                        'auth_required': True
                    },
                    'raw_socket': {
                        'enabled': False,
                        'port': 9999,
                        'require_root': True
                    }
                },
                'max_connections': 1000,
                'buffer_size': 8192,
                'timeout': 30
            },
            'auth': {
                'enable': False,
                'method': 'userpass',
                'users': {
                    'admin': 'password123'
                }
            },
            'rules': {
                'allow_all': True,
                'blocked_domains': [],
                'blocked_ips': [],
                'allowed_ports': []
            },
            'logging': {
                'level': 'INFO',
                'file': 'proxy_server.log',
                'max_size': '10MB',
                'backup_count': 5
            }
        }
        
        if config_file and Path(config_file).exists():
            try:
                user_config = load_config(config_file)
                # 合并配置
                for section, values in user_config.items():
                    if section in default_config:
                        if isinstance(default_config[section], dict):
                            default_config[section].update(values)
                        else:
                            default_config[section] = values
                    else:
                        default_config[section] = values
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认配置")
        
        return default_config
    
    async def start(self):
        """启动代理服务器"""
        try:
            logger.info("正在启动多协议代理服务器...")
            
            # 设置日志
            setup_logger(
                level=self.config['logging']['level'],
                log_file=self.config['logging']['file']
            )
            
            # 启动连接管理器
            await self.connection_manager.start()
            
            # 启动各协议代理
            await self._start_protocol_proxies()
            
            self.is_running = True
            logger.info("代理服务器启动成功")
            
            # 等待所有任务完成
            if self.tasks:
                await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"代理服务器启动失败: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """停止代理服务器"""
        logger.info("正在停止代理服务器...")
        
        self.is_running = False
        
        # 取消所有任务
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # 等待任务完成
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # 停止所有代理实例
        for proxy in self.proxy_instances.values():
            if hasattr(proxy, 'stop'):
                await proxy.stop()
        
        # 停止TCP/UDP服务器
        for server in self.tcp_servers.values():
            await server.stop()
        
        for server in self.udp_servers.values():
            await server.stop()
        
        # 停止连接管理器
        await self.connection_manager.stop()
        
        logger.info("代理服务器已停止")
    
    async def _start_protocol_proxies(self):
        """启动各协议代理"""
        protocols_config = self.config['proxy']['protocols']
        
        # HTTP代理
        if protocols_config.get('http', {}).get('enabled', False):
            await self._start_http_proxy(protocols_config['http'])
        
        # HTTPS代理
        if protocols_config.get('https', {}).get('enabled', False):
            await self._start_https_proxy(protocols_config['https'])
        
        # SOCKS4代理
        if protocols_config.get('socks4', {}).get('enabled', False):
            await self._start_socks4_proxy(protocols_config['socks4'])
        
        # SOCKS5代理
        if protocols_config.get('socks5', {}).get('enabled', False):
            await self._start_socks5_proxy(protocols_config['socks5'])
        
        # WebSocket代理
        if protocols_config.get('websocket', {}).get('enabled', False):
            await self._start_websocket_proxy(protocols_config['websocket'])
        
        # SSH隧道
        if protocols_config.get('ssh', {}).get('enabled', False):
            await self._start_ssh_tunnel(protocols_config['ssh'])
        
        # 原始套接字代理
        if protocols_config.get('raw_socket', {}).get('enabled', False):
            await self._start_raw_socket_proxy(protocols_config['raw_socket'])
    
    async def _start_http_proxy(self, config: Dict[str, Any]):
        """启动HTTP代理"""
        try:
            proxy = HTTPProxy(
                auth_required=config.get('auth_required', False),
                username=config.get('username'),
                password=config.get('password')
            )
            
            await proxy.start(
                host=self.config['proxy']['host'],
                port=config['port']
            )
            
            self.proxy_instances['http'] = proxy
            logger.info(f"HTTP代理启动: {self.config['proxy']['host']}:{config['port']}")
            
        except Exception as e:
            logger.error(f"HTTP代理启动失败: {e}")
    
    async def _start_https_proxy(self, config: Dict[str, Any]):
        """启动HTTPS代理"""
        try:
            proxy = HTTPSProxy(
                ssl_cert=config.get('ssl_cert'),
                ssl_key=config.get('ssl_key'),
                auth_required=config.get('auth_required', False),
                username=config.get('username'),
                password=config.get('password')
            )
            
            await proxy.start(
                host=self.config['proxy']['host'],
                port=config['port']
            )
            
            self.proxy_instances['https'] = proxy
            logger.info(f"HTTPS代理启动: {self.config['proxy']['host']}:{config['port']}")
            
        except Exception as e:
            logger.error(f"HTTPS代理启动失败: {e}")
    
    async def _start_socks4_proxy(self, config: Dict[str, Any]):
        """启动SOCKS4代理"""
        try:
            proxy = SocksProxy(version=4)
            
            await proxy.start(
                host=self.config['proxy']['host'],
                port=config['port']
            )
            
            self.proxy_instances['socks4'] = proxy
            logger.info(f"SOCKS4代理启动: {self.config['proxy']['host']}:{config['port']}")
            
        except Exception as e:
            logger.error(f"SOCKS4代理启动失败: {e}")
    
    async def _start_socks5_proxy(self, config: Dict[str, Any]):
        """启动SOCKS5代理"""
        try:
            proxy = SocksProxy(
                version=5,
                auth_required=config.get('auth_required', False),
                username=config.get('username'),
                password=config.get('password')
            )
            
            await proxy.start(
                host=self.config['proxy']['host'],
                port=config['port']
            )
            
            self.proxy_instances['socks5'] = proxy
            logger.info(f"SOCKS5代理启动: {self.config['proxy']['host']}:{config['port']}")
            
        except Exception as e:
            logger.error(f"SOCKS5代理启动失败: {e}")
    
    async def _start_websocket_proxy(self, config: Dict[str, Any]):
        """启动WebSocket代理"""
        try:
            proxy = WebSocketTunnelProxy(
                path=config.get('path', '/ws'),
                auth_required=config.get('auth_required', False)
            )
            
            await proxy.start(
                host=self.config['proxy']['host'],
                port=config['port']
            )
            
            self.proxy_instances['websocket'] = proxy
            logger.info(f"WebSocket代理启动: {self.config['proxy']['host']}:{config['port']}{config.get('path', '/ws')}")
            
        except Exception as e:
            logger.error(f"WebSocket代理启动失败: {e}")
    
    async def _start_ssh_tunnel(self, config: Dict[str, Any]):
        """启动SSH隧道"""
        try:
            tunnel = SSHTunnel(
                host_key_file=config.get('host_key'),
                auth_required=config.get('auth_required', True)
            )
            
            await tunnel.start(
                host=self.config['proxy']['host'],
                port=config['port']
            )
            
            self.proxy_instances['ssh'] = tunnel
            logger.info(f"SSH隧道启动: {self.config['proxy']['host']}:{config['port']}")
            
        except Exception as e:
            logger.error(f"SSH隧道启动失败: {e}")
    
    async def _start_raw_socket_proxy(self, config: Dict[str, Any]):
        """启动原始套接字代理"""
        try:
            # 检查权限
            if config.get('require_root', True):
                import os
                if os.geteuid() != 0:
                    logger.warning("原始套接字代理需要root权限，跳过启动")
                    return
            
            proxy = RawSocketProxy()
            
            await proxy.start(
                host=self.config['proxy']['host'],
                port=config['port']
            )
            
            self.proxy_instances['raw_socket'] = proxy
            logger.info(f"原始套接字代理启动: {self.config['proxy']['host']}:{config['port']}")
            
        except Exception as e:
            logger.error(f"原始套接字代理启动失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        # 更新活跃连接数
        self.stats['active_connections'] = len(self.connection_manager.get_all_connections())
        
        # 获取各协议统计
        for name, proxy in self.proxy_instances.items():
            if hasattr(proxy, 'get_stats'):
                self.stats['protocols_stats'][name] = proxy.get_stats()
        
        return self.stats.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        return {
            'running': self.is_running,
            'protocols': list(self.proxy_instances.keys()),
            'stats': self.get_stats()
        }

# 全局代理服务器实例
_proxy_server: Optional[ProxyServer] = None

def get_proxy_server() -> Optional[ProxyServer]:
    """获取全局代理服务器实例"""
    return _proxy_server

def set_proxy_server(server: ProxyServer):
    """设置全局代理服务器实例"""
    global _proxy_server
    _proxy_server = server

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='多协议代理服务器')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=1080, help='监听端口')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='日志级别')
    
    args = parser.parse_args()
    
    # 创建代理服务器
    proxy = ProxyServer(args.config)
    set_proxy_server(proxy)
    
    # 设置信号处理
    def signal_handler(signum, frame):
        logger.info(f"接收到信号 {signum}，正在关闭...")
        asyncio.create_task(proxy.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动代理服务器
        await proxy.start()
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭代理服务器...")
    except Exception as e:
        logger.error(f"代理服务器运行错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())