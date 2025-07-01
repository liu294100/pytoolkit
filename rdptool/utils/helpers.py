#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
辅助工具函数模块

提供各种通用的辅助函数：
- 数据转换
- 文件操作
- 网络工具
- 时间处理
- 系统信息
"""

import os
import sys
import time
import socket
import hashlib
import base64
import json
import struct
import platform
import subprocess
from typing import Union, Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import ipaddress
import urllib.parse

def bytes_to_human(size: int, decimal_places: int = 2) -> str:
    """
    将字节数转换为人类可读的格式
    
    Args:
        size: 字节数
        decimal_places: 小数位数
    
    Returns:
        格式化的字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024.0
    return f"{size:.{decimal_places}f} EB"

def human_to_bytes(size_str: str) -> int:
    """
    将人类可读的大小转换为字节数
    
    Args:
        size_str: 大小字符串，如 "10MB", "1.5GB"
    
    Returns:
        字节数
    """
    size_str = size_str.strip().upper()
    
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4,
        'PB': 1024**5
    }
    
    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            number = float(size_str[:-len(unit)])
            return int(number * multiplier)
    
    # 如果没有单位，假设是字节
    return int(float(size_str))

def format_duration(seconds: float) -> str:
    """
    格式化时间间隔
    
    Args:
        seconds: 秒数
    
    Returns:
        格式化的时间字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}小时"
    else:
        days = seconds / 86400
        return f"{days:.1f}天"

def get_timestamp(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    获取当前时间戳
    
    Args:
        format_str: 时间格式字符串
    
    Returns:
        格式化的时间字符串
    """
    return datetime.now().strftime(format_str)

def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    解析时间戳字符串
    
    Args:
        timestamp_str: 时间戳字符串
        format_str: 时间格式字符串
    
    Returns:
        datetime对象
    """
    return datetime.strptime(timestamp_str, format_str)

def calculate_hash(data: Union[str, bytes], algorithm: str = 'sha256') -> str:
    """
    计算数据的哈希值
    
    Args:
        data: 要计算哈希的数据
        algorithm: 哈希算法
    
    Returns:
        十六进制哈希字符串
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()

def encode_base64(data: Union[str, bytes]) -> str:
    """
    Base64编码
    
    Args:
        data: 要编码的数据
    
    Returns:
        Base64编码字符串
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.b64encode(data).decode('ascii')

def decode_base64(encoded_data: str) -> bytes:
    """
    Base64解码
    
    Args:
        encoded_data: Base64编码的字符串
    
    Returns:
        解码后的字节数据
    """
    return base64.b64decode(encoded_data)

def is_valid_ip(ip: str) -> bool:
    """
    检查IP地址是否有效
    
    Args:
        ip: IP地址字符串
    
    Returns:
        是否有效
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def is_valid_port(port: Union[str, int]) -> bool:
    """
    检查端口号是否有效
    
    Args:
        port: 端口号
    
    Returns:
        是否有效
    """
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False

def get_local_ip() -> str:
    """
    获取本地IP地址
    
    Returns:
        本地IP地址
    """
    try:
        # 连接到一个远程地址来获取本地IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def get_public_ip() -> Optional[str]:
    """
    获取公网IP地址
    
    Returns:
        公网IP地址或None
    """
    try:
        import urllib.request
        response = urllib.request.urlopen('https://api.ipify.org', timeout=5)
        return response.read().decode('utf-8').strip()
    except Exception:
        return None

def check_port_open(host: str, port: int, timeout: float = 3.0) -> bool:
    """
    检查端口是否开放
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间
    
    Returns:
        端口是否开放
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False

def find_free_port(start_port: int = 8000, end_port: int = 9000) -> Optional[int]:
    """
    查找可用端口
    
    Args:
        start_port: 起始端口
        end_port: 结束端口
    
    Returns:
        可用端口号或None
    """
    for port in range(start_port, end_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

def parse_url(url: str) -> Dict[str, Any]:
    """
    解析URL
    
    Args:
        url: URL字符串
    
    Returns:
        解析结果字典
    """
    parsed = urllib.parse.urlparse(url)
    return {
        'scheme': parsed.scheme,
        'hostname': parsed.hostname,
        'port': parsed.port,
        'path': parsed.path,
        'query': parsed.query,
        'fragment': parsed.fragment,
        'username': parsed.username,
        'password': parsed.password
    }

def build_url(scheme: str, hostname: str, port: Optional[int] = None, 
              path: str = '', query: str = '', fragment: str = '',
              username: Optional[str] = None, password: Optional[str] = None) -> str:
    """
    构建URL
    
    Args:
        scheme: 协议
        hostname: 主机名
        port: 端口号
        path: 路径
        query: 查询字符串
        fragment: 片段
        username: 用户名
        password: 密码
    
    Returns:
        完整URL
    """
    netloc = hostname
    if port:
        netloc += f":{port}"
    if username:
        auth = username
        if password:
            auth += f":{password}"
        netloc = f"{auth}@{netloc}"
    
    return urllib.parse.urlunparse((
        scheme, netloc, path, '', query, fragment
    ))

def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息
    
    Returns:
        系统信息字典
    """
    return {
        'platform': platform.platform(),
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'python_implementation': platform.python_implementation()
    }

def run_command(command: List[str], timeout: Optional[float] = None, 
                capture_output: bool = True) -> Tuple[int, str, str]:
    """
    运行系统命令
    
    Args:
        command: 命令列表
        timeout: 超时时间
        capture_output: 是否捕获输出
    
    Returns:
        (返回码, 标准输出, 标准错误)
    """
    try:
        result = subprocess.run(
            command,
            timeout=timeout,
            capture_output=capture_output,
            text=True
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'Command timed out'
    except Exception as e:
        return -1, '', str(e)

def ensure_dir(path: Union[str, Path]) -> Path:
    """
    确保目录存在
    
    Args:
        path: 目录路径
    
    Returns:
        Path对象
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj

def safe_filename(filename: str) -> str:
    """
    生成安全的文件名
    
    Args:
        filename: 原始文件名
    
    Returns:
        安全的文件名
    """
    # 移除或替换不安全的字符
    unsafe_chars = '<>:"/\\|?*'
    safe_name = filename
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')
    
    # 移除前后空格和点
    safe_name = safe_name.strip(' .')
    
    # 确保不为空
    if not safe_name:
        safe_name = 'unnamed'
    
    return safe_name

def read_file_chunks(file_path: Union[str, Path], chunk_size: int = 8192):
    """
    分块读取文件
    
    Args:
        file_path: 文件路径
        chunk_size: 块大小
    
    Yields:
        文件数据块
    """
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

def pack_data(data: Any) -> bytes:
    """
    打包数据为字节
    
    Args:
        data: 要打包的数据
    
    Returns:
        打包后的字节数据
    """
    if isinstance(data, bytes):
        return data
    elif isinstance(data, str):
        return data.encode('utf-8')
    elif isinstance(data, (dict, list, tuple)):
        return json.dumps(data, ensure_ascii=False).encode('utf-8')
    else:
        return str(data).encode('utf-8')

def unpack_data(data: bytes, data_type: str = 'auto') -> Any:
    """
    解包字节数据
    
    Args:
        data: 字节数据
        data_type: 数据类型 ('auto', 'str', 'json')
    
    Returns:
        解包后的数据
    """
    if data_type == 'auto':
        try:
            # 尝试解析为JSON
            text = data.decode('utf-8')
            return json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return data
    elif data_type == 'str':
        return data.decode('utf-8')
    elif data_type == 'json':
        return json.loads(data.decode('utf-8'))
    else:
        return data

def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                      backoff: float = 2.0, exceptions: Tuple = (Exception,)):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间
        backoff: 退避倍数
        exceptions: 要捕获的异常类型
    
    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise e
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator

def rate_limit(calls_per_second: float):
    """
    速率限制装饰器
    
    Args:
        calls_per_second: 每秒调用次数
    
    Returns:
        装饰器函数
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并多个字典
    
    Args:
        *dicts: 要合并的字典
    
    Returns:
        合并后的字典
    """
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    展平嵌套字典
    
    Args:
        d: 嵌套字典
        parent_key: 父键名
        sep: 分隔符
    
    Returns:
        展平后的字典
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def get_nested_value(d: Dict[str, Any], key_path: str, default: Any = None, sep: str = '.') -> Any:
    """
    获取嵌套字典中的值
    
    Args:
        d: 字典
        key_path: 键路径，如 'a.b.c'
        default: 默认值
        sep: 分隔符
    
    Returns:
        值或默认值
    """
    keys = key_path.split(sep)
    value = d
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

def set_nested_value(d: Dict[str, Any], key_path: str, value: Any, sep: str = '.') -> None:
    """
    设置嵌套字典中的值
    
    Args:
        d: 字典
        key_path: 键路径，如 'a.b.c'
        value: 要设置的值
        sep: 分隔符
    """
    keys = key_path.split(sep)
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value