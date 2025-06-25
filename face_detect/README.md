# 人脸检测与活体检测系统

一个集成了人脸检测和活体检测功能的Python应用程序，支持多种GUI界面和多语言切换。

## 功能特性

- **人脸检测**: 基于MediaPipe的高精度人脸检测
- **活体检测**: 实时眨眼检测防止照片欺骗
- **多GUI版本**: 提供简单版、轻量版、活体检测版等多种界面
- **多语言支持**: 支持中英文界面切换
- **跨平台**: 支持Windows、Linux、macOS

## 项目结构

```
face_detect/
├── main.py                 # 主入口文件
├── requirements.txt        # 依赖配置
├── src/                    # 源代码目录
│   ├── core/              # 核心功能模块
│   │   ├── detect.py      # 人脸检测引擎
│   │   ├── liveness_detection.py  # 活体检测引擎
│   │   └── resp_entity.py # 响应实体类
│   ├── gui/               # GUI界面模块
│   │   ├── face_detect_gui.py                    # 简单GUI
│   │   ├── face_detect_gui_lite.py               # 轻量级GUI
│   │   ├── face_detect_with_liveness_gui.py      # 活体检测GUI(中文)
│   │   ├── face_detect_with_liveness_gui_en.py   # 活体检测GUI(英文)
│   │   └── face_detect_with_liveness_gui_multilang.py # 多语言GUI(推荐)
│   └── utils/             # 工具模块
├── tests/                 # 测试文件
├── scripts/               # 启动脚本
│   ├── windows/          # Windows批处理脚本
│   └── unix/             # Unix shell脚本
├── docs/                  # 文档目录
│   ├── zh/               # 中文文档
│   └── en/               # 英文文档
└── config/                # 配置文件目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行应用

#### 使用主入口文件（推荐）

```bash
# 启动多语言GUI（默认）
python main.py

# 启动简单GUI
python main.py --gui simple

# 启动轻量级GUI
python main.py --gui lite

# 启动活体检测GUI
python main.py --gui liveness

# 启动英文活体检测GUI
python main.py --gui liveness-en

# 启动英文界面
python main.py --lang en
```

#### 使用启动脚本

**Windows:**
```bash
scripts\windows\run_gui.bat
```

**Linux/macOS:**
```bash
scripts/unix/run_gui.sh
```

### 3. 使用说明

1. **静态图片检测**: 点击"选择图片"按钮，选择要检测的图片文件
2. **实时活体检测**: 点击"开始活体检测"按钮，对着摄像头进行眨眼动作
3. **语言切换**: 在多语言版本中可以切换中英文界面

## 系统要求

- Python 3.7+
- OpenCV 4.0+
- MediaPipe 0.8+
- Tkinter (通常随Python安装)
- 摄像头设备（用于活体检测）

## 依赖包

- `opencv-python`: 图像处理
- `mediapipe`: 人脸检测和关键点检测
- `Pillow`: 图像格式支持
- `numpy`: 数值计算
- `pydantic`: 数据验证
- `scipy`: 科学计算
- `scikit-learn`: 机器学习工具

## 开发指南

### 添加新的GUI版本

1. 在 `src/gui/` 目录下创建新的GUI文件
2. 在 `main.py` 中添加相应的启动选项
3. 更新 `src/gui/__init__.py` 文件

### 扩展检测功能

1. 在 `src/core/` 目录下添加新的检测模块
2. 更新 `src/core/__init__.py` 文件
3. 在GUI中集成新功能

## 故障排除

### 常见问题

1. **MediaPipe安装失败**
   - 参考 `docs/zh/MediaPipe安装指南.md`

2. **摄像头无法打开**
   - 检查摄像头是否被其他应用占用
   - 确认摄像头驱动正常

3. **导入模块失败**
   - 确保所有依赖已正确安装
   - 检查Python路径配置

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 更新日志

### v1.0.0 (2025-06-25)
- 重构项目结构
- 添加主入口文件
- 优化导入路径
- 完善文档结构
- 修复眨眼检测功能


## Next Steps Priority
1. High Priority : Add comprehensive logging and error handling
2. Medium Priority : Implement unit tests and configuration management
3. Low Priority : Add performance monitoring and async processing
## 💡 Additional Suggestions
- Code Quality Tools : Add black , flake8 , mypy , pre-commit
- Version Management : Implement semantic versioning
- User Feedback : Add telemetry for usage analytics
- Internationalization : Expand language support beyond zh/en
- Plugin Architecture : Allow custom detection algorithms
Your project has excellent structure! These enhancements will make it production-ready and highly maintainable