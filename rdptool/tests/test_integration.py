#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试
"""

import unittest
import asyncio
import threading
import time
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from tests import RDPToolTestCase

try:
    from main import main, create_default_config, run_server, run_client, run_proxy
    from proxy_server import ProxyServer, ProxyConfig, ProxyProtocol
    from core.network import NetworkManager, ConnectionManager
    from core.security import SecurityManager
    from utils.config import ConfigManager
    from utils.logger import get_logger
except ImportError as e:
    print(f"导入错误: {e}")
    print("某些集成测试可能会跳过")

class TestMainIntegration(RDPToolTestCase):
    """主程序集成测试"""
    
    def setUp(self):
        super().setUp()
        self.temp_config_dir = self.get_test_temp_path('configs')
        self.temp_config_dir.mkdir(exist_ok=True)
    
    def test_config_generation(self):
        """测试配置文件生成"""
        # 测试服务端配置生成
        server_config = create_default_config('server')
        
        self.assertIn('server', server_config)
        self.assertIn('host', server_config['server'])
        self.assertIn('port', server_config['server'])
        self.assertIn('security', server_config)
        self.assertIn('logging', server_config)
        
        # 测试客户端配置生成
        client_config = create_default_config('client')
        
        self.assertIn('client', client_config)
        self.assertIn('server_host', client_config['client'])
        self.assertIn('server_port', client_config['client'])
        self.assertIn('display', client_config)
        
        # 测试代理配置生成
        proxy_config = create_default_config('proxy')
        
        self.assertIn('proxy', proxy_config)
        self.assertIn('host', proxy_config['proxy'])
        self.assertIn('port', proxy_config['proxy'])
        self.assertIn('protocols', proxy_config['proxy'])
    
    @patch('main.RDPServer')
    async def test_server_startup(self, mock_rdp_server):
        """测试服务端启动"""
        mock_server = AsyncMock()
        mock_rdp_server.return_value = mock_server
        mock_server.start.return_value = True
        
        # 创建测试配置
        config = {
            'server': {
                'host': '127.0.0.1',
                'port': 8888
            },
            'security': {
                'encryption': True
            }
        }
        
        # 测试服务端启动
        result = await run_server(config)
        
        self.assertTrue(result)
        mock_rdp_server.assert_called_once()
        mock_server.start.assert_called_once()
    
    @patch('main.RDPClient')
    async def test_client_startup(self, mock_rdp_client):
        """测试客户端启动"""
        mock_client = AsyncMock()
        mock_rdp_client.return_value = mock_client
        mock_client.connect.return_value = True
        
        # 创建测试配置
        config = {
            'client': {
                'server_host': '127.0.0.1',
                'server_port': 8888
            },
            'display': {
                'resolution': '1920x1080'
            }
        }
        
        # 测试客户端启动
        result = await run_client(config)
        
        self.assertTrue(result)
        mock_rdp_client.assert_called_once()
        mock_client.connect.assert_called_once()
    
    @patch('main.ProxyServer')
    async def test_proxy_startup(self, mock_proxy_server):
        """测试代理服务启动"""
        mock_proxy = AsyncMock()
        mock_proxy_server.return_value = mock_proxy
        mock_proxy.start.return_value = True
        
        # 创建测试配置
        config = {
            'proxy': {
                'host': '127.0.0.1',
                'port': 8080,
                'protocols': ['http', 'socks5']
            }
        }
        
        # 测试代理启动
        result = await run_proxy(config)
        
        self.assertTrue(result)
        mock_proxy_server.assert_called_once()
        mock_proxy.start.assert_called_once()

class TestServerClientIntegration(RDPToolTestCase):
    """服务端-客户端集成测试"""
    
    def setUp(self):
        super().setUp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        self.loop.close()
        super().tearDown()
    
    async def mock_server_client_communication(self):
        """模拟服务端-客户端通信"""
        # 模拟服务端
        server_messages = []
        
        async def mock_server_handler(reader, writer):
            try:
                while True:
                    data = await reader.read(1024)
                    if not data:
                        break
                    
                    message = data.decode()
                    server_messages.append(message)
                    
                    # 回复客户端
                    response = f"Server received: {message}"
                    writer.write(response.encode())
                    await writer.drain()
            except Exception:
                pass
            finally:
                writer.close()
                await writer.wait_closed()
        
        # 启动模拟服务器
        server = await asyncio.start_server(mock_server_handler, '127.0.0.1', 0)
        server_host, server_port = server.sockets[0].getsockname()
        
        try:
            # 启动服务器任务
            server_task = asyncio.create_task(server.serve_forever())
            
            # 等待服务器启动
            await asyncio.sleep(0.1)
            
            # 模拟客户端连接
            reader, writer = await asyncio.open_connection(server_host, server_port)
            
            # 发送测试消息
            test_messages = ['Hello', 'Test Message', 'Goodbye']
            responses = []
            
            for message in test_messages:
                writer.write(message.encode())
                await writer.drain()
                
                response_data = await reader.read(1024)
                responses.append(response_data.decode())
            
            writer.close()
            await writer.wait_closed()
            
            return server_messages, responses
            
        finally:
            # 清理
            server.close()
            await server.wait_closed()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    def test_server_client_communication(self):
        """测试服务端-客户端通信"""
        server_messages, client_responses = self.loop.run_until_complete(
            self.mock_server_client_communication()
        )
        
        # 验证通信
        expected_messages = ['Hello', 'Test Message', 'Goodbye']
        self.assertEqual(server_messages, expected_messages)
        
        for i, response in enumerate(client_responses):
            expected_response = f"Server received: {expected_messages[i]}"
            self.assertEqual(response, expected_response)
    
    async def test_multiple_client_connections(self):
        """测试多客户端连接"""
        connected_clients = []
        
        async def mock_server_handler(reader, writer):
            client_id = len(connected_clients)
            connected_clients.append(client_id)
            
            try:
                # 发送欢迎消息
                welcome = f"Welcome client {client_id}"
                writer.write(welcome.encode())
                await writer.drain()
                
                # 保持连接
                await asyncio.sleep(0.1)
                
            except Exception:
                pass
            finally:
                writer.close()
                await writer.wait_closed()
        
        # 启动服务器
        server = await asyncio.start_server(mock_server_handler, '127.0.0.1', 0)
        server_host, server_port = server.sockets[0].getsockname()
        
        try:
            server_task = asyncio.create_task(server.serve_forever())
            await asyncio.sleep(0.1)
            
            # 创建多个客户端连接
            num_clients = 5
            client_tasks = []
            
            async def client_connect(client_id):
                reader, writer = await asyncio.open_connection(server_host, server_port)
                
                # 接收欢迎消息
                welcome_data = await reader.read(1024)
                welcome_message = welcome_data.decode()
                
                writer.close()
                await writer.wait_closed()
                
                return welcome_message
            
            # 启动所有客户端
            for i in range(num_clients):
                task = asyncio.create_task(client_connect(i))
                client_tasks.append(task)
            
            # 等待所有客户端完成
            welcome_messages = await asyncio.gather(*client_tasks)
            
            # 验证结果
            self.assertEqual(len(connected_clients), num_clients)
            self.assertEqual(len(welcome_messages), num_clients)
            
            for i, message in enumerate(welcome_messages):
                self.assertIn(f"client {i}", message)
            
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    def test_multiple_clients(self):
        """运行多客户端测试"""
        self.loop.run_until_complete(self.test_multiple_client_connections())

class TestProxyIntegration(RDPToolTestCase):
    """代理集成测试"""
    
    def setUp(self):
        super().setUp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        self.loop.close()
        super().tearDown()
    
    def test_proxy_server_integration(self):
        """测试代理服务器集成"""
        # 创建代理配置
        proxy_config = ProxyConfig(
            host='127.0.0.1',
            port=0,  # 自动分配端口
            protocols=[ProxyProtocol.HTTP, ProxyProtocol.SOCKS5]
        )
        
        proxy_server = ProxyServer(proxy_config)
        
        # 测试代理服务器创建
        self.assertIsNotNone(proxy_server)
        self.assertEqual(proxy_server.config, proxy_config)
        self.assertFalse(proxy_server.is_running)
        
        # 测试统计信息
        stats = proxy_server.get_stats()
        self.assertIn('connections', stats)
        self.assertIn('bytes_transferred', stats)
        self.assertIn('protocols', stats)
    
    async def test_proxy_http_handling(self):
        """测试代理HTTP处理"""
        # 模拟HTTP代理请求处理
        async def mock_http_proxy_handler(reader, writer):
            try:
                # 读取HTTP请求
                request_data = await reader.read(1024)
                request = request_data.decode()
                
                # 解析CONNECT请求
                if request.startswith('CONNECT'):
                    # 发送200 Connection established响应
                    response = "HTTP/1.1 200 Connection established\r\n\r\n"
                    writer.write(response.encode())
                    await writer.drain()
                    
                    # 模拟隧道建立
                    tunnel_data = await reader.read(1024)
                    if tunnel_data:
                        # 回显数据（模拟目标服务器）
                        writer.write(tunnel_data)
                        await writer.drain()
                
            except Exception:
                pass
            finally:
                writer.close()
                await writer.wait_closed()
        
        # 启动模拟代理服务器
        proxy_server = await asyncio.start_server(mock_http_proxy_handler, '127.0.0.1', 0)
        proxy_host, proxy_port = proxy_server.sockets[0].getsockname()
        
        try:
            server_task = asyncio.create_task(proxy_server.serve_forever())
            await asyncio.sleep(0.1)
            
            # 模拟客户端通过代理连接
            reader, writer = await asyncio.open_connection(proxy_host, proxy_port)
            
            # 发送CONNECT请求
            connect_request = "CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n"
            writer.write(connect_request.encode())
            await writer.drain()
            
            # 读取代理响应
            response_data = await reader.read(1024)
            response = response_data.decode()
            
            # 验证连接建立响应
            self.assertIn('200 Connection established', response)
            
            # 发送隧道数据
            tunnel_message = "Hello through proxy"
            writer.write(tunnel_message.encode())
            await writer.drain()
            
            # 接收回显数据
            echo_data = await reader.read(1024)
            echo_message = echo_data.decode()
            
            self.assertEqual(echo_message, tunnel_message)
            
            writer.close()
            await writer.wait_closed()
            
        finally:
            proxy_server.close()
            await proxy_server.wait_closed()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    def test_http_proxy_integration(self):
        """运行HTTP代理集成测试"""
        self.loop.run_until_complete(self.test_proxy_http_handling())

class TestSecurityIntegration(RDPToolTestCase):
    """安全集成测试"""
    
    def setUp(self):
        super().setUp()
        self.security_manager = SecurityManager()
        self.config_manager = ConfigManager()
    
    def test_end_to_end_encryption(self):
        """测试端到端加密"""
        # 生成密钥对
        server_key = self.security_manager.generate_key()
        client_key = self.security_manager.generate_key()
        
        # 模拟客户端发送加密数据
        original_message = "This is a secret message from client to server"
        
        # 客户端加密
        encrypted_message = self.security_manager.encrypt(
            original_message.encode(), client_key
        )
        
        # 服务端解密（假设密钥已交换）
        decrypted_message = self.security_manager.decrypt(
            encrypted_message, client_key
        )
        
        self.assertEqual(original_message, decrypted_message.decode())
        
        # 模拟服务端回复
        server_reply = "Server received your message"
        
        # 服务端加密回复
        encrypted_reply = self.security_manager.encrypt(
            server_reply.encode(), server_key
        )
        
        # 客户端解密回复
        decrypted_reply = self.security_manager.decrypt(
            encrypted_reply, server_key
        )
        
        self.assertEqual(server_reply, decrypted_reply.decode())
    
    def test_authentication_flow(self):
        """测试认证流程"""
        # 模拟用户注册
        username = "test_user"
        password = "secure_password_123"
        
        # 服务端存储密码哈希
        password_hash = self.security_manager.hash_password(password)
        
        # 模拟用户登录
        login_password = "secure_password_123"
        
        # 验证密码
        is_valid = self.security_manager.verify_password(login_password, password_hash)
        self.assertTrue(is_valid)
        
        # 测试错误密码
        wrong_password = "wrong_password"
        is_valid = self.security_manager.verify_password(wrong_password, password_hash)
        self.assertFalse(is_valid)
    
    def test_secure_config_handling(self):
        """测试安全配置处理"""
        # 创建包含敏感信息的配置
        sensitive_config = {
            'database': {
                'host': 'localhost',
                'username': 'admin',
                'password': 'super_secret_password'
            },
            'api_keys': {
                'service_a': 'key_123456789',
                'service_b': 'key_987654321'
            }
        }
        
        # 保存配置（应该加密敏感字段）
        config_file = self.get_test_temp_path('secure_config.json')
        
        # 模拟安全配置保存
        encrypted_config = sensitive_config.copy()
        
        # 加密敏感字段
        key = self.security_manager.generate_key()
        
        encrypted_config['database']['password'] = self.security_manager.encrypt(
            sensitive_config['database']['password'].encode(), key
        ).hex()
        
        for service, api_key in sensitive_config['api_keys'].items():
            encrypted_config['api_keys'][service] = self.security_manager.encrypt(
                api_key.encode(), key
            ).hex()
        
        # 保存加密配置
        self.config_manager.save_config(encrypted_config, str(config_file))
        
        # 加载并解密配置
        loaded_config = self.config_manager.load_config(str(config_file))
        
        # 解密敏感字段
        decrypted_password = self.security_manager.decrypt(
            bytes.fromhex(loaded_config['database']['password']), key
        ).decode()
        
        self.assertEqual(decrypted_password, sensitive_config['database']['password'])
        
        for service, encrypted_key in loaded_config['api_keys'].items():
            decrypted_key = self.security_manager.decrypt(
                bytes.fromhex(encrypted_key), key
            ).decode()
            self.assertEqual(decrypted_key, sensitive_config['api_keys'][service])

class TestFullSystemIntegration(RDPToolTestCase):
    """完整系统集成测试"""
    
    def setUp(self):
        super().setUp()
        self.temp_dir = self.get_test_temp_path('full_system_test')
        self.temp_dir.mkdir(exist_ok=True)
    
    def test_config_to_runtime_integration(self):
        """测试从配置到运行时的完整流程"""
        # 1. 创建配置文件
        server_config = {
            'server': {
                'host': '127.0.0.1',
                'port': 8888,
                'max_connections': 10
            },
            'security': {
                'encryption': True,
                'authentication': True
            },
            'logging': {
                'level': 'INFO',
                'file': str(self.temp_dir / 'server.log')
            }
        }
        
        config_file = self.temp_dir / 'server_config.json'
        with open(config_file, 'w') as f:
            json.dump(server_config, f, indent=2)
        
        # 2. 加载配置
        config_manager = ConfigManager()
        loaded_config = config_manager.load_config(str(config_file))
        
        # 3. 验证配置加载
        self.assertEqual(loaded_config['server']['host'], '127.0.0.1')
        self.assertEqual(loaded_config['server']['port'], 8888)
        self.assertTrue(loaded_config['security']['encryption'])
        
        # 4. 模拟组件初始化
        network_manager = NetworkManager()
        security_manager = SecurityManager()
        
        # 5. 验证组件可以使用配置
        self.assertIsNotNone(network_manager)
        self.assertIsNotNone(security_manager)
        
        # 6. 测试日志配置
        logger = get_logger('test_integration')
        logger.info("Integration test message")
        
        # 验证日志文件创建（如果日志系统已实现）
        # log_file = Path(loaded_config['logging']['file'])
        # self.assertTrue(log_file.exists())
    
    def test_component_interaction(self):
        """测试组件间交互"""
        # 创建各个组件
        network_manager = NetworkManager()
        security_manager = SecurityManager()
        connection_manager = ConnectionManager()
        
        # 测试组件协作
        # 1. 网络管理器创建连接
        mock_connection = Mock()
        
        # 2. 连接管理器管理连接
        conn_id = 'test_integration_conn'
        connection_manager.add_connection(conn_id, mock_connection)
        
        # 3. 安全管理器处理加密
        test_data = b"Integration test data"
        key = security_manager.generate_key()
        encrypted_data = security_manager.encrypt(test_data, key)
        
        # 4. 验证组件协作结果
        self.assertEqual(connection_manager.get_connection_count(), 1)
        self.assertIsNotNone(connection_manager.get_connection(conn_id))
        
        decrypted_data = security_manager.decrypt(encrypted_data, key)
        self.assertEqual(test_data, decrypted_data)
        
        # 5. 清理
        connection_manager.remove_connection(conn_id)
        self.assertEqual(connection_manager.get_connection_count(), 0)
    
    def test_error_propagation(self):
        """测试错误传播"""
        # 测试配置错误传播
        config_manager = ConfigManager()
        
        with self.assertRaises(Exception):
            config_manager.load_config('/nonexistent/config.json')
        
        # 测试网络错误传播
        network_manager = NetworkManager()
        
        with self.assertRaises(Exception):
            # 尝试连接到无效地址
            network_manager.create_tcp_connection('invalid.host', 99999, timeout=1)
        
        # 测试安全错误传播
        security_manager = SecurityManager()
        
        with self.assertRaises(Exception):
            # 使用错误密钥解密
            wrong_key = b'wrong_key_123456789012345678901234'
            test_data = b'test'
            correct_key = security_manager.generate_key()
            encrypted = security_manager.encrypt(test_data, correct_key)
            security_manager.decrypt(encrypted, wrong_key)

if __name__ == '__main__':
    unittest.main(verbosity=2)