# RDPTool - 多协议远程桌面工具

一个功能强大的纯Python远程桌面工具，支持多种网络协议和代理功能。

## 🚀 特性

### 远程桌面功能
- **屏幕共享**: 实时屏幕捕获和传输
- **远程控制**: 鼠标和键盘事件转发
- **多显示器支持**: 支持多显示器环境
- **图像压缩**: 多种压缩格式（JPEG、PNG、WebP）
- **自适应质量**: 根据网络状况自动调整图像质量

### 多协议代理
- **HTTP/HTTPS代理**: 支持HTTP/1.1和HTTPS隧道
- **SOCKS代理**: 完整的SOCKS4/SOCKS5支持（含UDP）
- **WebSocket隧道**: 基于WebSocket的数据隧道
- **SSH隧道**: SSH端口转发和动态代理
- **原始套接字**: 底层网络数据包处理

### 安全特性
- **端到端加密**: AES-256加密保护
- **身份认证**: 多种认证方式（密码、证书）
- **会话管理**: 安全的会话建立和管理
- **权限控制**: 细粒度的访问控制

### 网络功能
- **连接管理**: 智能连接池和负载均衡
- **自动重连**: 网络中断自动恢复
- **流量监控**: 实时网络流量统计
- **性能优化**: 数据压缩和缓存机制

## 📦 安装

### 系统要求
- Python 3.8+
- Windows/Linux/macOS

### 依赖安装
```bash
# 基础依赖（可选，工具会自动处理）
pip install pillow opencv-python mss pynput psutil cryptography

# 或者使用纯Python实现（无外部依赖）
# 工具内置了所有必要的纯Python实现
```

### 快速安装
```bash
git clone <repository-url>
cd rdptool
python main.py --help
```

## 🎯 使用方法

### 1. 启动远程桌面服务端
```bash
# 使用默认配置
python main.py server

# 使用自定义配置
python main.py server --config server_config.json

# 后台运行
python main.py server --daemon
```

### 2. 启动远程桌面客户端
```bash
# GUI模式
python main.py client --gui

# 命令行模式
python main.py client --host 192.168.1.100 --port 8888 --username admin
```

### 3. 启动代理服务器
```bash
# 启动多协议代理
python main.py proxy --config proxy_config.json

# 后台运行
python main.py proxy --daemon
```

### 4. 生成配置文件
```bash
# 生成服务端配置
python main.py config --type server --output server.json

# 生成客户端配置
python main.py config --type client --output client.json

# 生成代理配置
python main.py config --type proxy --output proxy.json
```

## ⚙️ 配置说明

### 服务端配置示例
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8888,
    "protocol": "tcp",
    "max_clients": 10
  },
  "screen": {
    "method": "pil",
    "format": "jpeg",
    "quality": 80,
    "fps": 30,
    "scale_factor": 1.0
  },
  "security": {
    "encryption_type": "aes_256_cbc",
    "auth_method": "password",
    "require_encryption": true,
    "session_timeout": 3600
  }
}
```

### 代理配置示例
```json
{
  "proxy": {
    "host": "0.0.0.0",
    "protocols": {
      "http": {
        "enabled": true,
        "port": 8080
      },
      "socks5": {
        "enabled": true,
        "port": 1080,
        "auth_required": false
      },
      "websocket": {
        "enabled": true,
        "port": 8888,
        "path": "/ws"
      }
    }
  }
}
```

## 🏗️ 架构设计

### 模块结构
```
rdptool/
├── core/                   # 核心功能模块
│   ├── network.py         # 网络管理
│   ├── protocol.py        # 协议处理
│   ├── screen.py          # 屏幕捕获
│   ├── input.py           # 输入控制
│   └── security.py        # 安全管理
├── protocols/             # 协议实现
│   ├── http_proxy.py      # HTTP/HTTPS代理
│   ├── socks_proxy.py     # SOCKS代理
│   ├── websocket_proxy.py # WebSocket代理
│   ├── ssh_tunnel.py      # SSH隧道
│   └── raw_socket.py      # 原始套接字
├── network/               # 网络层
│   ├── connection_manager.py # 连接管理
│   ├── tcp_handler.py     # TCP处理
│   ├── udp_handler.py     # UDP处理
│   └── network_monitor.py # 网络监控
├── utils/                 # 工具模块
│   ├── logger.py          # 日志系统
│   ├── config.py          # 配置管理
│   ├── compression.py     # 数据压缩
│   ├── performance.py     # 性能监控
│   └── helpers.py         # 辅助函数
├── client.py              # 客户端
├── server.py              # 服务端
├── proxy_server.py        # 代理服务器
└── main.py                # 主入口
```

### 核心组件

#### 1. 网络管理器 (NetworkManager)
- 统一的网络连接管理
- 支持TCP/UDP/WebSocket等协议
- 连接池和负载均衡
- 自动重连和故障恢复

#### 2. 协议处理器 (ProtocolHandler)
- 消息序列化和反序列化
- 协议版本协商
- 消息路由和分发
- 错误处理和恢复

#### 3. 安全管理器 (SecurityManager)
- 端到端加密
- 身份认证和授权
- 密钥管理和交换
- 会话安全

#### 4. 屏幕捕获器 (ScreenCapture)
- 多种捕获方法（PIL、OpenCV、MSS）
- 实时屏幕流
- 图像压缩和优化
- 多显示器支持

#### 5. 输入控制器 (InputController)
- 鼠标和键盘事件处理
- 跨平台输入模拟
- 事件队列和批处理
- 安全限制

## 🔧 高级功能

### 1. 自定义协议
```python
from core.protocol import ProtocolHandler, MessageType

class CustomProtocol(ProtocolHandler):
    def handle_custom_message(self, message):
        # 自定义消息处理逻辑
        pass
```

### 2. 插件系统
```python
from core.network import NetworkManager

class CustomPlugin:
    def on_connection_established(self, connection):
        # 连接建立时的处理
        pass
    
    def on_data_received(self, data):
        # 数据接收时的处理
        pass
```

### 3. 性能监控
```python
from utils.performance import PerformanceMonitor

monitor = PerformanceMonitor()
monitor.start_monitoring()

# 获取性能指标
metrics = monitor.get_current_metrics()
print(f"CPU使用率: {metrics.cpu_percent}%")
print(f"内存使用率: {metrics.memory_percent}%")
```

## 🛡️ 安全考虑

### 1. 网络安全
- 所有通信默认加密
- 支持TLS/SSL证书验证
- 防止中间人攻击
- 网络流量混淆

### 2. 访问控制
- 基于IP的访问限制
- 用户认证和授权
- 会话超时管理
- 操作审计日志

### 3. 数据保护
- 敏感数据加密存储
- 内存数据清理
- 安全的密钥管理
- 数据完整性校验

## 📊 性能优化

### 1. 网络优化
- 数据压缩算法
- 连接复用
- 带宽自适应
- 缓存机制

### 2. 图像优化
- 动态质量调整
- 增量更新
- 区域压缩
- 格式选择

### 3. 系统优化
- 多线程处理
- 异步I/O
- 内存池管理
- CPU亲和性

## 🐛 故障排除

### 常见问题

1. **连接失败**
   - 检查防火墙设置
   - 验证端口是否开放
   - 确认网络连通性

2. **性能问题**
   - 调整图像质量设置
   - 检查网络带宽
   - 优化压缩参数

3. **认证失败**
   - 验证用户名密码
   - 检查证书配置
   - 确认权限设置

### 调试模式
```bash
# 启用详细日志
python main.py server --log-level DEBUG

# 查看网络状态
python -c "from network.network_monitor import NetworkMonitor; m=NetworkMonitor(); print(m.get_network_info())"
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- 参考了 [pproxy](https://github.com/qwj/python-proxy) 的设计理念
- 感谢所有开源项目的贡献者
- 特别感谢测试和反馈的用户

## 📞 联系方式

- 项目主页: [GitHub Repository]
- 问题报告: [GitHub Issues]
- 文档: [Wiki Pages]

---

**注意**: 本工具仅供学习和合法用途使用，请遵守当地法律法规。