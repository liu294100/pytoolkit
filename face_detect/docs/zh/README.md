# 人脸检测GUI工具

这是一个基于Python和tkinter的人脸检测GUI应用程序，可以检测图片中的人脸并进行多项质量评估。

## 功能特性

- **人脸检测**: 检测图片中是否存在人脸
- **多人脸检测**: 检测是否存在多张人脸
- **图片质量检测**: 
  - 亮度检测
  - 模糊度检测
  - 人脸完整度检测
- **面部特征检测**:
  - 墨镜检测
  - 闭眼检测
  - 口罩检测
  - 表情检测（闭嘴/微笑/大笑）
- **头部姿态检测**: 检测头部的俯仰、偏航、翻滚角度
- **遮挡检测**: 检测鼻子、嘴部、眼部、脸颊是否被遮挡

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 启动GUI应用

```bash
python face_detect_gui.py
```

### 使用命令行版本

```bash
python detect.py <图片路径>
```

## GUI界面说明

1. **选择图片**: 点击"选择图片"按钮选择要检测的图片文件
2. **开始检测**: 选择图片后，点击"开始检测"按钮进行人脸检测
3. **查看结果**: 检测结果会显示在左侧的结果面板中，包括：
   - 总体合规性结果
   - 各项检测的详细结果
   - 置信度信息
   - 遮挡检测结果

## 检测标准

### 图片要求
- 人脸检测置信度 ≥ 0.7
- 图片亮度 ≥ 130
- 图片清晰度 ≥ 100
- 人脸完整度 ≥ 0.9
- 头部姿态角度 ≤ 30°

### 面部要求
- 不能佩戴墨镜
- 不能闭眼
- 不能有明显遮挡
- 表情自然（不能大笑）

## 文件结构

```
face_detect/
├── detect.py              # 核心检测算法
├── resp_entity.py          # 响应实体类
├── face_detect_gui.py      # GUI应用程序
├── requirements.txt        # 依赖包列表
└── README.md              # 说明文档
```

## 技术栈

- **OpenCV**: 图像处理和计算机视觉
- **MediaPipe**: Google的机器学习框架，用于人脸检测和关键点检测
- **tkinter**: Python标准GUI库
- **PIL/Pillow**: 图像处理库
- **Pydantic**: 数据验证和设置管理
- **NumPy**: 数值计算库

## 注意事项

1. 支持的图片格式：JPG, JPEG, PNG, BMP, TIFF
2. 建议图片分辨率不要过大，以免影响检测速度
3. 检测算法对光照条件较为敏感，建议在良好光照条件下拍摄
4. 美颜或磨皮处理可能会影响模糊度检测结果

## 故障排除

如果遇到导入错误，请确保已安装所有依赖包：

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

如果在Windows系统上遇到OpenCV相关问题，可以尝试：

```bash
pip uninstall opencv-python
pip install opencv-python-headless
```