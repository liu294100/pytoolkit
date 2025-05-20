# 数学3D视频生成器 (Math3D Video Generator)

一个自动化工具，用于将数学题目转换为3D动画解题视频，包含AI解题、动画生成、配音和视频合成功能。

## 项目结构

```
math3d-video-generator/
├── main.py                   # 主控制脚本（自动化流程入口）
├── problems/                 # 数学题目目录
│   └── problem1.txt          # 示例数学题
├── scripts/                  # 功能模块脚本
│   ├── solve.py              # AI 解题 & 生成解说文案
│   ├── draw.py               # Manim 画图脚本生成器
│   ├── tts.py                # 文案转语音（edge-tts）
│   ├── compose.py            # 合成动画视频+语音
├── assets/                   # 资源文件
│   └── bgm.mp3               # 背景音乐（可选）
├── outputs/                  # 输出目录
│   ├── audio/                # 生成的音频文件
│   ├── video/                # 生成的视频文件
│   └── final/                # 最终合成视频
└── requirements.txt          # 所需依赖包
```

## 功能模块

1. **获取试题**：从本地文件读取数学题目
2. **解答步骤**：使用AI（GPT-4）或SymPy自动生成详细解题步骤
3. **解说文案生成**：将解题步骤转为通俗语言，适合短视频讲解
4. **图形+动画生成**：使用Manim生成数学动画
5. **视频合成**：合成视频、图形与解说音频
6. **配音 + bgm**：使用edge-tts自动配音，添加背景音乐

## 安装指南

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 安装Manim依赖

Manim需要一些额外的系统依赖，请参考[Manim安装文档](https://docs.manim.community/en/stable/installation.html)。

#### Windows

```bash
# 安装FFmpeg
choco install ffmpeg

# 安装LaTeX (可选，用于渲染数学公式)
choco install miktex
```

#### Linux

```bash
# 安装FFmpeg和其他依赖
sudo apt update
sudo apt install ffmpeg libcairo2-dev libpango1.0-dev ffmpeg2theora sox

# 安装LaTeX (可选)
sudo apt install texlive texlive-latex-extra texlive-fonts-extra texlive-latex-recommended texlive-science
```

## 使用方法

### 基本用法

```bash
# 处理默认problems目录中的所有题目
python main.py

# 处理单个题目文件
python main.py -p problems/problem1.txt

# 处理指定目录中的所有题目
python main.py -d path/to/problems/

# 使用自定义背景音乐
python main.py -b path/to/custom/bgm.mp3
```

### 配置OpenAI API

如果要使用GPT-4进行解题，需要设置OpenAI API密钥。创建一个`.env`文件：

```
OPENAI_API_KEY=your_api_key_here
```

如果未配置API密钥，系统将使用SymPy尝试解题，或提供模拟解答。

## 自定义和扩展

- **添加新题目**：将题目文本文件放入`problems`目录
- **自定义背景音乐**：替换`assets/bgm.mp3`文件
- **调整TTS语音**：修改`scripts/tts.py`中的语音设置
- **扩展解题能力**：在`scripts/solve.py`中添加更多类型的问题解法

## 示例输出

成功运行后，您可以在以下位置找到生成的文件：

- 解说音频：`outputs/audio/`
- 动画视频：`outputs/video/`
- 最终视频：`outputs/final/`

## 注意事项

- 首次运行Manim可能需要一些时间来编译和渲染
- 视频渲染过程较为耗时，请耐心等待
- 确保有足够的磁盘空间用于存储生成的视频文件

## 许可证

MIT