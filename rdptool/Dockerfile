# RDP Tool Dockerfile
# 支持服务端和客户端模式

FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libx11-dev \
    libxext-dev \
    libxrandr-dev \
    libxss-dev \
    libgconf-2-4 \
    libnss3-dev \
    libxss1 \
    libasound2-dev \
    libpangocairo-1.0-0 \
    libatk1.0-dev \
    libcairo-gobject2 \
    libgtk-3-dev \
    libgdk-pixbuf2.0-dev \
    telnet \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p /var/log/rdptool

# 创建配置目录
RUN mkdir -p /app/configs

# 设置环境变量
ENV PYTHONPATH=/app
ENV RDPTOOL_LOG_DIR=/var/log/rdptool
ENV RDPTOOL_CONFIG_DIR=/app/configs

# 暴露端口
EXPOSE 8888 8889 1080

# 创建启动脚本
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# 检查运行模式\n\
if [ "$RDPTOOL_MODE" = "server" ]; then\n\
    echo "Starting RDP Server..."\n\
    exec python main.py server --host 0.0.0.0 --port ${RDPTOOL_PORT:-8888} --config ${RDPTOOL_CONFIG:-/app/configs/server_config.json}\n\
elif [ "$RDPTOOL_MODE" = "client" ]; then\n\
    echo "Starting RDP Client..."\n\
    exec python main.py client --host ${RDPTOOL_SERVER_HOST:-localhost} --port ${RDPTOOL_SERVER_PORT:-8888} --config ${RDPTOOL_CONFIG:-/app/configs/client_config.json}\n\
elif [ "$RDPTOOL_MODE" = "proxy" ]; then\n\
    echo "Starting RDP Proxy..."\n\
    exec python main.py proxy --host 0.0.0.0 --port ${RDPTOOL_PROXY_PORT:-1080} --config ${RDPTOOL_CONFIG:-/app/configs/proxy_config.json}\n\
else\n\
    echo "Please set RDPTOOL_MODE environment variable to: server, client, or proxy"\n\
    exit 1\n\
fi' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# 设置入口点
ENTRYPOINT ["/app/entrypoint.sh"]