#!/usr/bin/env python3
"""
Performance Optimization Module for TradingAgents GUI

This module provides comprehensive performance optimization features:
- Memory management and caching
- Asynchronous operations
- UI responsiveness optimization
- Data processing acceleration
- Resource monitoring and alerts

Author: TradingAgents GUI Team
Version: 1.0.0
"""

import asyncio
import threading
import time
import psutil
import gc
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass
import weakref
import functools
import concurrent.futures
from queue import Queue, Empty

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    cpu_usage: float
    memory_usage: float
    memory_available: float
    response_time: float
    cache_hit_rate: float
    active_threads: int
    queue_size: int
    timestamp: datetime

class MemoryManager:
    """Advanced memory management with caching and cleanup."""
    
    def __init__(self, max_cache_size: int = 1000, cache_ttl: int = 300):
        self.max_cache_size = max_cache_size
        self.cache_ttl = cache_ttl
        self.cache = {}
        self.cache_timestamps = {}
        self.access_counts = defaultdict(int)
        self.memory_threshold = 0.8  # 80% memory usage threshold
        
    def cache_data(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Cache data with automatic cleanup."""
        current_time = datetime.now()
        ttl = ttl or self.cache_ttl
        
        # Clean expired entries first
        self._cleanup_expired_cache()
        
        # Check memory usage
        if self._should_cleanup_memory():
            self._cleanup_lru_cache()
        
        # Add new entry
        self.cache[key] = data
        self.cache_timestamps[key] = current_time + timedelta(seconds=ttl)
        self.access_counts[key] = 1
        
        # Enforce size limit
        if len(self.cache) > self.max_cache_size:
            self._cleanup_lru_cache(int(self.max_cache_size * 0.1))  # Remove 10%
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Retrieve cached data."""
        if key not in self.cache:
            return None
            
        # Check if expired
        if datetime.now() > self.cache_timestamps[key]:
            self._remove_cache_entry(key)
            return None
        
        # Update access count
        self.access_counts[key] += 1
        return self.cache[key]
    
    def _cleanup_expired_cache(self) -> None:
        """Remove expired cache entries."""
        current_time = datetime.now()
        expired_keys = [
            key for key, expiry in self.cache_timestamps.items()
            if current_time > expiry
        ]
        
        for key in expired_keys:
            self._remove_cache_entry(key)
    
    def _cleanup_lru_cache(self, num_to_remove: Optional[int] = None) -> None:
        """Remove least recently used cache entries."""
        if not self.cache:
            return
            
        num_to_remove = num_to_remove or max(1, len(self.cache) // 10)
        
        # Sort by access count (ascending)
        sorted_keys = sorted(self.access_counts.items(), key=lambda x: x[1])
        keys_to_remove = [key for key, _ in sorted_keys[:num_to_remove]]
        
        for key in keys_to_remove:
            self._remove_cache_entry(key)
    
    def _remove_cache_entry(self, key: str) -> None:
        """Remove a single cache entry."""
        self.cache.pop(key, None)
        self.cache_timestamps.pop(key, None)
        self.access_counts.pop(key, None)
    
    def _should_cleanup_memory(self) -> bool:
        """Check if memory cleanup is needed."""
        memory_percent = psutil.virtual_memory().percent / 100
        return memory_percent > self.memory_threshold
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = sum(self.access_counts.values())
        cache_hits = len([count for count in self.access_counts.values() if count > 1])
        hit_rate = cache_hits / max(total_requests, 1)
        
        return {
            'cache_size': len(self.cache),
            'max_cache_size': self.max_cache_size,
            'hit_rate': hit_rate,
            'total_requests': total_requests,
            'memory_usage': psutil.virtual_memory().percent
        }
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
        self.cache_timestamps.clear()
        self.access_counts.clear()
        gc.collect()  # Force garbage collection

class AsyncTaskManager:
    """Manage asynchronous tasks for better UI responsiveness."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = weakref.WeakSet()
        self.task_queue = Queue()
        self.results_queue = Queue()
        self.is_running = True
        
        # Start background worker
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
    
    def submit_task(self, func: Callable, *args, callback: Optional[Callable] = None, **kwargs) -> None:
        """Submit a task for asynchronous execution."""
        task_id = id(func) + hash(str(args) + str(kwargs))
        task = {
            'id': task_id,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'callback': callback,
            'submitted_at': time.time()
        }
        
        self.task_queue.put(task)
    
    def _worker_loop(self) -> None:
        """Background worker loop."""
        while self.is_running:
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:  # Shutdown signal
                    break
                
                start_time = time.time()
                
                try:
                    # Execute task
                    result = task['func'](*task['args'], **task['kwargs'])
                    
                    # Store result
                    task_result = {
                        'id': task['id'],
                        'result': result,
                        'error': None,
                        'execution_time': time.time() - start_time,
                        'callback': task['callback']
                    }
                    
                    self.results_queue.put(task_result)
                    
                except Exception as e:
                    # Store error
                    task_result = {
                        'id': task['id'],
                        'result': None,
                        'error': str(e),
                        'execution_time': time.time() - start_time,
                        'callback': task['callback']
                    }
                    
                    self.results_queue.put(task_result)
                
                finally:
                    self.task_queue.task_done()
                    
            except Empty:
                continue
            except Exception as e:
                print(f"Worker loop error: {e}")
    
    def process_results(self) -> List[Dict[str, Any]]:
        """Process completed task results."""
        results = []
        
        while True:
            try:
                result = self.results_queue.get_nowait()
                results.append(result)
                
                # Execute callback if provided
                if result['callback'] and result['error'] is None:
                    try:
                        result['callback'](result['result'])
                    except Exception as e:
                        print(f"Callback error: {e}")
                        
            except Empty:
                break
        
        return results
    
    def get_queue_size(self) -> int:
        """Get current task queue size."""
        return self.task_queue.qsize()
    
    def shutdown(self) -> None:
        """Shutdown the task manager."""
        self.is_running = False
        self.task_queue.put(None)  # Shutdown signal
        self.worker_thread.join(timeout=5)
        self.executor.shutdown(wait=True)

class UIOptimizer:
    """Optimize UI responsiveness and rendering."""
    
    def __init__(self):
        self.update_intervals = {}
        self.last_updates = {}
        self.pending_updates = {}
        self.batch_size = 50  # Maximum updates per batch
        
    def throttle_update(self, widget_id: str, update_func: Callable, 
                       interval_ms: int = 100) -> bool:
        """Throttle UI updates to prevent overwhelming the interface."""
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check if enough time has passed
        if widget_id in self.last_updates:
            time_since_last = current_time - self.last_updates[widget_id]
            if time_since_last < interval_ms:
                # Store pending update
                self.pending_updates[widget_id] = update_func
                return False
        
        # Execute update
        try:
            update_func()
            self.last_updates[widget_id] = current_time
            self.pending_updates.pop(widget_id, None)
            return True
        except Exception as e:
            print(f"UI update error for {widget_id}: {e}")
            return False
    
    def batch_updates(self, updates: List[Callable]) -> None:
        """Batch multiple UI updates for better performance."""
        # Process updates in batches
        for i in range(0, len(updates), self.batch_size):
            batch = updates[i:i + self.batch_size]
            
            for update_func in batch:
                try:
                    update_func()
                except Exception as e:
                    print(f"Batch update error: {e}")
            
            # Small delay between batches to maintain responsiveness
            if i + self.batch_size < len(updates):
                time.sleep(0.001)  # 1ms delay
    
    def process_pending_updates(self) -> None:
        """Process all pending throttled updates."""
        current_time = time.time() * 1000
        
        for widget_id, update_func in list(self.pending_updates.items()):
            interval = self.update_intervals.get(widget_id, 100)
            last_update = self.last_updates.get(widget_id, 0)
            
            if current_time - last_update >= interval:
                try:
                    update_func()
                    self.last_updates[widget_id] = current_time
                    del self.pending_updates[widget_id]
                except Exception as e:
                    print(f"Pending update error for {widget_id}: {e}")

class DataProcessor:
    """Accelerate data processing operations."""
    
    def __init__(self):
        self.processing_cache = {}
        
    @functools.lru_cache(maxsize=128)
    def calculate_technical_indicators(self, prices_tuple: tuple, 
                                     indicator_type: str) -> Dict[str, float]:
        """Calculate technical indicators with caching."""
        prices = list(prices_tuple)
        
        if indicator_type == 'sma':
            return self._calculate_sma(prices)
        elif indicator_type == 'rsi':
            return self._calculate_rsi(prices)
        elif indicator_type == 'bollinger':
            return self._calculate_bollinger_bands(prices)
        else:
            return {}
    
    def _calculate_sma(self, prices: List[float], periods: List[int] = [20, 50]) -> Dict[str, float]:
        """Calculate Simple Moving Averages."""
        result = {}
        
        for period in periods:
            if len(prices) >= period:
                sma = sum(prices[-period:]) / period
                result[f'sma_{period}'] = sma
        
        return result
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Dict[str, float]:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return {'rsi': 50.0}  # Neutral RSI
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return {'rsi': 50.0}
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return {'rsi': 100.0}
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return {'rsi': rsi}
    
    def _calculate_bollinger_bands(self, prices: List[float], 
                                  period: int = 20, std_dev: float = 2) -> Dict[str, float]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            current_price = prices[-1] if prices else 0
            return {
                'bb_upper': current_price * 1.02,
                'bb_middle': current_price,
                'bb_lower': current_price * 0.98
            }
        
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period
        
        # Calculate standard deviation
        variance = sum((price - sma) ** 2 for price in recent_prices) / period
        std = variance ** 0.5
        
        return {
            'bb_upper': sma + (std_dev * std),
            'bb_middle': sma,
            'bb_lower': sma - (std_dev * std)
        }
    
    def process_market_data_batch(self, data_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple market data entries efficiently."""
        processed_data = []
        
        for data in data_batch:
            try:
                # Extract price history
                prices = data.get('price_history', [])
                if not prices:
                    continue
                
                # Calculate indicators
                prices_tuple = tuple(prices)
                sma_data = self.calculate_technical_indicators(prices_tuple, 'sma')
                rsi_data = self.calculate_technical_indicators(prices_tuple, 'rsi')
                bb_data = self.calculate_technical_indicators(prices_tuple, 'bollinger')
                
                # Combine all data
                processed_entry = {
                    **data,
                    'indicators': {
                        **sma_data,
                        **rsi_data,
                        **bb_data
                    },
                    'processed_at': datetime.now()
                }
                
                processed_data.append(processed_entry)
                
            except Exception as e:
                print(f"Error processing market data: {e}")
                continue
        
        return processed_data

class ResourceMonitor:
    """Monitor system resources and performance."""
    
    def __init__(self, alert_threshold: float = 0.8):
        self.alert_threshold = alert_threshold
        self.metrics_history = deque(maxlen=100)
        self.alerts = []
        
    def collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        metrics = PerformanceMetrics(
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            memory_available=memory.available / (1024**3),  # GB
            response_time=0.0,  # Will be updated by caller
            cache_hit_rate=0.0,  # Will be updated by caller
            active_threads=threading.active_count(),
            queue_size=0,  # Will be updated by caller
            timestamp=datetime.now()
        )
        
        self.metrics_history.append(metrics)
        self._check_alerts(metrics)
        
        return metrics
    
    def _check_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check for performance alerts."""
        alerts = []
        
        if metrics.cpu_usage > self.alert_threshold * 100:
            alerts.append(f"High CPU usage: {metrics.cpu_usage:.1f}%")
        
        if metrics.memory_usage > self.alert_threshold * 100:
            alerts.append(f"High memory usage: {metrics.memory_usage:.1f}%")
        
        if metrics.active_threads > 20:
            alerts.append(f"High thread count: {metrics.active_threads}")
        
        if alerts:
            self.alerts.extend(alerts)
            # Keep only recent alerts
            self.alerts = self.alerts[-10:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.metrics_history:
            return {}
        
        recent_metrics = list(self.metrics_history)[-10:]  # Last 10 measurements
        
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_threads = sum(m.active_threads for m in recent_metrics) / len(recent_metrics)
        
        return {
            'avg_cpu_usage': avg_cpu,
            'avg_memory_usage': avg_memory,
            'avg_active_threads': avg_threads,
            'current_alerts': self.alerts.copy(),
            'metrics_count': len(self.metrics_history)
        }
    
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()

class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.task_manager = AsyncTaskManager()
        self.ui_optimizer = UIOptimizer()
        self.data_processor = DataProcessor()
        self.resource_monitor = ResourceMonitor()
        
        self.optimization_enabled = True
        self.auto_cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        
    def optimize_data_operation(self, operation_key: str, 
                              operation_func: Callable, *args, **kwargs) -> Any:
        """Optimize a data operation with caching and async execution."""
        # Check cache first
        cached_result = self.memory_manager.get_cached_data(operation_key)
        if cached_result is not None:
            return cached_result
        
        # Execute operation
        start_time = time.time()
        result = operation_func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        # Cache result if operation took significant time
        if execution_time > 0.1:  # 100ms threshold
            self.memory_manager.cache_data(operation_key, result)
        
        return result
    
    def submit_background_task(self, task_func: Callable, 
                             callback: Optional[Callable] = None, 
                             *args, **kwargs) -> None:
        """Submit a task for background execution."""
        self.task_manager.submit_task(task_func, *args, callback=callback, **kwargs)
    
    def update_ui_element(self, element_id: str, update_func: Callable, 
                         throttle_ms: int = 100) -> bool:
        """Update UI element with throttling."""
        return self.ui_optimizer.throttle_update(element_id, update_func, throttle_ms)
    
    def process_market_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process market data efficiently."""
        return self.data_processor.process_market_data_batch(data)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        metrics = self.resource_monitor.collect_metrics()
        cache_stats = self.memory_manager.get_cache_stats()
        performance_summary = self.resource_monitor.get_performance_summary()
        
        # Update metrics with additional info
        metrics.cache_hit_rate = cache_stats['hit_rate']
        metrics.queue_size = self.task_manager.get_queue_size()
        
        return {
            'current_metrics': metrics,
            'cache_stats': cache_stats,
            'performance_summary': performance_summary,
            'optimization_enabled': self.optimization_enabled
        }
    
    def perform_maintenance(self) -> Dict[str, Any]:
        """Perform system maintenance and cleanup."""
        maintenance_results = {
            'cache_cleared': False,
            'memory_freed': 0,
            'tasks_processed': 0,
            'alerts_cleared': False
        }
        
        # Process completed tasks
        completed_tasks = self.task_manager.process_results()
        maintenance_results['tasks_processed'] = len(completed_tasks)
        
        # Process pending UI updates
        self.ui_optimizer.process_pending_updates()
        
        # Check if cleanup is needed
        current_time = time.time()
        if current_time - self.last_cleanup > self.auto_cleanup_interval:
            # Clear cache if memory usage is high
            if psutil.virtual_memory().percent > 80:
                cache_size_before = len(self.memory_manager.cache)
                self.memory_manager.clear_cache()
                maintenance_results['cache_cleared'] = True
                maintenance_results['memory_freed'] = cache_size_before
            
            # Clear old alerts
            self.resource_monitor.clear_alerts()
            maintenance_results['alerts_cleared'] = True
            
            # Force garbage collection
            gc.collect()
            
            self.last_cleanup = current_time
        
        return maintenance_results
    
    def shutdown(self) -> None:
        """Shutdown the performance optimizer."""
        self.task_manager.shutdown()
        self.memory_manager.clear_cache()
        self.optimization_enabled = False