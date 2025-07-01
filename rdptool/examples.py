#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程桌面工具使用示例
"""

import asyncio
import json
import time
from pathlib import Path

# 导入主要模块
try:
    from main import main, create_default_config, run_server, run_client, run_proxy
    from proxy_server import ProxyServer, ProxyConfig, ProxyProtocol
    from core.network import NetworkManager
    from core.security import SecurityManager
    from utils.config import ConfigManager
    from utils.logger import get_logger
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保所有模块都已正确实现")

def example_create_configs():
    """
    示例1: 创建默认配置文件
    """
    print("=== 示例1: 创建默认配置文件 ===")
    
    # 创建配置目录
    config_dir = Path('example_configs')
    config_dir.mkdir(exist_ok=True)
    
    # 创建服务端配置
    server_config = create_default_config('server')
    server_config_file = config_dir / 'server_config.json'
    
    with open(server_config_file, 'w', encoding='utf-8') as f:
        json.dump(server_config, f, indent=2, ensure_ascii=False)
    
    print(f"服务端配置已保存到: {server_config_file}")
    
    # 创建客户端配置
    client_config = create_default_config('client')
    client_config_file = config_dir / 'client_config.json'
    
    with open(client_config_file, 'w', encoding='utf-8') as f:
        json.dump(client_config, f, indent=2, ensure_ascii=False)
    
    print(f"客户端配置已保存到: {client_config_file}")
    
    # 创建代理配置
    proxy_config = create_default_config('proxy')
    proxy_config_file = config_dir / 'proxy_config.json'
    
    with open(proxy_config_file, 'w', encoding='utf-8') as f:
        json.dump(proxy_config, f, indent=2, ensure_ascii=False)
    
    print(f"代理配置已保存到: {proxy_config_file}")
    print()

def example_config_management():
    """
    示例2: 配置管理
    """
    print("=== 示例2: 配置管理 ===")
    
    config_manager = ConfigManager()
    
    # 创建自定义配置
    custom_config = {
        'server': {
            'host': '0.0.0.0',
            'port': 9999,
            'max_connections': 50
        },
        'security': {
            'encryption': True,
            'authentication': True,
            'ssl_cert': '/path/to/cert.pem',
            'ssl_key': '/path/to/key.pem'
        },
        'features': {
            'screen_sharing': True,
            'file_transfer': True,
            'clipboard_sync': True,
            'audio_streaming': False
        },
        'performance': {
            'compression': 'zlib',
            'quality': 'high',
            'frame_rate': 30
        }
    }
    
    # 保存配置
    config_file = 'example_configs/custom_server.json'
    config_manager.save_config(custom_config, config_file)
    print(f"自定义配置已保存到: {config_file}")
    
    # 加载配置
    loaded_config = config_manager.load_config(config_file)
    print(f"配置加载成功，服务器端口: {loaded_config['server']['port']}")
    
    # 获取嵌套配置值
    encryption_enabled = config_manager.get_nested_value(
        loaded_config, 'security.encryption', False
    )
    print(f"加密启用状态: {encryption_enabled}")
    
    # 设置嵌套配置值
    config_manager.set_nested_value(
        loaded_config, 'performance.frame_rate', 60
    )
    print(f"帧率已更新为: {loaded_config['performance']['frame_rate']}")
    print()

def example_security_features():
    """
    示例3: 安全功能
    """
    print("=== 示例3: 安全功能 ===")
    
    security_manager = SecurityManager()
    
    # 密码哈希和验证
    password = "my_secure_password_123"
    password_hash = security_manager.hash_password(password)
    print(f"密码哈希: {password_hash[:50]}...")
    
    # 验证密码
    is_valid = security_manager.verify_password(password, password_hash)
    print(f"密码验证结果: {is_valid}")
    
    # 数据加密和解密
    secret_data = "这是需要加密的敏感数据"
    encryption_key = security_manager.generate_key()
    
    encrypted_data = security_manager.encrypt(secret_data.encode(), encryption_key)
    print(f"加密数据长度: {len(encrypted_data)} 字节")
    
    decrypted_data = security_manager.decrypt(encrypted_data, encryption_key)
    print(f"解密数据: {decrypted_data.decode()}")
    
    # 生成安全随机数
    random_bytes = security_manager.generate_secure_random(32)
    print(f"安全随机数: {random_bytes.hex()[:32]}...")
    print()

def example_proxy_server():
    """
    示例4: 代理服务器
    """
    print("=== 示例4: 代理服务器 ===")
    
    # 创建代理配置
    proxy_config = ProxyConfig(
        host='127.0.0.1',
        port=8080,
        protocols=[
            ProxyProtocol.HTTP,
            ProxyProtocol.SOCKS5,
            ProxyProtocol.WEBSOCKET
        ]
    )
    
    # 创建代理服务器
    proxy_server = ProxyServer(proxy_config)
    
    print(f"代理服务器配置:")
    print(f"  地址: {proxy_config.host}:{proxy_config.port}")
    print(f"  支持协议: {[p.value for p in proxy_config.protocols]}")
    
    # 获取统计信息
    stats = proxy_server.get_stats()
    print(f"代理服务器统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"代理服务器运行状态: {proxy_server.is_running}")
    print()

async def example_async_operations():
    """
    示例5: 异步操作
    """
    print("=== 示例5: 异步操作 ===")
    
    # 网络管理器
    network_manager = NetworkManager()
    
    # 模拟异步网络操作
    async def simulate_network_task(task_id, duration):
        print(f"任务 {task_id} 开始执行...")
        await asyncio.sleep(duration)
        print(f"任务 {task_id} 执行完成 (耗时 {duration}s)")
        return f"任务 {task_id} 结果"
    
    # 并发执行多个网络任务
    tasks = [
        simulate_network_task(1, 1),
        simulate_network_task(2, 2),
        simulate_network_task(3, 1.5)
    ]
    
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    print(f"所有任务完成，总耗时: {end_time - start_time:.2f}s")
    for result in results:
        print(f"  {result}")
    
    # 模拟连接管理
    print("\n模拟连接管理:")
    
    async def simulate_connection(conn_id):
        print(f"连接 {conn_id} 建立")
        await asyncio.sleep(0.5)  # 模拟连接处理时间
        print(f"连接 {conn_id} 处理完成")
        return conn_id
    
    # 并发处理多个连接
    connection_tasks = [
        simulate_connection(f"conn_{i}")
        for i in range(5)
    ]
    
    connection_results = await asyncio.gather(*connection_tasks)
    print(f"处理了 {len(connection_results)} 个连接")
    print()

def example_logging():
    """
    示例6: 日志记录
    """
    print("=== 示例6: 日志记录 ===")
    
    # 获取不同模块的日志记录器
    server_logger = get_logger('rdp_server')
    client_logger = get_logger('rdp_client')
    proxy_logger = get_logger('proxy_server')
    
    # 记录不同级别的日志
    server_logger.info("服务器启动")
    server_logger.warning("连接数接近上限")
    
    client_logger.info("客户端连接到服务器")
    client_logger.error("连接失败，正在重试")
    
    proxy_logger.info("代理服务器开始监听")
    proxy_logger.debug("处理HTTP代理请求")
    
    print("日志记录完成，请查看日志文件")
    print()

def example_performance_monitoring():
    """
    示例7: 性能监控
    """
    print("=== 示例7: 性能监控 ===")
    
    # 模拟性能数据收集
    performance_data = {
        'cpu_usage': 45.2,
        'memory_usage': 67.8,
        'network_in': 1024 * 1024,  # 1MB
        'network_out': 2048 * 1024,  # 2MB
        'active_connections': 15,
        'frame_rate': 28.5,
        'latency': 45  # ms
    }
    
    print("当前性能指标:")
    print(f"  CPU使用率: {performance_data['cpu_usage']:.1f}%")
    print(f"  内存使用率: {performance_data['memory_usage']:.1f}%")
    print(f"  网络入流量: {performance_data['network_in'] / 1024 / 1024:.1f} MB")
    print(f"  网络出流量: {performance_data['network_out'] / 1024 / 1024:.1f} MB")
    print(f"  活跃连接数: {performance_data['active_connections']}")
    print(f"  帧率: {performance_data['frame_rate']:.1f} FPS")
    print(f"  延迟: {performance_data['latency']} ms")
    
    # 性能警告检查
    warnings = []
    if performance_data['cpu_usage'] > 80:
        warnings.append("CPU使用率过高")
    if performance_data['memory_usage'] > 90:
        warnings.append("内存使用率过高")
    if performance_data['latency'] > 100:
        warnings.append("网络延迟过高")
    if performance_data['frame_rate'] < 20:
        warnings.append("帧率过低")
    
    if warnings:
        print("\n性能警告:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
    else:
        print("\n✅ 性能状态良好")
    
    print()

def example_command_line_usage():
    """
    示例8: 命令行使用方法
    """
    print("=== 示例8: 命令行使用方法 ===")
    
    print("1. 启动服务端:")
    print("   python main.py server --config configs/server_config.json")
    print("   python main.py server --host 0.0.0.0 --port 8888")
    
    print("\n2. 启动客户端:")
    print("   python main.py client --config configs/client_config.json")
    print("   python main.py client --host 192.168.1.100 --port 8888")
    
    print("\n3. 启动代理服务器:")
    print("   python main.py proxy --config configs/proxy_config.json")
    print("   python main.py proxy --host 127.0.0.1 --port 8080 --protocols http,socks5")
    
    print("\n4. 生成配置文件:")
    print("   python main.py generate-config server")
    print("   python main.py generate-config client")
    print("   python main.py generate-config proxy")
    
    print("\n5. GUI模式:")
    print("   python main.py gui")
    print("   python main.py gui --theme dark")
    
    print("\n6. 查看帮助:")
    print("   python main.py --help")
    print("   python main.py server --help")
    print()

def example_integration_scenarios():
    """
    示例9: 集成场景
    """
    print("=== 示例9: 集成场景 ===")
    
    print("场景1: 企业内网远程办公")
    print("  - 在办公室服务器上运行RDP服务端")
    print("  - 员工在家使用客户端连接")
    print("  - 启用加密和身份验证")
    print("  - 配置文件传输和剪贴板同步")
    
    print("\n场景2: 通过代理访问")
    print("  - 客户端 -> SOCKS5代理 -> RDP服务端")
    print("  - 绕过网络限制")
    print("  - 隐藏真实服务器地址")
    
    print("\n场景3: 多协议支持")
    print("  - HTTP代理用于Web流量")
    print("  - SOCKS5代理用于应用程序")
    print("  - WebSocket用于实时通信")
    print("  - SSH隧道用于安全传输")
    
    print("\n场景4: 高可用部署")
    print("  - 多个RDP服务端实例")
    print("  - 负载均衡器分发连接")
    print("  - 故障自动切换")
    print("  - 会话持久化")
    
    print("\n场景5: 开发和测试")
    print("  - 本地开发环境")
    print("  - 自动化测试")
    print("  - 性能基准测试")
    print("  - 安全渗透测试")
    print()

def main_examples():
    """
    运行所有示例
    """
    print("🚀 远程桌面工具使用示例")
    print("=" * 50)
    
    try:
        # 同步示例
        example_create_configs()
        example_config_management()
        example_security_features()
        example_proxy_server()
        example_logging()
        example_performance_monitoring()
        example_command_line_usage()
        example_integration_scenarios()
        
        # 异步示例
        print("运行异步示例...")
        asyncio.run(example_async_operations())
        
        print("✅ 所有示例运行完成！")
        print("\n📖 更多信息请参考:")
        print("  - README.md: 详细文档")
        print("  - configs/: 配置文件模板")
        print("  - tests/: 单元测试")
        
    except Exception as e:
        print(f"❌ 示例运行出错: {e}")
        print("请确保所有依赖模块都已正确实现")

if __name__ == '__main__':
    main_examples()