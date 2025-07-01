#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDPTool 测试模块
"""

import os
import sys
import unittest
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试配置
TEST_CONFIG = {
    'test_server_host': '127.0.0.1',
    'test_server_port': 18888,
    'test_proxy_port': 18080,
    'test_timeout': 10,
    'test_data_dir': project_root / 'tests' / 'data',
    'test_logs_dir': project_root / 'tests' / 'logs',
    'test_temp_dir': project_root / 'tests' / 'temp',
}

# 创建测试目录
for dir_path in [TEST_CONFIG['test_data_dir'], TEST_CONFIG['test_logs_dir'], TEST_CONFIG['test_temp_dir']]:
    dir_path.mkdir(parents=True, exist_ok=True)

def get_test_config():
    """获取测试配置"""
    return TEST_CONFIG.copy()

def setup_test_environment():
    """设置测试环境"""
    # 设置环境变量
    os.environ['RDPTOOL_TEST_MODE'] = '1'
    os.environ['RDPTOOL_LOG_LEVEL'] = 'DEBUG'
    os.environ['RDPTOOL_CONFIG_DIR'] = str(TEST_CONFIG['test_data_dir'])
    
    # 创建测试配置文件
    create_test_configs()

def cleanup_test_environment():
    """清理测试环境"""
    import shutil
    
    # 清理临时文件
    if TEST_CONFIG['test_temp_dir'].exists():
        shutil.rmtree(TEST_CONFIG['test_temp_dir'])
        TEST_CONFIG['test_temp_dir'].mkdir()
    
    # 清理环境变量
    for key in ['RDPTOOL_TEST_MODE', 'RDPTOOL_LOG_LEVEL', 'RDPTOOL_CONFIG_DIR']:
        os.environ.pop(key, None)

def create_test_configs():
    """创建测试配置文件"""
    import json
    
    # 测试服务端配置
    server_config = {
        "server": {
            "host": TEST_CONFIG['test_server_host'],
            "port": TEST_CONFIG['test_server_port'],
            "protocol": "tcp",
            "max_clients": 2
        },
        "security": {
            "encryption_type": "none",
            "auth_method": "none",
            "require_encryption": False
        },
        "logging": {
            "level": "DEBUG",
            "file": str(TEST_CONFIG['test_logs_dir'] / 'test_server.log'),
            "console": False
        }
    }
    
    # 测试客户端配置
    client_config = {
        "client": {
            "server_host": TEST_CONFIG['test_server_host'],
            "server_port": TEST_CONFIG['test_server_port'],
            "protocol": "tcp",
            "timeout": TEST_CONFIG['test_timeout']
        },
        "security": {
            "encryption_type": "none",
            "verify_server": False
        },
        "logging": {
            "level": "DEBUG",
            "file": str(TEST_CONFIG['test_logs_dir'] / 'test_client.log'),
            "console": False
        }
    }
    
    # 测试代理配置
    proxy_config = {
        "proxy": {
            "host": TEST_CONFIG['test_server_host'],
            "max_connections": 10
        },
        "protocols": {
            "http": {
                "enabled": True,
                "port": TEST_CONFIG['test_proxy_port'],
                "auth_required": False
            }
        },
        "logging": {
            "level": "DEBUG",
            "file": str(TEST_CONFIG['test_logs_dir'] / 'test_proxy.log'),
            "console": False
        }
    }
    
    # 保存配置文件
    configs = {
        'test_server_config.json': server_config,
        'test_client_config.json': client_config,
        'test_proxy_config.json': proxy_config,
    }
    
    for filename, config in configs.items():
        config_path = TEST_CONFIG['test_data_dir'] / filename
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

class RDPToolTestCase(unittest.TestCase):
    """RDPTool测试基类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类设置"""
        setup_test_environment()
    
    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        cleanup_test_environment()
    
    def setUp(self):
        """测试方法设置"""
        self.test_config = get_test_config()
    
    def tearDown(self):
        """测试方法清理"""
        pass
    
    def get_test_data_path(self, filename):
        """获取测试数据文件路径"""
        return self.test_config['test_data_dir'] / filename
    
    def get_test_temp_path(self, filename):
        """获取测试临时文件路径"""
        return self.test_config['test_temp_dir'] / filename

def run_all_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()

if __name__ == '__main__':
    run_all_tests()