# Docker 部署指南

本文档详细说明如何使用Docker部署RDP工具，支持容器化的服务端、客户端和代理服务。

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [服务架构](#服务架构)
- [配置说明](#配置说明)
- [部署模式](#部署模式)
- [监控和日志](#监控和日志)
- [故障排除](#故障排除)
- [生产环境部署](#生产环境部署)

## 系统要求

### 软件要求
- Docker Engine 20.10+
- Docker Compose 2.0+
- 至少 4GB RAM
- 至少 10GB 可用磁盘空间

### 网络要求
- 端口 8888：RDP服务端
- 端口 1080：代理服务（可选）
- 端口 6379：Redis缓存（可选）
- 端口 9090：监控服务（可选）

## 快速开始

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd rdptool
```

### 2. 构建镜像
```bash
docker-compose build
```

### 3. 启动服务端
```bash
# 仅启动RDP服务端
docker-compose up rdp-server

# 后台运行
docker-compose up -d rdp-server
```

### 4. 验证部署
```bash
# 检查服务状态
curl http://localhost:8888/api/status

# 查看容器状态
docker-compose ps
```

## 服务架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   控制端客户端   │    │   被控端客户端   │    │    代理服务     │
│  (Controller)   │    │    (Target)     │    │    (Proxy)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴───────────┐
                    │      RDP服务端          │
                    │   (Connection Pool)     │
                    │      Port: 8888         │
                    └─────────────────────────┘
                                 │
                    ┌─────────────┴───────────┐
                    │      Redis缓存          │
                    │   (Session Store)       │
                    │      Port: 6379         │
                    └─────────────────────────┘
```

## 配置说明

### 环境变量

#### 通用环境变量
- `RDPTOOL_MODE`: 运行模式 (server/client/proxy)
- `RDPTOOL_LOG_DIR`: 日志目录 (默认: /var/log/rdptool)
- `RDPTOOL_CONFIG_DIR`: 配置目录 (默认: /app/configs)

#### 服务端环境变量
- `RDPTOOL_PORT`: 服务端端口 (默认: 8888)
- `RDPTOOL_CONFIG`: 配置文件路径

#### 客户端环境变量
- `RDPTOOL_SERVER_HOST`: 服务端主机地址
- `RDPTOOL_SERVER_PORT`: 服务端端口
- `DISPLAY`: X11显示变量 (Linux)

#### 代理环境变量
- `RDPTOOL_PROXY_PORT`: 代理端口 (默认: 1080)

### 配置文件

项目提供了以下Docker专用配置文件：

- `configs/docker_server_config.json`: 服务端配置
- `configs/docker_target_client_config.json`: 被控端客户端配置
- `configs/docker_controller_client_config.json`: 控制端客户端配置
- `configs/docker_proxy_config.json`: 代理服务配置

## 部署模式

### 1. 仅服务端模式
```bash
# 启动RDP服务端
docker-compose up rdp-server
```

### 2. 完整服务模式
```bash
# 启动服务端和代理
docker-compose --profile proxy up rdp-server rdp-proxy
```

### 3. 包含客户端模式
```bash
# 启动服务端和示例客户端
docker-compose --profile target-client --profile controller-client up
```

### 4. 监控模式
```bash
# 启动服务端和监控服务
docker-compose --profile monitoring up rdp-server rdp-monitor
```

### 5. 完整部署
```bash
# 启动所有服务
docker-compose --profile proxy --profile target-client --profile controller-client --profile cache --profile monitoring up
```

### 使用启动脚本

项目提供了便捷的启动脚本 `docker-start.sh`：

```bash
# Linux/macOS
chmod +x docker-start.sh

# 仅启动服务端
./docker-start.sh server-only

# 后台启动完整服务
./docker-start.sh full -d

# 重新构建并启动
./docker-start.sh with-clients --build

# 查看帮助
./docker-start.sh --help
```

## 监控和日志

### 日志管理

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs rdp-server

# 实时跟踪日志
docker-compose logs -f rdp-server

# 查看最近100行日志
docker-compose logs --tail=100 rdp-server
```

### 监控服务

启用监控模式后，可以通过以下方式访问监控服务：

- Prometheus: http://localhost:9090
- 服务端指标: http://localhost:8888/api/metrics
- 代理指标: http://localhost:1080/metrics

### 健康检查

```bash
# 检查服务端健康状态
curl http://localhost:8888/api/status

# 检查所有容器状态
docker-compose ps

# 查看容器健康检查
docker inspect rdp-server | grep Health -A 10
```

## 故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 查看容器日志
docker-compose logs rdp-server

# 检查配置文件
docker-compose config

# 重新构建镜像
docker-compose build --no-cache
```

#### 2. 网络连接问题
```bash
# 检查网络配置
docker network ls
docker network inspect rdptool_rdp-network

# 测试容器间连接
docker-compose exec rdp-server ping rdp-proxy
```

#### 3. 端口冲突
```bash
# 检查端口占用
netstat -tulpn | grep :8888

# 修改docker-compose.yml中的端口映射
# 例如："8889:8888"
```

#### 4. 权限问题
```bash
# 检查日志目录权限
ls -la logs/

# 修复权限
sudo chown -R $USER:$USER logs/ data/
```

### 调试模式

```bash
# 进入容器调试
docker-compose exec rdp-server bash

# 查看进程状态
docker-compose exec rdp-server ps aux

# 查看网络状态
docker-compose exec rdp-server netstat -tulpn
```

## 生产环境部署

### 1. 安全配置

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  rdp-server:
    environment:
      - RDPTOOL_SSL_ENABLE=true
      - RDPTOOL_SSL_CERT=/app/certs/server.crt
      - RDPTOOL_SSL_KEY=/app/certs/server.key
    volumes:
      - ./certs:/app/certs:ro
```

### 2. 资源限制

```yaml
services:
  rdp-server:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### 3. 数据持久化

```yaml
volumes:
  rdp-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/rdptool/data
```

### 4. 负载均衡

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - rdp-server
```

### 5. 自动重启

```yaml
services:
  rdp-server:
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8888/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 6. 环境变量管理

```bash
# 创建 .env 文件
cat > .env << EOF
RDPTOOL_SERVER_HOST=your-server.com
RDPTOOL_SSL_ENABLE=true
RDPTOOL_LOG_LEVEL=INFO
REDIS_PASSWORD=your-redis-password
EOF
```

### 7. 备份策略

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/rdptool_$DATE"

# 备份配置和数据
mkdir -p $BACKUP_DIR
cp -r configs/ $BACKUP_DIR/
cp -r data/ $BACKUP_DIR/
cp docker-compose.yml $BACKUP_DIR/

# 备份数据库
docker-compose exec redis redis-cli BGSAVE
cp data/dump.rdb $BACKUP_DIR/

echo "备份完成: $BACKUP_DIR"
```

## 性能优化

### 1. 镜像优化

```dockerfile
# 多阶段构建
FROM python:3.9-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
```

### 2. 网络优化

```yaml
networks:
  rdp-network:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.name: rdp-br0
      com.docker.network.driver.mtu: 1500
```

### 3. 存储优化

```yaml
volumes:
  redis-data:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=1g,uid=999,gid=999
```

## 扩展部署

### Docker Swarm 集群

```yaml
# docker-stack.yml
version: '3.8'

services:
  rdp-server:
    image: rdptool:latest
    deploy:
      replicas: 3
      placement:
        constraints:
          - node.role == worker
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
```

### Kubernetes 部署

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rdp-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rdp-server
  template:
    metadata:
      labels:
        app: rdp-server
    spec:
      containers:
      - name: rdp-server
        image: rdptool:latest
        ports:
        - containerPort: 8888
        env:
        - name: RDPTOOL_MODE
          value: "server"
```

## 总结

本Docker部署方案提供了：

1. **灵活的部署模式** - 支持多种服务组合
2. **完整的配置管理** - 预配置的Docker专用配置文件
3. **便捷的管理工具** - 启动脚本和管理命令
4. **生产环境支持** - 安全、监控、备份等企业级特性
5. **扩展性** - 支持集群和容器编排平台

通过Docker部署，您可以快速搭建RDP服务环境，实现跨平台的远程桌面连接服务。