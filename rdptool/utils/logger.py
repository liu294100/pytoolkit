#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志配置模块

提供统一的日志配置和管理功能：
- 多级别日志
- 文件和控制台输出
- 日志轮转
- 格式化输出
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import threading
from datetime import datetime

# 全局日志配置
_loggers: Dict[str, logging.Logger] = {}
_lock = threading.Lock()

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }
    
    def format(self, record):
        # 获取原始格式化结果
        log_message = super().format(record)
        
        # 添加颜色
        if sys.stdout.isatty():  # 只在终端中使用颜色
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            log_message = f"{color}{log_message}{reset}"
        
        return log_message

class PerformanceFilter(logging.Filter):
    """性能日志过滤器"""
    
    def filter(self, record):
        # 添加性能相关信息
        if not hasattr(record, 'performance'):
            record.performance = {
                'timestamp': datetime.now().isoformat(),
                'thread_id': threading.get_ident(),
                'process_id': record.process
            }
        return True

def setup_logger(
    name: str = 'rdptool',
    level: str = 'INFO',
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        max_file_size: 最大文件大小（字节）
        backup_count: 备份文件数量
        console_output: 是否输出到控制台
        format_string: 自定义格式字符串
    
    Returns:
        配置好的日志记录器
    """
    with _lock:
        # 如果已存在，直接返回
        if name in _loggers:
            return _loggers[name]
        
        # 创建日志记录器
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        
        # 清除现有处理器
        logger.handlers.clear()
        
        # 默认格式
        if format_string is None:
            format_string = (
                '%(asctime)s - %(name)s - %(levelname)s - '
                '[%(filename)s:%(lineno)d] - %(message)s'
            )
        
        # 控制台处理器
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, level.upper()))
            
            # 使用彩色格式化器
            console_formatter = ColoredFormatter(format_string)
            console_handler.setFormatter(console_formatter)
            
            # 添加性能过滤器
            console_handler.addFilter(PerformanceFilter())
            
            logger.addHandler(console_handler)
        
        # 文件处理器
        if log_file:
            # 确保日志目录存在
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用轮转文件处理器
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, level.upper()))
            
            # 文件格式化器（不使用颜色）
            file_formatter = logging.Formatter(format_string)
            file_handler.setFormatter(file_formatter)
            
            # 添加性能过滤器
            file_handler.addFilter(PerformanceFilter())
            
            logger.addHandler(file_handler)
        
        # 缓存日志记录器
        _loggers[name] = logger
        
        return logger

def get_logger(name: str = 'rdptool') -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        日志记录器
    """
    with _lock:
        if name in _loggers:
            return _loggers[name]
        else:
            # 如果不存在，使用默认配置创建
            return setup_logger(name)

def configure_module_logger(module_name: str, level: str = 'INFO') -> logging.Logger:
    """
    为特定模块配置日志记录器
    
    Args:
        module_name: 模块名称
        level: 日志级别
    
    Returns:
        配置好的日志记录器
    """
    logger_name = f'rdptool.{module_name}'
    return setup_logger(
        name=logger_name,
        level=level,
        log_file=f'logs/{module_name}.log'
    )

class LogContext:
    """
    日志上下文管理器
    
    用于在特定代码块中添加额外的日志信息
    """
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        # 保存原始记录工厂
        self.old_factory = logging.getLogRecordFactory()
        
        # 创建新的记录工厂
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            # 添加上下文信息
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        # 设置新的记录工厂
        logging.setLogRecordFactory(record_factory)
        
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原始记录工厂
        logging.setLogRecordFactory(self.old_factory)

class StructuredLogger:
    """
    结构化日志记录器
    
    支持结构化日志输出，便于日志分析
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_event(self, event_type: str, level: str = 'INFO', **data):
        """
        记录结构化事件
        
        Args:
            event_type: 事件类型
            level: 日志级别
            **data: 事件数据
        """
        log_data = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            **data
        }
        
        # 格式化为JSON字符串
        import json
        message = json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))
        
        # 记录日志
        log_level = getattr(logging, level.upper())
        self.logger.log(log_level, message)
    
    def log_performance(self, operation: str, duration: float, **metadata):
        """
        记录性能日志
        
        Args:
            operation: 操作名称
            duration: 持续时间（秒）
            **metadata: 额外元数据
        """
        self.log_event(
            'performance',
            level='INFO',
            operation=operation,
            duration=duration,
            **metadata
        )
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """
        记录错误日志
        
        Args:
            error: 异常对象
            context: 错误上下文
        """
        import traceback
        
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }
        
        if context:
            error_data['context'] = context
        
        self.log_event('error', level='ERROR', **error_data)

def create_performance_logger(name: str = 'performance') -> StructuredLogger:
    """
    创建性能日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        结构化日志记录器
    """
    logger = setup_logger(
        name=f'rdptool.{name}',
        level='INFO',
        log_file=f'logs/{name}.log'
    )
    return StructuredLogger(logger)

def log_function_call(func):
    """
    函数调用日志装饰器
    
    Args:
        func: 要装饰的函数
    
    Returns:
        装饰后的函数
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger()
        
        # 记录函数调用开始
        start_time = time.time()
        logger.debug(f"调用函数: {func.__name__}")
        
        try:
            # 执行函数
            result = func(*args, **kwargs)
            
            # 记录成功完成
            duration = time.time() - start_time
            logger.debug(f"函数 {func.__name__} 完成，耗时: {duration:.3f}秒")
            
            return result
            
        except Exception as e:
            # 记录异常
            duration = time.time() - start_time
            logger.error(f"函数 {func.__name__} 异常，耗时: {duration:.3f}秒，错误: {e}")
            raise
    
    return wrapper

# 预配置的日志记录器
network_logger = configure_module_logger('network')
screen_logger = configure_module_logger('screen')
input_logger = configure_module_logger('input')
protocol_logger = configure_module_logger('protocol')
security_logger = configure_module_logger('security')
performance_logger = create_performance_logger()

# 导出常用功能
__all__ = [
    'setup_logger',
    'get_logger',
    'configure_module_logger',
    'LogContext',
    'StructuredLogger',
    'create_performance_logger',
    'log_function_call',
    'network_logger',
    'screen_logger',
    'input_logger',
    'protocol_logger',
    'security_logger',
    'performance_logger'
]