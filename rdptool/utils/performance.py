#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能监控工具模块

提供系统性能监控和分析功能：
- CPU使用率监控
- 内存使用监控
- 网络流量监控
- 函数执行时间分析
- 性能统计和报告
"""

import time
import psutil
import threading
import functools
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
import statistics
from contextlib import contextmanager

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used: int  # 字节
    memory_available: int  # 字节
    network_sent: int  # 字节
    network_recv: int  # 字节
    disk_read: int  # 字节
    disk_write: int  # 字节
    process_count: int
    thread_count: int

@dataclass
class FunctionMetrics:
    """函数性能指标"""
    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    last_call_time: Optional[float] = None
    error_count: int = 0
    call_times: deque = field(default_factory=lambda: deque(maxlen=1000))

@dataclass
class NetworkMetrics:
    """网络性能指标"""
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    connections: int = 0
    bandwidth_usage: float = 0.0  # 百分比
    latency: float = 0.0  # 毫秒

class PerformanceMonitor:
    """
    性能监控器
    
    监控系统资源使用情况和应用性能
    """
    
    def __init__(self, sample_interval: float = 1.0, max_samples: int = 3600):
        """
        初始化性能监控器
        
        Args:
            sample_interval: 采样间隔（秒）
            max_samples: 最大样本数量
        """
        self.sample_interval = sample_interval
        self.max_samples = max_samples
        self.metrics_history: deque = deque(maxlen=max_samples)
        self.function_metrics: Dict[str, FunctionMetrics] = {}
        self.network_metrics = NetworkMetrics()
        
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()
        
        # 初始网络统计
        self._last_network_stats = psutil.net_io_counters()
        self._last_disk_stats = psutil.disk_io_counters()
        self._last_sample_time = time.time()
    
    def start_monitoring(self):
        """开始性能监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止性能监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                with self.lock:
                    self.metrics_history.append(metrics)
                time.sleep(self.sample_interval)
            except Exception as e:
                print(f"性能监控错误: {e}")
                time.sleep(self.sample_interval)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        current_time = time.time()
        
        # CPU和内存
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # 网络统计
        current_network = psutil.net_io_counters()
        network_sent = current_network.bytes_sent - self._last_network_stats.bytes_sent
        network_recv = current_network.bytes_recv - self._last_network_stats.bytes_recv
        
        # 磁盘统计
        current_disk = psutil.disk_io_counters()
        if current_disk and self._last_disk_stats:
            disk_read = current_disk.read_bytes - self._last_disk_stats.read_bytes
            disk_write = current_disk.write_bytes - self._last_disk_stats.write_bytes
        else:
            disk_read = disk_write = 0
        
        # 进程和线程数
        process_count = len(psutil.pids())
        current_process = psutil.Process()
        thread_count = current_process.num_threads()
        
        # 更新上次统计
        self._last_network_stats = current_network
        self._last_disk_stats = current_disk
        self._last_sample_time = current_time
        
        return PerformanceMetrics(
            timestamp=current_time,
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used=memory.used,
            memory_available=memory.available,
            network_sent=network_sent,
            network_recv=network_recv,
            disk_read=disk_read,
            disk_write=disk_write,
            process_count=process_count,
            thread_count=thread_count
        )
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """获取当前性能指标"""
        with self.lock:
            if self.metrics_history:
                return self.metrics_history[-1]
            return None
    
    def get_metrics_history(self, duration_seconds: Optional[int] = None) -> List[PerformanceMetrics]:
        """获取性能指标历史"""
        with self.lock:
            if duration_seconds is None:
                return list(self.metrics_history)
            
            cutoff_time = time.time() - duration_seconds
            return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_average_metrics(self, duration_seconds: Optional[int] = None) -> Dict[str, float]:
        """获取平均性能指标"""
        history = self.get_metrics_history(duration_seconds)
        if not history:
            return {}
        
        return {
            'avg_cpu_percent': statistics.mean(m.cpu_percent for m in history),
            'avg_memory_percent': statistics.mean(m.memory_percent for m in history),
            'avg_memory_used': statistics.mean(m.memory_used for m in history),
            'total_network_sent': sum(m.network_sent for m in history),
            'total_network_recv': sum(m.network_recv for m in history),
            'total_disk_read': sum(m.disk_read for m in history),
            'total_disk_write': sum(m.disk_write for m in history),
            'avg_process_count': statistics.mean(m.process_count for m in history),
            'avg_thread_count': statistics.mean(m.thread_count for m in history)
        }
    
    def record_function_call(self, function_name: str, execution_time: float, error: bool = False):
        """记录函数调用性能"""
        with self.lock:
            if function_name not in self.function_metrics:
                self.function_metrics[function_name] = FunctionMetrics(function_name)
            
            metrics = self.function_metrics[function_name]
            metrics.call_count += 1
            metrics.total_time += execution_time
            metrics.min_time = min(metrics.min_time, execution_time)
            metrics.max_time = max(metrics.max_time, execution_time)
            metrics.avg_time = metrics.total_time / metrics.call_count
            metrics.last_call_time = time.time()
            metrics.call_times.append(execution_time)
            
            if error:
                metrics.error_count += 1
    
    def get_function_metrics(self, function_name: Optional[str] = None) -> Dict[str, FunctionMetrics]:
        """获取函数性能指标"""
        with self.lock:
            if function_name:
                return {function_name: self.function_metrics.get(function_name)}
            return self.function_metrics.copy()
    
    def get_top_functions(self, metric: str = 'total_time', limit: int = 10) -> List[Tuple[str, FunctionMetrics]]:
        """获取性能排名前N的函数"""
        with self.lock:
            if metric == 'total_time':
                key_func = lambda item: item[1].total_time
            elif metric == 'avg_time':
                key_func = lambda item: item[1].avg_time
            elif metric == 'call_count':
                key_func = lambda item: item[1].call_count
            elif metric == 'error_count':
                key_func = lambda item: item[1].error_count
            else:
                raise ValueError(f"不支持的指标: {metric}")
            
            sorted_functions = sorted(self.function_metrics.items(), key=key_func, reverse=True)
            return sorted_functions[:limit]
    
    def reset_function_metrics(self):
        """重置函数性能指标"""
        with self.lock:
            self.function_metrics.clear()
    
    def export_metrics(self, filename: str, duration_seconds: Optional[int] = None):
        """导出性能指标到文件"""
        history = self.get_metrics_history(duration_seconds)
        function_metrics = self.get_function_metrics()
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'sample_interval': self.sample_interval,
            'metrics_count': len(history),
            'system_metrics': [
                {
                    'timestamp': m.timestamp,
                    'datetime': datetime.fromtimestamp(m.timestamp).isoformat(),
                    'cpu_percent': m.cpu_percent,
                    'memory_percent': m.memory_percent,
                    'memory_used_mb': m.memory_used / (1024 * 1024),
                    'memory_available_mb': m.memory_available / (1024 * 1024),
                    'network_sent_kb': m.network_sent / 1024,
                    'network_recv_kb': m.network_recv / 1024,
                    'disk_read_kb': m.disk_read / 1024,
                    'disk_write_kb': m.disk_write / 1024,
                    'process_count': m.process_count,
                    'thread_count': m.thread_count
                } for m in history
            ],
            'function_metrics': {
                name: {
                    'call_count': metrics.call_count,
                    'total_time': metrics.total_time,
                    'avg_time': metrics.avg_time,
                    'min_time': metrics.min_time if metrics.min_time != float('inf') else 0,
                    'max_time': metrics.max_time,
                    'error_count': metrics.error_count,
                    'error_rate': metrics.error_count / metrics.call_count if metrics.call_count > 0 else 0,
                    'last_call_time': metrics.last_call_time
                } for name, metrics in function_metrics.items()
            },
            'summary': self.get_average_metrics(duration_seconds)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

class FunctionProfiler:
    """
    函数性能分析器
    
    用于分析函数执行性能
    """
    
    def __init__(self, monitor: Optional[PerformanceMonitor] = None):
        self.monitor = monitor or PerformanceMonitor()
        self.active_calls: Dict[str, float] = {}
        self.lock = threading.RLock()
    
    def profile(self, func_name: Optional[str] = None):
        """函数性能分析装饰器"""
        def decorator(func: Callable) -> Callable:
            name = func_name or f"{func.__module__}.{func.__qualname__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                error_occurred = False
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_occurred = True
                    raise
                finally:
                    execution_time = time.time() - start_time
                    self.monitor.record_function_call(name, execution_time, error_occurred)
            
            return wrapper
        return decorator
    
    @contextmanager
    def profile_context(self, context_name: str):
        """上下文管理器形式的性能分析"""
        start_time = time.time()
        error_occurred = False
        
        try:
            yield
        except Exception:
            error_occurred = True
            raise
        finally:
            execution_time = time.time() - start_time
            self.monitor.record_function_call(context_name, execution_time, error_occurred)

class ResourceMonitor:
    """
    资源监控器
    
    监控特定资源的使用情况
    """
    
    def __init__(self):
        self.resource_usage: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        self.lock = threading.RLock()
    
    def record_resource_usage(self, resource_name: str, usage_value: float):
        """记录资源使用情况"""
        with self.lock:
            timestamp = time.time()
            self.resource_usage[resource_name].append((timestamp, usage_value))
            
            # 保持最近1小时的数据
            cutoff_time = timestamp - 3600
            self.resource_usage[resource_name] = [
                (t, v) for t, v in self.resource_usage[resource_name] if t >= cutoff_time
            ]
    
    def get_resource_stats(self, resource_name: str, duration_seconds: int = 3600) -> Dict[str, float]:
        """获取资源统计信息"""
        with self.lock:
            if resource_name not in self.resource_usage:
                return {}
            
            cutoff_time = time.time() - duration_seconds
            recent_data = [
                value for timestamp, value in self.resource_usage[resource_name]
                if timestamp >= cutoff_time
            ]
            
            if not recent_data:
                return {}
            
            return {
                'count': len(recent_data),
                'min': min(recent_data),
                'max': max(recent_data),
                'avg': statistics.mean(recent_data),
                'median': statistics.median(recent_data),
                'std_dev': statistics.stdev(recent_data) if len(recent_data) > 1 else 0.0,
                'current': recent_data[-1] if recent_data else 0.0
            }
    
    def get_all_resources(self) -> List[str]:
        """获取所有监控的资源名称"""
        with self.lock:
            return list(self.resource_usage.keys())

class PerformanceAlert:
    """
    性能告警器
    
    监控性能指标并触发告警
    """
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_callbacks: List[Callable] = []
        self.lock = threading.RLock()
    
    def add_alert_rule(self, rule_name: str, metric: str, threshold: float, 
                      comparison: str = 'greater', duration: int = 60):
        """
        添加告警规则
        
        Args:
            rule_name: 规则名称
            metric: 监控指标
            threshold: 阈值
            comparison: 比较方式 ('greater', 'less', 'equal')
            duration: 持续时间（秒）
        """
        with self.lock:
            self.alert_rules[rule_name] = {
                'metric': metric,
                'threshold': threshold,
                'comparison': comparison,
                'duration': duration,
                'triggered': False,
                'trigger_time': None
            }
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)
    
    def check_alerts(self):
        """检查告警条件"""
        current_metrics = self.monitor.get_current_metrics()
        if not current_metrics:
            return
        
        current_time = time.time()
        
        with self.lock:
            for rule_name, rule in self.alert_rules.items():
                metric_value = getattr(current_metrics, rule['metric'], None)
                if metric_value is None:
                    continue
                
                # 检查阈值条件
                condition_met = False
                if rule['comparison'] == 'greater':
                    condition_met = metric_value > rule['threshold']
                elif rule['comparison'] == 'less':
                    condition_met = metric_value < rule['threshold']
                elif rule['comparison'] == 'equal':
                    condition_met = abs(metric_value - rule['threshold']) < 0.001
                
                if condition_met:
                    if not rule['triggered']:
                        rule['trigger_time'] = current_time
                        rule['triggered'] = True
                    elif current_time - rule['trigger_time'] >= rule['duration']:
                        # 触发告警
                        alert_data = {
                            'rule_name': rule_name,
                            'metric': rule['metric'],
                            'current_value': metric_value,
                            'threshold': rule['threshold'],
                            'duration': current_time - rule['trigger_time']
                        }
                        
                        for callback in self.alert_callbacks:
                            try:
                                callback(rule_name, alert_data)
                            except Exception as e:
                                print(f"告警回调执行失败: {e}")
                else:
                    rule['triggered'] = False
                    rule['trigger_time'] = None

# 全局性能监控器实例
_global_monitor = None

def get_global_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
        _global_monitor.start_monitoring()
    return _global_monitor

def profile_function(func_name: Optional[str] = None):
    """函数性能分析装饰器（使用全局监控器）"""
    monitor = get_global_monitor()
    profiler = FunctionProfiler(monitor)
    return profiler.profile(func_name)

@contextmanager
def profile_context(context_name: str):
    """上下文性能分析（使用全局监控器）"""
    monitor = get_global_monitor()
    profiler = FunctionProfiler(monitor)
    with profiler.profile_context(context_name):
        yield

def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    return {
        'cpu_count': psutil.cpu_count(),
        'cpu_count_logical': psutil.cpu_count(logical=True),
        'memory_total': psutil.virtual_memory().total,
        'disk_usage': {p.mountpoint: psutil.disk_usage(p.mountpoint)._asdict() 
                      for p in psutil.disk_partitions()},
        'network_interfaces': {name: addrs for name, addrs in psutil.net_if_addrs().items()},
        'boot_time': psutil.boot_time(),
        'python_version': psutil.version_info
    }

# 导出功能
__all__ = [
    'PerformanceMetrics',
    'FunctionMetrics',
    'NetworkMetrics',
    'PerformanceMonitor',
    'FunctionProfiler',
    'ResourceMonitor',
    'PerformanceAlert',
    'get_global_monitor',
    'profile_function',
    'profile_context',
    'get_system_info'
]