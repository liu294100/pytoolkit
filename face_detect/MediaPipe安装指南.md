# MediaPipe 安装指南

## 问题说明

MediaPipe 是人脸检测功能的核心依赖，但目前**不支持 Python 3.13**。

### 当前状态
- ❌ Python 3.13 + MediaPipe：不兼容
- ✅ Python 3.8-3.12 + MediaPipe：完全支持
- ⚠️ 预发布版本：暂时不可用

## 解决方案

### 方案1：降级Python版本（推荐）

#### 步骤1：下载并安装Python 3.12
1. 访问 [Python官网](https://www.python.org/downloads/)
2. 下载 Python 3.12.x 最新版本
3. 安装时勾选 "Add Python to PATH"
4. 选择 "Install for all users"（可选）

#### 步骤2：验证安装
```bash
python --version
# 应该显示: Python 3.12.x
```

#### 步骤3：安装依赖
```bash
cd f:\Other\Code\dev\pytoolkit\face_detect
pip install -r requirements.txt
```

#### 步骤4：测试安装
```bash
python test_gui.py
```

### 方案2：使用Conda虚拟环境

#### 安装Anaconda/Miniconda
1. 下载 [Anaconda](https://www.anaconda.com/download) 或 [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
2. 安装完成后重启命令行

#### 创建虚拟环境
```bash
# 创建Python 3.12环境
conda create -n face_detect python=3.12

# 激活环境
conda activate face_detect

# 安装依赖
cd f:\Other\Code\dev\pytoolkit\face_detect
pip install -r requirements.txt

# 运行GUI
python face_detect_gui.py
```

#### 后续使用
```bash
# 每次使用前激活环境
conda activate face_detect
python face_detect_gui.py

# 使用完毕后退出环境
conda deactivate
```

### 方案3：使用pyenv（Linux/macOS）

```bash
# 安装pyenv
curl https://pyenv.run | bash

# 安装Python 3.12
pyenv install 3.12.0

# 在项目目录设置Python版本
cd f:/Other/Code/dev/pytoolkit/face_detect
pyenv local 3.12.0

# 安装依赖
pip install -r requirements.txt
```

### 方案4：使用venv虚拟环境

如果您已经安装了Python 3.12，可以使用venv：

```bash
# 创建虚拟环境
python3.12 -m venv face_detect_env

# 激活环境 (Windows)
face_detect_env\Scripts\activate

# 激活环境 (Linux/macOS)
source face_detect_env/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行GUI
python face_detect_gui.py
```

## 验证安装

### 快速测试
```bash
python -c "import mediapipe; print('MediaPipe版本:', mediapipe.__version__)"
```

### 完整测试
```bash
python test_gui.py
```

预期输出：
```
✅ OpenCV 可用
✅ MediaPipe 可用
✅ Pillow 可用
✅ Pydantic 可用
✅ NumPy 可用
✅ Tkinter 可用
✅ detect.py 模块导入成功
✅ resp_entity.py 模块导入成功
✅ ImageStatus 实例创建成功
✅ face_detect_gui.py 模块导入成功

测试结果: 4/4 通过 ✅
所有依赖都已正确安装！
```

## 常见问题

### Q1: 安装MediaPipe时出现编译错误
**A**: 确保使用支持的Python版本（3.8-3.12），并更新pip：
```bash
pip install --upgrade pip
pip install mediapipe
```

### Q2: 多个Python版本冲突
**A**: 使用虚拟环境隔离不同项目的依赖：
```bash
# 查看已安装的Python版本
py -0  # Windows
# 或
ls /usr/bin/python*  # Linux

# 使用特定版本创建虚拟环境
py -3.12 -m venv face_detect_env  # Windows
python3.12 -m venv face_detect_env  # Linux
```

### Q3: conda环境激活失败
**A**: 初始化conda：
```bash
conda init
# 重启命令行后再试
```

### Q4: 权限错误
**A**: 使用管理员权限或用户安装：
```bash
pip install --user -r requirements.txt
```

## 推荐配置

### 开发环境
- **Python版本**: 3.12.x（最新稳定版）
- **包管理**: conda（推荐）或 venv
- **IDE**: VS Code + Python扩展

### 生产环境
- **Python版本**: 3.11.x（长期支持）
- **容器化**: Docker（可选）
- **依赖锁定**: requirements.txt + pip-tools

## 自动化脚本

### Windows批处理脚本
创建 `setup_env.bat`：
```batch
@echo off
echo 正在设置人脸检测环境...

:: 检查conda是否可用
conda --version >nul 2>&1
if %errorlevel% == 0 (
    echo 使用conda创建环境...
    conda create -n face_detect python=3.12 -y
    conda activate face_detect
    pip install -r requirements.txt
    echo 环境设置完成！
    echo 使用方法: conda activate face_detect
) else (
    echo conda不可用，请手动安装Python 3.12
    pause
)
```

### Linux/macOS脚本
创建 `setup_env.sh`：
```bash
#!/bin/bash
echo "正在设置人脸检测环境..."

if command -v conda &> /dev/null; then
    echo "使用conda创建环境..."
    conda create -n face_detect python=3.12 -y
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate face_detect
    pip install -r requirements.txt
    echo "环境设置完成！"
    echo "使用方法: conda activate face_detect"
else
    echo "conda不可用，请手动安装Python 3.12"
fi
```

## 技术支持

如果遇到问题，请：
1. 检查Python版本：`python --version`
2. 运行测试脚本：`python test_gui.py`
3. 查看错误日志并搜索解决方案
4. 考虑使用虚拟环境隔离依赖

---

**注意**: MediaPipe团队正在努力支持Python 3.13，预计在未来版本中会提供支持。在此之前，建议使用Python 3.11或3.12以获得最佳兼容性。