#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
解题模块 - 使用AI生成解题步骤和解说文案
"""

import os
import json
import logging
from pathlib import Path
import sympy as sp
import openai
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

def solve_with_sympy(problem_text):
    """
    使用SymPy尝试解决数学问题
    适用于方程、几何等可以用符号计算解决的问题
    
    Args:
        problem_text: 数学题目文本
        
    Returns:
        solution: 解题步骤（如果成功）
    """
    try:
        # 这里只是一个简单示例，实际应用中需要根据题目类型进行分类处理
        if "三角形" in problem_text and "边长" in problem_text:
            # 余弦定理解三角形问题
            # 示例：某三角形两边长为5cm和7cm，夹角为60度，求第三边长度
            import re
            import math
            
            # 提取数字
            numbers = re.findall(r'\d+', problem_text)
            if len(numbers) >= 3:
                a = float(numbers[0])
                b = float(numbers[1])
                angle_deg = float(numbers[2])
                angle_rad = math.radians(angle_deg)
                
                # 余弦定理: c^2 = a^2 + b^2 - 2ab*cos(C)
                c_squared = a**2 + b**2 - 2*a*b*math.cos(angle_rad)
                c = math.sqrt(c_squared)
                
                solution = [
                    "使用余弦定理求解：",
                    f"已知两边长 a = {a}cm, b = {b}cm, 夹角 C = {angle_deg}°",
                    "根据余弦定理: c² = a² + b² - 2ab·cos(C)",
                    f"c² = {a}² + {b}² - 2·{a}·{b}·cos({angle_deg}°)",
                    f"c² = {a**2} + {b**2} - 2·{a}·{b}·{math.cos(angle_rad):.4f}",
                    f"c² = {a**2 + b**2} - {2*a*b*math.cos(angle_rad):.4f}",
                    f"c² = {c_squared:.4f}",
                    f"c = √{c_squared:.4f} = {c:.4f}cm",
                    f"所以第三边长度为 {c:.2f}cm"
                ]
                return "\n".join(solution)
        
        # 可以添加更多类型的问题解法
        
        return None  # 无法用SymPy解决
    except Exception as e:
        logger.warning(f"SymPy解题失败: {e}")
        return None

def solve_with_ai(problem_text):
    """
    使用AI（如GPT-4）解决数学问题
    
    Args:
        problem_text: 数学题目文本
        
    Returns:
        solution: 解题步骤
    """
    try:
        prompt = f"""
请详细解答以下数学题，分步骤输出，并使用LaTeX格式表示数学公式：

题目：{problem_text}

请提供详细的解题步骤，包括使用的公式、计算过程和最终答案。
"""
        
        # 检查API密钥是否配置
        if not openai.api_key:
            logger.warning("未配置OpenAI API密钥，使用模拟解答")
            # 如果没有API密钥，返回一个模拟的解答
            if "三角形" in problem_text and "边长" in problem_text:
                return solve_with_sympy(problem_text) or "使用余弦定理可以解决这个问题..."
            return "这是一个模拟的AI解答，请配置OpenAI API密钥获取真实解答。"
        
        # 调用OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一位专业的数学老师，擅长解答数学题目并提供详细的解题步骤。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        solution = response.choices[0].message.content.strip()
        return solution
    
    except Exception as e:
        logger.error(f"AI解题失败: {e}")
        # 尝试使用SymPy作为备选
        sympy_solution = solve_with_sympy(problem_text)
        if sympy_solution:
            return sympy_solution
        return f"解题失败: {e}\n请检查API配置或网络连接。"

def generate_explanation_script(problem_text, solution):
    """
    生成解说文案
    
    Args:
        problem_text: 数学题目文本
        solution: 解题步骤
        
    Returns:
        script: 解说文案
    """
    try:
        prompt = f"""
请根据以下数学题目和解题步骤，生成一个生动有趣的解说文案，适合制作短视频讲解：

题目：{problem_text}

解题步骤：
{solution}

要求：
1. 使用通俗易懂的语言
2. 加入一些吸引人的表达，如"这道题很多人都会做错"
3. 分成清晰的段落，每段对应一个解题步骤
4. 总结时强调解题技巧和要点
5. 整体风格活泼但不失专业性
"""
        
        # 检查API密钥是否配置
        if not openai.api_key:
            logger.warning("未配置OpenAI API密钥，使用模板解说文案")
            # 如果没有API密钥，返回一个模板解说文案
            return f"""
大家好！今天我们来解决一道很多人容易做错的数学题。

题目是：{problem_text}

这道题乍一看很简单，但其中有一个关键点需要注意。

{solution.replace('\n', '\n\n')}

记住这个解题技巧，类似的题目就能轻松解决了！

如果觉得有帮助，请点赞关注，我们下期再见！
"""
        
        # 调用OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一位受欢迎的数学短视频创作者，擅长用生动有趣的方式讲解数学题目。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        script = response.choices[0].message.content.strip()
        return script
    
    except Exception as e:
        logger.error(f"生成解说文案失败: {e}")
        # 返回一个简单的备选文案
        return f"""
大家好！今天我们来解决这道数学题：{problem_text}

解题步骤如下：
{solution}

希望这个讲解对你有帮助！
"""

def generate_solution(problem_text):
    """
    生成解题步骤和解说文案
    
    Args:
        problem_text: 数学题目文本
        
    Returns:
        solution: 解题步骤
        script: 解说文案
    """
    logger.info(f"开始解题: {problem_text}")
    
    # 首先尝试使用SymPy解题
    solution = solve_with_sympy(problem_text)
    
    # 如果SymPy解题失败，使用AI解题
    if not solution:
        logger.info("SymPy解题失败，尝试使用AI解题")
        solution = solve_with_ai(problem_text)
    
    # 生成解说文案
    script = generate_explanation_script(problem_text, solution)
    
    return solution, script

# 测试代码
if __name__ == "__main__":
    test_problem = "某三角形两边长为5cm和7cm，夹角为60度，求第三边长度。"
    solution, script = generate_solution(test_problem)
    print("\n解题步骤:\n", solution)
    print("\n解说文案:\n", script)