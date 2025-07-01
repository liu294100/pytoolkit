# 云服务器远程桌面部署指南

本文档详细介绍如何在云服务器上部署远程桌面服务，实现多客户端远程连接。

## 部署方式

本RDP工具支持多种部署方式，您可以根据实际需求选择合适的部署方案：

### 1. 传统部署
本文档描述的传统部署方式，直接在云服务器上安装和运行RDP工具。

**优点：**
- 部署简单，易于理解
- 直接访问系统资源
- 便于调试和维护

**适用场景：**
- 小规模部署
- 开发和测试环境
- 对容器化不熟悉的团队

### 2. Docker容器化部署
使用Docker容器部署RDP工具，提供更好的隔离性和可移植性。

**优点：**
- 环境隔离，避免依赖冲突
- 快速部署和扩展
- 支持容器编排
- 便于版本管理和回滚

**适用场景：**
- 生产环境部署
- 微服务架构
- 需要快速扩展的场景
- 多环境部署

**详细说明：** 请参考 [Docker部署指南](DOCKER_DEPLOYMENT.md)

### 3. 混合部署
结合传统部署和Docker部署的优势，在不同环境使用不同的部署方式。

**示例：**
- 云服务器：Docker部署（服务端）
- 客户端设备：传统部署（被控端/控制端）

## 系统架构

```
云服务器 (公网IP)
├── RDP服务端 (端口8888) - 连接池/转发服务
│   ├── 管理多个客户端连接
│   ├── 转发控制指令
│   └── 会话管理
└── 代理服务 (可选，端口1080)
    ├── SOCKS5代理
    ├── HTTP代理
    └── 流量转发

控制端客户端A ──┐
控制端客户端B ──┼── 互联网 ──> 云服务器 <──── 被控端客户端 (目标桌面)
控制端客户端C ──┘                      ↑
                                   通过内网或VPN连接

角色说明：
- 云服务器：RDP服务端，负责连接池管理和指令转发
- 控制端客户端：发送控制指令的一方
- 被控端客户端：接收控制指令的目标桌面
```

## 前置要求

### 云服务器配置
- **操作系统**: Ubuntu 20.04+ / CentOS 7+ / Windows Server 2019+
- **CPU**: 2核心以上
- **内存**: 4GB以上 (推荐8GB)
- **带宽**: 5Mbps以上 (推荐10Mbps)
- **存储**: 20GB以上可用空间

### 网络配置
- 公网IP地址
- 开放端口: 8888 (RDP服务), 1080 (代理服务，可选)
- 防火墙配置允许入站连接

### 软件依赖
- Python 3.8+
- pip包管理器
- 必要的系统库

## 被控端客户端连接配置

被控端客户端是指需要被远程控制的计算机（目标桌面）。它作为客户端连接到云服务器，接收来自控制端客户端的控制指令。根据网络环境不同，有以下几种连接方式：

### 方案一：被控端客户端直接连接云服务器（推荐）

**适用场景**：被控端客户端有公网访问能力

#### 配置步骤：

1. **在被控端桌面上安装RDP工具**
```bash
# 下载并安装RDP工具
git clone <your-repo-url>
cd rdptool
pip install -r requirements.txt
```

2. **配置被控端为客户端模式**
```bash
# 生成客户端配置
python main.py config --type client --output target_client_config.json
```

3. **编辑配置文件**
```json
{
  "client": {
    "mode": "target",
    "server_host": "YOUR_CLOUD_SERVER_IP",
    "server_port": 8888,
    "device_id": "target_desktop_001",
    "auto_reconnect": true,
    "heartbeat_interval": 30,
    "screen_sharing": {
      "enable": true,
      "quality": "medium",
      "fps": 30
    },
    "input_control": {
      "enable": true,
      "mouse": true,
      "keyboard": true
    }
  }
}
```

4. **启动被控端客户端**
```bash
python main.py client --config target_client_config.json
```

### 方案二：通过VPN连接

**适用场景**：被控端客户端在内网环境，通过VPN与云服务器建立连接

#### 配置步骤：

1. **建立VPN连接**
   - 在云服务器上配置VPN服务器（如OpenVPN、WireGuard）
   - 被控端客户端连接到VPN，获得虚拟IP

2. **被控端客户端配置**
```json
{
  "client": {
    "mode": "target",
    "server_host": "YOUR_CLOUD_SERVER_IP",
    "server_port": 8888,
    "device_id": "target_desktop_vpn_001",
    "network": {
      "tunnel_mode": true,
      "vpn_interface": "tun0"
    },
    "auto_reconnect": true
  }
}
```

3. **启动被控端客户端**
```bash
python main.py client --config vpn_client_config.json
```

### 方案三：NAT穿透模式

**适用场景**：被控端客户端在NAT后面，无法直接被访问

#### 工作原理：
1. 被控端客户端主动连接云服务器
2. 建立持久连接通道
3. 控制端客户端通过云服务器转发控制指令

#### 配置步骤：

1. **云服务器配置NAT穿透支持**
```json
{
  "server": {
    "nat_traversal": {
      "enable": true,
      "target_registration": true,
      "keep_alive_interval": 30
    }
  }
}
```

2. **被控端客户端配置**
```json
{
  "client": {
    "mode": "target",
    "server_host": "YOUR_CLOUD_SERVER_IP",
    "server_port": 8888,
    "device_id": "target_desktop_nat_001",
    "nat_traversal": {
      "enable": true,
      "keep_alive": true
    },
    "auto_reconnect": true
  }
}
```

3. **启动被控端客户端**
```bash
python main.py client --config nat_client_config.json
```

### 方案四：路由器端口转发

**适用场景**：被控端客户端在路由器后面，可以配置端口转发

#### 配置步骤：

1. **路由器端口转发设置**
   - 配置路由器，确保被控端客户端可以访问外网
   - 如需要，可设置DMZ或特定端口转发

2. **被控端客户端配置**
```json
{
  "client": {
    "mode": "target",
    "server_host": "YOUR_CLOUD_SERVER_IP",
    "server_port": 8888,
    "device_id": "target_desktop_router_001",
    "network": {
      "router_mode": true,
      "public_ip_detection": true
    },
    "auto_reconnect": true
  }
}
```

3. **启动被控端客户端**
```bash
python main.py client --config router_client_config.json
```

### 连接验证

无论使用哪种方案，都需要验证连接是否正常：

```bash
# 测试云服务器连接
telnet YOUR_CLOUD_SERVER_IP 8888

# 查看已连接的被控端客户端
curl http://YOUR_CLOUD_SERVER_IP:8888/api/clients

# 查看服务端状态
curl http://YOUR_CLOUD_SERVER_IP:8888/api/status

# 检查服务端日志
tail -f /var/log/rdptool/server.log

# 检查被控端客户端日志
tail -f /var/log/rdptool/client.log
```

### 网络要求

- **带宽**：上行至少2Mbps，推荐5Mbps以上
- **延迟**：建议小于100ms
- **稳定性**：连接应保持稳定，避免频繁断线

## 控制端客户端连接

控制端客户端是发送控制指令的一方，用于远程控制被控端客户端。

### 配置步骤：

1. **安装RDP工具**
```bash
git clone <your-repo-url>
cd rdptool
pip install -r requirements.txt
```

2. **生成控制端配置**
```bash
python main.py config --type client --output controller_config.json
```

3. **编辑配置文件**
```json
{
  "client": {
    "mode": "controller",
    "server_host": "YOUR_CLOUD_SERVER_IP",
    "server_port": 8888,
    "target_device_id": "target_desktop_001",
    "user_credentials": {
      "username": "your_username",
      "password": "your_password"
    },
    "display": {
      "resolution": "1920x1080",
      "color_depth": 24,
      "compression": "medium"
    }
  }
}
```

4. **启动控制端客户端**
```bash
# 命令行模式
python main.py client --config controller_config.json

# GUI模式
python main.py client --config controller_config.json --gui
```

5. **连接到指定被控端**
```bash
# 连接到特定设备
python main.py client --host YOUR_CLOUD_SERVER_IP --port 8888 --target target_desktop_001 --gui
```

## 部署步骤

### 快速开始（Docker部署）

如果您希望快速部署，推荐使用Docker方式：

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd rdptool

# 2. 启动服务端
docker-compose up -d rdp-server

# 3. 验证部署
curl http://localhost:8888/api/status
```

**详细的Docker部署说明请参考：** [Docker部署指南](DOCKER_DEPLOYMENT.md)

### 传统部署步骤

#### 1. 服务器环境准备

##### Ubuntu/Debian系统
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python和依赖
sudo apt install python3 python3-pip python3-venv git -y

# 安装系统依赖
sudo apt install build-essential libssl-dev libffi-dev python3-dev -y
sudo apt install xvfb x11vnc fluxbox -y  # 虚拟显示支持
```

#### CentOS/RHEL系统
```bash
# 更新系统
sudo yum update -y

# 安装Python和依赖
sudo yum install python3 python3-pip git -y

# 安装系统依赖
sudo yum groupinstall "Development Tools" -y
sudo yum install openssl-devel libffi-devel python3-devel -y
sudo yum install xorg-x11-server-Xvfb x11vnc fluxbox -y
```

#### Windows Server系统
```powershell
# 安装Python (下载并安装Python 3.8+)
# 从 https://www.python.org/downloads/ 下载

# 安装Git
# 从 https://git-scm.com/download/win 下载

# 安装Visual Studio Build Tools (如需编译)
```

### 2. 下载和安装RDP工具

```bash
# 创建工作目录
mkdir -p /opt/rdptool
cd /opt/rdptool

# 克隆项目 (或上传项目文件)
git clone <your-repo-url> .
# 或者直接上传项目文件到服务器

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置服务端

#### 创建服务端配置文件
```bash
# 生成默认配置
python main.py config --type server --output server_config.json
```

#### 编辑配置文件 `server_config.json`
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8888,
    "max_connections": 10,
    "connection_timeout": 300,
    "enable_ssl": true,
    "ssl_cert_file": "/opt/rdptool/certs/server.crt",
    "ssl_key_file": "/opt/rdptool/certs/server.key"
  },
  "screen": {
    "capture_method": "xvfb",
    "resolution": "1920x1080",
    "color_depth": 24,
    "frame_rate": 30,
    "compression": "jpeg",
    "quality": 80
  },
  "auth": {
    "enable": true,
    "method": "userpass",
    "users": {
      "admin": "your_secure_password",
      "user1": "password1",
      "user2": "password2"
    },
    "session_timeout": 3600
  },
  "security": {
    "encryption_type": "aes_256_cbc",
    "require_encryption": true,
    "max_failed_attempts": 3,
    "ban_duration": 300
  },
  "logging": {
    "level": "INFO",
    "file": "/var/log/rdptool/server.log",
    "max_size": "100MB",
    "backup_count": 5
  }
}
```

### 4. 生成SSL证书 (推荐)

```bash
# 创建证书目录
sudo mkdir -p /opt/rdptool/certs
cd /opt/rdptool/certs

# 生成自签名证书 (测试用)
sudo openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes

# 或使用Let's Encrypt (生产环境推荐)
sudo apt install certbot -y
sudo certbot certonly --standalone -d your-domain.com
# 然后在配置中使用 /etc/letsencrypt/live/your-domain.com/ 下的证书
```

### 5. 配置防火墙

#### Ubuntu (ufw)
```bash
sudo ufw allow 8888/tcp
sudo ufw allow 1080/tcp  # 如果使用代理服务
sudo ufw enable
```

#### CentOS (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=8888/tcp
sudo firewall-cmd --permanent --add-port=1080/tcp  # 如果使用代理服务
sudo firewall-cmd --reload
```

#### 云服务商安全组
在云服务商控制台中配置安全组规则:
- 入站规则: TCP 8888 端口，来源 0.0.0.0/0
- 入站规则: TCP 1080 端口，来源 0.0.0.0/0 (可选)

### 6. 启动服务

#### 前台运行 (测试)
```bash
cd /opt/rdptool
source venv/bin/activate
python main.py server --config server_config.json
```

#### 后台运行 (生产)
```bash
# 使用systemd服务
sudo tee /etc/systemd/system/rdptool.service > /dev/null <<EOF
[Unit]
Description=RDP Tool Server
After=network.target

[Service]
Type=simple
User=rdptool
Group=rdptool
WorkingDirectory=/opt/rdptool
Environment=PATH=/opt/rdptool/venv/bin
ExecStart=/opt/rdptool/venv/bin/python main.py server --config server_config.json --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 创建服务用户
sudo useradd -r -s /bin/false rdptool
sudo chown -R rdptool:rdptool /opt/rdptool

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable rdptool
sudo systemctl start rdptool

# 检查状态
sudo systemctl status rdptool
```

## 客户端连接

### 1. 客户端配置

#### 生成客户端配置
```bash
python main.py config --type client --output client_config.json
```

#### 编辑客户端配置 `client_config.json`
```json
{
  "client": {
    "auto_reconnect": true,
    "reconnect_interval": 5,
    "connection_timeout": 30
  },
  "display": {
    "auto_scale": true,
    "quality": "high",
    "color_depth": 24
  },
  "security": {
    "encryption_type": "aes_256_cbc",
    "verify_certificate": false
  },
  "logging": {
    "level": "INFO",
    "file": "rdp_client.log"
  }
}
```

### 2. 连接方式

#### GUI模式连接
```bash
python main.py client --gui --config client_config.json
```

#### 命令行模式连接
```bash
python main.py client --host YOUR_SERVER_IP --port 8888 --username admin --password your_secure_password
```

## 多客户端支持

### 并发连接管理

服务端支持多个客户端同时连接，每个连接都有独立的会话:

1. **会话隔离**: 每个客户端连接都有唯一的会话ID
2. **资源管理**: 服务端自动管理多个连接的资源分配
3. **权限控制**: 可以为不同用户设置不同的权限
4. **负载均衡**: 自动分配连接到可用的处理线程

### 用户权限配置

在 `server_config.json` 中配置不同用户:

```json
{
  "auth": {
    "users": {
      "admin": {
        "password": "admin_password",
        "permissions": ["view", "control", "file_transfer"]
      },
      "viewer1": {
        "password": "viewer_password",
        "permissions": ["view"]
      },
      "operator1": {
        "password": "operator_password",
        "permissions": ["view", "control"]
      }
    }
  }
}
```

### 连接监控

查看当前连接状态:
```bash
# 查看服务日志
sudo journalctl -u rdptool -f

# 查看连接统计
curl http://localhost:8888/api/status
```

## 性能优化

### 1. 网络优化
- 使用压缩传输减少带宽占用
- 调整帧率和质量平衡性能和体验
- 启用增量更新减少数据传输

### 2. 服务器优化
- 增加服务器内存和CPU核心数
- 使用SSD存储提高I/O性能
- 配置适当的连接池大小

### 3. 客户端优化
- 使用有线网络连接
- 关闭不必要的后台程序
- 调整显示分辨率和色彩深度

## 故障排除

### 常见问题

1. **连接超时**
   - 检查防火墙设置
   - 验证端口是否正确开放
   - 确认服务端正在运行

2. **认证失败**
   - 检查用户名密码是否正确
   - 验证配置文件中的用户设置

3. **画面卡顿**
   - 降低帧率和质量设置
   - 检查网络带宽
   - 优化服务器性能

4. **SSL证书错误**
   - 检查证书文件路径
   - 验证证书有效性
   - 客户端设置忽略证书验证(测试环境)

### 日志分析

```bash
# 查看服务端日志
tail -f /var/log/rdptool/server.log

# 查看系统日志
sudo journalctl -u rdptool -n 100

# 查看网络连接
netstat -tlnp | grep 8888
```

## 安全建议

1. **强密码策略**: 使用复杂密码，定期更换
2. **SSL加密**: 生产环境必须启用SSL
3. **访问控制**: 限制允许连接的IP地址
4. **定期更新**: 保持系统和软件最新版本
5. **监控日志**: 定期检查访问日志和异常
6. **备份配置**: 定期备份配置文件和证书

## 扩展功能

### 代理服务配置

如需通过代理访问，可以启用内置代理服务:

```bash
# 生成代理配置
python main.py config --type proxy --output proxy_config.json

# 启动代理服务
python main.py proxy --config proxy_config.json
```

### 文件传输

支持客户端和服务端之间的文件传输功能，在客户端GUI中可以直接拖拽文件。

### 剪贴板同步

支持客户端和服务端之间的剪贴板内容同步。

## 总结

通过以上配置，您可以在云服务器上成功部署支持多客户端连接的远程桌面服务。关键要点:

1. 确保服务器有足够的资源支持多个并发连接
2. 正确配置网络和防火墙规则
3. 使用SSL加密保证连接安全
4. 合理设置用户权限和会话管理
5. 定期监控和维护服务状态

如有问题，请查看日志文件或联系技术支持。