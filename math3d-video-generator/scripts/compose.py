#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
视频合成模块 - 将动画视频和解说音频合成为最终视频
"""

import os
import logging
from pathlib import Path
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips
from pydub import AudioSegment

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义项目路径
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BASE_DIR / 'outputs'
FINAL_DIR = OUTPUTS_DIR / 'final'

# 确保输出目录存在
FINAL_DIR.mkdir(exist_ok=True, parents=True)

def adjust_audio_length(audio_path, target_duration):
    """
    调整音频长度以匹配视频长度
    
    Args:
        audio_path: 音频文件路径
        target_duration: 目标时长（秒）
        
    Returns:
        temp_audio_path: 调整后的临时音频文件路径
    """
    try:
        # 加载音频
        audio = AudioSegment.from_file(audio_path)
        audio_duration = len(audio) / 1000  # 转换为秒
        
        if abs(audio_duration - target_duration) < 1.0:
            # 如果差异小于1秒，不做调整
            return audio_path
        
        # 创建临时文件路径
        temp_dir = Path(os.path.dirname(audio_path))
        temp_audio_path = temp_dir / f"temp_{os.path.basename(audio_path)}"
        
        if audio_duration > target_duration:
            # 如果音频时长大于视频时长，需要加速音频
            speed_factor = audio_duration / target_duration
            # 使用ffmpeg调整速度
            os.system(f'ffmpeg -i "{audio_path}" -filter:a "atempo={speed_factor}" -y "{temp_audio_path}"')
        else:
            # 如果音频时长小于视频时长，需要在末尾添加静音
            silence_duration = int((target_duration - audio_duration) * 1000)  # 毫秒
            silence = AudioSegment.silent(duration=silence_duration)
            extended_audio = audio + silence
            extended_audio.export(temp_audio_path, format="mp3")
        
        return str(temp_audio_path)
    
    except Exception as e:
        logger.error(f"调整音频长度失败: {e}")
        return audio_path

def create_video(video_path, audio_path, output_name, bgm_path=None, bgm_volume=0.1):
    """
    合成最终视频
    
    Args:
        video_path: 动画视频路径
        audio_path: 解说音频路径
        output_name: 输出文件名（不含扩展名）
        bgm_path: 背景音乐路径（可选）
        bgm_volume: 背景音乐音量（0.0-1.0）
        
    Returns:
        output_path: 最终视频路径
    """
    logger.info(f"开始合成视频: {output_name}")
    
    try:
        # 设置输出视频路径
        output_path = FINAL_DIR / f"{output_name}.mp4"
        
        # 加载视频
        video = VideoFileClip(video_path)
        video_duration = video.duration
        
        # 调整音频长度以匹配视频长度
        adjusted_audio_path = adjust_audio_length(audio_path, video_duration)
        
        # 加载解说音频
        narration = AudioFileClip(adjusted_audio_path)
        
        # 准备音频轨道
        audio_tracks = [narration]
        
        # 如果有背景音乐，添加到音频轨道
        if bgm_path and os.path.exists(bgm_path):
            try:
                # 加载背景音乐
                bgm = AudioFileClip(bgm_path)
                
                # 如果背景音乐时长小于视频时长，循环播放
                if bgm.duration < video_duration:
                    repeats = int(np.ceil(video_duration / bgm.duration))
                    bgm = concatenate_videoclips([bgm] * repeats).subclip(0, video_duration)
                else:
                    # 如果背景音乐时长大于视频时长，截取部分
                    bgm = bgm.subclip(0, video_duration)
                
                # 调整背景音乐音量
                bgm = bgm.volumex(bgm_volume)
                
                # 添加到音频轨道
                audio_tracks.append(bgm)
                
                logger.info(f"已添加背景音乐: {bgm_path}")
            
            except Exception as e:
                logger.error(f"添加背景音乐失败: {e}")
        
        # 合成音频
        final_audio = CompositeAudioClip(audio_tracks)
        
        # 设置视频音频
        final_video = video.set_audio(final_audio)
        
        # 导出最终视频
        final_video.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(OUTPUTS_DIR / "temp_audio.m4a"),
            remove_temp=True,
            threads=4,
            preset="medium"
        )
        
        # 清理临时文件
        if adjusted_audio_path != audio_path and os.path.exists(adjusted_audio_path):
            os.remove(adjusted_audio_path)
        
        logger.info(f"视频合成完成: {output_path}")
        return str(output_path)
    
    except Exception as e:
        logger.error(f"视频合成失败: {e}")
        return None

# 测试代码
if __name__ == "__main__":
    test_video_path = str(OUTPUTS_DIR / "video" / "triangle_problem.mp4")
    test_audio_path = str(OUTPUTS_DIR / "audio" / "triangle_problem.mp3")
    test_output_name = "triangle_problem_final"
    
    # 检查测试文件是否存在
    if not os.path.exists(test_video_path):
        print(f"测试视频文件不存在: {test_video_path}")
        test_video_path = input("请输入测试视频文件路径: ")
    
    if not os.path.exists(test_audio_path):
        print(f"测试音频文件不存在: {test_audio_path}")
        test_audio_path = input("请输入测试音频文件路径: ")
    
    # 测试背景音乐（可选）
    test_bgm_path = str(BASE_DIR / "assets" / "bgm.mp3")
    if not os.path.exists(test_bgm_path):
        print(f"背景音乐文件不存在: {test_bgm_path}")
        test_bgm_path = None
    
    # 合成测试视频
    output_path = create_video(
        video_path=test_video_path,
        audio_path=test_audio_path,
        output_name=test_output_name,
        bgm_path=test_bgm_path
    )
    
    print(f"生成的最终视频路径: {output_path}")