#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能监控模块

提供系统性能监控和网络监控功能：
- CPU、内存、磁盘使用率监控
- 网络流量监控
- 连接数统计
- 性能指标收集
- 告警功能
"""

import time
import threading
import psutil
import socket
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SystemMetrics:
    """系统指标数据类"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_percent': self.disk_percent,
            'network_bytes_sent': self.network_bytes_sent,
            'network_bytes_recv': self.network_bytes_recv,
            'active_connections': self.active_connections
        }


@dataclass
class NetworkMetrics:
    """网络指标数据类"""
    timestamp: float
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    connections_count: int
    bandwidth_usage: float
    latency: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'bytes_sent': self.bytes_sent,
            'bytes_recv': self.bytes_recv,
            'packets_sent': self.packets_sent,
            'packets_recv': self.packets_recv,
            'connections_count': self.connections_count,
            'bandwidth_usage': self.bandwidth_usage,
            'latency': self.latency
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, 
                 interval: float = 1.0,
                 history_size: int = 1000,
                 alert_thresholds: Optional[Dict[str, float]] = None):
        """
        初始化性能监控器
        
        Args:
            interval: 监控间隔（秒）
            history_size: 历史数据保存数量
            alert_thresholds: 告警阈值配置
        """
        self.interval = interval
        self.history_size = history_size
        self.alert_thresholds = alert_thresholds or {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0
        }
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._metrics_history: deque = deque(maxlen=history_size)
        self._alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self._last_network_stats = None
        
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """添加告警回调函数"""
        self._alert_callbacks.append(callback)
        
    def remove_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """移除告警回调函数"""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
            
    def start(self):
        """开始监控"""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            
    def get_current_metrics(self) -> SystemMetrics:
        """获取当前系统指标"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # 网络统计
            network_stats = psutil.net_io_counters()
            
            # 活跃连接数
            try:
                connections = psutil.net_connections()
                active_connections = len([c for c in connections if c.status == 'ESTABLISHED'])
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                active_connections = 0
                
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_bytes_sent=network_stats.bytes_sent,
                network_bytes_recv=network_stats.bytes_recv,
                active_connections=active_connections
            )
            
        except Exception as e:
            # 如果获取指标失败，返回默认值
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                active_connections=0
            )
            
    def get_metrics_history(self, 
                           start_time: Optional[float] = None,
                           end_time: Optional[float] = None) -> List[SystemMetrics]:
        """获取历史指标数据"""
        metrics = list(self._metrics_history)
        
        if start_time is not None:
            metrics = [m for m in metrics if m.timestamp >= start_time]
            
        if end_time is not None:
            metrics = [m for m in metrics if m.timestamp <= end_time]
            
        return metrics
        
    def get_average_metrics(self, duration: int = 300) -> Optional[Dict[str, float]]:
        """获取指定时间段内的平均指标"""
        end_time = time.time()
        start_time = end_time - duration
        
        metrics = self.get_metrics_history(start_time, end_time)
        if not metrics:
            return None
            
        total_cpu = sum(m.cpu_percent for m in metrics)
        total_memory = sum(m.memory_percent for m in metrics)
        total_disk = sum(m.disk_percent for m in metrics)
        count = len(metrics)
        
        return {
            'cpu_percent': total_cpu / count,
            'memory_percent': total_memory / count,
            'disk_percent': total_disk / count,
            'sample_count': count
        }
        
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                metrics = self.get_current_metrics()
                self._metrics_history.append(metrics)
                
                # 检查告警条件
                self._check_alerts(metrics)
                
                time.sleep(self.interval)
                
            except Exception as e:
                # 监控过程中出现异常，记录但不中断监控
                print(f"监控异常: {e}")
                time.sleep(self.interval)
                
    def _check_alerts(self, metrics: SystemMetrics):
        """检查告警条件"""
        alerts = []
        
        # CPU 告警
        if metrics.cpu_percent > self.alert_thresholds.get('cpu_percent', 80.0):
            alerts.append({
                'type': 'cpu_high',
                'message': f'CPU 使用率过高: {metrics.cpu_percent:.1f}%',
                'value': metrics.cpu_percent,
                'threshold': self.alert_thresholds['cpu_percent']
            })
            
        # 内存告警
        if metrics.memory_percent > self.alert_thresholds.get('memory_percent', 85.0):
            alerts.append({
                'type': 'memory_high',
                'message': f'内存使用率过高: {metrics.memory_percent:.1f}%',
                'value': metrics.memory_percent,
                'threshold': self.alert_thresholds['memory_percent']
            })
            
        # 磁盘告警
        if metrics.disk_percent > self.alert_thresholds.get('disk_percent', 90.0):
            alerts.append({
                'type': 'disk_high',
                'message': f'磁盘使用率过高: {metrics.disk_percent:.1f}%',
                'value': metrics.disk_percent,
                'threshold': self.alert_thresholds['disk_percent']
            })
            
        # 触发告警回调
        for alert in alerts:
            for callback in self._alert_callbacks:
                try:
                    callback(alert['type'], alert)
                except Exception as e:
                    print(f"告警回调异常: {e}")


class NetworkMonitor:
    """网络监控器"""
    
    def __init__(self, 
                 interval: float = 1.0,
                 history_size: int = 1000,
                 bandwidth_limit: Optional[float] = None):
        """
        初始化网络监控器
        
        Args:
            interval: 监控间隔（秒）
            history_size: 历史数据保存数量
            bandwidth_limit: 带宽限制（字节/秒）
        """
        self.interval = interval
        self.history_size = history_size
        self.bandwidth_limit = bandwidth_limit
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._metrics_history: deque = deque(maxlen=history_size)
        self._connection_stats: Dict[str, Any] = defaultdict(int)
        self._last_network_stats = None
        self._alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """添加告警回调函数"""
        self._alert_callbacks.append(callback)
        
    def start(self):
        """开始监控"""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            
    def get_current_metrics(self) -> NetworkMetrics:
        """获取当前网络指标"""
        try:
            # 网络 I/O 统计
            network_stats = psutil.net_io_counters()
            
            # 计算带宽使用率
            bandwidth_usage = 0.0
            if self._last_network_stats and self.bandwidth_limit:
                time_diff = time.time() - self._last_network_stats['timestamp']
                if time_diff > 0:
                    bytes_diff = (network_stats.bytes_sent + network_stats.bytes_recv) - \
                                (self._last_network_stats['bytes_sent'] + self._last_network_stats['bytes_recv'])
                    current_bandwidth = bytes_diff / time_diff
                    bandwidth_usage = (current_bandwidth / self.bandwidth_limit) * 100
                    
            # 连接数统计
            try:
                connections = psutil.net_connections()
                connections_count = len(connections)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                connections_count = 0
                
            # 简单的延迟测试（ping localhost）
            latency = self._measure_latency()
            
            # 更新最后的网络统计
            self._last_network_stats = {
                'timestamp': time.time(),
                'bytes_sent': network_stats.bytes_sent,
                'bytes_recv': network_stats.bytes_recv
            }
            
            return NetworkMetrics(
                timestamp=time.time(),
                bytes_sent=network_stats.bytes_sent,
                bytes_recv=network_stats.bytes_recv,
                packets_sent=network_stats.packets_sent,
                packets_recv=network_stats.packets_recv,
                connections_count=connections_count,
                bandwidth_usage=bandwidth_usage,
                latency=latency
            )
            
        except Exception as e:
            return NetworkMetrics(
                timestamp=time.time(),
                bytes_sent=0,
                bytes_recv=0,
                packets_sent=0,
                packets_recv=0,
                connections_count=0,
                bandwidth_usage=0.0,
                latency=0.0
            )
            
    def get_connection_stats(self) -> Dict[str, int]:
        """获取连接统计信息"""
        try:
            connections = psutil.net_connections()
            stats = defaultdict(int)
            
            for conn in connections:
                stats[conn.status] += 1
                
            return dict(stats)
            
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return {}
            
    def get_bandwidth_usage(self, duration: int = 60) -> Dict[str, float]:
        """获取带宽使用情况"""
        end_time = time.time()
        start_time = end_time - duration
        
        metrics = [m for m in self._metrics_history 
                  if start_time <= m.timestamp <= end_time]
                  
        if len(metrics) < 2:
            return {'upload': 0.0, 'download': 0.0, 'total': 0.0}
            
        first_metric = metrics[0]
        last_metric = metrics[-1]
        
        time_diff = last_metric.timestamp - first_metric.timestamp
        if time_diff <= 0:
            return {'upload': 0.0, 'download': 0.0, 'total': 0.0}
            
        upload_bytes = last_metric.bytes_sent - first_metric.bytes_sent
        download_bytes = last_metric.bytes_recv - first_metric.bytes_recv
        
        upload_rate = upload_bytes / time_diff
        download_rate = download_bytes / time_diff
        total_rate = upload_rate + download_rate
        
        return {
            'upload': upload_rate,
            'download': download_rate,
            'total': total_rate
        }
        
    def _measure_latency(self) -> float:
        """测量网络延迟"""
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex(('127.0.0.1', 80))
            sock.close()
            end_time = time.time()
            
            if result == 0:
                return (end_time - start_time) * 1000  # 转换为毫秒
            else:
                return 0.0
                
        except Exception:
            return 0.0
            
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                metrics = self.get_current_metrics()
                self._metrics_history.append(metrics)
                
                # 检查带宽告警
                if (self.bandwidth_limit and 
                    metrics.bandwidth_usage > 90.0):
                    
                    alert = {
                        'type': 'bandwidth_high',
                        'message': f'带宽使用率过高: {metrics.bandwidth_usage:.1f}%',
                        'value': metrics.bandwidth_usage,
                        'threshold': 90.0
                    }
                    
                    for callback in self._alert_callbacks:
                        try:
                            callback(alert['type'], alert)
                        except Exception as e:
                            print(f"网络告警回调异常: {e}")
                            
                time.sleep(self.interval)
                
            except Exception as e:
                print(f"网络监控异常: {e}")
                time.sleep(self.interval)


# 全局监控器实例
_performance_monitor: Optional[PerformanceMonitor] = None
_network_monitor: Optional[NetworkMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def get_network_monitor() -> NetworkMonitor:
    """获取全局网络监控器实例"""
    global _network_monitor
    if _network_monitor is None:
        _network_monitor = NetworkMonitor()
    return _network_monitor


def start_monitoring(performance: bool = True, network: bool = True):
    """启动监控"""
    if performance:
        get_performance_monitor().start()
    if network:
        get_network_monitor().start()


def stop_monitoring():
    """停止所有监控"""
    global _performance_monitor, _network_monitor
    
    if _performance_monitor:
        _performance_monitor.stop()
    if _network_monitor:
        _network_monitor.stop()


if __name__ == '__main__':
    # 测试代码
    def alert_handler(alert_type: str, alert_data: Dict[str, Any]):
        print(f"告警: {alert_type} - {alert_data['message']}")
    
    # 创建监控器
    perf_monitor = PerformanceMonitor(interval=2.0)
    net_monitor = NetworkMonitor(interval=2.0)
    
    # 添加告警回调
    perf_monitor.add_alert_callback(alert_handler)
    net_monitor.add_alert_callback(alert_handler)
    
    # 启动监控
    perf_monitor.start()
    net_monitor.start()
    
    try:
        # 运行 30 秒
        time.sleep(30)
        
        # 获取当前指标
        print("\n=== 当前系统指标 ===")
        current_metrics = perf_monitor.get_current_metrics()
        print(f"CPU: {current_metrics.cpu_percent:.1f}%")
        print(f"内存: {current_metrics.memory_percent:.1f}%")
        print(f"磁盘: {current_metrics.disk_percent:.1f}%")
        print(f"活跃连接: {current_metrics.active_connections}")
        
        print("\n=== 当前网络指标 ===")
        net_metrics = net_monitor.get_current_metrics()
        print(f"发送字节: {net_metrics.bytes_sent:,}")
        print(f"接收字节: {net_metrics.bytes_recv:,}")
        print(f"连接数: {net_metrics.connections_count}")
        print(f"延迟: {net_metrics.latency:.2f}ms")
        
        print("\n=== 平均指标 (最近5分钟) ===")
        avg_metrics = perf_monitor.get_average_metrics(300)
        if avg_metrics:
            print(f"平均 CPU: {avg_metrics['cpu_percent']:.1f}%")
            print(f"平均内存: {avg_metrics['memory_percent']:.1f}%")
            print(f"平均磁盘: {avg_metrics['disk_percent']:.1f}%")
            
    except KeyboardInterrupt:
        print("\n停止监控...")
    finally:
        perf_monitor.stop()
        net_monitor.stop()
        print("监控已停止")