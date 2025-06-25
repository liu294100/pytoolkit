# Python版本兼容性说明

## 当前问题

您正在使用 **Python 3.13**，但是 **MediaPipe** 目前还不支持 Python 3.13。这会导致人脸检测功能无法正常工作。

## 解决方案

### 方案1：降级Python版本（推荐）

建议使用以下Python版本之一：
- **Python 3.11** （推荐）
- **Python 3.12**
- Python 3.10
- Python 3.9

#### 安装步骤：
1. 下载并安装 Python 3.11 或 3.12
2. 使用新的Python版本安装依赖：
   ```bash
   # 假设新Python安装在 C:\Python311
   C:\Python311\python.exe -m pip install -r requirements.txt
   ```

### 方案2：使用虚拟环境

如果您需要保留Python 3.13用于其他项目，可以使用conda创建虚拟环境：

```bash
# 安装conda后执行
conda create -n face_detect python=3.11
conda activate face_detect
pip install -r requirements.txt
```

### 方案3：尝试预发布版本（不推荐）

可以尝试安装MediaPipe的预发布版本，但可能不稳定：

```bash
"E:\Program Files\Python\Python313\python.exe" -m pip install --pre mediapipe
```

## 当前已安装的包

✅ 以下包已成功安装在您的Python 3.13环境中：
- opencv-python (4.11.0.86)
- pydantic (2.x)
- Pillow (10.x)
- numpy (1.24+)

❌ 缺失的包：
- mediapipe（Python 3.13不兼容）

## 验证安装

安装完成后，可以运行测试脚本验证：

```bash
# 使用兼容的Python版本
python test_gui.py
```

## MediaPipe官方支持的Python版本

根据MediaPipe官方文档，目前支持的Python版本为：
- Python 3.8 - 3.12

## 更新日志

- 2025-01-02: 发现Python 3.13兼容性问题
- MediaPipe团队正在开发对Python 3.13的支持

## 联系支持

如果您在安装过程中遇到其他问题，请：
1. 检查Python版本：`python --version`
2. 检查pip版本：`pip --version`
3. 尝试清理pip缓存：`pip cache purge`