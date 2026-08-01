# MPV 播放器库

[English](README.md) | 中文

本目录存放 MPV 播放器库文件，用于视频播放。

## 快速下载

### 自动下载

运行以下任一脚本：

```bash
# Windows 批处理
download_mpv.bat

# Python（跨平台）
python download_mpv.py

# Linux/macOS
./download_mpv.sh
```

### 手动下载（Windows）

1. **打开下载页面：**
   
   https://github.com/shinchiro/mpv-winbuild-cmake/releases/

2. **下载 `mpv-dev-x86_64-v3-xxxxxxxx-git-xxxxxxx.7z` 文件：**
   
   找到以 `mpv-dev-x86_64` 开头、`.7z` 结尾的文件
   
   示例：`mpv-dev-x86_64-v3-20260610-git-304426c.7z`
   
   直接下载链接：
   https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z
   
   > ⚠️ 注意下载 `mpv-dev-x86_64-*.7z`，不是 `mpv-x86_64-*.7z`
   > 
   > `mpv-dev` 版本才包含所需的 `libmpv-2.dll` 文件

3. **解压 `libmpv-2.dll`：**
   
   使用 [7-Zip](https://www.7-zip.org/) 或其他工具解压 `.7z` 文件
   
   在压缩包中找到 `libmpv-2.dll`

4. **复制到本目录：**
   
   ```
   iptvgui/
   └── mpv/
       └── libmpv-2.dll   <-- 放到这里
   ```

### 手动安装（Linux）

通过包管理器安装：

```bash
# Ubuntu/Debian
sudo apt install libmpv-dev libmpv1

# Fedora
sudo dnf install mpv-libs-devel

# Arch Linux
sudo pacman -S mpv
```

### 手动安装（macOS）

```bash
brew install mpv
```

## 目录结构

安装完成后，本目录应包含：

```
iptvgui/mpv/
├── libmpv-2.dll      # ← Windows 必需（约 112 MB）
├── README.md         # 英文说明
├── README_ZH.md      # 中文说明（本文件）
├── download_mpv.bat  # Windows 下载脚本
├── download_mpv.py   # Python 下载脚本
└── download_mpv.sh   # Linux/macOS 下载脚本
```

## 验证安装

检查文件是否正确放置：

```bash
# Windows
dir mpv\libmpv-2.dll

# 应显示类似：
# 2026/06/10  12:00    117,532,160 libmpv-2.dll
```

文件大小应约为 **112-120 MB**。

## 常见问题

### 提示"未找到 MPV"

- 确认 `libmpv-2.dll` 在 `iptvgui/mpv/` 目录下
- 检查文件大小是否约 112 MB（不是 0 字节或很小的文件）
- 尝试重新下载

### 下载链接失效

Release 页面会不定期更新，请访问：
https://github.com/shinchiro/mpv-winbuild-cmake/releases/

下载最新的 `mpv-dev-x86_64-*.7z` 文件。

### 解压失败

- 安装 [7-Zip](https://www.7-zip.org/) 来解压 `.7z` 文件
- 或使用 Python：`pip install py7zr`

### 硬件解码不工作

1. 更新显卡驱动
2. 播放器会自动选择最佳可用的解码器

## 版本信息

- 推荐版本：[shinchiro/mpv-winbuild-cmake](https://github.com/shinchiro/mpv-winbuild-cmake) 最新 release
- 功能特性：GPU 加速、H.264/H.265/HEVC 硬件解码
