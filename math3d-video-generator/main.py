#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数学3D视频生成器 - 主控制脚本
自动化流程：从数学题目到解题视频的生成
"""

import os
import sys
import argparse
from pathlib import Path
import logging
from tqdm import tqdm

# 导入项目模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scripts.solve import generate_solution
from scripts.draw import generate_manim_script
from scripts.tts import generate_audio
from scripts.compose import create_video

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义项目路径
BASE_DIR = Path(__file__).resolve().parent
PROBLEMS_DIR = BASE_DIR / 'problems'
OUTPUTS_DIR = BASE_DIR / 'outputs'
AUDIO_DIR = OUTPUTS_DIR / 'audio'
VIDEO_DIR = OUTPUTS_DIR / 'video'
FINAL_DIR = OUTPUTS_DIR / 'final'

# 确保输出目录存在
for dir_path in [AUDIO_DIR, VIDEO_DIR, FINAL_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

def process_problem(problem_file, bgm_file=None):
    """
    处理单个数学题目，生成完整的解题视频
    
    Args:
        problem_file: 数学题目文件路径
        bgm_file: 背景音乐文件路径（可选）
    
    Returns:
        final_video_path: 最终视频文件路径
    """
    problem_name = os.path.splitext(os.path.basename(problem_file))[0]
    logger.info(f"开始处理问题: {problem_name}")
    
    # 1. 读取题目
    with open(problem_file, 'r', encoding='utf-8') as f:
        problem_text = f.read().strip()
    logger.info(f"题目: {problem_text}")
    
    # 2. 生成解题步骤和解说文案
    solution, script = generate_solution(problem_text)
    logger.info("✓ 解题步骤和解说文案生成完成")
    
    # 3. 生成Manim动画脚本并渲染
    video_path = generate_manim_script(problem_name, problem_text, solution)
    logger.info(f"✓ 动画视频生成完成: {video_path}")
    
    # 4. 生成解说音频
    audio_path = generate_audio(problem_name, script)
    logger.info(f"✓ 解说音频生成完成: {audio_path}")
    
    # 5. 合成最终视频
    final_video_path = create_video(
        video_path=video_path,
        audio_path=audio_path,
        output_name=problem_name,
        bgm_path=bgm_file
    )
    logger.info(f"✓ 最终视频合成完成: {final_video_path}")
    
    return final_video_path

def main():
    parser = argparse.ArgumentParser(description='数学3D视频生成器')
    parser.add_argument('-p', '--problem', help='单个数学题目文件路径')
    parser.add_argument('-d', '--directory', help='包含多个数学题目的目录路径')
    parser.add_argument('-b', '--bgm', help='背景音乐文件路径')
    args = parser.parse_args()
    
    # 设置默认背景音乐
    bgm_file = args.bgm
    if not bgm_file and os.path.exists(BASE_DIR / 'assets' / 'bgm.mp3'):
        bgm_file = str(BASE_DIR / 'assets' / 'bgm.mp3')
    
    # 处理单个问题或目录中的所有问题
    if args.problem:
        process_problem(args.problem, bgm_file)
    elif args.directory:
        problem_dir = Path(args.directory)
        problem_files = list(problem_dir.glob('*.txt'))
        
        if not problem_files:
            logger.error(f"在目录 {args.directory} 中未找到任何题目文件")
            return
        
        logger.info(f"找到 {len(problem_files)} 个题目文件")
        for problem_file in tqdm(problem_files, desc="处理题目"):
            try:
                process_problem(str(problem_file), bgm_file)
            except Exception as e:
                logger.error(f"处理题目 {problem_file} 时出错: {e}")
    else:
        # 默认处理problems目录中的所有题目
        problem_files = list(PROBLEMS_DIR.glob('*.txt'))
        
        if not problem_files:
            logger.error(f"在默认目录 {PROBLEMS_DIR} 中未找到任何题目文件")
            return
        
        logger.info(f"找到 {len(problem_files)} 个题目文件")
        for problem_file in tqdm(problem_files, desc="处理题目"):
            try:
                process_problem(str(problem_file), bgm_file)
            except Exception as e:
                logger.error(f"处理题目 {problem_file} 时出错: {e}")

if __name__ == "__main__":
    main()