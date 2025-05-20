#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文案转语音模块 - 使用edge-tts将文本转换为语音
"""

import os
import asyncio
import logging
from pathlib import Path
import edge_tts

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义项目路径
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BASE_DIR / 'outputs'
AUDIO_DIR = OUTPUTS_DIR / 'audio'

# 确保输出目录存在
AUDIO_DIR.mkdir(exist_ok=True, parents=True)

# 默认TTS配置
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"  # 中文女声
DEFAULT_RATE = "+0%"  # 正常语速
DEFAULT_VOLUME = "+0%"  # 正常音量

async def text_to_speech(text, output_path, voice=DEFAULT_VOICE, rate=DEFAULT_RATE, volume=DEFAULT_VOLUME):
    """
    将文本转换为语音
    
    Args:
        text: 要转换的文本
        output_path: 输出音频文件路径
        voice: 语音角色
        rate: 语速
        volume: 音量
    """
    try:
        # 创建TTS通信对象
        tts = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
        
        # 生成语音
        await tts.save(output_path)
        
        logger.info(f"语音生成成功: {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"语音生成失败: {e}")
        return False

def generate_audio(problem_name, script):
    """
    生成解说音频
    
    Args:
        problem_name: 问题名称
        script: 解说文案
        
    Returns:
        audio_path: 生成的音频文件路径
    """
    logger.info(f"开始为问题 '{problem_name}' 生成解说音频")
    
    # 设置输出音频路径
    audio_path = AUDIO_DIR / f"{problem_name}.mp3"
    
    # 运行异步TTS函数
    success = asyncio.run(text_to_speech(script, str(audio_path)))
    
    if success:
        return str(audio_path)
    else:
        logger.error("语音生成失败")
        return None

# 获取可用的语音列表
def list_available_voices():
    """
    获取edge-tts可用的语音列表
    
    Returns:
        voices: 语音列表
    """
    try:
        voices = asyncio.run(edge_tts.list_voices())
        return voices
    except Exception as e:
        logger.error(f"获取语音列表失败: {e}")
        return []

# 测试代码
if __name__ == "__main__":
    test_problem_name = "triangle_problem"
    test_script = """大家好！今天我们来解决一道很多人容易做错的数学题。

题目是：某三角形两边长为5cm和7cm，夹角为60度，求第三边长度。

这道题乍一看很简单，但其中有一个关键点需要注意。

我们需要使用余弦定理来解决这个问题。余弦定理是什么呢？它告诉我们，在任意三角形中，一边的平方等于其他两边平方的和减去这两边与它们夹角余弦的积的两倍。

具体到这道题，我们已知两边长a=5cm，b=7cm，它们的夹角C=60°。

根据余弦定理，我们有：c² = a² + b² - 2ab·cos(C)

代入数值：c² = 5² + 7² - 2·5·7·cos(60°)

计算一下：c² = 25 + 49 - 2·5·7·0.5

c² = 74 - 35 = 39

所以c = √39 ≈ 6.24cm

因此，第三边的长度约为6.24厘米。

记住这个解题技巧，类似的题目就能轻松解决了！

如果觉得有帮助，请点赞关注，我们下期再见！"""
    
    audio_path = generate_audio(test_problem_name, test_script)
    print(f"生成的音频路径: {audio_path}")
    
    # 打印可用的语音列表
    voices = list_available_voices()
    print(f"可用的语音数量: {len(voices)}")
    for voice in voices[:5]:  # 只打印前5个
        print(f"- {voice['ShortName']}: {voice['LocalName']} ({voice['Locale']})")