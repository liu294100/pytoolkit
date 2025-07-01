# RDPTool API 文档

## 概述

RDPTool 是一个纯 Python 实现的远程桌面工具，支持多种网络协议和代理功能。本文档详细介绍了各个模块的 API 接口。

## 目录

- [核心模块](#核心模块)
  - [ConfigManager](#configmanager)
  - [SecurityManager](#securitymanager)
  - [NetworkManager](#networkmanager)
  - [ConnectionManager](#connectionmanager)
- [代理服务器](#代理服务器)
  - [ProxyServer](#proxyserver)
  - [ProxyConfig](#proxyconfig)
- [远程桌面](#远程桌面)
  - [RDPServer](#rdpserver)
  - [RDPClient](#rdpclient)
- [工具类](#工具类)
  - [Logger](#logger)
  - [Utils](#utils)

---

## 核心模块

### ConfigManager

配置管理器，负责配置文件的加载、保存和操作。

#### 类定义

```python
class ConfigManager:
    def __init__(self, default_config_dir: str = 'configs')
```

#### 方法

##### load_config

```python
def load_config(self, config_path: str) -> dict:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        dict: 配置字典
        
    Raises:
        FileNotFoundError: 配置文件不存在
        json.JSONDecodeError: 配置文件格式错误
    """
```

##### save_config

```python
def save_config(self, config: dict, config_path: str) -> bool:
    """
    保存配置文件
    
    Args:
        config: 配置字典
        config_path: 保存路径
        
    Returns:
        bool: 保存是否成功
    """
```

##### get_nested_value

```python
def get_nested_value(self, config: dict, key_path: str, default=None):
    """
    获取嵌套配置值
    
    Args:
        config: 配置字典
        key_path: 键路径，如 'server.host'
        default: 默认值
        
    Returns:
        配置值或默认值
    """
```

##### set_nested_value

```python
def set_nested_value(self, config: dict, key_path: str, value) -> bool:
    """
    设置嵌套配置值
    
    Args:
        config: 配置字典
        key_path: 键路径，如 'server.host'
        value: 要设置的值
        
    Returns:
        bool: 设置是否成功
    """
```

##### merge_configs

```python
def merge_configs(self, base_config: dict, override_config: dict) -> dict:
    """
    合并配置
    
    Args:
        base_config: 基础配置
        override_config: 覆盖配置
        
    Returns:
        dict: 合并后的配置
    """
```

#### 使用示例

```python
from utils.config import ConfigManager

# 创建配置管理器
config_manager = ConfigManager()

# 加载配置
config = config_manager.load_config('configs/server_config.json')

# 获取嵌套值
host = config_manager.get_nested_value(config, 'server.host', '127.0.0.1')

# 设置嵌套值
config_manager.set_nested_value(config, 'server.port', 8888)

# 保存配置
config_manager.save_config(config, 'configs/updated_config.json')
```

---

### SecurityManager

安全管理器，提供加密、解密、哈希等安全功能。

#### 类定义

```python
class SecurityManager:
    def __init__(self, algorithm: str = 'AES')
```

#### 方法

##### generate_key

```python
def generate_key(self, key_size: int = 32) -> bytes:
    """
    生成加密密钥
    
    Args:
        key_size: 密钥长度（字节）
        
    Returns:
        bytes: 生成的密钥
    """
```

##### encrypt

```python
def encrypt(self, data: bytes, key: bytes) -> bytes:
    """
    加密数据
    
    Args:
        data: 要加密的数据
        key: 加密密钥
        
    Returns:
        bytes: 加密后的数据
        
    Raises:
        ValueError: 密钥长度不正确
    """
```

##### decrypt

```python
def decrypt(self, encrypted_data: bytes, key: bytes) -> bytes:
    """
    解密数据
    
    Args:
        encrypted_data: 加密的数据
        key: 解密密钥
        
    Returns:
        bytes: 解密后的数据
        
    Raises:
        ValueError: 解密失败
    """
```

##### hash_password

```python
def hash_password(self, password: str, salt: bytes = None) -> str:
    """
    哈希密码
    
    Args:
        password: 明文密码
        salt: 盐值（可选）
        
    Returns:
        str: 哈希后的密码
    """
```

##### verify_password

```python
def verify_password(self, password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        password: 明文密码
        hashed_password: 哈希密码
        
    Returns:
        bool: 验证结果
    """
```

##### generate_secure_random

```python
def generate_secure_random(self, length: int) -> bytes:
    """
    生成安全随机数
    
    Args:
        length: 随机数长度
        
    Returns:
        bytes: 安全随机数
    """
```

#### 使用示例

```python
from core.security import SecurityManager

# 创建安全管理器
security = SecurityManager()

# 生成密钥
key = security.generate_key()

# 加密数据
data = b"sensitive information"
encrypted = security.encrypt(data, key)

# 解密数据
decrypted = security.decrypt(encrypted, key)

# 密码哈希
password = "user_password"
hashed = security.hash_password(password)

# 验证密码
is_valid = security.verify_password(password, hashed)
```

---

### NetworkManager

网络管理器，处理网络连接和通信。

#### 类定义

```python
class NetworkManager:
    def __init__(self, max_connections: int = 100)
```

#### 方法

##### create_tcp_connection

```python
async def create_tcp_connection(self, host: str, port: int, timeout: float = 10.0) -> tuple:
    """
    创建TCP连接
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间
        
    Returns:
        tuple: (reader, writer)
        
    Raises:
        ConnectionError: 连接失败
        asyncio.TimeoutError: 连接超时
    """
```

##### start_tcp_server

```python
async def start_tcp_server(self, handler, host: str, port: int) -> asyncio.Server:
    """
    启动TCP服务器
    
    Args:
        handler: 连接处理函数
        host: 监听地址
        port: 监听端口
        
    Returns:
        asyncio.Server: 服务器对象
    """
```

##### send_data

```python
async def send_data(self, writer, data: bytes) -> bool:
    """
    发送数据
    
    Args:
        writer: 写入器
        data: 要发送的数据
        
    Returns:
        bool: 发送是否成功
    """
```

##### receive_data

```python
async def receive_data(self, reader, max_size: int = 8192) -> bytes:
    """
    接收数据
    
    Args:
        reader: 读取器
        max_size: 最大读取大小
        
    Returns:
        bytes: 接收到的数据
    """
```

##### get_connection_pool_stats

```python
def get_connection_pool_stats(self) -> dict:
    """
    获取连接池统计信息
    
    Returns:
        dict: 统计信息
    """
```

#### 使用示例

```python
from core.network import NetworkManager
import asyncio

async def main():
    network = NetworkManager()
    
    # 创建连接
    reader, writer = await network.create_tcp_connection('127.0.0.1', 8080)
    
    # 发送数据
    await network.send_data(writer, b'Hello Server')
    
    # 接收数据
    response = await network.receive_data(reader)
    
    # 关闭连接
    writer.close()
    await writer.wait_closed()

asyncio.run(main())
```

---

### ConnectionManager

连接管理器，管理活跃连接。

#### 类定义

```python
class ConnectionManager:
    def __init__(self, max_connections: int = 1000)
```

#### 方法

##### add_connection

```python
def add_connection(self, connection_id: str, connection) -> bool:
    """
    添加连接
    
    Args:
        connection_id: 连接ID
        connection: 连接对象
        
    Returns:
        bool: 添加是否成功
    """
```

##### remove_connection

```python
def remove_connection(self, connection_id: str) -> bool:
    """
    移除连接
    
    Args:
        connection_id: 连接ID
        
    Returns:
        bool: 移除是否成功
    """
```

##### get_connection

```python
def get_connection(self, connection_id: str):
    """
    获取连接
    
    Args:
        connection_id: 连接ID
        
    Returns:
        连接对象或None
    """
```

##### get_connection_count

```python
def get_connection_count(self) -> int:
    """
    获取连接数量
    
    Returns:
        int: 当前连接数
    """
```

##### cleanup_expired_connections

```python
def cleanup_expired_connections(self, max_idle_time: float = 300.0) -> int:
    """
    清理过期连接
    
    Args:
        max_idle_time: 最大空闲时间（秒）
        
    Returns:
        int: 清理的连接数
    """
```

#### 使用示例

```python
from core.network import ConnectionManager

# 创建连接管理器
conn_manager = ConnectionManager(max_connections=500)

# 添加连接
conn_manager.add_connection('client_001', connection_object)

# 获取连接
connection = conn_manager.get_connection('client_001')

# 获取连接数
count = conn_manager.get_connection_count()

# 清理过期连接
cleaned = conn_manager.cleanup_expired_connections()
```

---

## 代理服务器

### ProxyServer

代理服务器主类，支持多种协议。

#### 类定义

```python
class ProxyServer:
    def __init__(self, config: ProxyConfig)
```

#### 方法

##### start

```python
async def start(self) -> bool:
    """
    启动代理服务器
    
    Returns:
        bool: 启动是否成功
    """
```

##### stop

```python
async def stop(self) -> bool:
    """
    停止代理服务器
    
    Returns:
        bool: 停止是否成功
    """
```

##### get_stats

```python
def get_stats(self) -> dict:
    """
    获取统计信息
    
    Returns:
        dict: 统计信息
    """
```

##### is_running

```python
@property
def is_running(self) -> bool:
    """
    检查服务器是否运行
    
    Returns:
        bool: 运行状态
    """
```

#### 使用示例

```python
from proxy_server import ProxyServer, ProxyConfig, ProxyProtocol
import asyncio

async def main():
    # 创建配置
    config = ProxyConfig(
        host='127.0.0.1',
        port=8080,
        protocols=[ProxyProtocol.HTTP, ProxyProtocol.SOCKS5]
    )
    
    # 创建代理服务器
    proxy = ProxyServer(config)
    
    # 启动服务器
    await proxy.start()
    
    # 获取统计信息
    stats = proxy.get_stats()
    print(f"代理服务器统计: {stats}")
    
    # 停止服务器
    await proxy.stop()

asyncio.run(main())
```

---

### ProxyConfig

代理配置类。

#### 类定义

```python
class ProxyConfig:
    def __init__(self, 
                 host: str = '127.0.0.1',
                 port: int = 8080,
                 protocols: List[ProxyProtocol] = None,
                 auth_required: bool = False,
                 max_connections: int = 1000)
```

#### 属性

- `host`: 监听地址
- `port`: 监听端口
- `protocols`: 支持的协议列表
- `auth_required`: 是否需要认证
- `max_connections`: 最大连接数

#### 方法

##### to_dict

```python
def to_dict(self) -> dict:
    """
    转换为字典
    
    Returns:
        dict: 配置字典
    """
```

##### from_dict

```python
@classmethod
def from_dict(cls, config_dict: dict) -> 'ProxyConfig':
    """
    从字典创建配置
    
    Args:
        config_dict: 配置字典
        
    Returns:
        ProxyConfig: 配置对象
    """
```

---

## 远程桌面

### RDPServer

远程桌面服务端。

#### 类定义

```python
class RDPServer:
    def __init__(self, config: dict)
```

#### 方法

##### start

```python
async def start(self) -> bool:
    """
    启动RDP服务器
    
    Returns:
        bool: 启动是否成功
    """
```

##### stop

```python
async def stop(self) -> bool:
    """
    停止RDP服务器
    
    Returns:
        bool: 停止是否成功
    """
```

##### handle_client

```python
async def handle_client(self, reader, writer) -> None:
    """
    处理客户端连接
    
    Args:
        reader: 读取器
        writer: 写入器
    """
```

---

### RDPClient

远程桌面客户端。

#### 类定义

```python
class RDPClient:
    def __init__(self, config: dict)
```

#### 方法

##### connect

```python
async def connect(self) -> bool:
    """
    连接到RDP服务器
    
    Returns:
        bool: 连接是否成功
    """
```

##### disconnect

```python
async def disconnect(self) -> bool:
    """
    断开连接
    
    Returns:
        bool: 断开是否成功
    """
```

##### send_input

```python
async def send_input(self, input_data: dict) -> bool:
    """
    发送输入事件
    
    Args:
        input_data: 输入数据
        
    Returns:
        bool: 发送是否成功
    """
```

---

## 工具类

### Logger

日志工具。

#### 函数

##### get_logger

```python
def get_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        
    Returns:
        logging.Logger: 日志记录器
    """
```

#### 使用示例

```python
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger('my_module')

# 记录日志
logger.info('应用程序启动')
logger.warning('连接数接近上限')
logger.error('连接失败')
```

---

### Utils

通用工具函数。

#### 函数

##### is_valid_ip

```python
def is_valid_ip(ip: str) -> bool:
    """
    验证IP地址
    
    Args:
        ip: IP地址字符串
        
    Returns:
        bool: 是否有效
    """
```

##### is_valid_port

```python
def is_valid_port(port: int) -> bool:
    """
    验证端口号
    
    Args:
        port: 端口号
        
    Returns:
        bool: 是否有效
    """
```

##### find_free_port

```python
def find_free_port(start_port: int = 8000, end_port: int = 9000) -> int:
    """
    查找空闲端口
    
    Args:
        start_port: 起始端口
        end_port: 结束端口
        
    Returns:
        int: 空闲端口号
        
    Raises:
        RuntimeError: 没有找到空闲端口
    """
```

##### format_bytes

```python
def format_bytes(bytes_count: int) -> str:
    """
    格式化字节数
    
    Args:
        bytes_count: 字节数
        
    Returns:
        str: 格式化后的字符串
    """
```

#### 使用示例

```python
from utils.helpers import is_valid_ip, find_free_port, format_bytes

# 验证IP
if is_valid_ip('192.168.1.1'):
    print('有效的IP地址')

# 查找空闲端口
free_port = find_free_port(8000, 9000)
print(f'空闲端口: {free_port}')

# 格式化字节数
size_str = format_bytes(1024 * 1024)  # '1.0 MB'
```

---

## 错误处理

### 异常类

#### RDPToolError

```python
class RDPToolError(Exception):
    """RDPTool基础异常类"""
    pass
```

#### ConfigError

```python
class ConfigError(RDPToolError):
    """配置相关异常"""
    pass
```

#### NetworkError

```python
class NetworkError(RDPToolError):
    """网络相关异常"""
    pass
```

#### SecurityError

```python
class SecurityError(RDPToolError):
    """安全相关异常"""
    pass
```

### 错误处理示例

```python
from core.exceptions import ConfigError, NetworkError

try:
    config = config_manager.load_config('invalid_config.json')
except ConfigError as e:
    logger.error(f'配置错误: {e}')
    
try:
    await network.create_tcp_connection('invalid.host', 80)
except NetworkError as e:
    logger.error(f'网络错误: {e}')
```

---

## 配置文件格式

### 服务端配置

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8888,
    "max_connections": 100
  },
  "security": {
    "encryption": true,
    "authentication": true,
    "ssl_cert": "/path/to/cert.pem",
    "ssl_key": "/path/to/key.pem"
  },
  "features": {
    "screen_sharing": true,
    "file_transfer": true,
    "clipboard_sync": true,
    "audio_streaming": false
  },
  "logging": {
    "level": "INFO",
    "file": "logs/server.log"
  }
}
```

### 客户端配置

```json
{
  "client": {
    "server_host": "127.0.0.1",
    "server_port": 8888,
    "auto_reconnect": true
  },
  "display": {
    "resolution": "1920x1080",
    "color_depth": 24,
    "fullscreen": false
  },
  "input": {
    "keyboard": true,
    "mouse": true,
    "clipboard": true
  },
  "logging": {
    "level": "INFO",
    "file": "logs/client.log"
  }
}
```

### 代理配置

```json
{
  "proxy": {
    "host": "127.0.0.1",
    "port": 8080,
    "protocols": ["http", "socks5", "websocket"],
    "max_connections": 1000
  },
  "security": {
    "auth_required": false,
    "allowed_ips": [],
    "blocked_ips": []
  },
  "logging": {
    "level": "INFO",
    "file": "logs/proxy.log"
  }
}
```

---

## 版本信息

- **当前版本**: 1.0.0
- **Python要求**: 3.8+
- **最后更新**: 2024-01-01

## 许可证

MIT License

## 联系方式

- **项目主页**: https://github.com/rdptool/rdptool
- **问题反馈**: https://github.com/rdptool/rdptool/issues
- **邮箱**: support@rdptool.com