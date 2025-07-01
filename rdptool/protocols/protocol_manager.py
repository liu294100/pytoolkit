#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
协议管理器模块

统一管理和调度各种网络协议
"""

import asyncio
import threading
import time
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
import logging
from abc import ABC, abstractmethod

class ProtocolType(Enum):
    """协议类型枚举"""
    TCP = "tcp"
    UDP = "udp"
    HTTP = "http"
    HTTPS = "https"
    HTTP2 = "http2"
    HTTP3 = "http3"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    SHADOWSOCKS = "shadowsocks"
    SSR = "ssr"
    TROJAN = "trojan"
    SSH = "ssh"
    WEBSOCKET = "websocket"
    RAW_SOCKET = "raw_socket"

class ProtocolStatus(Enum):
    """协议状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class ProtocolConfig:
    """协议配置"""
    protocol_type: ProtocolType
    name: str
    host: str = "0.0.0.0"
    port: int = 8080
    target_host: Optional[str] = None
    target_port: Optional[int] = None
    auth_required: bool = False
    username: Optional[str] = None
    password: Optional[str] = None
    encryption: Optional[str] = None
    compression: bool = False
    timeout: int = 30
    max_connections: int = 1000
    buffer_size: int = 8192
    enable_logging: bool = True
    custom_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProtocolStats:
    """协议统计信息"""
    protocol_name: str
    protocol_type: ProtocolType
    status: ProtocolStatus
    start_time: Optional[float] = None
    stop_time: Optional[float] = None
    total_connections: int = 0
    active_connections: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors: int = 0
    last_error: Optional[str] = None
    uptime: float = 0.0

class BaseProtocol(ABC):
    """
    协议基类
    
    所有协议实现都应继承此类
    """
    
    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.status = ProtocolStatus.STOPPED
        self.stats = ProtocolStats(
            protocol_name=config.name,
            protocol_type=config.protocol_type,
            status=self.status
        )
        self.logger = logging.getLogger(f"protocol.{config.name}")
        self._stop_event = threading.Event()
        self._server_task: Optional[asyncio.Task] = None
        self._connections: Dict[str, Any] = {}
        self._lock = threading.RLock()
    
    @abstractmethod
    async def start(self) -> bool:
        """启动协议服务"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """停止协议服务"""
        pass
    
    @abstractmethod
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理连接"""
        pass
    
    def get_status(self) -> ProtocolStatus:
        """获取协议状态"""
        return self.status
    
    def get_stats(self) -> ProtocolStats:
        """获取统计信息"""
        with self._lock:
            if self.stats.start_time and self.status == ProtocolStatus.RUNNING:
                self.stats.uptime = time.time() - self.stats.start_time
            return self.stats
    
    def update_stats(self, **kwargs):
        """更新统计信息"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.stats, key):
                    setattr(self.stats, key, value)
    
    def add_connection(self, conn_id: str, connection: Any):
        """添加连接"""
        with self._lock:
            self._connections[conn_id] = connection
            self.stats.active_connections = len(self._connections)
            self.stats.total_connections += 1
    
    def remove_connection(self, conn_id: str):
        """移除连接"""
        with self._lock:
            if conn_id in self._connections:
                del self._connections[conn_id]
                self.stats.active_connections = len(self._connections)
    
    def get_connections(self) -> Dict[str, Any]:
        """获取所有连接"""
        with self._lock:
            return self._connections.copy()

class ProtocolManager:
    """
    协议管理器
    
    管理多个协议实例的生命周期
    """
    
    def __init__(self):
        self.protocols: Dict[str, BaseProtocol] = {}
        self.configs: Dict[str, ProtocolConfig] = {}
        self.event_callbacks: Dict[str, List[Callable]] = {
            'protocol_started': [],
            'protocol_stopped': [],
            'protocol_error': [],
            'connection_established': [],
            'connection_closed': [],
            'data_transferred': []
        }
        self.logger = logging.getLogger("protocol_manager")
        self._lock = threading.RLock()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    def register_protocol(self, name: str, protocol: BaseProtocol):
        """
        注册协议实例
        
        Args:
            name: 协议名称
            protocol: 协议实例
        """
        with self._lock:
            if name in self.protocols:
                raise ValueError(f"协议 {name} 已存在")
            
            self.protocols[name] = protocol
            self.configs[name] = protocol.config
            self.logger.info(f"注册协议: {name} ({protocol.config.protocol_type.value})")
    
    def unregister_protocol(self, name: str) -> bool:
        """
        注销协议实例
        
        Args:
            name: 协议名称
        
        Returns:
            是否成功注销
        """
        with self._lock:
            if name not in self.protocols:
                return False
            
            # 先停止协议
            asyncio.create_task(self.stop_protocol(name))
            
            del self.protocols[name]
            del self.configs[name]
            self.logger.info(f"注销协议: {name}")
            return True
    
    async def start_protocol(self, name: str) -> bool:
        """
        启动指定协议
        
        Args:
            name: 协议名称
        
        Returns:
            是否成功启动
        """
        if name not in self.protocols:
            self.logger.error(f"协议 {name} 不存在")
            return False
        
        protocol = self.protocols[name]
        
        try:
            self.logger.info(f"启动协议: {name}")
            success = await protocol.start()
            
            if success:
                self._emit_event('protocol_started', name, protocol)
                self.logger.info(f"协议 {name} 启动成功")
            else:
                self.logger.error(f"协议 {name} 启动失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"启动协议 {name} 时发生错误: {e}")
            self._emit_event('protocol_error', name, protocol, str(e))
            return False
    
    async def stop_protocol(self, name: str) -> bool:
        """
        停止指定协议
        
        Args:
            name: 协议名称
        
        Returns:
            是否成功停止
        """
        if name not in self.protocols:
            self.logger.error(f"协议 {name} 不存在")
            return False
        
        protocol = self.protocols[name]
        
        try:
            self.logger.info(f"停止协议: {name}")
            success = await protocol.stop()
            
            if success:
                self._emit_event('protocol_stopped', name, protocol)
                self.logger.info(f"协议 {name} 停止成功")
            else:
                self.logger.error(f"协议 {name} 停止失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"停止协议 {name} 时发生错误: {e}")
            self._emit_event('protocol_error', name, protocol, str(e))
            return False
    
    async def restart_protocol(self, name: str) -> bool:
        """
        重启指定协议
        
        Args:
            name: 协议名称
        
        Returns:
            是否成功重启
        """
        if await self.stop_protocol(name):
            await asyncio.sleep(1)  # 等待完全停止
            return await self.start_protocol(name)
        return False
    
    async def start_all_protocols(self) -> Dict[str, bool]:
        """
        启动所有协议
        
        Returns:
            各协议启动结果
        """
        results = {}
        
        for name in self.protocols.keys():
            results[name] = await self.start_protocol(name)
        
        return results
    
    async def stop_all_protocols(self) -> Dict[str, bool]:
        """
        停止所有协议
        
        Returns:
            各协议停止结果
        """
        results = {}
        
        for name in self.protocols.keys():
            results[name] = await self.stop_protocol(name)
        
        return results
    
    def get_protocol_status(self, name: str) -> Optional[ProtocolStatus]:
        """
        获取协议状态
        
        Args:
            name: 协议名称
        
        Returns:
            协议状态
        """
        if name in self.protocols:
            return self.protocols[name].get_status()
        return None
    
    def get_protocol_stats(self, name: str) -> Optional[ProtocolStats]:
        """
        获取协议统计信息
        
        Args:
            name: 协议名称
        
        Returns:
            协议统计信息
        """
        if name in self.protocols:
            return self.protocols[name].get_stats()
        return None
    
    def get_all_protocols_status(self) -> Dict[str, ProtocolStatus]:
        """
        获取所有协议状态
        
        Returns:
            所有协议状态字典
        """
        return {
            name: protocol.get_status()
            for name, protocol in self.protocols.items()
        }
    
    def get_all_protocols_stats(self) -> Dict[str, ProtocolStats]:
        """
        获取所有协议统计信息
        
        Returns:
            所有协议统计信息字典
        """
        return {
            name: protocol.get_stats()
            for name, protocol in self.protocols.items()
        }
    
    def list_protocols(self) -> List[str]:
        """
        列出所有协议名称
        
        Returns:
            协议名称列表
        """
        return list(self.protocols.keys())
    
    def get_protocol_config(self, name: str) -> Optional[ProtocolConfig]:
        """
        获取协议配置
        
        Args:
            name: 协议名称
        
        Returns:
            协议配置
        """
        return self.configs.get(name)
    
    def update_protocol_config(self, name: str, config: ProtocolConfig) -> bool:
        """
        更新协议配置
        
        Args:
            name: 协议名称
            config: 新配置
        
        Returns:
            是否成功更新
        """
        if name not in self.protocols:
            return False
        
        self.configs[name] = config
        self.protocols[name].config = config
        return True
    
    def add_event_callback(self, event_type: str, callback: Callable):
        """
        添加事件回调
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
    
    def remove_event_callback(self, event_type: str, callback: Callable):
        """
        移除事件回调
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self.event_callbacks:
            try:
                self.event_callbacks[event_type].remove(callback)
            except ValueError:
                pass
    
    def _emit_event(self, event_type: str, *args, **kwargs):
        """
        触发事件
        
        Args:
            event_type: 事件类型
            *args: 事件参数
            **kwargs: 事件关键字参数
        """
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"事件回调执行失败: {e}")
    
    async def start_monitoring(self):
        """
        启动监控任务
        """
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("协议监控已启动")
    
    async def stop_monitoring(self):
        """
        停止监控任务
        """
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("协议监控已停止")
    
    async def _monitor_loop(self):
        """
        监控循环
        """
        while self._running:
            try:
                # 检查协议状态
                for name, protocol in self.protocols.items():
                    status = protocol.get_status()
                    
                    # 如果协议意外停止，尝试重启
                    if status == ProtocolStatus.ERROR:
                        self.logger.warning(f"检测到协议 {name} 错误，尝试重启")
                        await self.restart_protocol(name)
                
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(5)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取管理器摘要信息
        
        Returns:
            摘要信息字典
        """
        total_protocols = len(self.protocols)
        running_protocols = sum(1 for p in self.protocols.values() if p.get_status() == ProtocolStatus.RUNNING)
        total_connections = sum(p.get_stats().active_connections for p in self.protocols.values())
        total_bytes_sent = sum(p.get_stats().bytes_sent for p in self.protocols.values())
        total_bytes_received = sum(p.get_stats().bytes_received for p in self.protocols.values())
        
        return {
            'total_protocols': total_protocols,
            'running_protocols': running_protocols,
            'stopped_protocols': total_protocols - running_protocols,
            'total_connections': total_connections,
            'total_bytes_sent': total_bytes_sent,
            'total_bytes_received': total_bytes_received,
            'monitoring_active': self._running
        }

# 全局协议管理器实例
_global_manager = None

def get_global_manager() -> ProtocolManager:
    """
    获取全局协议管理器
    
    Returns:
        全局协议管理器实例
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = ProtocolManager()
    return _global_manager

# 导出功能
__all__ = [
    'ProtocolType',
    'ProtocolStatus',
    'ProtocolConfig',
    'ProtocolStats',
    'BaseProtocol',
    'ProtocolManager',
    'get_global_manager'
]