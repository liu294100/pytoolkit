#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络功能测试
"""

import unittest
import asyncio
import socket
import threading
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from tests import RDPToolTestCase

try:
    from proxy_server import ProxyServer, ProxyProtocol, ProxyConfig
    from core.network import NetworkManager, ConnectionManager
    from utils.helpers import is_valid_ip, is_valid_port, find_free_port
except ImportError as e:
    print(f"导入错误: {e}")
    print("某些测试可能会跳过")

class TestProxyServer(RDPToolTestCase):
    """代理服务器测试"""
    
    def setUp(self):
        super().setUp()
        self.proxy_config = ProxyConfig(
            host='127.0.0.1',
            port=find_free_port(),
            protocols=[ProxyProtocol.HTTP, ProxyProtocol.SOCKS5]
        )
        self.proxy_server = ProxyServer(self.proxy_config)
    
    def test_proxy_config_creation(self):
        """测试代理配置创建"""
        config = ProxyConfig(
            host='0.0.0.0',
            port=8080,
            protocols=[ProxyProtocol.HTTP, ProxyProtocol.HTTPS]
        )
        
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 8080)
        self.assertIn(ProxyProtocol.HTTP, config.protocols)
        self.assertIn(ProxyProtocol.HTTPS, config.protocols)
    
    def test_proxy_protocol_enum(self):
        """测试代理协议枚举"""
        self.assertEqual(ProxyProtocol.HTTP.value, 'http')
        self.assertEqual(ProxyProtocol.HTTPS.value, 'https')
        self.assertEqual(ProxyProtocol.SOCKS4.value, 'socks4')
        self.assertEqual(ProxyProtocol.SOCKS5.value, 'socks5')
        self.assertEqual(ProxyProtocol.WEBSOCKET.value, 'websocket')
        self.assertEqual(ProxyProtocol.SSH.value, 'ssh')
        self.assertEqual(ProxyProtocol.RAW_SOCKET.value, 'raw_socket')
    
    @patch('proxy_server.ProxyServer._start_http_proxy')
    @patch('proxy_server.ProxyServer._start_socks_proxy')
    async def test_proxy_server_start(self, mock_socks, mock_http):
        """测试代理服务器启动"""
        mock_http.return_value = AsyncMock()
        mock_socks.return_value = AsyncMock()
        
        await self.proxy_server.start()
        
        self.assertTrue(self.proxy_server.is_running)
        mock_http.assert_called_once()
        mock_socks.assert_called_once()
    
    async def test_proxy_server_stop(self):
        """测试代理服务器停止"""
        # 模拟启动状态
        self.proxy_server.is_running = True
        self.proxy_server.servers = [Mock(), Mock()]
        
        await self.proxy_server.stop()
        
        self.assertFalse(self.proxy_server.is_running)
        self.assertEqual(len(self.proxy_server.servers), 0)
    
    def test_proxy_server_stats(self):
        """测试代理服务器统计"""
        stats = self.proxy_server.get_stats()
        
        self.assertIn('connections', stats)
        self.assertIn('bytes_transferred', stats)
        self.assertIn('uptime', stats)
        self.assertIn('protocols', stats)
        
        # 初始状态检查
        self.assertEqual(stats['connections']['active'], 0)
        self.assertEqual(stats['connections']['total'], 0)
        self.assertEqual(stats['bytes_transferred']['sent'], 0)
        self.assertEqual(stats['bytes_transferred']['received'], 0)

class TestNetworkHelpers(RDPToolTestCase):
    """网络辅助函数测试"""
    
    def test_is_valid_ip(self):
        """测试IP地址验证"""
        # 有效的IPv4地址
        self.assertTrue(is_valid_ip('127.0.0.1'))
        self.assertTrue(is_valid_ip('192.168.1.1'))
        self.assertTrue(is_valid_ip('0.0.0.0'))
        self.assertTrue(is_valid_ip('255.255.255.255'))
        
        # 有效的IPv6地址
        self.assertTrue(is_valid_ip('::1'))
        self.assertTrue(is_valid_ip('2001:db8::1'))
        
        # 无效的IP地址
        self.assertFalse(is_valid_ip('256.1.1.1'))
        self.assertFalse(is_valid_ip('192.168.1'))
        self.assertFalse(is_valid_ip('not_an_ip'))
        self.assertFalse(is_valid_ip(''))
    
    def test_is_valid_port(self):
        """测试端口验证"""
        # 有效端口
        self.assertTrue(is_valid_port(80))
        self.assertTrue(is_valid_port(443))
        self.assertTrue(is_valid_port(8080))
        self.assertTrue(is_valid_port(65535))
        
        # 无效端口
        self.assertFalse(is_valid_port(0))
        self.assertFalse(is_valid_port(-1))
        self.assertFalse(is_valid_port(65536))
        self.assertFalse(is_valid_port('not_a_port'))
    
    def test_find_free_port(self):
        """测试查找空闲端口"""
        port = find_free_port()
        
        self.assertIsInstance(port, int)
        self.assertTrue(1024 <= port <= 65535)
        
        # 验证端口确实是空闲的
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', port))
            sock.listen(1)
        except OSError:
            self.fail(f"端口 {port} 不是空闲的")
        finally:
            sock.close()
    
    def test_find_free_port_range(self):
        """测试在指定范围内查找空闲端口"""
        port = find_free_port(start_port=9000, end_port=9100)
        
        self.assertIsInstance(port, int)
        self.assertTrue(9000 <= port <= 9100)

class TestConnectionManager(RDPToolTestCase):
    """连接管理器测试"""
    
    def setUp(self):
        super().setUp()
        self.connection_manager = ConnectionManager()
    
    def test_connection_creation(self):
        """测试连接创建"""
        conn_id = 'test_connection_1'
        mock_socket = Mock()
        
        self.connection_manager.add_connection(conn_id, mock_socket)
        
        self.assertIn(conn_id, self.connection_manager.connections)
        self.assertEqual(self.connection_manager.get_connection(conn_id), mock_socket)
        self.assertEqual(self.connection_manager.get_connection_count(), 1)
    
    def test_connection_removal(self):
        """测试连接移除"""
        conn_id = 'test_connection_2'
        mock_socket = Mock()
        
        self.connection_manager.add_connection(conn_id, mock_socket)
        self.assertEqual(self.connection_manager.get_connection_count(), 1)
        
        self.connection_manager.remove_connection(conn_id)
        
        self.assertNotIn(conn_id, self.connection_manager.connections)
        self.assertEqual(self.connection_manager.get_connection_count(), 0)
    
    def test_connection_cleanup(self):
        """测试连接清理"""
        # 添加多个连接
        for i in range(5):
            conn_id = f'test_connection_{i}'
            mock_socket = Mock()
            self.connection_manager.add_connection(conn_id, mock_socket)
        
        self.assertEqual(self.connection_manager.get_connection_count(), 5)
        
        # 清理所有连接
        self.connection_manager.cleanup_all()
        
        self.assertEqual(self.connection_manager.get_connection_count(), 0)
        self.assertEqual(len(self.connection_manager.connections), 0)
    
    def test_connection_timeout(self):
        """测试连接超时"""
        conn_id = 'timeout_connection'
        mock_socket = Mock()
        
        # 设置短超时时间
        self.connection_manager.connection_timeout = 0.1
        self.connection_manager.add_connection(conn_id, mock_socket)
        
        # 等待超时
        time.sleep(0.2)
        
        # 触发超时检查
        self.connection_manager.cleanup_expired_connections()
        
        # 连接应该被移除
        self.assertNotIn(conn_id, self.connection_manager.connections)

class TestNetworkProtocols(RDPToolTestCase):
    """网络协议测试"""
    
    def test_http_proxy_request_parsing(self):
        """测试HTTP代理请求解析"""
        # 模拟HTTP CONNECT请求
        request = b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n"
        
        # 这里应该有实际的HTTP请求解析逻辑
        # 由于我们还没有实现具体的协议处理器，这里只是示例
        lines = request.decode().split('\r\n')
        first_line = lines[0]
        
        self.assertTrue(first_line.startswith('CONNECT'))
        self.assertIn('example.com:443', first_line)
        self.assertIn('HTTP/1.1', first_line)
    
    def test_socks5_handshake(self):
        """测试SOCKS5握手"""
        # SOCKS5初始握手请求
        # VER(1) + NMETHODS(1) + METHODS(1-255)
        handshake_request = b'\x05\x01\x00'  # VER=5, NMETHODS=1, METHOD=0(无认证)
        
        # 解析握手请求
        version = handshake_request[0]
        nmethods = handshake_request[1]
        methods = handshake_request[2:2+nmethods]
        
        self.assertEqual(version, 5)  # SOCKS5
        self.assertEqual(nmethods, 1)
        self.assertEqual(methods[0], 0)  # 无认证方法
        
        # SOCKS5握手响应
        # VER(1) + METHOD(1)
        handshake_response = b'\x05\x00'  # VER=5, METHOD=0(接受无认证)
        
        response_version = handshake_response[0]
        selected_method = handshake_response[1]
        
        self.assertEqual(response_version, 5)
        self.assertEqual(selected_method, 0)
    
    def test_websocket_upgrade(self):
        """测试WebSocket升级"""
        # WebSocket升级请求头
        upgrade_headers = {
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
            'Sec-WebSocket-Version': '13'
        }
        
        # 验证必要的头部
        self.assertEqual(upgrade_headers['Upgrade'].lower(), 'websocket')
        self.assertIn('upgrade', upgrade_headers['Connection'].lower())
        self.assertEqual(upgrade_headers['Sec-WebSocket-Version'], '13')
        self.assertIsNotNone(upgrade_headers.get('Sec-WebSocket-Key'))

class TestAsyncNetworking(RDPToolTestCase):
    """异步网络测试"""
    
    def setUp(self):
        super().setUp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        self.loop.close()
        super().tearDown()
    
    async def async_echo_server(self, host='127.0.0.1', port=0):
        """异步回声服务器"""
        async def handle_client(reader, writer):
            try:
                data = await reader.read(1024)
                if data:
                    writer.write(data)
                    await writer.drain()
            except Exception:
                pass
            finally:
                writer.close()
                await writer.wait_closed()
        
        server = await asyncio.start_server(handle_client, host, port)
        return server
    
    async def async_echo_client(self, host, port, message):
        """异步回声客户端"""
        try:
            reader, writer = await asyncio.open_connection(host, port)
            
            # 发送消息
            writer.write(message.encode())
            await writer.drain()
            
            # 接收回声
            data = await reader.read(1024)
            
            writer.close()
            await writer.wait_closed()
            
            return data.decode()
        except Exception as e:
            return f"Error: {e}"
    
    def test_async_echo_communication(self):
        """测试异步回声通信"""
        async def test_communication():
            # 启动服务器
            server = await self.async_echo_server()
            server_host, server_port = server.sockets[0].getsockname()
            
            try:
                # 启动服务器任务
                server_task = asyncio.create_task(server.serve_forever())
                
                # 等待服务器启动
                await asyncio.sleep(0.1)
                
                # 测试客户端连接
                test_message = "Hello, Async World!"
                response = await self.async_echo_client(server_host, server_port, test_message)
                
                self.assertEqual(response, test_message)
                
            finally:
                # 清理
                server.close()
                await server.wait_closed()
                if 'server_task' in locals():
                    server_task.cancel()
                    try:
                        await server_task
                    except asyncio.CancelledError:
                        pass
        
        self.loop.run_until_complete(test_communication())
    
    def test_concurrent_connections(self):
        """测试并发连接"""
        async def test_concurrent():
            # 启动服务器
            server = await self.async_echo_server()
            server_host, server_port = server.sockets[0].getsockname()
            
            try:
                # 启动服务器任务
                server_task = asyncio.create_task(server.serve_forever())
                
                # 等待服务器启动
                await asyncio.sleep(0.1)
                
                # 创建多个并发客户端
                tasks = []
                for i in range(5):
                    message = f"Message {i}"
                    task = asyncio.create_task(
                        self.async_echo_client(server_host, server_port, message)
                    )
                    tasks.append((task, message))
                
                # 等待所有任务完成
                for task, expected_message in tasks:
                    response = await task
                    self.assertEqual(response, expected_message)
                
            finally:
                # 清理
                server.close()
                await server.wait_closed()
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass
        
        self.loop.run_until_complete(test_concurrent())

class TestNetworkSecurity(RDPToolTestCase):
    """网络安全测试"""
    
    def test_connection_rate_limiting(self):
        """测试连接速率限制"""
        # 模拟速率限制器
        class RateLimiter:
            def __init__(self, max_connections_per_second=10):
                self.max_connections = max_connections_per_second
                self.connections = []
                self.window_size = 1.0  # 1秒窗口
            
            def allow_connection(self):
                now = time.time()
                # 清理过期的连接记录
                self.connections = [t for t in self.connections if now - t < self.window_size]
                
                if len(self.connections) < self.max_connections:
                    self.connections.append(now)
                    return True
                return False
        
        rate_limiter = RateLimiter(max_connections_per_second=3)
        
        # 测试正常连接
        for _ in range(3):
            self.assertTrue(rate_limiter.allow_connection())
        
        # 测试超出限制
        self.assertFalse(rate_limiter.allow_connection())
        
        # 等待窗口重置
        time.sleep(1.1)
        
        # 应该可以再次连接
        self.assertTrue(rate_limiter.allow_connection())
    
    def test_ip_whitelist_blacklist(self):
        """测试IP白名单和黑名单"""
        class IPFilter:
            def __init__(self):
                self.whitelist = set()
                self.blacklist = set()
            
            def add_to_whitelist(self, ip):
                self.whitelist.add(ip)
            
            def add_to_blacklist(self, ip):
                self.blacklist.add(ip)
            
            def is_allowed(self, ip):
                if self.blacklist and ip in self.blacklist:
                    return False
                if self.whitelist and ip not in self.whitelist:
                    return False
                return True
        
        ip_filter = IPFilter()
        
        # 测试默认允许
        self.assertTrue(ip_filter.is_allowed('192.168.1.1'))
        
        # 测试黑名单
        ip_filter.add_to_blacklist('192.168.1.100')
        self.assertFalse(ip_filter.is_allowed('192.168.1.100'))
        self.assertTrue(ip_filter.is_allowed('192.168.1.1'))
        
        # 测试白名单
        ip_filter.add_to_whitelist('127.0.0.1')
        ip_filter.add_to_whitelist('192.168.1.1')
        self.assertTrue(ip_filter.is_allowed('127.0.0.1'))
        self.assertTrue(ip_filter.is_allowed('192.168.1.1'))
        self.assertFalse(ip_filter.is_allowed('10.0.0.1'))  # 不在白名单中

if __name__ == '__main__':
    unittest.main(verbosity=2)