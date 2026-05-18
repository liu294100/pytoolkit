# 🔄 UWP 网络回环管理器

一个现代化的 Windows UWP 应用网络回环管理工具，让 UWP 应用能够访问本地代理（如 Clash、Fiddler、Charles 等）。

## 📖 功能特性

- ✅ **一键扫描** - 自动检测系统中所有 UWP 应用
- ✅ **批量管理** - 勾选应用，一键启用/禁用回环访问
- ✅ **友好名称** - 显示应用的中文名称，小白也能看懂
- ✅ **实时搜索** - 快速搜索应用，支持模糊匹配
- ✅ **状态同步** - 实时显示当前启用状态
- ✅ **现代化界面** - 深色主题，简洁美观

## 🎯 使用场景

当你使用本地代理（如 Clash、Fiddler、Charles 等）时，UWP 应用默认无法访问 `127.0.0.1`，导致无法正常联网。

**本工具的作用：** 解除 UWP 应用的网络回环限制，让它们能够使用本地代理。

## 📸 截图

```
┌──────────────────────────────────────────────────────────────────┐
│  🔄 网络回环管理器                                                │
│  勾选需要启用本地网络回环的应用，然后点击保存                       │
├──────────────────────────────────────────────────────────────────┤
│  启用 │ 应用名称        │ 友好名称    │ 包名称           │ 状态   │
│  ────────────────────────────────────────────────────────────── │
│   ☑  │ Microsoft Edge  │ Edge 浏览器 │ Microsoft.Edge.. │ ✅启用 │
│   ☐  │ QQ              │ QQ          │ Tencent.QQ...    │ ⚪未启用│
│   ☐  │ WeChat          │ 微信        │ Tencent.WeChat.. │ ⚪未启用│
├──────────────────────────────────────────────────────────────────┤
│  [🔄刷新] [全选] [取消全选] [💾 保存更改]                         │
└──────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 运行要求

- Windows 10/11
- Python 3.7+（可选，如果直接运行 `.py` 文件）
- **管理员权限**（必须）

### 方法一：直接运行 Python 脚本

```bash
# 克隆或下载项目
git clone https://github.com/your-repo/uwp-loopback-manager.git
cd uwp-loopback-manager

# 以管理员身份运行
python uwp_loopback_manager.py
```

### 方法二：打包为 EXE（可选）

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包
pyinstaller --onefile --windowed --uac-admin uwp_loopback_manager.py

# 生成的 EXE 在 dist 目录下
```

## 📝 使用说明

1. **以管理员身份运行** 程序
2. 点击 **「刷新列表」** 扫描系统中的 UWP 应用
3. **勾选** 需要启用回环的应用
4. 点击 **「保存更改」** 应用设置
5. 重启对应的 UWP 应用，即可使用本地代理

## 🔧 技术实现

### 核心技术

- **NetworkIsolationEnumAppContainers API** - 通过 Windows FirewallAPI.dll 枚举所有 UWP 应用容器
- **CheckNetIsolation 命令** - 启用/禁用应用的回环访问权限
- **SID 标识** - 使用 AppContainer SID 精确标识应用

### 关键代码

```python
# 调用 Windows API 获取 UWP 应用列表
NetworkIsolationEnumAppContainers(NETISO_FLAG_MAX, &count, &ptr_array)

# 启用回环访问
CheckNetIsolation LoopbackExempt -a -p={SID}

# 禁用回环访问
CheckNetIsolation LoopbackExempt -d -p={SID}
```

## 📋 支持的应用（部分）

| 应用名称 | 友好名称 |
|---------|---------|
| Microsoft Edge | Edge 浏览器 |
| Microsoft Store | 应用商店 |
| QQ | QQ |
| WeChat | 微信 |
| 网易云音乐 | 网易云音乐 |
| 哔哩哔哩 | 哔哩哔哩 |
| ChatGPT | ChatGPT |
| Teams | Microsoft Teams |
| ... | 更多应用 |

## ❓ 常见问题

### Q: 为什么需要管理员权限？

A: 修改网络回环设置需要系统管理员权限，请右键以管理员身份运行。

### Q: 启用后还是无法访问代理？

A: 请确保：
1. 已点击「保存更改」
2. 重启了对应的 UWP 应用
3. 代理软件正在运行且监听 `127.0.0.1`

### Q: 应用列表为空？

A: 可能的原因：
1. 系统中没有 UWP 应用
2. 防火墙服务未启动
3. 权限不足

### Q: 搜索不到某个应用？

A: 
1. 确保已点击「刷新列表」
2. 尝试搜索包名或友好名称
3. 搜索不区分大小写

## 🔗 参考资料

- [Richasy/LoopbackManager.Desktop](https://github.com/Richasy/LoopbackManager.Desktop)
- [Lumysia/UWP-LoopBack-Tool](https://github.com/Lumysia/UWP-LoopBack-Tool)
- [NetworkIsolationEnumAppContainers API](https://docs.microsoft.com/en-us/windows/win32/api/netioapi/nf-netioapi-networkisolationenumappcontainers)

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**💡 提示：** 如果觉得有用，请给个 ⭐ Star 支持一下！
