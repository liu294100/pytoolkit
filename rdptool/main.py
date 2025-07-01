#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
远程桌面工具主入口

提供统一的命令行接口：
- 启动服务端
- 启动客户端
- 配置管理
- 代理服务
"""

import asyncio
import argparse
import sys
import signal
import logging
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from server import RDPServer
from client import RDPClient
from proxy_server import ProxyServer
from utils.logger import setup_logger
from utils.config import load_config, save_config

logger = logging.getLogger(__name__)

def setup_signal_handlers(server_or_client):
    """设置信号处理器"""
    def signal_handler(signum, frame):
        logger.info(f"接收到信号 {signum}，正在关闭...")
        if hasattr(server_or_client, 'stop'):
            asyncio.create_task(server_or_client.stop())
        else:
            sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def create_default_config(config_type: str) -> dict:
    """创建默认配置"""
    if config_type == 'server':
        return {
            'server': {
                'host': '0.0.0.0',
                'port': 8888,
                'protocol': 'tcp',
                'max_clients': 10
            },
            'screen': {
                'method': 'pil',
                'format': 'jpeg',
                'quality': 80,
                'fps': 30,
                'scale_factor': 1.0
            },
            'input': {
                'enable_mouse': True,
                'enable_keyboard': True,
                'security_enabled': True
            },
            'security': {
                'encryption_type': 'aes_256_cbc',
                'auth_method': 'password',
                'require_encryption': True,
                'session_timeout': 3600
            },
            'logging': {
                'level': 'INFO',
                'file': 'rdp_server.log'
            }
        }
    elif config_type == 'client':
        return {
            'client': {
                'auto_reconnect': True,
                'reconnect_interval': 5,
                'connection_timeout': 30
            },
            'display': {
                'fullscreen': False,
                'scale_mode': 'fit',
                'quality': 'high'
            },
            'input': {
                'mouse_sensitivity': 1.0,
                'keyboard_layout': 'auto'
            },
            'security': {
                'verify_certificate': True,
                'save_credentials': False
            },
            'logging': {
                'level': 'INFO',
                'file': 'rdp_client.log'
            }
        }
    elif config_type == 'proxy':
        return {
            'proxy': {
                'host': '0.0.0.0',
                'port': 1080,
                'protocols': ['socks5', 'http', 'https'],
                'max_connections': 1000
            },
            'auth': {
                'enable': False,
                'method': 'userpass',
                'users': {}
            },
            'rules': {
                'allow_all': True,
                'blocked_domains': [],
                'blocked_ips': []
            },
            'logging': {
                'level': 'INFO',
                'file': 'proxy_server.log'
            }
        }
    else:
        return {}

async def run_server(args):
    """运行服务端"""
    try:
        # 设置日志
        setup_logger(
            name='rdptool.server',
            level=args.log_level,
            log_file=args.log_file,
            console_output=not args.daemon
        )
        
        logger.info("启动远程桌面服务端...")
        
        # 创建服务器实例
        server = RDPServer(args.config)
        
        # 设置信号处理
        setup_signal_handlers(server)
        
        # 启动服务器
        await server.start()
        
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器运行错误: {e}")
        sys.exit(1)

async def run_client(args):
    """运行客户端"""
    try:
        # 设置日志
        setup_logger(
            name='rdptool.client',
            level=args.log_level,
            log_file=args.log_file
        )
        
        logger.info("启动远程桌面客户端...")
        
        # 创建客户端实例
        client = RDPClient(args.config)
        
        # 设置信号处理
        setup_signal_handlers(client)
        
        if args.gui:
            # GUI模式
            client.start_gui()
        else:
            # 命令行模式
            if not args.host:
                logger.error("命令行模式需要指定主机地址")
                sys.exit(1)
            
            await client.connect(
                host=args.host,
                port=args.port,
                username=args.username,
                password=args.password
            )
        
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭客户端...")
    except Exception as e:
        logger.error(f"客户端运行错误: {e}")
        sys.exit(1)

async def run_proxy(args):
    """运行代理服务"""
    try:
        # 设置日志
        setup_logger(
            name='rdptool.proxy',
            level=args.log_level,
            log_file=args.log_file,
            console_output=not args.daemon
        )
        
        logger.info("启动代理服务器...")
        
        # 创建代理服务器实例
        proxy = ProxyServer(args.config)
        
        # 设置信号处理
        setup_signal_handlers(proxy)
        
        # 启动代理服务器
        await proxy.start()
        
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭代理服务器...")
    except Exception as e:
        logger.error(f"代理服务器运行错误: {e}")
        sys.exit(1)

def generate_config(args):
    """生成配置文件"""
    config_type = args.type
    output_file = args.output or f'{config_type}_config.json'
    
    # 创建默认配置
    config = create_default_config(config_type)
    
    if not config:
        print(f"不支持的配置类型: {config_type}")
        sys.exit(1)
    
    try:
        # 保存配置文件
        save_config(config, output_file)
        print(f"配置文件已生成: {output_file}")
    except Exception as e:
        print(f"生成配置文件失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='远程桌面工具 - 支持多协议代理的远程桌面解决方案',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s server --config server_config.json
  %(prog)s client --gui
  %(prog)s client --host 192.168.1.100 --port 8888
  %(prog)s proxy --config proxy_config.json
  %(prog)s config --type server --output server.json
        """
    )
    
    # 全局参数
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='日志级别')
    parser.add_argument('--log-file', help='日志文件路径')
    parser.add_argument('--config', help='配置文件路径')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 服务端命令
    server_parser = subparsers.add_parser('server', help='启动远程桌面服务端')
    server_parser.add_argument('--daemon', action='store_true', help='后台运行')
    
    # 客户端命令
    client_parser = subparsers.add_parser('client', help='启动远程桌面客户端')
    client_parser.add_argument('--gui', action='store_true', help='启动图形界面')
    client_parser.add_argument('--host', help='服务器地址')
    client_parser.add_argument('--port', type=int, default=8888, help='服务器端口')
    client_parser.add_argument('--username', help='用户名')
    client_parser.add_argument('--password', help='密码')
    
    # 代理服务命令
    proxy_parser = subparsers.add_parser('proxy', help='启动代理服务器')
    proxy_parser.add_argument('--daemon', action='store_true', help='后台运行')
    
    # 配置生成命令
    config_parser = subparsers.add_parser('config', help='生成配置文件')
    config_parser.add_argument('--type', choices=['server', 'client', 'proxy'], 
                              required=True, help='配置类型')
    config_parser.add_argument('--output', help='输出文件路径')
    
    # 解析参数
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 执行对应命令
    if args.command == 'server':
        asyncio.run(run_server(args))
    elif args.command == 'client':
        asyncio.run(run_client(args))
    elif args.command == 'proxy':
        asyncio.run(run_proxy(args))
    elif args.command == 'config':
        generate_config(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()