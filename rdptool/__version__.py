#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDPTool 版本信息
"""

__version__ = '1.0.0'
__version_info__ = (1, 0, 0)

__title__ = 'RDPTool'
__description__ = '多协议远程桌面工具 - 纯Python实现'
__author__ = 'RDPTool Team'
__author_email__ = 'rdptool@example.com'
__license__ = 'MIT'
__copyright__ = 'Copyright 2024 RDPTool Team'
__url__ = 'https://github.com/example/rdptool'

# 构建信息
__build__ = '20240101'
__commit__ = 'unknown'

# 支持的Python版本
__python_requires__ = '>=3.8'

# 功能特性版本
__features__ = {
    'remote_desktop': '1.0.0',
    'multi_protocol_proxy': '1.0.0',
    'security': '1.0.0',
    'network_monitoring': '1.0.0',
    'performance_optimization': '1.0.0',
}

# 协议支持版本
__protocols__ = {
    'tcp': '1.0.0',
    'udp': '1.0.0',
    'http': '1.0.0',
    'https': '1.0.0',
    'websocket': '1.0.0',
    'socks4': '1.0.0',
    'socks5': '1.0.0',
    'ssh': '1.0.0',
    'raw_socket': '1.0.0',
}

# API版本
__api_version__ = '1.0'

def get_version():
    """获取版本字符串"""
    return __version__

def get_version_info():
    """获取版本信息元组"""
    return __version_info__

def get_full_version():
    """获取完整版本信息"""
    return f"{__title__} {__version__} (build {__build__})"

def get_user_agent():
    """获取用户代理字符串"""
    return f"{__title__}/{__version__}"

def check_version_compatibility(required_version):
    """检查版本兼容性"""
    try:
        required = tuple(map(int, required_version.split('.')))
        return __version_info__ >= required
    except (ValueError, AttributeError):
        return False

# 版本历史
__changelog__ = {
    '1.0.0': [
        '初始版本发布',
        '实现远程桌面核心功能',
        '支持多种网络协议代理',
        '集成安全加密机制',
        '添加性能监控功能',
        '提供完整的配置管理',
    ],
}

if __name__ == '__main__':
    print(get_full_version())
    print(f"Python要求: {__python_requires__}")
    print(f"API版本: {__api_version__}")
    print("\n支持的协议:")
    for protocol, version in __protocols__.items():
        print(f"  {protocol}: {version}")
    print("\n功能特性:")
    for feature, version in __features__.items():
        print(f"  {feature}: {version}")