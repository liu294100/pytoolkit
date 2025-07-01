#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心功能测试
"""

import unittest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from tests import RDPToolTestCase

try:
    from core.network import NetworkManager, ConnectionManager
    from core.protocol import ProtocolHandler, MessageType
    from core.security import SecurityManager, EncryptionType
    from utils.config import ConfigManager
    from utils.logger import get_logger
except ImportError as e:
    print(f"导入错误: {e}")
    print("某些测试可能会跳过")

class TestConfigManager(RDPToolTestCase):
    """配置管理器测试"""
    
    def setUp(self):
        super().setUp()
        self.config_manager = ConfigManager()
        self.test_config_file = self.get_test_temp_path('test_config.json')
    
    def test_load_config(self):
        """测试配置加载"""
        test_config = {
            'server': {
                'host': '127.0.0.1',
                'port': 8888
            },
            'security': {
                'encryption': True
            }
        }
        
        # 保存测试配置
        self.config_manager.save_config(test_config, str(self.test_config_file))
        
        # 加载配置
        loaded_config = self.config_manager.load_config(str(self.test_config_file))
        
        self.assertEqual(loaded_config['server']['host'], '127.0.0.1')
        self.assertEqual(loaded_config['server']['port'], 8888)
        self.assertTrue(loaded_config['security']['encryption'])
    
    def test_get_nested_value(self):
        """测试嵌套值获取"""
        config = {
            'server': {
                'network': {
                    'port': 8888
                }
            }
        }
        
        value = self.config_manager.get('server.network.port', config)
        self.assertEqual(value, 8888)
        
        # 测试默认值
        value = self.config_manager.get('server.network.timeout', config, default=30)
        self.assertEqual(value, 30)
    
    def test_set_nested_value(self):
        """测试嵌套值设置"""
        config = {}
        
        self.config_manager.set('server.network.port', 9999, config)
        self.assertEqual(config['server']['network']['port'], 9999)
    
    def test_merge_configs(self):
        """测试配置合并"""
        base_config = {
            'server': {
                'host': '0.0.0.0',
                'port': 8888
            },
            'security': {
                'encryption': True
            }
        }
        
        override_config = {
            'server': {
                'port': 9999
            },
            'logging': {
                'level': 'DEBUG'
            }
        }
        
        merged = self.config_manager.merge_configs(base_config, override_config)
        
        self.assertEqual(merged['server']['host'], '0.0.0.0')
        self.assertEqual(merged['server']['port'], 9999)
        self.assertTrue(merged['security']['encryption'])
        self.assertEqual(merged['logging']['level'], 'DEBUG')

class TestSecurityManager(RDPToolTestCase):
    """安全管理器测试"""
    
    def setUp(self):
        super().setUp()
        self.security_manager = SecurityManager()
    
    def test_password_hashing(self):
        """测试密码哈希"""
        password = "test_password_123"
        
        # 生成哈希
        hash1 = self.security_manager.hash_password(password)
        hash2 = self.security_manager.hash_password(password)
        
        # 哈希应该不同（因为盐值不同）
        self.assertNotEqual(hash1, hash2)
        
        # 验证密码
        self.assertTrue(self.security_manager.verify_password(password, hash1))
        self.assertTrue(self.security_manager.verify_password(password, hash2))
        self.assertFalse(self.security_manager.verify_password("wrong_password", hash1))
    
    def test_encryption_decryption(self):
        """测试加密解密"""
        data = b"Hello, World! This is a test message."
        key = self.security_manager.generate_key()
        
        # 加密
        encrypted_data = self.security_manager.encrypt(data, key)
        self.assertNotEqual(data, encrypted_data)
        
        # 解密
        decrypted_data = self.security_manager.decrypt(encrypted_data, key)
        self.assertEqual(data, decrypted_data)
    
    def test_key_generation(self):
        """测试密钥生成"""
        key1 = self.security_manager.generate_key()
        key2 = self.security_manager.generate_key()
        
        # 密钥应该不同
        self.assertNotEqual(key1, key2)
        
        # 密钥长度应该正确
        self.assertEqual(len(key1), 32)  # AES-256
        self.assertEqual(len(key2), 32)
    
    @patch('core.security.os.urandom')
    def test_secure_random(self, mock_urandom):
        """测试安全随机数生成"""
        mock_urandom.return_value = b'\x00' * 16
        
        random_data = self.security_manager.generate_random(16)
        self.assertEqual(len(random_data), 16)
        mock_urandom.assert_called_once_with(16)

class TestProtocolHandler(RDPToolTestCase):
    """协议处理器测试"""
    
    def setUp(self):
        super().setUp()
        self.protocol_handler = ProtocolHandler()
    
    def test_message_serialization(self):
        """测试消息序列化"""
        message = {
            'type': MessageType.SCREEN_DATA.value,
            'data': b'test_image_data',
            'timestamp': 1234567890,
            'metadata': {
                'width': 1920,
                'height': 1080,
                'format': 'jpeg'
            }
        }
        
        # 序列化
        serialized = self.protocol_handler.serialize_message(message)
        self.assertIsInstance(serialized, bytes)
        
        # 反序列化
        deserialized = self.protocol_handler.deserialize_message(serialized)
        self.assertEqual(deserialized['type'], message['type'])
        self.assertEqual(deserialized['data'], message['data'])
        self.assertEqual(deserialized['timestamp'], message['timestamp'])
        self.assertEqual(deserialized['metadata'], message['metadata'])
    
    def test_message_validation(self):
        """测试消息验证"""
        valid_message = {
            'type': MessageType.SCREEN_DATA.value,
            'data': b'test_data',
            'timestamp': 1234567890
        }
        
        invalid_message = {
            'type': 'invalid_type',
            'data': 'not_bytes',
        }
        
        self.assertTrue(self.protocol_handler.validate_message(valid_message))
        self.assertFalse(self.protocol_handler.validate_message(invalid_message))
    
    def test_protocol_negotiation(self):
        """测试协议协商"""
        client_protocols = ['rdp_v1', 'rdp_v2']
        server_protocols = ['rdp_v2', 'rdp_v3']
        
        negotiated = self.protocol_handler.negotiate_protocol(client_protocols, server_protocols)
        self.assertEqual(negotiated, 'rdp_v2')
        
        # 测试无匹配协议
        client_protocols = ['rdp_v1']
        server_protocols = ['rdp_v3']
        
        negotiated = self.protocol_handler.negotiate_protocol(client_protocols, server_protocols)
        self.assertIsNone(negotiated)

class TestNetworkManager(RDPToolTestCase):
    """网络管理器测试"""
    
    def setUp(self):
        super().setUp()
        self.network_manager = NetworkManager()
    
    @patch('socket.socket')
    def test_tcp_connection(self, mock_socket):
        """测试TCP连接"""
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        # 模拟成功连接
        mock_sock.connect.return_value = None
        
        result = self.network_manager.create_tcp_connection('127.0.0.1', 8888)
        
        mock_socket.assert_called_once()
        mock_sock.connect.assert_called_once_with(('127.0.0.1', 8888))
        self.assertIsNotNone(result)
    
    def test_connection_pool(self):
        """测试连接池"""
        pool = self.network_manager.get_connection_pool()
        
        # 测试连接池初始状态
        self.assertEqual(pool.active_connections, 0)
        self.assertEqual(pool.max_connections, 100)  # 默认值
        
        # 模拟添加连接
        mock_connection = Mock()
        pool.add_connection('test_id', mock_connection)
        
        self.assertEqual(pool.active_connections, 1)
        self.assertIn('test_id', pool.connections)
    
    def test_bandwidth_monitoring(self):
        """测试带宽监控"""
        monitor = self.network_manager.get_bandwidth_monitor()
        
        # 模拟数据传输
        monitor.record_sent(1024)
        monitor.record_received(2048)
        
        stats = monitor.get_stats()
        self.assertEqual(stats['bytes_sent'], 1024)
        self.assertEqual(stats['bytes_received'], 2048)
        self.assertGreater(stats['total_bytes'], 0)

class TestAsyncOperations(RDPToolTestCase):
    """异步操作测试"""
    
    def setUp(self):
        super().setUp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        self.loop.close()
        super().tearDown()
    
    async def async_test_connection(self):
        """异步连接测试"""
        # 模拟异步连接
        await asyncio.sleep(0.1)
        return True
    
    def test_async_connection(self):
        """测试异步连接"""
        result = self.loop.run_until_complete(self.async_test_connection())
        self.assertTrue(result)
    
    async def async_test_data_transfer(self):
        """异步数据传输测试"""
        # 模拟数据传输
        data = b'test_data' * 1000
        await asyncio.sleep(0.05)  # 模拟网络延迟
        return len(data)
    
    def test_async_data_transfer(self):
        """测试异步数据传输"""
        result = self.loop.run_until_complete(self.async_test_data_transfer())
        self.assertEqual(result, 9000)  # len(b'test_data') * 1000

class TestErrorHandling(RDPToolTestCase):
    """错误处理测试"""
    
    def test_connection_timeout(self):
        """测试连接超时"""
        network_manager = NetworkManager()
        
        with self.assertRaises(Exception):
            # 尝试连接到不存在的地址
            network_manager.create_tcp_connection('192.0.2.1', 12345, timeout=1)
    
    def test_invalid_config(self):
        """测试无效配置"""
        config_manager = ConfigManager()
        
        with self.assertRaises(Exception):
            # 尝试加载不存在的配置文件
            config_manager.load_config('/nonexistent/config.json')
    
    def test_encryption_error(self):
        """测试加密错误"""
        security_manager = SecurityManager()
        
        with self.assertRaises(Exception):
            # 使用错误的密钥解密
            wrong_key = b'wrong_key_123456789012345678901234'
            encrypted_data = security_manager.encrypt(b'test', security_manager.generate_key())
            security_manager.decrypt(encrypted_data, wrong_key)

if __name__ == '__main__':
    unittest.main(verbosity=2)