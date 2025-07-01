#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连接管理器模块

实现网络连接的统一管理，包括：
- 连接池管理
- 连接状态监控
- 连接事件处理
- 连接生命周期管理
- 连接负载均衡
"""

import asyncio
import time
import uuid
import weakref
from typing import Dict, List, Optional, Callable, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict, deque
import threading

class ConnectionStatus(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    ERROR = "error"
    TIMEOUT = "timeout"

class ConnectionType(Enum):
    """连接类型"""
    TCP = "tcp"
    UDP = "udp"
    WEBSOCKET = "websocket"
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    SSH = "ssh"
    RAW = "raw"

class NetworkEventType(Enum):
    """网络事件类型"""
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_ERROR = "connection_error"
    CONNECTION_TIMEOUT = "connection_timeout"
    DATA_RECEIVED = "data_received"
    DATA_SENT = "data_sent"
    BANDWIDTH_CHANGED = "bandwidth_changed"
    LATENCY_CHANGED = "latency_changed"
    QUALITY_CHANGED = "quality_changed"

@dataclass
class ConnectionInfo:
    """连接信息"""
    conn_id: str
    conn_type: ConnectionType
    status: ConnectionStatus
    local_addr: Optional[Tuple[str, int]] = None
    remote_addr: Optional[Tuple[str, int]] = None
    created_time: float = field(default_factory=time.time)
    connected_time: Optional[float] = None
    last_activity: float = field(default_factory=time.time)
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    errors: int = 0
    reconnect_count: int = 0
    latency: float = 0.0
    bandwidth: float = 0.0
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)

@dataclass
class NetworkEvent:
    """网络事件"""
    event_type: NetworkEventType
    conn_id: str
    timestamp: float = field(default_factory=time.time)
    data: Optional[Any] = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class ConnectionPool:
    """
    连接池
    
    管理一组相同类型的连接
    """
    
    def __init__(self, pool_id: str, conn_type: ConnectionType, max_size: int = 10):
        self.pool_id = pool_id
        self.conn_type = conn_type
        self.max_size = max_size
        
        # 连接存储
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self.idle_connections: deque = deque()
        self.pending_connections: Dict[str, ConnectionInfo] = {}
        
        # 统计信息
        self.total_created = 0
        self.total_destroyed = 0
        self.peak_active = 0
        
        # 同步锁
        self._lock = threading.RLock()
        
        # 日志记录器
        self.logger = logging.getLogger(f"network.pool.{pool_id}")
    
    def get_connection(self, conn_id: Optional[str] = None) -> Optional[ConnectionInfo]:
        """
        获取连接
        
        Args:
            conn_id: 指定连接ID，如果为None则从空闲连接中获取
        
        Returns:
            ConnectionInfo: 连接信息，如果没有可用连接则返回None
        """
        with self._lock:
            if conn_id:
                # 获取指定连接
                return self.active_connections.get(conn_id)
            
            # 从空闲连接中获取
            if self.idle_connections:
                conn_info = self.idle_connections.popleft()
                self.active_connections[conn_info.conn_id] = conn_info
                return conn_info
            
            return None
    
    def add_connection(self, conn_info: ConnectionInfo) -> bool:
        """
        添加连接到池中
        
        Args:
            conn_info: 连接信息
        
        Returns:
            bool: 是否成功添加
        """
        with self._lock:
            if len(self.active_connections) >= self.max_size:
                self.logger.warning(f"连接池 {self.pool_id} 已满，无法添加新连接")
                return False
            
            self.active_connections[conn_info.conn_id] = conn_info
            self.total_created += 1
            
            # 更新峰值
            current_active = len(self.active_connections)
            if current_active > self.peak_active:
                self.peak_active = current_active
            
            self.logger.debug(f"连接 {conn_info.conn_id} 已添加到池 {self.pool_id}")
            return True
    
    def remove_connection(self, conn_id: str) -> Optional[ConnectionInfo]:
        """
        从池中移除连接
        
        Args:
            conn_id: 连接ID
        
        Returns:
            ConnectionInfo: 被移除的连接信息
        """
        with self._lock:
            # 从活跃连接中移除
            conn_info = self.active_connections.pop(conn_id, None)
            if conn_info:
                self.total_destroyed += 1
                self.logger.debug(f"连接 {conn_id} 已从池 {self.pool_id} 中移除")
                return conn_info
            
            # 从空闲连接中移除
            for i, idle_conn in enumerate(self.idle_connections):
                if idle_conn.conn_id == conn_id:
                    del self.idle_connections[i]
                    self.total_destroyed += 1
                    self.logger.debug(f"空闲连接 {conn_id} 已从池 {self.pool_id} 中移除")
                    return idle_conn
            
            # 从待处理连接中移除
            conn_info = self.pending_connections.pop(conn_id, None)
            if conn_info:
                self.logger.debug(f"待处理连接 {conn_id} 已从池 {self.pool_id} 中移除")
                return conn_info
            
            return None
    
    def release_connection(self, conn_id: str) -> bool:
        """
        释放连接到空闲池
        
        Args:
            conn_id: 连接ID
        
        Returns:
            bool: 是否成功释放
        """
        with self._lock:
            conn_info = self.active_connections.pop(conn_id, None)
            if conn_info and conn_info.status == ConnectionStatus.CONNECTED:
                self.idle_connections.append(conn_info)
                self.logger.debug(f"连接 {conn_id} 已释放到空闲池")
                return True
            
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取连接池统计信息
        
        Returns:
            dict: 统计信息
        """
        with self._lock:
            return {
                'pool_id': self.pool_id,
                'conn_type': self.conn_type.value,
                'max_size': self.max_size,
                'active_count': len(self.active_connections),
                'idle_count': len(self.idle_connections),
                'pending_count': len(self.pending_connections),
                'total_created': self.total_created,
                'total_destroyed': self.total_destroyed,
                'peak_active': self.peak_active,
                'utilization': len(self.active_connections) / self.max_size if self.max_size > 0 else 0
            }
    
    def cleanup_idle_connections(self, max_idle_time: float = 300.0):
        """
        清理空闲连接
        
        Args:
            max_idle_time: 最大空闲时间（秒）
        """
        with self._lock:
            current_time = time.time()
            cleaned_count = 0
            
            # 清理过期的空闲连接
            while self.idle_connections:
                conn_info = self.idle_connections[0]
                if current_time - conn_info.last_activity > max_idle_time:
                    self.idle_connections.popleft()
                    self.total_destroyed += 1
                    cleaned_count += 1
                else:
                    break
            
            if cleaned_count > 0:
                self.logger.info(f"清理了 {cleaned_count} 个空闲连接")
    
    def clear(self):
        """
        清空连接池
        """
        with self._lock:
            self.active_connections.clear()
            self.idle_connections.clear()
            self.pending_connections.clear()
            self.logger.info(f"连接池 {self.pool_id} 已清空")

class ConnectionManager:
    """
    连接管理器
    
    统一管理所有网络连接
    """
    
    def __init__(self):
        # 连接存储
        self.connections: Dict[str, ConnectionInfo] = {}
        self.connection_pools: Dict[str, ConnectionPool] = {}
        
        # 事件处理
        self.event_handlers: Dict[NetworkEventType, List[Callable]] = defaultdict(list)
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.event_history: deque = deque(maxlen=1000)
        
        # 监控和统计
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0,
            'total_errors': 0,
            'start_time': time.time()
        }
        
        # 配置
        self.config = {
            'max_connections': 1000,
            'connection_timeout': 30.0,
            'keepalive_interval': 60.0,
            'cleanup_interval': 300.0,
            'event_processing': True,
            'auto_reconnect': True,
            'max_reconnect_attempts': 3
        }
        
        # 任务和状态
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._event_processor_task: Optional[asyncio.Task] = None
        
        # 同步锁
        self._lock = asyncio.Lock()
        
        # 日志记录器
        self.logger = logging.getLogger("network.connection_manager")
    
    async def start(self):
        """
        启动连接管理器
        """
        if self._running:
            return
        
        self._running = True
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # 启动事件处理任务
        if self.config['event_processing']:
            self._event_processor_task = asyncio.create_task(self._event_processor_loop())
        
        self.logger.info("连接管理器已启动")
    
    async def stop(self):
        """
        停止连接管理器
        """
        if not self._running:
            return
        
        self._running = False
        
        # 停止任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._event_processor_task:
            self._event_processor_task.cancel()
            try:
                await self._event_processor_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有连接
        await self.close_all_connections()
        
        self.logger.info("连接管理器已停止")
    
    async def add_connection(self, conn_info: ConnectionInfo) -> bool:
        """
        添加连接
        
        Args:
            conn_info: 连接信息
        
        Returns:
            bool: 是否成功添加
        """
        async with self._lock:
            if len(self.connections) >= self.config['max_connections']:
                self.logger.warning("连接数已达到最大限制")
                return False
            
            self.connections[conn_info.conn_id] = conn_info
            self.stats['total_connections'] += 1
            self.stats['active_connections'] = len(self.connections)
            
            # 添加到连接池
            pool_id = f"{conn_info.conn_type.value}_pool"
            if pool_id not in self.connection_pools:
                self.connection_pools[pool_id] = ConnectionPool(
                    pool_id, conn_info.conn_type
                )
            
            self.connection_pools[pool_id].add_connection(conn_info)
            
            # 发送事件
            await self._emit_event(NetworkEvent(
                event_type=NetworkEventType.CONNECTION_ESTABLISHED,
                conn_id=conn_info.conn_id,
                data=conn_info
            ))
            
            self.logger.info(f"连接 {conn_info.conn_id} 已添加")
            return True
    
    async def remove_connection(self, conn_id: str) -> Optional[ConnectionInfo]:
        """
        移除连接
        
        Args:
            conn_id: 连接ID
        
        Returns:
            ConnectionInfo: 被移除的连接信息
        """
        async with self._lock:
            conn_info = self.connections.pop(conn_id, None)
            if conn_info:
                self.stats['active_connections'] = len(self.connections)
                
                # 从连接池中移除
                pool_id = f"{conn_info.conn_type.value}_pool"
                if pool_id in self.connection_pools:
                    self.connection_pools[pool_id].remove_connection(conn_id)
                
                # 发送事件
                await self._emit_event(NetworkEvent(
                    event_type=NetworkEventType.CONNECTION_LOST,
                    conn_id=conn_id,
                    data=conn_info
                ))
                
                self.logger.info(f"连接 {conn_id} 已移除")
            
            return conn_info
    
    async def get_connection(self, conn_id: str) -> Optional[ConnectionInfo]:
        """
        获取连接信息
        
        Args:
            conn_id: 连接ID
        
        Returns:
            ConnectionInfo: 连接信息
        """
        return self.connections.get(conn_id)
    
    async def update_connection_status(self, conn_id: str, status: ConnectionStatus, error: Optional[Exception] = None):
        """
        更新连接状态
        
        Args:
            conn_id: 连接ID
            status: 新状态
            error: 错误信息（如果有）
        """
        conn_info = self.connections.get(conn_id)
        if conn_info:
            old_status = conn_info.status
            conn_info.status = status
            conn_info.last_activity = time.time()
            
            if status == ConnectionStatus.CONNECTED and old_status != ConnectionStatus.CONNECTED:
                conn_info.connected_time = time.time()
            
            if error:
                conn_info.errors += 1
                self.stats['total_errors'] += 1
                
                # 发送错误事件
                await self._emit_event(NetworkEvent(
                    event_type=NetworkEventType.CONNECTION_ERROR,
                    conn_id=conn_id,
                    error=error,
                    data=conn_info
                ))
            
            self.logger.debug(f"连接 {conn_id} 状态更新: {old_status.value} -> {status.value}")
    
    async def update_connection_stats(self, conn_id: str, bytes_sent: int = 0, bytes_received: int = 0, 
                                    packets_sent: int = 0, packets_received: int = 0):
        """
        更新连接统计信息
        
        Args:
            conn_id: 连接ID
            bytes_sent: 发送字节数
            bytes_received: 接收字节数
            packets_sent: 发送包数
            packets_received: 接收包数
        """
        conn_info = self.connections.get(conn_id)
        if conn_info:
            conn_info.bytes_sent += bytes_sent
            conn_info.bytes_received += bytes_received
            conn_info.packets_sent += packets_sent
            conn_info.packets_received += packets_received
            conn_info.last_activity = time.time()
            
            # 更新全局统计
            self.stats['total_bytes_sent'] += bytes_sent
            self.stats['total_bytes_received'] += bytes_received
            
            # 发送数据事件
            if bytes_sent > 0:
                await self._emit_event(NetworkEvent(
                    event_type=NetworkEventType.DATA_SENT,
                    conn_id=conn_id,
                    data={'bytes': bytes_sent, 'packets': packets_sent}
                ))
            
            if bytes_received > 0:
                await self._emit_event(NetworkEvent(
                    event_type=NetworkEventType.DATA_RECEIVED,
                    conn_id=conn_id,
                    data={'bytes': bytes_received, 'packets': packets_received}
                ))
    
    async def get_connections_by_type(self, conn_type: ConnectionType) -> List[ConnectionInfo]:
        """
        根据类型获取连接列表
        
        Args:
            conn_type: 连接类型
        
        Returns:
            List[ConnectionInfo]: 连接信息列表
        """
        return [conn for conn in self.connections.values() if conn.conn_type == conn_type]
    
    async def get_connections_by_status(self, status: ConnectionStatus) -> List[ConnectionInfo]:
        """
        根据状态获取连接列表
        
        Args:
            status: 连接状态
        
        Returns:
            List[ConnectionInfo]: 连接信息列表
        """
        return [conn for conn in self.connections.values() if conn.status == status]
    
    async def get_connections_by_tag(self, tag: str) -> List[ConnectionInfo]:
        """
        根据标签获取连接列表
        
        Args:
            tag: 标签
        
        Returns:
            List[ConnectionInfo]: 连接信息列表
        """
        return [conn for conn in self.connections.values() if tag in conn.tags]
    
    async def close_connection(self, conn_id: str):
        """
        关闭指定连接
        
        Args:
            conn_id: 连接ID
        """
        conn_info = await self.get_connection(conn_id)
        if conn_info:
            await self.update_connection_status(conn_id, ConnectionStatus.DISCONNECTING)
            # 这里应该调用实际的连接关闭逻辑
            await self.remove_connection(conn_id)
    
    async def close_connections_by_type(self, conn_type: ConnectionType):
        """
        关闭指定类型的所有连接
        
        Args:
            conn_type: 连接类型
        """
        connections = await self.get_connections_by_type(conn_type)
        for conn_info in connections:
            await self.close_connection(conn_info.conn_id)
    
    async def close_all_connections(self):
        """
        关闭所有连接
        """
        conn_ids = list(self.connections.keys())
        for conn_id in conn_ids:
            await self.close_connection(conn_id)
    
    def add_event_handler(self, event_type: NetworkEventType, handler: Callable):
        """
        添加事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理器函数
        """
        self.event_handlers[event_type].append(handler)
        self.logger.debug(f"已添加 {event_type.value} 事件处理器")
    
    def remove_event_handler(self, event_type: NetworkEventType, handler: Callable):
        """
        移除事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理器函数
        """
        if handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
            self.logger.debug(f"已移除 {event_type.value} 事件处理器")
    
    async def _emit_event(self, event: NetworkEvent):
        """
        发送事件
        
        Args:
            event: 网络事件
        """
        if self.config['event_processing']:
            await self.event_queue.put(event)
            self.event_history.append(event)
    
    async def _event_processor_loop(self):
        """
        事件处理循环
        """
        while self._running:
            try:
                # 等待事件
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # 处理事件
                handlers = self.event_handlers.get(event.event_type, [])
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        self.logger.error(f"事件处理器错误: {e}")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"事件处理循环错误: {e}")
                await asyncio.sleep(1.0)
    
    async def _cleanup_loop(self):
        """
        清理循环
        """
        while self._running:
            try:
                await asyncio.sleep(self.config['cleanup_interval'])
                await self._cleanup_connections()
                await self._cleanup_pools()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"清理循环错误: {e}")
    
    async def _cleanup_connections(self):
        """
        清理过期连接
        """
        current_time = time.time()
        timeout = self.config['connection_timeout']
        
        expired_connections = []
        
        for conn_id, conn_info in self.connections.items():
            # 检查超时连接
            if (conn_info.status in [ConnectionStatus.CONNECTING, ConnectionStatus.RECONNECTING] and
                current_time - conn_info.last_activity > timeout):
                expired_connections.append(conn_id)
            
            # 检查错误连接
            elif conn_info.status == ConnectionStatus.ERROR:
                if not self.config['auto_reconnect'] or conn_info.reconnect_count >= self.config['max_reconnect_attempts']:
                    expired_connections.append(conn_id)
        
        # 移除过期连接
        for conn_id in expired_connections:
            await self.remove_connection(conn_id)
        
        if expired_connections:
            self.logger.info(f"清理了 {len(expired_connections)} 个过期连接")
    
    async def _cleanup_pools(self):
        """
        清理连接池
        """
        for pool in self.connection_pools.values():
            pool.cleanup_idle_connections()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            dict: 统计信息
        """
        current_time = time.time()
        uptime = current_time - self.stats['start_time']
        
        stats = self.stats.copy()
        stats.update({
            'uptime': uptime,
            'connections_by_type': {},
            'connections_by_status': {},
            'pool_stats': {}
        })
        
        # 按类型统计连接
        for conn_info in self.connections.values():
            conn_type = conn_info.conn_type.value
            status = conn_info.status.value
            
            if conn_type not in stats['connections_by_type']:
                stats['connections_by_type'][conn_type] = 0
            stats['connections_by_type'][conn_type] += 1
            
            if status not in stats['connections_by_status']:
                stats['connections_by_status'][status] = 0
            stats['connections_by_status'][status] += 1
        
        # 连接池统计
        for pool_id, pool in self.connection_pools.items():
            stats['pool_stats'][pool_id] = pool.get_stats()
        
        return stats
    
    def cleanup(self):
        """
        清理资源
        """
        try:
            # 清空连接
            self.connections.clear()
            
            # 清空连接池
            for pool in self.connection_pools.values():
                pool.clear()
            self.connection_pools.clear()
            
            # 清空事件
            self.event_handlers.clear()
            self.event_history.clear()
            
            self.logger.info("连接管理器资源已清理")
        
        except Exception as e:
            self.logger.error(f"清理连接管理器资源时发生错误: {e}")

# 导出功能
__all__ = [
    'ConnectionStatus',
    'ConnectionType',
    'NetworkEventType',
    'ConnectionInfo',
    'NetworkEvent',
    'ConnectionPool',
    'ConnectionManager'
]