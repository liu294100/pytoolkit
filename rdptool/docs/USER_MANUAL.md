# RDPTool 用户手册

## 概述

欢迎使用 RDPTool！这是一个功能强大的远程桌面和代理工具，支持多种协议和高级功能。本手册将帮助您快速上手并充分利用 RDPTool 的各项功能。

## 目录

- [快速开始](#快速开始)
- [安装指南](#安装指南)
- [基本使用](#基本使用)
- [高级功能](#高级功能)
- [配置详解](#配置详解)
- [故障排除](#故障排除)
- [常见问题](#常见问题)
- [最佳实践](#最佳实践)

---

## 快速开始

### 5分钟快速体验

1. **安装 RDPTool**
   ```bash
   pip install rdptool
   ```

2. **生成配置文件**
   ```bash
   rdptool generate-config server > server.json
   rdptool generate-config client > client.json
   ```

3. **启动服务端**
   ```bash
   rdptool server --config server.json
   ```

4. **启动客户端**
   ```bash
   rdptool client --config client.json
   ```

5. **开始使用**
   - 在客户端界面输入服务端地址
   - 点击连接按钮
   - 享受远程桌面体验！

---

## 安装指南

### 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10+, macOS 11+, Linux (Ubuntu 20.04+)
- **内存**: 最少 2GB RAM
- **网络**: 稳定的网络连接

### 安装方法

#### 方法1: 使用 pip 安装 (推荐)
```bash
# 基础安装
pip install rdptool

# 完整安装 (包含所有可选依赖)
pip install rdptool[all]

# 按需安装
pip install rdptool[gui]      # GUI 界面
pip install rdptool[crypto]   # 加密功能
pip install rdptool[image]    # 图像处理
```

#### 方法2: 从源码安装
```bash
git clone https://github.com/rdptool/rdptool.git
cd rdptool
pip install -r requirements.txt
pip install -e .
```

#### 方法3: 使用 Docker
```bash
docker pull rdptool/rdptool:latest
docker run -p 8888:8888 rdptool/rdptool:latest
```

### 验证安装
```bash
rdptool --version
rdptool --help
```

---

## 基本使用

### 命令行界面

RDPTool 提供了简洁易用的命令行界面：

```bash
rdptool [命令] [选项]
```

#### 主要命令

| 命令 | 描述 | 示例 |
|------|------|------|
| `server` | 启动服务端 | `rdptool server --port 8888` |
| `client` | 启动客户端 | `rdptool client --host 192.168.1.100` |
| `proxy` | 启动代理服务器 | `rdptool proxy --port 8080` |
| `gui` | 启动图形界面 | `rdptool gui` |
| `generate-config` | 生成配置文件 | `rdptool generate-config server` |

#### 常用选项

| 选项 | 描述 | 示例 |
|------|------|------|
| `--config` | 指定配置文件 | `--config server.json` |
| `--host` | 指定主机地址 | `--host 0.0.0.0` |
| `--port` | 指定端口 | `--port 8888` |
| `--verbose` | 详细输出 | `--verbose` |
| `--help` | 显示帮助 | `--help` |

### 服务端使用

#### 启动服务端
```bash
# 使用默认配置
rdptool server

# 指定端口
rdptool server --port 8888

# 使用配置文件
rdptool server --config server.json

# 启用详细日志
rdptool server --verbose
```

#### 服务端配置示例
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8888,
    "max_connections": 100
  },
  "security": {
    "authentication": true,
    "encryption": true,
    "password": "your-password"
  },
  "features": {
    "screen_sharing": true,
    "file_transfer": true,
    "clipboard_sync": true
  }
}
```

### 客户端使用

#### 启动客户端
```bash
# 连接到服务端
rdptool client --host 192.168.1.100 --port 8888

# 使用配置文件
rdptool client --config client.json

# 启用全屏模式
rdptool client --fullscreen
```

#### 客户端配置示例
```json
{
  "client": {
    "server_host": "192.168.1.100",
    "server_port": 8888,
    "auto_connect": false
  },
  "display": {
    "fullscreen": false,
    "resolution": "1920x1080",
    "color_depth": 24
  },
  "security": {
    "password": "your-password",
    "verify_certificate": true
  }
}
```

### 代理服务器使用

#### 启动代理服务器
```bash
# HTTP 代理
rdptool proxy --protocol http --port 8080

# SOCKS5 代理
rdptool proxy --protocol socks5 --port 1080

# 多协议代理
rdptool proxy --config proxy.json
```

#### 代理配置示例
```json
{
  "proxy": {
    "host": "0.0.0.0",
    "port": 8080,
    "protocols": ["http", "socks5"],
    "max_connections": 1000
  },
  "security": {
    "auth_required": false,
    "allowed_ips": [],
    "rate_limit": {
      "enabled": true,
      "max_requests": 100
    }
  }
}
```

### 图形界面使用

#### 启动 GUI
```bash
rdptool gui
```

#### GUI 功能

1. **主界面**
   - 服务端/客户端/代理切换
   - 快速连接
   - 设置管理

2. **连接管理**
   - 添加/编辑/删除连接
   - 连接历史
   - 收藏夹

3. **实时监控**
   - 连接状态
   - 网络流量
   - 性能指标

4. **设置界面**
   - 网络设置
   - 显示设置
   - 安全设置
   - 高级选项

---

## 高级功能

### 多协议支持

RDPTool 支持多种网络协议：

#### TCP/UDP 代理
```bash
# TCP 代理
rdptool proxy --protocol tcp --listen-port 8080 --target-host example.com --target-port 80

# UDP 代理
rdptool proxy --protocol udp --listen-port 53 --target-host 8.8.8.8 --target-port 53
```

#### HTTP/HTTPS 代理
```bash
# HTTP 代理
rdptool proxy --protocol http --port 8080

# HTTPS 代理 (带 SSL)
rdptool proxy --protocol https --port 8443 --ssl-cert cert.pem --ssl-key key.pem
```

#### SOCKS 代理
```bash
# SOCKS4 代理
rdptool proxy --protocol socks4 --port 1080

# SOCKS5 代理 (带认证)
rdptool proxy --protocol socks5 --port 1080 --auth username:password
```

#### WebSocket 代理
```bash
# WebSocket 代理
rdptool proxy --protocol websocket --port 8080 --ws-path /proxy
```

### 安全功能

#### 加密通信
```json
{
  "security": {
    "encryption": {
      "enabled": true,
      "algorithm": "AES-256-GCM",
      "key_exchange": "ECDH"
    },
    "ssl": {
      "enabled": true,
      "cert_file": "server.crt",
      "key_file": "server.key",
      "verify_client": false
    }
  }
}
```

#### 身份认证
```json
{
  "security": {
    "authentication": {
      "enabled": true,
      "method": "password",
      "users": {
        "admin": "hashed_password",
        "user1": "hashed_password"
      },
      "session_timeout": 3600
    }
  }
}
```

#### 访问控制
```json
{
  "security": {
    "access_control": {
      "allowed_ips": ["192.168.1.0/24", "10.0.0.0/8"],
      "blocked_ips": ["192.168.1.100"],
      "rate_limit": {
        "enabled": true,
        "max_connections_per_ip": 10,
        "max_requests_per_minute": 100
      }
    }
  }
}
```

### 性能优化

#### 压缩设置
```json
{
  "performance": {
    "compression": {
      "enabled": true,
      "algorithm": "lz4",
      "level": 6
    },
    "buffer_size": 16384,
    "worker_threads": 4
  }
}
```

#### 缓存配置
```json
{
  "performance": {
    "cache": {
      "enabled": true,
      "size": "100MB",
      "ttl": 3600,
      "type": "memory"
    }
  }
}
```

### 文件传输

#### 启用文件传输
```json
{
  "features": {
    "file_transfer": {
      "enabled": true,
      "max_file_size": "100MB",
      "allowed_extensions": [".txt", ".pdf", ".jpg"],
      "upload_dir": "./uploads",
      "download_dir": "./downloads"
    }
  }
}
```

#### 使用文件传输
```bash
# 命令行文件传输
rdptool transfer upload --file document.pdf --host 192.168.1.100
rdptool transfer download --file remote_file.txt --host 192.168.1.100
```

### 会话录制

#### 启用录制功能
```json
{
  "features": {
    "session_recording": {
      "enabled": true,
      "format": "mp4",
      "quality": "high",
      "output_dir": "./recordings",
      "auto_start": false
    }
  }
}
```

#### 录制控制
```bash
# 开始录制
rdptool record start --session session_id

# 停止录制
rdptool record stop --session session_id

# 查看录制列表
rdptool record list
```

### 多显示器支持

#### 配置多显示器
```json
{
  "display": {
    "multi_monitor": {
      "enabled": true,
      "monitors": [
        {
          "id": 0,
          "resolution": "1920x1080",
          "position": {"x": 0, "y": 0}
        },
        {
          "id": 1,
          "resolution": "1920x1080",
          "position": {"x": 1920, "y": 0}
        }
      ]
    }
  }
}
```

---

## 配置详解

### 配置文件结构

RDPTool 使用 JSON 格式的配置文件，主要包含以下部分：

```json
{
  "server": {},      // 服务端配置
  "client": {},      // 客户端配置
  "proxy": {},       // 代理配置
  "security": {},    // 安全配置
  "performance": {}, // 性能配置
  "features": {},    // 功能配置
  "logging": {},     // 日志配置
  "monitoring": {}   // 监控配置
}
```

### 服务端配置

```json
{
  "server": {
    "host": "0.0.0.0",              // 监听地址
    "port": 8888,                   // 监听端口
    "max_connections": 100,         // 最大连接数
    "connection_timeout": 300,      // 连接超时 (秒)
    "keepalive_interval": 30,       // 心跳间隔 (秒)
    "backlog": 128,                 // 监听队列长度
    "reuse_address": true,          // 重用地址
    "tcp_nodelay": true             // 禁用 Nagle 算法
  }
}
```

### 客户端配置

```json
{
  "client": {
    "server_host": "localhost",     // 服务端地址
    "server_port": 8888,            // 服务端端口
    "auto_connect": false,          // 自动连接
    "reconnect_attempts": 3,        // 重连次数
    "reconnect_delay": 5,           // 重连延迟 (秒)
    "connection_timeout": 30,       // 连接超时 (秒)
    "keepalive_interval": 30        // 心跳间隔 (秒)
  }
}
```

### 显示配置

```json
{
  "display": {
    "resolution": "1920x1080",      // 分辨率
    "color_depth": 24,              // 色彩深度
    "fullscreen": false,            // 全屏模式
    "scaling": 1.0,                 // 缩放比例
    "cursor_visible": true,         // 显示光标
    "frame_rate": 30,               // 帧率
    "quality": "high",              // 画质 (low/medium/high)
    "adaptive_quality": true        // 自适应画质
  }
}
```

### 输入配置

```json
{
  "input": {
    "keyboard": {
      "enabled": true,              // 启用键盘
      "layout": "us",              // 键盘布局
      "shortcuts_enabled": true    // 启用快捷键
    },
    "mouse": {
      "enabled": true,              // 启用鼠标
      "sensitivity": 1.0,          // 灵敏度
      "acceleration": true,        // 加速度
      "wheel_enabled": true        // 启用滚轮
    },
    "touch": {
      "enabled": false,             // 启用触摸
      "gestures": true             // 启用手势
    }
  }
}
```

### 网络配置

```json
{
  "network": {
    "protocol": "tcp",              // 协议类型
    "buffer_size": 8192,            // 缓冲区大小
    "compression": "zlib",          // 压缩算法
    "bandwidth_limit": 0,           // 带宽限制 (0=无限制)
    "proxy": {
      "enabled": false,             // 启用代理
      "type": "http",              // 代理类型
      "host": "proxy.example.com", // 代理地址
      "port": 8080,                // 代理端口
      "username": "",              // 用户名
      "password": ""               // 密码
    }
  }
}
```

### 安全配置

```json
{
  "security": {
    "encryption": {
      "enabled": true,              // 启用加密
      "algorithm": "AES-256-GCM",  // 加密算法
      "key_size": 256,             // 密钥长度
      "key_exchange": "ECDH"       // 密钥交换
    },
    "authentication": {
      "enabled": true,              // 启用认证
      "method": "password",        // 认证方式
      "password": "your-password", // 密码
      "session_timeout": 3600      // 会话超时
    },
    "ssl": {
      "enabled": false,             // 启用 SSL
      "cert_file": "server.crt",   // 证书文件
      "key_file": "server.key",    // 私钥文件
      "ca_file": "ca.crt",         // CA 证书
      "verify_client": false       // 验证客户端
    }
  }
}
```

---

## 故障排除

### 连接问题

#### 无法连接到服务端

**症状**: 客户端显示连接失败

**可能原因**:
1. 服务端未启动
2. 网络不通
3. 防火墙阻止
4. 端口被占用

**解决方法**:
```bash
# 检查服务端状态
rdptool server --test-connection

# 检查端口是否开放
telnet server_ip 8888

# 检查防火墙
sudo ufw status

# 检查端口占用
netstat -an | grep 8888
```

#### 连接频繁断开

**症状**: 连接建立后很快断开

**可能原因**:
1. 网络不稳定
2. 超时设置过短
3. 资源不足

**解决方法**:
```json
{
  "client": {
    "connection_timeout": 60,
    "keepalive_interval": 10,
    "reconnect_attempts": 5
  }
}
```

### 性能问题

#### 画面卡顿

**症状**: 远程桌面画面更新缓慢

**解决方法**:
```json
{
  "display": {
    "quality": "medium",
    "frame_rate": 15,
    "adaptive_quality": true
  },
  "performance": {
    "compression": "lz4",
    "buffer_size": 16384
  }
}
```

#### 延迟过高

**症状**: 操作响应慢

**解决方法**:
```json
{
  "network": {
    "tcp_nodelay": true,
    "buffer_size": 4096
  },
  "performance": {
    "compression": "none",
    "worker_threads": 2
  }
}
```

### 安全问题

#### 认证失败

**症状**: 输入正确密码仍无法登录

**解决方法**:
```bash
# 重置密码
rdptool auth reset-password --user admin

# 检查认证配置
rdptool config validate --section security
```

#### SSL 证书错误

**症状**: SSL 连接失败

**解决方法**:
```bash
# 生成新证书
rdptool ssl generate-cert --host your-hostname

# 验证证书
openssl x509 -in server.crt -text -noout
```

### 日志分析

#### 启用详细日志
```json
{
  "logging": {
    "level": "DEBUG",
    "file": "rdptool.log",
    "console": true
  }
}
```

#### 常见错误信息

| 错误信息 | 原因 | 解决方法 |
|----------|------|----------|
| `Connection refused` | 服务端未启动 | 启动服务端 |
| `Authentication failed` | 密码错误 | 检查密码 |
| `SSL handshake failed` | SSL 配置错误 | 检查证书 |
| `Permission denied` | 权限不足 | 检查文件权限 |
| `Address already in use` | 端口被占用 | 更换端口 |

---

## 常见问题

### Q: 如何提高连接速度？

**A**: 可以通过以下方式优化：

1. **降低画质**:
   ```json
   {
     "display": {
       "quality": "medium",
       "frame_rate": 15
     }
   }
   ```

2. **启用压缩**:
   ```json
   {
     "performance": {
       "compression": "lz4"
     }
   }
   ```

3. **优化网络**:
   ```json
   {
     "network": {
       "tcp_nodelay": true,
       "buffer_size": 16384
     }
   }
   ```

### Q: 如何设置开机自启动？

**A**: 根据操作系统选择方法：

**Linux (systemd)**:
```bash
# 创建服务文件
sudo nano /etc/systemd/system/rdptool.service

# 启用服务
sudo systemctl enable rdptool
sudo systemctl start rdptool
```

**Windows**:
```cmd
# 使用任务计划程序
schtasks /create /tn "RDPTool" /tr "rdptool server" /sc onstart
```

**macOS**:
```bash
# 创建 LaunchAgent
cp rdptool.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/rdptool.plist
```

### Q: 如何配置多用户访问？

**A**: 在服务端配置中添加多个用户：

```json
{
  "security": {
    "authentication": {
      "enabled": true,
      "users": {
        "admin": "admin_password_hash",
        "user1": "user1_password_hash",
        "user2": "user2_password_hash"
      },
      "permissions": {
        "admin": ["all"],
        "user1": ["screen_sharing", "file_transfer"],
        "user2": ["screen_sharing"]
      }
    }
  }
}
```

### Q: 如何限制访问 IP？

**A**: 使用访问控制列表：

```json
{
  "security": {
    "access_control": {
      "allowed_ips": [
        "192.168.1.0/24",
        "10.0.0.0/8"
      ],
      "blocked_ips": [
        "192.168.1.100"
      ]
    }
  }
}
```

### Q: 如何备份和恢复配置？

**A**: 使用内置的备份功能：

```bash
# 备份配置
rdptool config backup --output backup.json

# 恢复配置
rdptool config restore --input backup.json

# 导出特定配置
rdptool config export --section security --output security.json
```

### Q: 如何监控系统状态？

**A**: 启用监控功能：

```json
{
  "monitoring": {
    "enabled": true,
    "metrics_port": 9090,
    "health_check_port": 8889,
    "alerts": {
      "email": "admin@example.com",
      "webhook": "https://hooks.slack.com/..."
    }
  }
}
```

### Q: 如何处理防火墙问题？

**A**: 根据防火墙类型配置：

**Windows 防火墙**:
```cmd
netsh advfirewall firewall add rule name="RDPTool" dir=in action=allow protocol=TCP localport=8888
```

**Linux iptables**:
```bash
sudo iptables -A INPUT -p tcp --dport 8888 -j ACCEPT
```

**Linux ufw**:
```bash
sudo ufw allow 8888/tcp
```

---

## 最佳实践

### 安全最佳实践

1. **启用加密**
   ```json
   {
     "security": {
       "encryption": {
         "enabled": true,
         "algorithm": "AES-256-GCM"
       }
     }
   }
   ```

2. **使用强密码**
   ```bash
   # 生成强密码
   rdptool auth generate-password --length 16
   ```

3. **定期更新证书**
   ```bash
   # 自动续期脚本
   #!/bin/bash
   rdptool ssl renew-cert --auto
   systemctl reload rdptool
   ```

4. **限制访问来源**
   ```json
   {
     "security": {
       "access_control": {
         "allowed_ips": ["trusted_network/24"]
       }
     }
   }
   ```

### 性能最佳实践

1. **合理设置缓冲区**
   ```json
   {
     "performance": {
       "buffer_size": 16384,
       "worker_threads": 4
     }
   }
   ```

2. **启用压缩**
   ```json
   {
     "performance": {
       "compression": "lz4",
       "compression_level": 6
     }
   }
   ```

3. **优化显示设置**
   ```json
   {
     "display": {
       "adaptive_quality": true,
       "frame_rate": 30,
       "quality": "high"
     }
   }
   ```

### 运维最佳实践

1. **定期备份**
   ```bash
   # 每日备份脚本
   #!/bin/bash
   rdptool config backup --output "/backup/rdptool-$(date +%Y%m%d).json"
   ```

2. **监控日志**
   ```bash
   # 日志轮转
   logrotate /etc/logrotate.d/rdptool
   ```

3. **健康检查**
   ```bash
   # 健康检查脚本
   #!/bin/bash
   curl -f http://localhost:8889/health || systemctl restart rdptool
   ```

4. **性能监控**
   ```json
   {
     "monitoring": {
       "metrics_enabled": true,
       "prometheus_port": 9090
     }
   }
   ```

### 网络最佳实践

1. **使用 CDN**
   ```json
   {
     "network": {
       "cdn": {
         "enabled": true,
         "provider": "cloudflare"
       }
     }
   }
   ```

2. **负载均衡**
   ```json
   {
     "cluster": {
       "enabled": true,
       "load_balancer": "round_robin",
       "nodes": [
         "server1.example.com:8888",
         "server2.example.com:8888"
       ]
     }
   }
   ```

3. **连接池**
   ```json
   {
     "performance": {
       "connection_pool": {
         "enabled": true,
         "max_size": 100,
         "min_size": 10
       }
     }
   }
   ```

---

## 技术支持

### 获取帮助

- **在线文档**: https://docs.rdptool.com
- **社区论坛**: https://community.rdptool.com
- **GitHub Issues**: https://github.com/rdptool/rdptool/issues
- **邮件支持**: support@rdptool.com

### 报告问题

在报告问题时，请提供以下信息：

1. **系统信息**
   ```bash
   rdptool --version
   rdptool system-info
   ```

2. **配置文件**
   ```bash
   rdptool config show --sanitized
   ```

3. **日志文件**
   ```bash
   rdptool logs export --last 100
   ```

4. **错误信息**
   - 完整的错误消息
   - 重现步骤
   - 预期行为

### 贡献代码

欢迎贡献代码！请参考 [开发指南](DEVELOPMENT.md)。

---

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持基本远程桌面功能
- 支持多种代理协议
- 提供 GUI 界面

### v1.1.0 (计划中)
- 增强安全功能
- 性能优化
- 移动端支持

---

*最后更新: 2024-01-01*