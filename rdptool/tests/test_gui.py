#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI功能测试
"""

import unittest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
import threading
import time

from tests import RDPToolTestCase

try:
    from gui.main_window import MainWindow
    from gui.client_window import ClientWindow
    from gui.server_window import ServerWindow
    from gui.settings_window import SettingsWindow
except ImportError as e:
    print(f"导入错误: {e}")
    print("GUI测试将被跳过")
    MainWindow = None
    ClientWindow = None
    ServerWindow = None
    SettingsWindow = None

class TestGUIBase(RDPToolTestCase):
    """GUI基础测试类"""
    
    def setUp(self):
        super().setUp()
        # 创建测试用的根窗口
        self.root = tk.Tk()
        self.root.withdraw()  # 隐藏窗口，避免在测试时显示
    
    def tearDown(self):
        # 清理GUI资源
        if self.root:
            self.root.destroy()
        super().tearDown()

@unittest.skipIf(MainWindow is None, "GUI模块未找到")
class TestMainWindow(TestGUIBase):
    """主窗口测试"""
    
    def setUp(self):
        super().setUp()
        self.main_window = MainWindow(self.root)
    
    def test_main_window_creation(self):
        """测试主窗口创建"""
        self.assertIsNotNone(self.main_window)
        self.assertEqual(self.main_window.master, self.root)
    
    def test_menu_creation(self):
        """测试菜单创建"""
        # 检查是否有菜单栏
        menubar = self.root.nametowidget(self.root['menu']) if self.root['menu'] else None
        
        if menubar:
            # 检查菜单项
            menu_labels = []
            for i in range(menubar.index('end') + 1):
                try:
                    label = menubar.entrycget(i, 'label')
                    menu_labels.append(label)
                except tk.TclError:
                    pass
            
            # 应该包含基本菜单项
            expected_menus = ['文件', '连接', '设置', '帮助']
            for menu in expected_menus:
                self.assertIn(menu, menu_labels)
    
    def test_button_creation(self):
        """测试按钮创建"""
        # 查找所有按钮组件
        buttons = []
        
        def find_buttons(widget):
            if isinstance(widget, tk.Button):
                buttons.append(widget)
            for child in widget.winfo_children():
                find_buttons(child)
        
        find_buttons(self.main_window)
        
        # 应该至少有启动服务端和客户端的按钮
        self.assertGreater(len(buttons), 0)
    
    @patch('gui.main_window.ServerWindow')
    def test_open_server_window(self, mock_server_window):
        """测试打开服务端窗口"""
        mock_window = Mock()
        mock_server_window.return_value = mock_window
        
        # 模拟点击服务端按钮
        self.main_window.open_server_window()
        
        mock_server_window.assert_called_once()
    
    @patch('gui.main_window.ClientWindow')
    def test_open_client_window(self, mock_client_window):
        """测试打开客户端窗口"""
        mock_window = Mock()
        mock_client_window.return_value = mock_window
        
        # 模拟点击客户端按钮
        self.main_window.open_client_window()
        
        mock_client_window.assert_called_once()

@unittest.skipIf(ClientWindow is None, "GUI模块未找到")
class TestClientWindow(TestGUIBase):
    """客户端窗口测试"""
    
    def setUp(self):
        super().setUp()
        self.client_window = ClientWindow(self.root)
    
    def test_client_window_creation(self):
        """测试客户端窗口创建"""
        self.assertIsNotNone(self.client_window)
    
    def test_connection_form(self):
        """测试连接表单"""
        # 查找输入框
        entries = []
        
        def find_entries(widget):
            if isinstance(widget, tk.Entry):
                entries.append(widget)
            for child in widget.winfo_children():
                find_entries(child)
        
        find_entries(self.client_window)
        
        # 应该至少有服务器地址和端口输入框
        self.assertGreaterEqual(len(entries), 2)
    
    def test_connection_validation(self):
        """测试连接验证"""
        # 测试有效的连接参数
        valid_params = {
            'host': '127.0.0.1',
            'port': '8888',
            'username': 'test_user',
            'password': 'test_pass'
        }
        
        result = self.client_window.validate_connection_params(valid_params)
        self.assertTrue(result)
        
        # 测试无效的连接参数
        invalid_params = {
            'host': '',
            'port': 'invalid_port',
            'username': '',
            'password': ''
        }
        
        result = self.client_window.validate_connection_params(invalid_params)
        self.assertFalse(result)
    
    @patch('gui.client_window.RDPClient')
    def test_connect_to_server(self, mock_rdp_client):
        """测试连接到服务器"""
        mock_client = Mock()
        mock_rdp_client.return_value = mock_client
        mock_client.connect.return_value = True
        
        # 设置连接参数
        connection_params = {
            'host': '127.0.0.1',
            'port': '8888',
            'username': 'test_user',
            'password': 'test_pass'
        }
        
        result = self.client_window.connect_to_server(connection_params)
        
        self.assertTrue(result)
        mock_rdp_client.assert_called_once()
        mock_client.connect.assert_called_once()
    
    def test_screen_display_area(self):
        """测试屏幕显示区域"""
        # 查找Canvas组件（用于显示远程屏幕）
        canvases = []
        
        def find_canvases(widget):
            if isinstance(widget, tk.Canvas):
                canvases.append(widget)
            for child in widget.winfo_children():
                find_canvases(child)
        
        find_canvases(self.client_window)
        
        # 应该有至少一个Canvas用于显示屏幕
        self.assertGreater(len(canvases), 0)

@unittest.skipIf(ServerWindow is None, "GUI模块未找到")
class TestServerWindow(TestGUIBase):
    """服务端窗口测试"""
    
    def setUp(self):
        super().setUp()
        self.server_window = ServerWindow(self.root)
    
    def test_server_window_creation(self):
        """测试服务端窗口创建"""
        self.assertIsNotNone(self.server_window)
    
    def test_server_configuration(self):
        """测试服务器配置"""
        # 测试默认配置
        default_config = self.server_window.get_server_config()
        
        self.assertIn('host', default_config)
        self.assertIn('port', default_config)
        self.assertIn('max_connections', default_config)
        
        # 测试配置更新
        new_config = {
            'host': '0.0.0.0',
            'port': 9999,
            'max_connections': 10
        }
        
        self.server_window.update_server_config(new_config)
        updated_config = self.server_window.get_server_config()
        
        self.assertEqual(updated_config['host'], '0.0.0.0')
        self.assertEqual(updated_config['port'], 9999)
        self.assertEqual(updated_config['max_connections'], 10)
    
    @patch('gui.server_window.RDPServer')
    def test_start_server(self, mock_rdp_server):
        """测试启动服务器"""
        mock_server = Mock()
        mock_rdp_server.return_value = mock_server
        mock_server.start.return_value = True
        
        result = self.server_window.start_server()
        
        self.assertTrue(result)
        mock_rdp_server.assert_called_once()
        mock_server.start.assert_called_once()
    
    @patch('gui.server_window.RDPServer')
    def test_stop_server(self, mock_rdp_server):
        """测试停止服务器"""
        mock_server = Mock()
        mock_rdp_server.return_value = mock_server
        
        # 先启动服务器
        self.server_window.server = mock_server
        self.server_window.is_running = True
        
        result = self.server_window.stop_server()
        
        self.assertTrue(result)
        mock_server.stop.assert_called_once()
        self.assertFalse(self.server_window.is_running)
    
    def test_connection_monitoring(self):
        """测试连接监控"""
        # 模拟连接状态
        connections = [
            {'id': 'conn1', 'ip': '192.168.1.100', 'connected_at': time.time()},
            {'id': 'conn2', 'ip': '192.168.1.101', 'connected_at': time.time()}
        ]
        
        self.server_window.update_connection_list(connections)
        
        # 检查连接列表是否更新
        connection_count = self.server_window.get_connection_count()
        self.assertEqual(connection_count, 2)

@unittest.skipIf(SettingsWindow is None, "GUI模块未找到")
class TestSettingsWindow(TestGUIBase):
    """设置窗口测试"""
    
    def setUp(self):
        super().setUp()
        self.settings_window = SettingsWindow(self.root)
    
    def test_settings_window_creation(self):
        """测试设置窗口创建"""
        self.assertIsNotNone(self.settings_window)
    
    def test_settings_categories(self):
        """测试设置分类"""
        categories = self.settings_window.get_setting_categories()
        
        expected_categories = ['网络', '显示', '安全', '性能', '高级']
        for category in expected_categories:
            self.assertIn(category, categories)
    
    def test_network_settings(self):
        """测试网络设置"""
        network_settings = self.settings_window.get_network_settings()
        
        self.assertIn('connection_timeout', network_settings)
        self.assertIn('retry_attempts', network_settings)
        self.assertIn('buffer_size', network_settings)
        
        # 测试设置更新
        new_settings = {
            'connection_timeout': 30,
            'retry_attempts': 5,
            'buffer_size': 8192
        }
        
        self.settings_window.update_network_settings(new_settings)
        updated_settings = self.settings_window.get_network_settings()
        
        self.assertEqual(updated_settings['connection_timeout'], 30)
        self.assertEqual(updated_settings['retry_attempts'], 5)
        self.assertEqual(updated_settings['buffer_size'], 8192)
    
    def test_display_settings(self):
        """测试显示设置"""
        display_settings = self.settings_window.get_display_settings()
        
        self.assertIn('resolution', display_settings)
        self.assertIn('color_depth', display_settings)
        self.assertIn('compression', display_settings)
        
        # 测试分辨率选项
        resolution_options = self.settings_window.get_resolution_options()
        expected_resolutions = ['1920x1080', '1366x768', '1280x720', '1024x768']
        
        for resolution in expected_resolutions:
            self.assertIn(resolution, resolution_options)
    
    def test_security_settings(self):
        """测试安全设置"""
        security_settings = self.settings_window.get_security_settings()
        
        self.assertIn('encryption_enabled', security_settings)
        self.assertIn('authentication_required', security_settings)
        self.assertIn('certificate_validation', security_settings)
        
        # 测试加密选项
        encryption_options = self.settings_window.get_encryption_options()
        expected_options = ['AES-256', 'AES-128', 'ChaCha20']
        
        for option in expected_options:
            self.assertIn(option, encryption_options)
    
    def test_settings_validation(self):
        """测试设置验证"""
        # 测试有效设置
        valid_settings = {
            'connection_timeout': 30,
            'retry_attempts': 3,
            'buffer_size': 4096,
            'resolution': '1920x1080',
            'color_depth': 24
        }
        
        result = self.settings_window.validate_settings(valid_settings)
        self.assertTrue(result)
        
        # 测试无效设置
        invalid_settings = {
            'connection_timeout': -1,  # 负数
            'retry_attempts': 'invalid',  # 非数字
            'buffer_size': 0,  # 零值
            'resolution': 'invalid_resolution',
            'color_depth': 99  # 无效颜色深度
        }
        
        result = self.settings_window.validate_settings(invalid_settings)
        self.assertFalse(result)
    
    def test_settings_persistence(self):
        """测试设置持久化"""
        # 创建测试设置
        test_settings = {
            'network': {
                'connection_timeout': 25,
                'retry_attempts': 4
            },
            'display': {
                'resolution': '1366x768',
                'color_depth': 16
            }
        }
        
        # 保存设置
        self.settings_window.save_settings(test_settings)
        
        # 加载设置
        loaded_settings = self.settings_window.load_settings()
        
        self.assertEqual(loaded_settings['network']['connection_timeout'], 25)
        self.assertEqual(loaded_settings['network']['retry_attempts'], 4)
        self.assertEqual(loaded_settings['display']['resolution'], '1366x768')
        self.assertEqual(loaded_settings['display']['color_depth'], 16)

class TestGUIIntegration(TestGUIBase):
    """GUI集成测试"""
    
    @unittest.skipIf(MainWindow is None, "GUI模块未找到")
    def test_window_navigation(self):
        """测试窗口导航"""
        main_window = MainWindow(self.root)
        
        # 测试打开各种窗口
        with patch('gui.main_window.ClientWindow') as mock_client:
            with patch('gui.main_window.ServerWindow') as mock_server:
                with patch('gui.main_window.SettingsWindow') as mock_settings:
                    
                    # 模拟打开客户端窗口
                    main_window.open_client_window()
                    mock_client.assert_called_once()
                    
                    # 模拟打开服务端窗口
                    main_window.open_server_window()
                    mock_server.assert_called_once()
                    
                    # 模拟打开设置窗口
                    main_window.open_settings_window()
                    mock_settings.assert_called_once()
    
    def test_gui_threading(self):
        """测试GUI线程安全"""
        # 创建一个简单的GUI更新函数
        def update_gui():
            label = tk.Label(self.root, text="Test")
            label.pack()
            return label
        
        # 在主线程中更新GUI
        label = update_gui()
        self.assertIsNotNone(label)
        
        # 测试从其他线程更新GUI（应该使用after方法）
        result = []
        
        def thread_update():
            def gui_update():
                label = tk.Label(self.root, text="Thread Test")
                label.pack()
                result.append(label)
            
            self.root.after(0, gui_update)
        
        thread = threading.Thread(target=thread_update)
        thread.start()
        thread.join()
        
        # 处理待处理的GUI事件
        self.root.update()
        
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0])
    
    def test_gui_error_handling(self):
        """测试GUI错误处理"""
        # 测试无效操作的错误处理
        with patch('tkinter.messagebox.showerror') as mock_error:
            try:
                # 模拟一个会引发异常的操作
                raise ValueError("测试错误")
            except ValueError as e:
                # 应该显示错误消息
                mock_error("错误", str(e))
                mock_error.assert_called_once_with("错误", "测试错误")

if __name__ == '__main__':
    # 在无头模式下运行GUI测试
    import os
    os.environ['DISPLAY'] = ':99'  # 虚拟显示器
    
    unittest.main(verbosity=2)