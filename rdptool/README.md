# 远程桌面工具 (Remote Desktop Tool)

一个基于Python和Web技术的跨平台远程桌面控制工具，支持多种客户端类型和实时屏幕共享。

## 功能特性

### 🖥️ 多端支持
- **Python GUI控制端**: 使用tkinter构建的桌面应用程序
- **Python GUI被控端**: 支持屏幕捕获和远程控制
- **Web控制端**: 基于浏览器的远程控制界面
- **Web服务端**: FastAPI + WebSocket实现的通信服务器

### 🚀 核心功能
- 实时屏幕共享和控制
- 鼠标和键盘事件传输
- 设备发现和连接管理
- 权限控制和密码保护
- 多设备同时在线
- 响应式Web界面

### 🔧 技术特性
- WebSocket实时通信
- 屏幕压缩和优化传输
- 跨平台兼容性
- 现代化UI设计
- 安全的连接机制

## 项目结构

```
rdptool/
├── server/
│   └── main.py              # FastAPI Web服务端
├── client/
│   ├── controlled_client.py # Python GUI被控端
│   └── controller_client.py # Python GUI控制端
├── templates/
│   └── index.html          # Web前端页面
├── static/
│   ├── css/
│   │   └── style.css       # 样式文件
│   └── js/
│       └── app.js          # JavaScript逻辑
├── requirements.txt        # Python依赖
└── README.md              # 项目说明
```

## 安装和配置

### 1. 环境要求
- Python 3.8+
- 现代浏览器 (Chrome, Firefox, Safari, Edge)
- Windows/macOS/Linux

### 2. 安装依赖

```bash
cd rdptool
pip install -r requirements.txt
```

### 3. 启动服务端

```bash
cd server
python main.py
```

服务端将在 `http://localhost:8000` 启动

### 4. 启动客户端

#### 被控端 (需要被远程控制的设备)
```bash
cd client
python controlled_client.py
```

#### 控制端 (用于控制其他设备)
```bash
cd client
python controller_client.py
```

#### Web控制端
打开浏览器访问: `http://localhost:8000`

## 使用说明

### 基本流程

1. **启动服务端**: 运行 `server/main.py`
2. **启动被控端**: 在需要被控制的设备上运行 `controlled_client.py`
3. **启动控制端**: 在控制设备上运行 `controller_client.py` 或打开Web界面
4. **建立连接**: 在控制端选择目标设备并发送控制请求
5. **开始控制**: 被控端接受请求后即可开始远程控制

### Web界面使用

1. **连接服务器**:
   - 输入服务器地址 (默认: localhost:8000)
   - 设置设备名称
   - 点击"连接"按钮

2. **选择设备**:
   - 在设备列表中选择要控制的设备
   - 输入控制密码 (如果需要)
   - 发送控制请求

3. **远程控制**:
   - 等待被控端接受请求
   - 使用鼠标和键盘控制远程设备
   - 使用快捷键面板发送特殊按键

### Python客户端使用

#### 被控端设置
- 启动后会显示设备信息和连接状态
- 可以设置控制密码
- 接收到控制请求时会弹出确认对话框

#### 控制端设置
- 连接服务器后会显示可用设备列表
- 双击设备名称发送控制请求
- 控制时可以使用所有鼠标和键盘功能

## 配置选项

### 服务端配置
- 端口: 默认8000，可在 `main.py` 中修改
- CORS: 支持跨域访问
- WebSocket: 自动处理连接管理

### 客户端配置
- 服务器地址: 可在客户端界面中设置
- 屏幕质量: 可调整压缩质量和分辨率
- 更新频率: 可设置屏幕刷新率

## 安全说明

- 所有通信基于WebSocket协议
- 支持密码保护的控制请求
- 被控端需要手动确认控制请求
- 可随时断开控制连接
- 建议在可信网络环境中使用

## 故障排除

### 常见问题

1. **连接失败**
   - 检查服务端是否正常运行
   - 确认网络连接和防火墙设置
   - 验证服务器地址和端口

2. **控制延迟**
   - 降低屏幕分辨率
   - 调整压缩质量
   - 检查网络带宽

3. **权限问题**
   - 确保客户端有屏幕捕获权限
   - 检查输入设备访问权限
   - 以管理员权限运行 (如需要)

### 日志调试
- 服务端日志会显示连接和消息信息
- 客户端控制台会输出详细的调试信息
- Web浏览器开发者工具可查看前端日志

## 开发说明

### 架构设计
- **服务端**: FastAPI + WebSocket处理客户端通信
- **客户端**: tkinter GUI + WebSocket客户端
- **Web端**: HTML5 + Bootstrap + WebSocket API

### 扩展开发
- 可添加文件传输功能
- 支持音频传输
- 实现录屏功能
- 添加聊天功能
- 支持多显示器

### 贡献指南
1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 发起Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 致谢

- 参考了 [billd-desk](https://github.com/galaxy-s10/billd-desk) 项目的设计思路
- 借鉴了向日葵、ToDesk等商业远程桌面工具的用户体验
- 使用了多个优秀的开源库和框架

## 联系方式

如有问题或建议，请通过以下方式联系:
- 提交Issue
- 发起Discussion
- 邮件联系

---

**注意**: 本工具仅供学习和合法用途使用，请遵守相关法律法规。