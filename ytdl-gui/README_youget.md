# You-Get GUI 多站点视频下载器

基于 [you-get](https://github.com/soimort/you-get) 的图形界面视频下载工具，支持国内外主流视频网站的视频和音频下载。

## 功能特点

### 🎯 支持的网站
- **国外网站**: YouTube, Vimeo, Dailymotion, Facebook, Instagram, Twitter 等
- **国内网站**: 哔哩哔哩, 优酷, 爱奇艺, 腾讯视频, 芒果TV, 搜狐视频等
- **短视频平台**: 抖音, 快手, 微博视频等
- **音乐平台**: 网易云音乐, QQ音乐等
- **其他**: 更多网站请参考 [you-get 支持列表](https://github.com/soimort/you-get#supported-sites)

### 📥 下载功能
- **视频下载**: 支持多种清晰度选择（4K/1080p/720p/480p等）
- **音频提取**: 支持从视频中提取音频，多种格式（MP3/AAC/OGG/FLAC/WAV）
- **字幕下载**: 自动下载可用的字幕文件
- **播放列表**: 支持下载整个播放列表
- **格式选择**: 支持多种输出格式（MP4/FLV/WebM等）

### 🔧 高级功能
- **代理支持**: 支持HTTP和SOCKS5代理，内置常用代理配置
- **重试机制**: 网络不稳定时自动重试
- **进度显示**: 实时显示下载进度和状态
- **批量下载**: 支持播放列表批量下载
- **智能解析**: 自动识别视频网站和可用格式

## 安装说明

### 系统要求
- Windows 10/11
- Python 3.6 或更高版本
- 网络连接

### 快速安装

1. **下载项目文件**
   ```bash
   git clone <repository-url>
   cd ytdl-gui
   ```

2. **运行安装脚本**
   ```bash
   # Windows
   install_youget.bat
   ```

3. **启动应用**
   ```bash
   # Windows
   run_youget.bat
   
   # 或直接运行
   python yougetgui.py
   ```

### 手动安装

如果自动安装失败，可以手动安装依赖：

```bash
# 安装you-get
pip install you-get

# 安装其他依赖
pip install requests

# 可选：安装FFmpeg支持（用于音频转换）
pip install ffmpeg-python
```

## 使用指南

### 基本使用

1. **输入视频URL**
   - 在"视频URL"输入框中粘贴要下载的视频链接
   - 支持的网站包括YouTube、B站、优酷等主流平台

2. **获取视频信息**
   - 点击"获取信息"按钮
   - 程序会自动解析视频标题、网站、大小等信息
   - 并显示可用的下载格式

3. **选择下载选项**
   - **下载类型**: 选择"视频"或"仅音频"
   - **质量选择**: 根据需要选择清晰度或音质
   - **输出格式**: 选择音频格式（仅音频模式）

4. **设置保存位置**
   - 点击"浏览..."选择下载文件的保存目录
   - 默认保存到用户的Downloads文件夹

5. **开始下载**
   - 点击"开始下载"按钮
   - 观察进度条和状态信息

### 高级功能

#### 代理设置
如果需要使用代理访问某些网站：

1. 勾选"使用代理"
2. 选择代理类型（HTTP或SOCKS5）
3. 输入代理地址（格式：IP:端口）
4. 可选择常用配置或点击"测试连接"验证

#### 高级选项
- **下载字幕**: 勾选后会同时下载可用的字幕文件
- **下载播放列表**: 适用于播放列表URL，下载所有视频
- **输出格式**: 指定视频的输出格式

### 支持的URL示例

```
# YouTube
https://www.youtube.com/watch?v=VIDEO_ID

# 哔哩哔哩
https://www.bilibili.com/video/BV1234567890

# 优酷
https://v.youku.com/v_show/id_XMzg2NzY4NjI4MA==.html

# 抖音
https://www.douyin.com/video/1234567890123456789

# 网易云音乐
https://music.163.com/song?id=12345678
```

## 常见问题

### Q: 提示"未找到you-get命令"
A: 请确保已正确安装you-get：
```bash
pip install you-get
# 或
pip3 install you-get
```

### Q: 某些网站无法下载
A: 可能的原因和解决方案：
1. **网络问题**: 尝试使用代理
2. **网站更新**: 更新you-get到最新版本
3. **地区限制**: 使用相应地区的代理

### Q: 下载速度很慢
A: 建议：
1. 检查网络连接
2. 尝试使用代理
3. 选择较低的清晰度
4. 避免网络高峰期下载

### Q: 音频格式转换失败
A: 需要安装FFmpeg：
1. 下载FFmpeg: https://ffmpeg.org/download.html
2. 添加到系统PATH
3. 或安装ffmpeg-python: `pip install ffmpeg-python`

### Q: 代理设置不生效
A: 检查：
1. 代理服务是否正常运行
2. 代理地址格式是否正确（IP:端口）
3. 防火墙是否阻止连接
4. 尝试点击"测试连接"验证

## 技术说明

### 依赖库
- **you-get**: 核心下载引擎
- **tkinter**: GUI界面（Python内置）
- **requests**: 网络请求（用于代理测试）
- **subprocess**: 执行you-get命令
- **threading**: 多线程处理

### 文件结构
```
ytdl-gui/
├── yougetgui.py              # 主程序文件
├── requirements_youget.txt   # 依赖列表
├── install_youget.bat       # 安装脚本
├── run_youget.bat          # 运行脚本
└── README_youget.md        # 说明文档
```

## 更新日志

### v1.0.0
- 初始版本发布
- 支持主流视频网站下载
- 提供图形界面操作
- 支持代理设置
- 支持音频提取
- 支持字幕下载

## 许可证

本项目基于 MIT 许可证开源。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。
https://github.com/soimort/you-get

## 免责声明

本工具仅供学习和研究使用，请遵守相关网站的服务条款和版权法律法规。下载的内容请勿用于商业用途。