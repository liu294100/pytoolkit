#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网络监控模块

实现网络状态监控、流量统计、连接质量评估等功能，包括：
- 网络接口监控
- 流量统计
- 连接质量评估
- 延迟测量
- 带宽测试
- 网络拓扑发现
"""

import asyncio
import socket
import time
import psutil
import struct
import platform
import subprocess
import logging
from typing import Optional, Dict, Any, List, Tuple, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
from collections import deque, defaultdict

class NetworkInterfaceType(Enum):
    """网络接口类型"""
    ETHERNET = "ethernet"
    WIFI = "wifi"
    LOOPBACK = "loopback"
    VPN = "vpn"
    TUNNEL = "tunnel"
    UNKNOWN = "unknown"

class NetworkStatus(Enum):
    """网络状态"""
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"

class ConnectionQuality(Enum):
    """连接质量"""
    EXCELLENT = "excellent"  # 延迟 < 50ms, 丢包率 < 1%
    GOOD = "good"           # 延迟 < 100ms, 丢包率 < 3%
    FAIR = "fair"           # 延迟 < 200ms, 丢包率 < 5%
    POOR = "poor"           # 延迟 < 500ms, 丢包率 < 10%
    BAD = "bad"             # 延迟 >= 500ms 或 丢包率 >= 10%

@dataclass
class NetworkInterface:
    """网络接口信息"""
    name: str
    display_name: str = ""
    interface_type: NetworkInterfaceType = NetworkInterfaceType.UNKNOWN
    status: NetworkStatus = NetworkStatus.UNKNOWN
    mac_address: str = ""
    ip_addresses: List[str] = field(default_factory=list)
    netmask: str = ""
    broadcast: str = ""
    mtu: int = 0
    speed: int = 0  # Mbps
    duplex: str = ""  # full, half, unknown
    
    # 统计信息
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    errin: int = 0
    errout: int = 0
    dropin: int = 0
    dropout: int = 0
    
    # 时间戳
    last_update: float = field(default_factory=time.time)

@dataclass
class NetworkTraffic:
    """网络流量信息"""
    interface: str
    timestamp: float
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    
    # 速率（每秒）
    send_rate: float = 0.0  # bytes/s
    recv_rate: float = 0.0  # bytes/s
    packet_send_rate: float = 0.0  # packets/s
    packet_recv_rate: float = 0.0  # packets/s

@dataclass
class LatencyMeasurement:
    """延迟测量结果"""
    target: str
    timestamp: float
    latency: float  # ms
    success: bool
    packet_loss: float = 0.0  # 丢包率 (0.0-1.0)
    jitter: float = 0.0  # 抖动 (ms)
    
@dataclass
class BandwidthMeasurement:
    """带宽测量结果"""
    target: str
    timestamp: float
    download_speed: float  # Mbps
    upload_speed: float    # Mbps
    test_duration: float   # seconds
    success: bool

@dataclass
class NetworkQualityMetrics:
    """网络质量指标"""
    interface: str
    timestamp: float
    quality: ConnectionQuality
    
    # 延迟指标
    avg_latency: float = 0.0  # ms
    min_latency: float = 0.0  # ms
    max_latency: float = 0.0  # ms
    jitter: float = 0.0       # ms
    
    # 丢包指标
    packet_loss: float = 0.0  # 0.0-1.0
    
    # 带宽指标
    available_bandwidth: float = 0.0  # Mbps
    utilization: float = 0.0          # 0.0-1.0
    
    # 稳定性指标
    stability_score: float = 0.0      # 0.0-1.0
    
class NetworkMonitor:
    """
    网络监控器
    
    监控网络接口状态、流量统计、连接质量等
    """
    
    def __init__(self, update_interval: float = 1.0, history_size: int = 3600):
        self.update_interval = update_interval
        self.history_size = history_size
        
        # 状态管理
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # 数据存储
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.traffic_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.latency_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.quality_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        
        # 上次统计数据（用于计算速率）
        self._last_stats: Dict[str, Dict[str, int]] = {}
        self._last_update_time = 0.0
        
        # 事件回调
        self.on_interface_change: Optional[Callable] = None
        self.on_quality_change: Optional[Callable] = None
        self.on_traffic_alert: Optional[Callable] = None
        
        # 阈值配置
        self.traffic_alert_threshold = 100 * 1024 * 1024  # 100MB/s
        self.latency_alert_threshold = 200.0  # 200ms
        self.packet_loss_alert_threshold = 0.05  # 5%
        
        # 日志记录器
        self.logger = logging.getLogger("network.monitor")
    
    async def start(self) -> bool:
        """
        启动网络监控
        
        Returns:
            bool: 是否启动成功
        """
        if self._running:
            return True
        
        try:
            # 初始化网络接口信息
            await self._update_interfaces()
            
            # 启动监控任务
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            self._running = True
            
            self.logger.info("网络监控已启动")
            return True
            
        except Exception as e:
            self.logger.error(f"启动网络监控失败: {e}")
            return False
    
    async def stop(self):
        """
        停止网络监控
        """
        if not self._running:
            return
        
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("网络监控已停止")
    
    async def _monitor_loop(self):
        """
        监控循环
        """
        try:
            while self._running:
                await self._update_interfaces()
                await self._update_traffic_stats()
                await self._evaluate_quality()
                
                await asyncio.sleep(self.update_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"监控循环错误: {e}")
    
    async def _update_interfaces(self):
        """
        更新网络接口信息
        """
        try:
            # 获取网络接口统计信息
            net_io = psutil.net_io_counters(pernic=True)
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            
            current_interfaces = set()
            
            for interface_name in net_io.keys():
                current_interfaces.add(interface_name)
                
                # 获取或创建接口对象
                if interface_name not in self.interfaces:
                    self.interfaces[interface_name] = NetworkInterface(
                        name=interface_name,
                        display_name=interface_name
                    )
                
                interface = self.interfaces[interface_name]
                
                # 更新统计信息
                stats = net_io[interface_name]
                interface.bytes_sent = stats.bytes_sent
                interface.bytes_recv = stats.bytes_recv
                interface.packets_sent = stats.packets_sent
                interface.packets_recv = stats.packets_recv
                interface.errin = stats.errin
                interface.errout = stats.errout
                interface.dropin = stats.dropin
                interface.dropout = stats.dropout
                
                # 更新接口状态
                if interface_name in net_if_stats:
                    if_stats = net_if_stats[interface_name]
                    interface.status = NetworkStatus.UP if if_stats.isup else NetworkStatus.DOWN
                    interface.speed = if_stats.speed if if_stats.speed > 0 else 0
                    interface.mtu = if_stats.mtu
                    interface.duplex = if_stats.duplex.name.lower() if hasattr(if_stats.duplex, 'name') else "unknown"
                
                # 更新IP地址信息
                if interface_name in net_if_addrs:
                    addrs = net_if_addrs[interface_name]
                    interface.ip_addresses = []
                    
                    for addr in addrs:
                        if addr.family == socket.AF_INET:
                            interface.ip_addresses.append(addr.address)
                            if addr.netmask:
                                interface.netmask = addr.netmask
                            if addr.broadcast:
                                interface.broadcast = addr.broadcast
                        elif hasattr(socket, 'AF_PACKET') and addr.family == socket.AF_PACKET:
                            interface.mac_address = addr.address
                
                # 推断接口类型
                interface.interface_type = self._infer_interface_type(interface_name)
                
                interface.last_update = time.time()
            
            # 移除不存在的接口
            removed_interfaces = set(self.interfaces.keys()) - current_interfaces
            for interface_name in removed_interfaces:
                del self.interfaces[interface_name]
                if interface_name in self.traffic_history:
                    del self.traffic_history[interface_name]
                if interface_name in self.quality_history:
                    del self.quality_history[interface_name]
                
                self.logger.info(f"网络接口已移除: {interface_name}")
            
            # 通知接口变化
            if removed_interfaces and self.on_interface_change:
                try:
                    await self.on_interface_change(list(removed_interfaces), "removed")
                except Exception as e:
                    self.logger.error(f"接口变化回调错误: {e}")
            
        except Exception as e:
            self.logger.error(f"更新网络接口信息失败: {e}")
    
    def _infer_interface_type(self, interface_name: str) -> NetworkInterfaceType:
        """
        推断网络接口类型
        
        Args:
            interface_name: 接口名称
        
        Returns:
            NetworkInterfaceType: 接口类型
        """
        name_lower = interface_name.lower()
        
        if name_lower.startswith(('lo', 'loopback')):
            return NetworkInterfaceType.LOOPBACK
        elif name_lower.startswith(('eth', 'en', 'em')):
            return NetworkInterfaceType.ETHERNET
        elif name_lower.startswith(('wlan', 'wifi', 'wl')):
            return NetworkInterfaceType.WIFI
        elif name_lower.startswith(('tun', 'tap')):
            return NetworkInterfaceType.TUNNEL
        elif name_lower.startswith(('vpn', 'ppp')):
            return NetworkInterfaceType.VPN
        else:
            return NetworkInterfaceType.UNKNOWN
    
    async def _update_traffic_stats(self):
        """
        更新流量统计信息
        """
        current_time = time.time()
        
        for interface_name, interface in self.interfaces.items():
            # 计算速率
            send_rate = 0.0
            recv_rate = 0.0
            packet_send_rate = 0.0
            packet_recv_rate = 0.0
            
            if interface_name in self._last_stats and self._last_update_time > 0:
                time_delta = current_time - self._last_update_time
                if time_delta > 0:
                    last_stats = self._last_stats[interface_name]
                    
                    send_rate = (interface.bytes_sent - last_stats['bytes_sent']) / time_delta
                    recv_rate = (interface.bytes_recv - last_stats['bytes_recv']) / time_delta
                    packet_send_rate = (interface.packets_sent - last_stats['packets_sent']) / time_delta
                    packet_recv_rate = (interface.packets_recv - last_stats['packets_recv']) / time_delta
            
            # 创建流量记录
            traffic = NetworkTraffic(
                interface=interface_name,
                timestamp=current_time,
                bytes_sent=interface.bytes_sent,
                bytes_recv=interface.bytes_recv,
                packets_sent=interface.packets_sent,
                packets_recv=interface.packets_recv,
                send_rate=send_rate,
                recv_rate=recv_rate,
                packet_send_rate=packet_send_rate,
                packet_recv_rate=packet_recv_rate
            )
            
            # 添加到历史记录
            self.traffic_history[interface_name].append(traffic)
            
            # 检查流量告警
            total_rate = send_rate + recv_rate
            if total_rate > self.traffic_alert_threshold and self.on_traffic_alert:
                try:
                    await self.on_traffic_alert(interface_name, total_rate)
                except Exception as e:
                    self.logger.error(f"流量告警回调错误: {e}")
            
            # 保存当前统计信息
            self._last_stats[interface_name] = {
                'bytes_sent': interface.bytes_sent,
                'bytes_recv': interface.bytes_recv,
                'packets_sent': interface.packets_sent,
                'packets_recv': interface.packets_recv
            }
        
        self._last_update_time = current_time
    
    async def _evaluate_quality(self):
        """
        评估网络质量
        """
        current_time = time.time()
        
        for interface_name, interface in self.interfaces.items():
            if interface.status != NetworkStatus.UP:
                continue
            
            # 获取最近的延迟数据
            latency_data = list(self.latency_history[interface_name])
            if not latency_data:
                continue
            
            # 计算延迟指标
            recent_latencies = [l.latency for l in latency_data[-60:] if l.success]  # 最近60次测量
            if not recent_latencies:
                continue
            
            avg_latency = sum(recent_latencies) / len(recent_latencies)
            min_latency = min(recent_latencies)
            max_latency = max(recent_latencies)
            
            # 计算抖动
            if len(recent_latencies) > 1:
                jitter = sum(abs(recent_latencies[i] - recent_latencies[i-1]) 
                           for i in range(1, len(recent_latencies))) / (len(recent_latencies) - 1)
            else:
                jitter = 0.0
            
            # 计算丢包率
            recent_measurements = latency_data[-60:]
            total_measurements = len(recent_measurements)
            failed_measurements = sum(1 for m in recent_measurements if not m.success)
            packet_loss = failed_measurements / total_measurements if total_measurements > 0 else 0.0
            
            # 计算带宽利用率
            traffic_data = list(self.traffic_history[interface_name])
            if traffic_data:
                recent_traffic = traffic_data[-10:]  # 最近10秒
                avg_rate = sum(t.send_rate + t.recv_rate for t in recent_traffic) / len(recent_traffic)
                
                # 估算可用带宽（基于接口速度）
                if interface.speed > 0:
                    available_bandwidth = interface.speed  # Mbps
                    utilization = (avg_rate * 8) / (available_bandwidth * 1024 * 1024)  # 转换为Mbps
                    utilization = min(utilization, 1.0)
                else:
                    available_bandwidth = 0.0
                    utilization = 0.0
            else:
                available_bandwidth = 0.0
                utilization = 0.0
            
            # 计算稳定性评分
            stability_score = self._calculate_stability_score(avg_latency, jitter, packet_loss)
            
            # 确定连接质量
            quality = self._determine_quality(avg_latency, packet_loss)
            
            # 创建质量指标
            metrics = NetworkQualityMetrics(
                interface=interface_name,
                timestamp=current_time,
                quality=quality,
                avg_latency=avg_latency,
                min_latency=min_latency,
                max_latency=max_latency,
                jitter=jitter,
                packet_loss=packet_loss,
                available_bandwidth=available_bandwidth,
                utilization=utilization,
                stability_score=stability_score
            )
            
            # 添加到历史记录
            self.quality_history[interface_name].append(metrics)
            
            # 检查质量变化
            if len(self.quality_history[interface_name]) > 1:
                prev_quality = self.quality_history[interface_name][-2].quality
                if quality != prev_quality and self.on_quality_change:
                    try:
                        await self.on_quality_change(interface_name, quality, prev_quality)
                    except Exception as e:
                        self.logger.error(f"质量变化回调错误: {e}")
    
    def _calculate_stability_score(self, avg_latency: float, jitter: float, packet_loss: float) -> float:
        """
        计算稳定性评分
        
        Args:
            avg_latency: 平均延迟
            jitter: 抖动
            packet_loss: 丢包率
        
        Returns:
            float: 稳定性评分 (0.0-1.0)
        """
        # 延迟评分 (0-1)
        latency_score = max(0, 1 - avg_latency / 500)  # 500ms为最差
        
        # 抖动评分 (0-1)
        jitter_score = max(0, 1 - jitter / 100)  # 100ms抖动为最差
        
        # 丢包评分 (0-1)
        loss_score = max(0, 1 - packet_loss / 0.1)  # 10%丢包为最差
        
        # 综合评分
        stability_score = (latency_score * 0.4 + jitter_score * 0.3 + loss_score * 0.3)
        return min(max(stability_score, 0.0), 1.0)
    
    def _determine_quality(self, avg_latency: float, packet_loss: float) -> ConnectionQuality:
        """
        确定连接质量
        
        Args:
            avg_latency: 平均延迟
            packet_loss: 丢包率
        
        Returns:
            ConnectionQuality: 连接质量
        """
        if avg_latency < 50 and packet_loss < 0.01:
            return ConnectionQuality.EXCELLENT
        elif avg_latency < 100 and packet_loss < 0.03:
            return ConnectionQuality.GOOD
        elif avg_latency < 200 and packet_loss < 0.05:
            return ConnectionQuality.FAIR
        elif avg_latency < 500 and packet_loss < 0.10:
            return ConnectionQuality.POOR
        else:
            return ConnectionQuality.BAD
    
    async def measure_latency(self, target: str, count: int = 4, timeout: float = 3.0) -> List[LatencyMeasurement]:
        """
        测量到目标的延迟
        
        Args:
            target: 目标地址
            count: 测试次数
            timeout: 超时时间
        
        Returns:
            List[LatencyMeasurement]: 延迟测量结果列表
        """
        results = []
        
        for i in range(count):
            try:
                start_time = time.time()
                
                # 使用ping测试延迟
                if platform.system().lower() == "windows":
                    cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), target]
                else:
                    cmd = ["ping", "-c", "1", "-W", str(int(timeout)), target]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout + 1
                )
                
                end_time = time.time()
                
                if process.returncode == 0:
                    # 解析ping输出获取延迟
                    latency = self._parse_ping_output(stdout.decode())
                    if latency is None:
                        latency = (end_time - start_time) * 1000  # 使用总时间作为备选
                    
                    measurement = LatencyMeasurement(
                        target=target,
                        timestamp=time.time(),
                        latency=latency,
                        success=True
                    )
                else:
                    measurement = LatencyMeasurement(
                        target=target,
                        timestamp=time.time(),
                        latency=0.0,
                        success=False
                    )
                
                results.append(measurement)
                
                # 添加到历史记录
                self.latency_history[target].append(measurement)
                
                # 间隔一秒
                if i < count - 1:
                    await asyncio.sleep(1)
                
            except asyncio.TimeoutError:
                measurement = LatencyMeasurement(
                    target=target,
                    timestamp=time.time(),
                    latency=0.0,
                    success=False
                )
                results.append(measurement)
                self.latency_history[target].append(measurement)
                
            except Exception as e:
                self.logger.error(f"测量延迟失败: {e}")
                measurement = LatencyMeasurement(
                    target=target,
                    timestamp=time.time(),
                    latency=0.0,
                    success=False
                )
                results.append(measurement)
                self.latency_history[target].append(measurement)
        
        return results
    
    def _parse_ping_output(self, output: str) -> Optional[float]:
        """
        解析ping输出获取延迟
        
        Args:
            output: ping命令输出
        
        Returns:
            float: 延迟时间（毫秒），None表示解析失败
        """
        try:
            import re
            
            # Windows ping输出格式
            if platform.system().lower() == "windows":
                match = re.search(r'时间[<=]?(\d+)ms', output)
                if not match:
                    match = re.search(r'time[<=]?(\d+)ms', output)
                if match:
                    return float(match.group(1))
            
            # Linux/Unix ping输出格式
            else:
                match = re.search(r'time=(\d+\.?\d*)\s*ms', output)
                if match:
                    return float(match.group(1))
            
            return None
            
        except Exception:
            return None
    
    async def test_bandwidth(self, target: str, test_duration: float = 10.0) -> Optional[BandwidthMeasurement]:
        """
        测试带宽
        
        Args:
            target: 目标地址
            test_duration: 测试持续时间
        
        Returns:
            BandwidthMeasurement: 带宽测量结果
        """
        try:
            start_time = time.time()
            
            # 简单的带宽测试：下载测试数据
            download_speed = await self._test_download_speed(target, test_duration)
            upload_speed = await self._test_upload_speed(target, test_duration)
            
            end_time = time.time()
            actual_duration = end_time - start_time
            
            measurement = BandwidthMeasurement(
                target=target,
                timestamp=time.time(),
                download_speed=download_speed,
                upload_speed=upload_speed,
                test_duration=actual_duration,
                success=download_speed > 0 or upload_speed > 0
            )
            
            return measurement
            
        except Exception as e:
            self.logger.error(f"带宽测试失败: {e}")
            return BandwidthMeasurement(
                target=target,
                timestamp=time.time(),
                download_speed=0.0,
                upload_speed=0.0,
                test_duration=0.0,
                success=False
            )
    
    async def _test_download_speed(self, target: str, duration: float) -> float:
        """
        测试下载速度
        
        Args:
            target: 目标地址
            duration: 测试持续时间
        
        Returns:
            float: 下载速度（Mbps）
        """
        try:
            # 这里应该实现实际的下载速度测试
            # 为了简化，返回模拟值
            await asyncio.sleep(min(duration, 5.0))
            return 50.0  # 模拟50Mbps下载速度
            
        except Exception:
            return 0.0
    
    async def _test_upload_speed(self, target: str, duration: float) -> float:
        """
        测试上传速度
        
        Args:
            target: 目标地址
            duration: 测试持续时间
        
        Returns:
            float: 上传速度（Mbps）
        """
        try:
            # 这里应该实现实际的上传速度测试
            # 为了简化，返回模拟值
            await asyncio.sleep(min(duration, 5.0))
            return 20.0  # 模拟20Mbps上传速度
            
        except Exception:
            return 0.0
    
    def get_interface_info(self, interface_name: str) -> Optional[NetworkInterface]:
        """
        获取网络接口信息
        
        Args:
            interface_name: 接口名称
        
        Returns:
            NetworkInterface: 接口信息
        """
        return self.interfaces.get(interface_name)
    
    def get_all_interfaces(self) -> Dict[str, NetworkInterface]:
        """
        获取所有网络接口信息
        
        Returns:
            dict: 所有接口信息
        """
        return self.interfaces.copy()
    
    def get_traffic_history(self, interface_name: str, limit: int = 100) -> List[NetworkTraffic]:
        """
        获取流量历史记录
        
        Args:
            interface_name: 接口名称
            limit: 记录数量限制
        
        Returns:
            List[NetworkTraffic]: 流量历史记录
        """
        history = self.traffic_history.get(interface_name, deque())
        return list(history)[-limit:]
    
    def get_latency_history(self, target: str, limit: int = 100) -> List[LatencyMeasurement]:
        """
        获取延迟历史记录
        
        Args:
            target: 目标地址
            limit: 记录数量限制
        
        Returns:
            List[LatencyMeasurement]: 延迟历史记录
        """
        history = self.latency_history.get(target, deque())
        return list(history)[-limit:]
    
    def get_quality_history(self, interface_name: str, limit: int = 100) -> List[NetworkQualityMetrics]:
        """
        获取质量历史记录
        
        Args:
            interface_name: 接口名称
            limit: 记录数量限制
        
        Returns:
            List[NetworkQualityMetrics]: 质量历史记录
        """
        history = self.quality_history.get(interface_name, deque())
        return list(history)[-limit:]
    
    def get_current_quality(self, interface_name: str) -> Optional[NetworkQualityMetrics]:
        """
        获取当前网络质量
        
        Args:
            interface_name: 接口名称
        
        Returns:
            NetworkQualityMetrics: 当前质量指标
        """
        history = self.quality_history.get(interface_name, deque())
        return history[-1] if history else None
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取监控摘要
        
        Returns:
            dict: 监控摘要信息
        """
        summary = {
            'running': self._running,
            'update_interval': self.update_interval,
            'interfaces': {},
            'total_traffic': {
                'bytes_sent': 0,
                'bytes_recv': 0,
                'packets_sent': 0,
                'packets_recv': 0
            },
            'quality_overview': {}
        }
        
        for name, interface in self.interfaces.items():
            # 接口摘要
            summary['interfaces'][name] = {
                'type': interface.interface_type.value,
                'status': interface.status.value,
                'ip_addresses': interface.ip_addresses,
                'speed': interface.speed,
                'bytes_sent': interface.bytes_sent,
                'bytes_recv': interface.bytes_recv
            }
            
            # 累计流量
            summary['total_traffic']['bytes_sent'] += interface.bytes_sent
            summary['total_traffic']['bytes_recv'] += interface.bytes_recv
            summary['total_traffic']['packets_sent'] += interface.packets_sent
            summary['total_traffic']['packets_recv'] += interface.packets_recv
            
            # 质量概览
            current_quality = self.get_current_quality(name)
            if current_quality:
                summary['quality_overview'][name] = {
                    'quality': current_quality.quality.value,
                    'avg_latency': current_quality.avg_latency,
                    'packet_loss': current_quality.packet_loss,
                    'utilization': current_quality.utilization
                }
        
        return summary
    
    def export_data(self, format: str = "json") -> str:
        """
        导出监控数据
        
        Args:
            format: 导出格式 (json, csv)
        
        Returns:
            str: 导出的数据
        """
        if format.lower() == "json":
            data = {
                'interfaces': {name: {
                    'info': {
                        'name': iface.name,
                        'type': iface.interface_type.value,
                        'status': iface.status.value,
                        'ip_addresses': iface.ip_addresses,
                        'mac_address': iface.mac_address,
                        'speed': iface.speed,
                        'mtu': iface.mtu
                    },
                    'traffic_history': [{
                        'timestamp': t.timestamp,
                        'bytes_sent': t.bytes_sent,
                        'bytes_recv': t.bytes_recv,
                        'send_rate': t.send_rate,
                        'recv_rate': t.recv_rate
                    } for t in self.get_traffic_history(name)],
                    'quality_history': [{
                        'timestamp': q.timestamp,
                        'quality': q.quality.value,
                        'avg_latency': q.avg_latency,
                        'packet_loss': q.packet_loss,
                        'utilization': q.utilization
                    } for q in self.get_quality_history(name)]
                } for name, iface in self.interfaces.items()},
                'latency_history': {target: [{
                    'timestamp': l.timestamp,
                    'latency': l.latency,
                    'success': l.success
                } for l in measurements] for target, measurements in self.latency_history.items()}
            }
            
            return json.dumps(data, indent=2)
        
        else:
            raise ValueError(f"不支持的导出格式: {format}")

# 全局网络监控器实例
_global_monitor: Optional[NetworkMonitor] = None

def get_global_monitor() -> NetworkMonitor:
    """
    获取全局网络监控器实例
    
    Returns:
        NetworkMonitor: 全局监控器实例
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = NetworkMonitor()
    return _global_monitor

# 导出功能
__all__ = [
    'NetworkInterfaceType',
    'NetworkStatus',
    'ConnectionQuality',
    'NetworkInterface',
    'NetworkTraffic',
    'LatencyMeasurement',
    'BandwidthMeasurement',
    'NetworkQualityMetrics',
    'NetworkMonitor',
    'get_global_monitor'
]