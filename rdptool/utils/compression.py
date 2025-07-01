#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据压缩工具模块

提供多种压缩算法：
- ZLIB压缩
- GZIP压缩
- LZ4压缩
- BZIP2压缩
- 自适应压缩
"""

import zlib
import gzip
import bz2
import io
from typing import Union, Optional, Dict, Any, Tuple
from enum import Enum
import time
import threading
from dataclasses import dataclass

try:
    import lz4.frame
    HAS_LZ4 = True
except ImportError:
    HAS_LZ4 = False

class CompressionType(Enum):
    """压缩类型枚举"""
    NONE = "none"
    ZLIB = "zlib"
    GZIP = "gzip"
    LZ4 = "lz4"
    BZIP2 = "bzip2"
    AUTO = "auto"

@dataclass
class CompressionConfig:
    """压缩配置"""
    compression_type: CompressionType = CompressionType.ZLIB
    compression_level: int = 6  # 压缩级别 (1-9)
    min_size_threshold: int = 1024  # 最小压缩阈值（字节）
    auto_select_threshold: float = 0.8  # 自动选择压缩比阈值
    enable_cache: bool = True  # 启用压缩缓存
    cache_size: int = 100  # 缓存大小

@dataclass
class CompressionResult:
    """压缩结果"""
    compressed_data: bytes
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_type: CompressionType
    compression_time: float

class CompressionError(Exception):
    """压缩相关异常"""
    pass

class CompressionCache:
    """
    压缩缓存类
    
    缓存压缩结果以提高性能
    """
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: Dict[bytes, CompressionResult] = {}
        self.access_times: Dict[bytes, float] = {}
        self.lock = threading.RLock()
    
    def get(self, data_hash: bytes) -> Optional[CompressionResult]:
        """获取缓存的压缩结果"""
        with self.lock:
            if data_hash in self.cache:
                self.access_times[data_hash] = time.time()
                return self.cache[data_hash]
            return None
    
    def put(self, data_hash: bytes, result: CompressionResult):
        """存储压缩结果到缓存"""
        with self.lock:
            # 如果缓存已满，删除最久未访问的项
            if len(self.cache) >= self.max_size:
                oldest_hash = min(self.access_times.keys(), key=lambda k: self.access_times[k])
                del self.cache[oldest_hash]
                del self.access_times[oldest_hash]
            
            self.cache[data_hash] = result
            self.access_times[data_hash] = time.time()
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)

class DataCompressor:
    """
    数据压缩器
    
    支持多种压缩算法和自适应压缩
    """
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        self.cache = CompressionCache(self.config.cache_size) if self.config.enable_cache else None
        self.stats = {
            'total_compressed': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'compression_count': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def compress(self, data: bytes, compression_type: Optional[CompressionType] = None) -> CompressionResult:
        """
        压缩数据
        
        Args:
            data: 要压缩的数据
            compression_type: 压缩类型（如果为None则使用配置中的类型）
        
        Returns:
            压缩结果
        """
        if not isinstance(data, bytes):
            raise CompressionError("数据必须是bytes类型")
        
        if len(data) == 0:
            return CompressionResult(
                compressed_data=data,
                original_size=0,
                compressed_size=0,
                compression_ratio=1.0,
                compression_type=CompressionType.NONE,
                compression_time=0.0
            )
        
        # 检查是否需要压缩
        if len(data) < self.config.min_size_threshold:
            return CompressionResult(
                compressed_data=data,
                original_size=len(data),
                compressed_size=len(data),
                compression_ratio=1.0,
                compression_type=CompressionType.NONE,
                compression_time=0.0
            )
        
        # 确定压缩类型
        comp_type = compression_type or self.config.compression_type
        
        # 检查缓存
        if self.cache:
            data_hash = self._hash_data(data)
            cached_result = self.cache.get(data_hash)
            if cached_result:
                self.stats['cache_hits'] += 1
                return cached_result
            self.stats['cache_misses'] += 1
        
        start_time = time.time()
        
        try:
            if comp_type == CompressionType.AUTO:
                result = self._auto_compress(data)
            else:
                compressed_data = self._compress_with_algorithm(data, comp_type)
                result = CompressionResult(
                    compressed_data=compressed_data,
                    original_size=len(data),
                    compressed_size=len(compressed_data),
                    compression_ratio=len(compressed_data) / len(data),
                    compression_type=comp_type,
                    compression_time=time.time() - start_time
                )
            
            # 更新统计信息
            self._update_stats(result)
            
            # 缓存结果
            if self.cache:
                self.cache.put(data_hash, result)
            
            return result
            
        except Exception as e:
            raise CompressionError(f"压缩失败: {e}")
    
    def decompress(self, compressed_data: bytes, compression_type: CompressionType) -> bytes:
        """
        解压缩数据
        
        Args:
            compressed_data: 压缩数据
            compression_type: 压缩类型
        
        Returns:
            解压缩后的数据
        """
        if not isinstance(compressed_data, bytes):
            raise CompressionError("压缩数据必须是bytes类型")
        
        if compression_type == CompressionType.NONE:
            return compressed_data
        
        try:
            return self._decompress_with_algorithm(compressed_data, compression_type)
        except Exception as e:
            raise CompressionError(f"解压缩失败: {e}")
    
    def _compress_with_algorithm(self, data: bytes, compression_type: CompressionType) -> bytes:
        """使用指定算法压缩数据"""
        if compression_type == CompressionType.ZLIB:
            return zlib.compress(data, self.config.compression_level)
        
        elif compression_type == CompressionType.GZIP:
            buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=self.config.compression_level) as f:
                f.write(data)
            return buffer.getvalue()
        
        elif compression_type == CompressionType.LZ4:
            if not HAS_LZ4:
                raise CompressionError("LZ4库未安装")
            return lz4.frame.compress(data, compression_level=self.config.compression_level)
        
        elif compression_type == CompressionType.BZIP2:
            return bz2.compress(data, compresslevel=self.config.compression_level)
        
        else:
            raise CompressionError(f"不支持的压缩类型: {compression_type}")
    
    def _decompress_with_algorithm(self, compressed_data: bytes, compression_type: CompressionType) -> bytes:
        """使用指定算法解压缩数据"""
        if compression_type == CompressionType.ZLIB:
            return zlib.decompress(compressed_data)
        
        elif compression_type == CompressionType.GZIP:
            return gzip.decompress(compressed_data)
        
        elif compression_type == CompressionType.LZ4:
            if not HAS_LZ4:
                raise CompressionError("LZ4库未安装")
            return lz4.frame.decompress(compressed_data)
        
        elif compression_type == CompressionType.BZIP2:
            return bz2.decompress(compressed_data)
        
        else:
            raise CompressionError(f"不支持的解压缩类型: {compression_type}")
    
    def _auto_compress(self, data: bytes) -> CompressionResult:
        """自动选择最佳压缩算法"""
        algorithms = [CompressionType.ZLIB, CompressionType.GZIP]
        
        if HAS_LZ4:
            algorithms.append(CompressionType.LZ4)
        
        # 对于大数据，也尝试BZIP2
        if len(data) > 10 * 1024 * 1024:  # 10MB
            algorithms.append(CompressionType.BZIP2)
        
        best_result = None
        best_ratio = float('inf')
        
        for algo in algorithms:
            try:
                start_time = time.time()
                compressed = self._compress_with_algorithm(data, algo)
                compression_time = time.time() - start_time
                
                ratio = len(compressed) / len(data)
                
                # 考虑压缩比和压缩时间
                score = ratio + (compression_time * 0.1)  # 时间权重较小
                
                if score < best_ratio:
                    best_ratio = score
                    best_result = CompressionResult(
                        compressed_data=compressed,
                        original_size=len(data),
                        compressed_size=len(compressed),
                        compression_ratio=ratio,
                        compression_type=algo,
                        compression_time=compression_time
                    )
            except Exception:
                continue  # 忽略失败的算法
        
        if best_result is None:
            # 如果所有算法都失败，返回原始数据
            return CompressionResult(
                compressed_data=data,
                original_size=len(data),
                compressed_size=len(data),
                compression_ratio=1.0,
                compression_type=CompressionType.NONE,
                compression_time=0.0
            )
        
        # 如果压缩效果不好，返回原始数据
        if best_result.compression_ratio > self.config.auto_select_threshold:
            return CompressionResult(
                compressed_data=data,
                original_size=len(data),
                compressed_size=len(data),
                compression_ratio=1.0,
                compression_type=CompressionType.NONE,
                compression_time=0.0
            )
        
        return best_result
    
    def _hash_data(self, data: bytes) -> bytes:
        """计算数据哈希值用于缓存"""
        import hashlib
        return hashlib.md5(data).digest()
    
    def _update_stats(self, result: CompressionResult):
        """更新统计信息"""
        self.stats['total_compressed'] += 1
        self.stats['total_original_size'] += result.original_size
        self.stats['total_compressed_size'] += result.compressed_size
        self.stats['compression_count'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        stats = self.stats.copy()
        if stats['total_original_size'] > 0:
            stats['overall_compression_ratio'] = stats['total_compressed_size'] / stats['total_original_size']
            stats['space_saved'] = stats['total_original_size'] - stats['total_compressed_size']
            stats['space_saved_percentage'] = (stats['space_saved'] / stats['total_original_size']) * 100
        else:
            stats['overall_compression_ratio'] = 1.0
            stats['space_saved'] = 0
            stats['space_saved_percentage'] = 0.0
        
        if self.cache:
            stats['cache_size'] = self.cache.size()
            stats['cache_hit_rate'] = (
                stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses'])
                if (stats['cache_hits'] + stats['cache_misses']) > 0 else 0.0
            )
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_compressed': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'compression_count': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def clear_cache(self):
        """清空缓存"""
        if self.cache:
            self.cache.clear()

class StreamCompressor:
    """
    流式压缩器
    
    支持流式数据的压缩和解压缩
    """
    
    def __init__(self, compression_type: CompressionType = CompressionType.ZLIB, level: int = 6):
        self.compression_type = compression_type
        self.level = level
        self.compressor = None
        self.decompressor = None
        self._init_compressor()
    
    def _init_compressor(self):
        """初始化压缩器"""
        if self.compression_type == CompressionType.ZLIB:
            self.compressor = zlib.compressobj(self.level)
            self.decompressor = zlib.decompressobj()
        elif self.compression_type == CompressionType.GZIP:
            self.compressor = zlib.compressobj(self.level, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
            self.decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        else:
            raise CompressionError(f"流式压缩不支持类型: {self.compression_type}")
    
    def compress_chunk(self, data: bytes) -> bytes:
        """
        压缩数据块
        
        Args:
            data: 数据块
        
        Returns:
            压缩后的数据块
        """
        if not self.compressor:
            raise CompressionError("压缩器未初始化")
        
        return self.compressor.compress(data)
    
    def flush_compress(self) -> bytes:
        """
        刷新压缩器缓冲区
        
        Returns:
            剩余的压缩数据
        """
        if not self.compressor:
            raise CompressionError("压缩器未初始化")
        
        return self.compressor.flush()
    
    def decompress_chunk(self, data: bytes) -> bytes:
        """
        解压缩数据块
        
        Args:
            data: 压缩数据块
        
        Returns:
            解压缩后的数据块
        """
        if not self.decompressor:
            raise CompressionError("解压缩器未初始化")
        
        return self.decompressor.decompress(data)
    
    def reset(self):
        """重置压缩器"""
        self._init_compressor()

# 便捷函数
def compress_data(data: bytes, compression_type: CompressionType = CompressionType.ZLIB, level: int = 6) -> Tuple[bytes, CompressionType]:
    """
    压缩数据（便捷函数）
    
    Args:
        data: 要压缩的数据
        compression_type: 压缩类型
        level: 压缩级别
    
    Returns:
        (压缩数据, 实际使用的压缩类型)
    """
    config = CompressionConfig(
        compression_type=compression_type,
        compression_level=level,
        enable_cache=False
    )
    compressor = DataCompressor(config)
    result = compressor.compress(data)
    return result.compressed_data, result.compression_type

def decompress_data(compressed_data: bytes, compression_type: CompressionType) -> bytes:
    """
    解压缩数据（便捷函数）
    
    Args:
        compressed_data: 压缩数据
        compression_type: 压缩类型
    
    Returns:
        解压缩后的数据
    """
    compressor = DataCompressor()
    return compressor.decompress(compressed_data, compression_type)

def get_compression_info(data: bytes) -> Dict[str, Any]:
    """
    获取数据的压缩信息
    
    Args:
        data: 原始数据
    
    Returns:
        压缩信息字典
    """
    info = {
        'original_size': len(data),
        'algorithms': {}
    }
    
    algorithms = [CompressionType.ZLIB, CompressionType.GZIP, CompressionType.BZIP2]
    if HAS_LZ4:
        algorithms.append(CompressionType.LZ4)
    
    for algo in algorithms:
        try:
            start_time = time.time()
            compressor = DataCompressor(CompressionConfig(compression_type=algo, enable_cache=False))
            result = compressor.compress(data, algo)
            
            info['algorithms'][algo.value] = {
                'compressed_size': result.compressed_size,
                'compression_ratio': result.compression_ratio,
                'compression_time': result.compression_time,
                'space_saved': result.original_size - result.compressed_size,
                'space_saved_percentage': ((result.original_size - result.compressed_size) / result.original_size) * 100
            }
        except Exception as e:
            info['algorithms'][algo.value] = {'error': str(e)}
    
    # 找出最佳压缩算法
    best_algo = None
    best_ratio = float('inf')
    for algo, data in info['algorithms'].items():
        if 'compression_ratio' in data and data['compression_ratio'] < best_ratio:
            best_ratio = data['compression_ratio']
            best_algo = algo
    
    info['best_algorithm'] = best_algo
    info['best_compression_ratio'] = best_ratio
    
    return info

# 导出功能
__all__ = [
    'CompressionType',
    'CompressionConfig',
    'CompressionResult',
    'CompressionError',
    'DataCompressor',
    'StreamCompressor',
    'compress_data',
    'decompress_data',
    'get_compression_info'
]