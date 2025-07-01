# RDPTool 部署指南

## 概述

本文档提供 RDPTool 在生产环境中的部署指南，包括系统要求、安装配置、安全设置、监控和维护等内容。

## 目录

- [系统要求](#系统要求)
- [安装部署](#安装部署)
- [配置管理](#配置管理)
- [安全设置](#安全设置)
- [性能优化](#性能优化)
- [监控和日志](#监控和日志)
- [高可用部署](#高可用部署)
- [容器化部署](#容器化部署)
- [故障排除](#故障排除)
- [维护和更新](#维护和更新)

---

## 系统要求

### 硬件要求

#### 最低配置
- **CPU**: 2 核心
- **内存**: 4GB RAM
- **存储**: 10GB 可用空间
- **网络**: 100Mbps 带宽

#### 推荐配置
- **CPU**: 4+ 核心
- **内存**: 8GB+ RAM
- **存储**: 50GB+ SSD
- **网络**: 1Gbps 带宽

#### 高负载配置
- **CPU**: 8+ 核心
- **内存**: 16GB+ RAM
- **存储**: 100GB+ NVMe SSD
- **网络**: 10Gbps 带宽

### 软件要求

#### 操作系统
- **Linux**: Ubuntu 20.04+, CentOS 8+, RHEL 8+
- **Windows**: Windows Server 2019+, Windows 10+
- **macOS**: macOS 11.0+ (开发/测试环境)

#### Python 环境
- **Python**: 3.8 或更高版本
- **pip**: 最新版本
- **virtualenv**: 推荐使用虚拟环境

#### 系统依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv \
    build-essential libssl-dev libffi-dev \
    libjpeg-dev libpng-dev libfreetype6-dev

# CentOS/RHEL
sudo yum update
sudo yum install -y python3 python3-pip python3-venv \
    gcc openssl-devel libffi-devel \
    libjpeg-devel libpng-devel freetype-devel

# Windows
# 安装 Visual Studio Build Tools
# 或 Microsoft C++ Build Tools
```

---

## 安装部署

### 单机部署

#### 1. 创建部署用户
```bash
# Linux
sudo useradd -m -s /bin/bash rdptool
sudo usermod -aG sudo rdptool
su - rdptool
```

#### 2. 下载和安装
```bash
# 方法1: 从源码安装
git clone https://github.com/rdptool/rdptool.git
cd rdptool
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 方法2: 从 PyPI 安装
python3 -m venv venv
source venv/bin/activate
pip install rdptool[all]
```

#### 3. 创建目录结构
```bash
mkdir -p /opt/rdptool/{configs,logs,data,ssl}
chown -R rdptool:rdptool /opt/rdptool
```

#### 4. 生成配置文件
```bash
# 生成默认配置
rdptool generate-config server > /opt/rdptool/configs/server.json
rdptool generate-config client > /opt/rdptool/configs/client.json
rdptool generate-config proxy > /opt/rdptool/configs/proxy.json
```

### 服务化部署

#### systemd 服务 (Linux)

创建服务文件 `/etc/systemd/system/rdptool-server.service`:

```ini
[Unit]
Description=RDPTool Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=rdptool
Group=rdptool
WorkingDirectory=/opt/rdptool
Environment=PATH=/opt/rdptool/venv/bin
ExecStart=/opt/rdptool/venv/bin/python -m rdptool server --config /opt/rdptool/configs/server.json
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/rdptool

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rdptool-server
sudo systemctl start rdptool-server
sudo systemctl status rdptool-server
```

#### Windows 服务

使用 `pywin32` 创建 Windows 服务:

```python
# rdptool_service.py
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os

class RDPToolService(win32serviceutil.ServiceFramework):
    _svc_name_ = "RDPToolServer"
    _svc_display_name_ = "RDPTool Server Service"
    _svc_description_ = "RDPTool Remote Desktop Server"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
    
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
    
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()
    
    def main(self):
        # 启动 RDPTool 服务器
        import asyncio
        from main import run_server
        
        config_path = r"C:\RDPTool\configs\server.json"
        asyncio.run(run_server(config_path))

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(RDPToolService)
```

安装服务:
```cmd
python rdptool_service.py install
net start RDPToolServer
```

---

## 配置管理

### 生产环境配置

#### 服务端配置 (`/opt/rdptool/configs/server.json`)

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8888,
    "max_connections": 1000,
    "connection_timeout": 300,
    "keepalive_interval": 30
  },
  "security": {
    "encryption": true,
    "authentication": true,
    "ssl_enabled": true,
    "ssl_cert": "/opt/rdptool/ssl/server.crt",
    "ssl_key": "/opt/rdptool/ssl/server.key",
    "allowed_ips": [],
    "blocked_ips": [],
    "rate_limit": {
      "enabled": true,
      "max_requests": 100,
      "time_window": 60
    }
  },
  "features": {
    "screen_sharing": true,
    "file_transfer": true,
    "clipboard_sync": true,
    "audio_streaming": false,
    "session_recording": true
  },
  "performance": {
    "compression": "zlib",
    "quality": "high",
    "frame_rate": 30,
    "buffer_size": 8192,
    "worker_threads": 4
  },
  "logging": {
    "level": "INFO",
    "file": "/opt/rdptool/logs/server.log",
    "max_size": "100MB",
    "backup_count": 10,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  },
  "monitoring": {
    "metrics_enabled": true,
    "metrics_port": 9090,
    "health_check_port": 8889
  }
}
```

#### 代理服务器配置 (`/opt/rdptool/configs/proxy.json`)

```json
{
  "proxy": {
    "host": "0.0.0.0",
    "port": 8080,
    "protocols": ["http", "socks5", "websocket"],
    "max_connections": 5000,
    "connection_timeout": 60
  },
  "routing": {
    "rules": [
      {
        "pattern": "*.internal.com",
        "action": "direct"
      },
      {
        "pattern": "*.blocked.com",
        "action": "block"
      }
    ],
    "default_action": "proxy"
  },
  "security": {
    "auth_required": false,
    "allowed_ips": [],
    "rate_limit": {
      "enabled": true,
      "max_connections_per_ip": 50,
      "max_requests_per_minute": 1000
    }
  },
  "performance": {
    "connection_pool_size": 100,
    "buffer_size": 16384,
    "compression": true,
    "cache_enabled": true,
    "cache_size": "1GB"
  },
  "logging": {
    "level": "INFO",
    "file": "/opt/rdptool/logs/proxy.log",
    "access_log": "/opt/rdptool/logs/access.log"
  }
}
```

### 环境变量配置

创建 `/opt/rdptool/.env` 文件:

```bash
# 基本配置
RDPTOOL_ENV=production
RDPTOOL_CONFIG_DIR=/opt/rdptool/configs
RDPTOOL_LOG_DIR=/opt/rdptool/logs
RDPTOOL_DATA_DIR=/opt/rdptool/data

# 安全配置
RDPTOOL_SECRET_KEY=your-secret-key-here
RDPTOOL_SSL_CERT=/opt/rdptool/ssl/server.crt
RDPTOOL_SSL_KEY=/opt/rdptool/ssl/server.key

# 数据库配置 (如果使用)
RDPTOOL_DB_URL=postgresql://user:pass@localhost/rdptool

# 监控配置
RDPTOOL_METRICS_ENABLED=true
RDPTOOL_HEALTH_CHECK_ENABLED=true
```

---

## 安全设置

### SSL/TLS 配置

#### 生成自签名证书 (测试环境)
```bash
openssl req -x509 -newkey rsa:4096 -keyout /opt/rdptool/ssl/server.key \
    -out /opt/rdptool/ssl/server.crt -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=rdptool.example.com"
```

#### 使用 Let's Encrypt (生产环境)
```bash
# 安装 certbot
sudo apt install certbot

# 获取证书
sudo certbot certonly --standalone -d rdptool.example.com

# 链接证书
ln -s /etc/letsencrypt/live/rdptool.example.com/fullchain.pem /opt/rdptool/ssl/server.crt
ln -s /etc/letsencrypt/live/rdptool.example.com/privkey.pem /opt/rdptool/ssl/server.key

# 设置自动续期
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### 防火墙配置

#### iptables (Linux)
```bash
# 允许 SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许 RDPTool 服务端
sudo iptables -A INPUT -p tcp --dport 8888 -j ACCEPT

# 允许代理服务器
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT

# 允许监控端口 (仅内网)
sudo iptables -A INPUT -p tcp -s 10.0.0.0/8 --dport 9090 -j ACCEPT
sudo iptables -A INPUT -p tcp -s 192.168.0.0/16 --dport 9090 -j ACCEPT

# 拒绝其他连接
sudo iptables -A INPUT -j DROP

# 保存规则
sudo iptables-save > /etc/iptables/rules.v4
```

#### ufw (Ubuntu)
```bash
# 启用防火墙
sudo ufw enable

# 允许 SSH
sudo ufw allow ssh

# 允许 RDPTool 端口
sudo ufw allow 8888/tcp
sudo ufw allow 8080/tcp

# 限制监控端口访问
sudo ufw allow from 10.0.0.0/8 to any port 9090
sudo ufw allow from 192.168.0.0/16 to any port 9090
```

### 用户权限管理

#### 创建专用用户
```bash
# 创建系统用户
sudo useradd -r -s /bin/false rdptool-server
sudo useradd -r -s /bin/false rdptool-proxy

# 设置目录权限
sudo chown -R rdptool-server:rdptool-server /opt/rdptool/server
sudo chown -R rdptool-proxy:rdptool-proxy /opt/rdptool/proxy
sudo chmod 750 /opt/rdptool/configs
sudo chmod 640 /opt/rdptool/configs/*.json
```

#### SELinux 配置 (RHEL/CentOS)
```bash
# 创建 SELinux 策略
sudo setsebool -P httpd_can_network_connect 1
sudo semanage port -a -t http_port_t -p tcp 8888
sudo semanage port -a -t http_port_t -p tcp 8080

# 设置文件上下文
sudo semanage fcontext -a -t bin_t "/opt/rdptool/venv/bin/python"
sudo restorecon -R /opt/rdptool
```

---

## 性能优化

### 系统级优化

#### 内核参数调优 (`/etc/sysctl.conf`)
```bash
# 网络优化
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.tcp_congestion_control = bbr
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 8192

# 文件描述符限制
fs.file-max = 2097152

# 应用生效
sudo sysctl -p
```

#### 文件描述符限制 (`/etc/security/limits.conf`)
```bash
rdptool soft nofile 65536
rdptool hard nofile 65536
rdptool soft nproc 32768
rdptool hard nproc 32768
```

### 应用级优化

#### 多进程部署
```bash
# 使用 gunicorn 部署多个工作进程
gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8888 --timeout 300 \
    --max-requests 1000 --max-requests-jitter 100 \
    main:app
```

#### 负载均衡配置 (nginx)
```nginx
upstream rdptool_backend {
    least_conn;
    server 127.0.0.1:8888 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8889 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8890 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8891 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name rdptool.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name rdptool.example.com;
    
    ssl_certificate /opt/rdptool/ssl/server.crt;
    ssl_certificate_key /opt/rdptool/ssl/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    location / {
        proxy_pass http://rdptool_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://rdptool_backend/health;
        access_log off;
    }
    
    # 静态文件
    location /static/ {
        alias /opt/rdptool/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 监控和日志

### 日志管理

#### logrotate 配置 (`/etc/logrotate.d/rdptool`)
```bash
/opt/rdptool/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 rdptool rdptool
    postrotate
        systemctl reload rdptool-server
        systemctl reload rdptool-proxy
    endscript
}
```

#### 集中化日志 (ELK Stack)

**Filebeat 配置** (`/etc/filebeat/filebeat.yml`):
```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /opt/rdptool/logs/*.log
  fields:
    service: rdptool
    environment: production
  fields_under_root: true
  multiline.pattern: '^\d{4}-\d{2}-\d{2}'
  multiline.negate: true
  multiline.match: after

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "rdptool-%{+yyyy.MM.dd}"

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644
```

### 性能监控

#### Prometheus 监控

**监控指标暴露** (`monitoring.py`):
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# 定义指标
connection_count = Gauge('rdptool_connections_total', 'Total connections')
request_duration = Histogram('rdptool_request_duration_seconds', 'Request duration')
error_count = Counter('rdptool_errors_total', 'Total errors', ['error_type'])
bytes_transferred = Counter('rdptool_bytes_transferred_total', 'Bytes transferred', ['direction'])

def start_metrics_server(port=9090):
    """启动指标服务器"""
    start_http_server(port)

def record_connection():
    """记录连接"""
    connection_count.inc()

def record_error(error_type):
    """记录错误"""
    error_count.labels(error_type=error_type).inc()
```

**Prometheus 配置** (`prometheus.yml`):
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'rdptool'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 5s
    metrics_path: /metrics
```

#### Grafana 仪表板

创建 Grafana 仪表板监控以下指标：
- 连接数趋势
- 请求响应时间
- 错误率
- 网络流量
- 系统资源使用率

### 健康检查

#### 健康检查端点
```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import psutil
import time

app = FastAPI()

@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查系统资源
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 检查服务状态
        service_status = check_service_status()
        
        health_data = {
            "status": "healthy" if service_status else "unhealthy",
            "timestamp": time.time(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": (disk.used / disk.total) * 100
            },
            "service": {
                "rdp_server": service_status,
                "proxy_server": check_proxy_status()
            }
        }
        
        status_code = 200 if service_status else 503
        return JSONResponse(content=health_data, status_code=status_code)
        
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

def check_service_status():
    """检查服务状态"""
    # 实现服务状态检查逻辑
    return True
```

---

## 高可用部署

### 主从架构

#### 主服务器配置
```json
{
  "server": {
    "role": "master",
    "host": "0.0.0.0",
    "port": 8888,
    "cluster": {
      "enabled": true,
      "nodes": [
        "rdptool-slave1.example.com:8888",
        "rdptool-slave2.example.com:8888"
      ],
      "heartbeat_interval": 10,
      "failover_timeout": 30
    }
  }
}
```

#### 从服务器配置
```json
{
  "server": {
    "role": "slave",
    "host": "0.0.0.0",
    "port": 8888,
    "cluster": {
      "enabled": true,
      "master": "rdptool-master.example.com:8888",
      "heartbeat_interval": 10
    }
  }
}
```

### 负载均衡

#### HAProxy 配置
```
global
    daemon
    maxconn 4096
    log stdout local0

defaults
    mode tcp
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    option tcplog

frontend rdptool_frontend
    bind *:8888
    default_backend rdptool_servers

backend rdptool_servers
    balance roundrobin
    option tcp-check
    tcp-check connect port 8889
    
    server rdp1 rdptool1.example.com:8888 check port 8889
    server rdp2 rdptool2.example.com:8888 check port 8889
    server rdp3 rdptool3.example.com:8888 check port 8889

frontend stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
```

### 数据同步

#### Redis 集群配置
```bash
# 安装 Redis
sudo apt install redis-server

# 配置 Redis 集群
redis-cli --cluster create \
    redis1.example.com:6379 \
    redis2.example.com:6379 \
    redis3.example.com:6379 \
    --cluster-replicas 1
```

#### 会话存储配置
```python
# session_store.py
import redis
import json
from typing import Dict, Any

class SessionStore:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    def save_session(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        """保存会话数据"""
        self.redis.setex(f"session:{session_id}", ttl, json.dumps(data))
    
    def load_session(self, session_id: str) -> Dict[str, Any]:
        """加载会话数据"""
        data = self.redis.get(f"session:{session_id}")
        return json.loads(data) if data else {}
    
    def delete_session(self, session_id: str):
        """删除会话"""
        self.redis.delete(f"session:{session_id}")
```

---

## 容器化部署

### Docker 部署

#### Dockerfile
```dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 安装应用
RUN pip install -e .

# 创建非 root 用户
RUN useradd -m -u 1000 rdptool && \
    chown -R rdptool:rdptool /app
USER rdptool

# 暴露端口
EXPOSE 8888 9090

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8889/health || exit 1

# 启动命令
CMD ["python", "-m", "rdptool", "server", "--config", "/app/configs/server.json"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  rdptool-server:
    build: .
    ports:
      - "8888:8888"
      - "9090:9090"
    volumes:
      - ./configs:/app/configs:ro
      - ./logs:/app/logs
      - ./ssl:/app/ssl:ro
    environment:
      - RDPTOOL_ENV=production
      - RDPTOOL_LOG_LEVEL=INFO
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - rdptool-network

  rdptool-proxy:
    build: .
    command: ["python", "-m", "rdptool", "proxy", "--config", "/app/configs/proxy.json"]
    ports:
      - "8080:8080"
    volumes:
      - ./configs:/app/configs:ro
      - ./logs:/app/logs
    environment:
      - RDPTOOL_ENV=production
    restart: unless-stopped
    networks:
      - rdptool-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - rdptool-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - rdptool-server
    restart: unless-stopped
    networks:
      - rdptool-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped
    networks:
      - rdptool-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    restart: unless-stopped
    networks:
      - rdptool-network

volumes:
  redis-data:
  prometheus-data:
  grafana-data:

networks:
  rdptool-network:
    driver: bridge
```

### Kubernetes 部署

#### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rdptool-server
  labels:
    app: rdptool-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rdptool-server
  template:
    metadata:
      labels:
        app: rdptool-server
    spec:
      containers:
      - name: rdptool-server
        image: rdptool/rdptool:latest
        ports:
        - containerPort: 8888
        - containerPort: 9090
        env:
        - name: RDPTOOL_ENV
          value: "production"
        - name: RDPTOOL_CONFIG_DIR
          value: "/app/configs"
        volumeMounts:
        - name: config-volume
          mountPath: /app/configs
        - name: ssl-volume
          mountPath: /app/ssl
        livenessProbe:
          httpGet:
            path: /health
            port: 8889
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8889
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: config-volume
        configMap:
          name: rdptool-config
      - name: ssl-volume
        secret:
          secretName: rdptool-ssl
```

#### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: rdptool-server-service
spec:
  selector:
    app: rdptool-server
  ports:
  - name: rdp
    port: 8888
    targetPort: 8888
  - name: metrics
    port: 9090
    targetPort: 9090
  type: LoadBalancer
```

#### ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rdptool-config
data:
  server.json: |
    {
      "server": {
        "host": "0.0.0.0",
        "port": 8888,
        "max_connections": 1000
      },
      "logging": {
        "level": "INFO"
      }
    }
```

---

## 故障排除

### 常见问题

#### 1. 连接超时
```bash
# 检查端口是否开放
telnet rdptool.example.com 8888

# 检查防火墙
sudo ufw status
sudo iptables -L

# 检查服务状态
sudo systemctl status rdptool-server
```

#### 2. 内存不足
```bash
# 检查内存使用
free -h
top -p $(pgrep -f rdptool)

# 检查日志
tail -f /opt/rdptool/logs/server.log | grep -i memory

# 调整配置
# 减少 max_connections
# 增加系统内存
```

#### 3. SSL 证书问题
```bash
# 检查证书有效性
openssl x509 -in /opt/rdptool/ssl/server.crt -text -noout

# 检查证书过期时间
openssl x509 -in /opt/rdptool/ssl/server.crt -enddate -noout

# 测试 SSL 连接
openssl s_client -connect rdptool.example.com:8888
```

### 日志分析

#### 错误日志分析
```bash
# 查看错误日志
grep -i error /opt/rdptool/logs/server.log

# 统计错误类型
grep -i error /opt/rdptool/logs/server.log | awk '{print $5}' | sort | uniq -c

# 查看最近的错误
tail -n 100 /opt/rdptool/logs/server.log | grep -i error
```

#### 性能分析
```bash
# 分析响应时间
grep "response_time" /opt/rdptool/logs/server.log | awk '{sum+=$6; count++} END {print "Average:", sum/count}'

# 查看慢请求
grep "response_time" /opt/rdptool/logs/server.log | awk '$6 > 1000 {print}'
```

### 性能调优

#### 系统级调优
```bash
# 增加文件描述符限制
echo "rdptool soft nofile 65536" >> /etc/security/limits.conf
echo "rdptool hard nofile 65536" >> /etc/security/limits.conf

# 优化网络参数
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65535" >> /etc/sysctl.conf
sudo sysctl -p
```

#### 应用级调优
```json
{
  "performance": {
    "worker_threads": 8,
    "connection_pool_size": 200,
    "buffer_size": 16384,
    "compression": "lz4",
    "cache_enabled": true
  }
}
```

---

## 维护和更新

### 备份策略

#### 配置备份
```bash
#!/bin/bash
# backup_config.sh

BACKUP_DIR="/backup/rdptool/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份配置文件
cp -r /opt/rdptool/configs $BACKUP_DIR/

# 备份 SSL 证书
cp -r /opt/rdptool/ssl $BACKUP_DIR/

# 备份数据库 (如果使用)
pg_dump rdptool > $BACKUP_DIR/database.sql

# 压缩备份
tar -czf $BACKUP_DIR.tar.gz -C /backup/rdptool $(basename $BACKUP_DIR)
rm -rf $BACKUP_DIR

# 清理旧备份 (保留30天)
find /backup/rdptool -name "*.tar.gz" -mtime +30 -delete
```

#### 自动备份
```bash
# 添加到 crontab
echo "0 2 * * * /opt/rdptool/scripts/backup_config.sh" | crontab -
```

### 更新流程

#### 滚动更新
```bash
#!/bin/bash
# rolling_update.sh

NEW_VERSION="$1"
if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

# 备份当前版本
./backup_config.sh

# 下载新版本
wget https://github.com/rdptool/rdptool/releases/download/v$NEW_VERSION/rdptool-$NEW_VERSION.tar.gz

# 停止服务
sudo systemctl stop rdptool-server
sudo systemctl stop rdptool-proxy

# 备份当前安装
mv /opt/rdptool /opt/rdptool.backup

# 安装新版本
tar -xzf rdptool-$NEW_VERSION.tar.gz -C /opt/
mv /opt/rdptool-$NEW_VERSION /opt/rdptool

# 恢复配置
cp -r /opt/rdptool.backup/configs /opt/rdptool/
cp -r /opt/rdptool.backup/ssl /opt/rdptool/

# 安装依赖
cd /opt/rdptool
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 启动服务
sudo systemctl start rdptool-server
sudo systemctl start rdptool-proxy

# 验证服务
sleep 10
curl -f http://localhost:8889/health

if [ $? -eq 0 ]; then
    echo "Update successful"
    rm -rf /opt/rdptool.backup
else
    echo "Update failed, rolling back"
    sudo systemctl stop rdptool-server
    sudo systemctl stop rdptool-proxy
    rm -rf /opt/rdptool
    mv /opt/rdptool.backup /opt/rdptool
    sudo systemctl start rdptool-server
    sudo systemctl start rdptool-proxy
fi
```

### 监控和告警

#### Prometheus 告警规则
```yaml
groups:
- name: rdptool
  rules:
  - alert: RDPToolDown
    expr: up{job="rdptool"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "RDPTool service is down"
      description: "RDPTool service has been down for more than 1 minute"

  - alert: HighErrorRate
    expr: rate(rdptool_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"

  - alert: HighMemoryUsage
    expr: (process_resident_memory_bytes / 1024 / 1024) > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value }}MB"
```

---

## 联系方式

- **技术支持**: support@rdptool.com
- **文档**: https://docs.rdptool.com
- **问题反馈**: https://github.com/rdptool/rdptool/issues
- **社区**: https://community.rdptool.com

---

*最后更新: 2024-01-01*