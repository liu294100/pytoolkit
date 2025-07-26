# Dict Learner

## 📖 项目简介

**Dict Learner** 是一个基于 [qwerty-learner](https://github.com/Realkai42/qwerty-learner) 项目的 Python 客户端实现，专为键盘工作者设计的单词记忆与英语肌肉记忆锻炼软件。

## ✨ 核心特性

### 🎯 设计理念
- **肌肉记忆训练**：通过打字练习巩固英语输入的肌肉记忆
- **单词记忆结合**：将英语单词记忆与键盘输入训练相结合
- **错误纠正**：输入错误时需要重新输入，避免形成错误的肌肉记忆
- **程序员友好**：内置程序员常用词库和API练习

### 🛠 功能列表

#### 📚 丰富词库
- **考试词库**：CET-4、CET-6、GMAT、GRE、IELTS、SAT、TOEFL
- **学术词库**：考研英语、专业四级、专业八级
- **程序员词库**：常用编程词汇、各语言API
- **自定义词库**：支持导入自定义单词列表

#### 🎵 音频功能
- **音标显示**：显示单词的国际音标
- **发音功能**：支持在线和离线发音
- **语音合成**：TTS文本转语音功能

#### 📝 学习模式
- **练习模式**：正常的单词输入练习
- **默写模式**：完成章节后的单词默写测试
- **复习模式**：针对错误单词的重点复习

#### 📊 数据统计
- **速度统计**：实时显示打字速度（WPM）
- **正确率统计**：统计输入正确率
- **进度跟踪**：记录学习进度和历史数据
- **数据导出**：支持学习数据导出功能

#### 🎨 界面特性
- **双语界面**：支持中文/英文界面切换
- **主题切换**：支持明暗主题
- **响应式设计**：适配不同屏幕尺寸
- **快捷键支持**：丰富的键盘快捷键

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Windows/macOS/Linux

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd dict-learner
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **运行程序**
```bash
# GUI模式（推荐）
python main.py

# 控制台模式
python main.py --mode console

# 指定词库启动
python main.py --dict cet4

# 英文界面
python main.py --lang en
```

## 📋 使用说明

### GUI模式
1. 启动程序后选择词库
2. 开始单词练习
3. 根据提示输入单词
4. 查看统计数据和进度
5. 使用默写模式巩固学习

### 控制台模式
1. 选择词库和章节
2. 按提示输入单词
3. 实时查看速度和正确率
4. 完成后查看详细统计

## 🎯 词库说明

### 内置词库
- **cet4**: 大学英语四级词汇
- **cet6**: 大学英语六级词汇
- **gre**: GRE考试词汇
- **toefl**: TOEFL考试词汇
- **ielts**: IELTS考试词汇
- **gmat**: GMAT考试词汇
- **sat**: SAT考试词汇
- **coder**: 程序员常用词汇

### 自定义词库
支持JSON格式的自定义词库：
```json
{
  "name": "自定义词库",
  "description": "词库描述",
  "words": [
    {
      "word": "example",
      "translation": "例子",
      "phonetic": "/ɪɡˈzæmpl/",
      "difficulty": 1
    }
  ]
}
```

## 🔧 配置说明

配置文件位于 `config/settings.json`：
```json
{
  "language": "zh",
  "theme": "light",
  "sound_enabled": true,
  "auto_pronunciation": true,
  "words_per_session": 20,
  "typing_speed_target": 40
}
```

## 📊 数据导出

学习数据自动保存在 `data/` 目录下：
- `progress.json`: 学习进度
- `statistics.json`: 统计数据
- `history/`: 历史记录

## 🤝 贡献指南

欢迎贡献代码和词库！

### 贡献词库
1. 在 `data/dictionaries/` 目录下添加JSON格式词库
2. 更新 `src/core/dictionary_manager.py` 中的词库列表
3. 提交Pull Request

### 贡献代码
1. Fork项目
2. 创建功能分支
3. 提交代码
4. 创建Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源。

## 🙏 致谢

- 感谢 [qwerty-learner](https://github.com/Realkai42/qwerty-learner) 项目提供的设计灵感
- 感谢所有贡献者的支持

## 📞 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。