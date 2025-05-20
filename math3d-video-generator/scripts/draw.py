#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Manim画图脚本生成器 - 生成数学动画
"""

import os
import sys
import tempfile
import subprocess
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义项目路径
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BASE_DIR / 'outputs'
VIDEO_DIR = OUTPUTS_DIR / 'video'

def generate_manim_code(problem_name, problem_text, solution):
    """
    根据问题和解题步骤生成Manim代码
    
    Args:
        problem_name: 问题名称
        problem_text: 问题文本
        solution: 解题步骤
        
    Returns:
        manim_code: 生成的Manim代码
    """
    # 解析解题步骤，确定问题类型
    is_triangle_problem = "三角形" in problem_text and "边长" in problem_text
    
    if is_triangle_problem:
        # 三角形问题的Manim代码
        manim_code = f"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from manim import *

class {problem_name.capitalize()}Solution(Scene):
    def construct(self):
        # 设置标题
        title = Text("三角形问题", font_size=40)
        title.to_edge(UP)
        self.play(Write(title))
        
        # 显示问题
        problem = Text("{problem_text}", font_size=24)
        problem.next_to(title, DOWN, buff=0.5)
        self.play(Write(problem))
        self.wait(1)
        
        # 创建三角形
        # 假设从问题中提取的数据：两边长为5cm和7cm，夹角为60度
        a, b = 5, 7
        angle = 60 * DEGREES
        
        # 计算第三边的长度（使用余弦定理）
        c = (a**2 + b**2 - 2*a*b*np.cos(angle))**0.5
        
        # 创建三角形顶点
        A = np.array([-2, -1, 0])
        B = np.array([2, -1, 0])
        C = np.array([A[0] + b * np.cos(angle), A[1] + b * np.sin(angle), 0])
        
        triangle = Polygon(A, B, C, color=BLUE)
        
        # 标记顶点
        dot_A = Dot(A, color=RED)
        dot_B = Dot(B, color=RED)
        dot_C = Dot(C, color=RED)
        
        label_A = Text("A", font_size=24).next_to(A, DOWN)
        label_B = Text("B", font_size=24).next_to(B, DOWN)
        label_C = Text("C", font_size=24).next_to(C, UP)
        
        # 标记边长
        label_a = Text(f"{a}cm", font_size=20)
        label_a.move_to((B + C) / 2 + 0.3 * normalize(np.cross(C - B, [0, 0, 1])))
        
        label_b = Text(f"{b}cm", font_size=20)
        label_b.move_to((A + C) / 2 + 0.3 * normalize(np.cross(C - A, [0, 0, 1])))
        
        label_c = Text(f"{c:.2f}cm", font_size=20)
        label_c.move_to((A + B) / 2 + 0.3 * normalize(np.cross(B - A, [0, 0, 1])))
        
        # 标记角度
        angle_arc = Arc(radius=0.5, angle=angle, start_angle=0, color=GREEN)
        angle_arc.shift(A)
        angle_label = Text("60°", font_size=20).move_to(A + 0.7 * np.array([np.cos(angle/2), np.sin(angle/2), 0]))
        
        # 动画展示三角形构建过程
        self.play(FadeOut(problem))
        self.play(Create(dot_A), Write(label_A))
        self.play(Create(dot_B), Write(label_B))
        self.play(Create(Line(A, B, color=BLUE)))
        self.play(Write(label_c))
        self.wait(0.5)
        
        self.play(Create(angle_arc), Write(angle_label))
        self.wait(0.5)
        
        self.play(Create(Line(A, C, color=BLUE)))
        self.play(Write(label_b))
        self.wait(0.5)
        
        self.play(Create(dot_C), Write(label_C))
        self.play(Create(Line(B, C, color=BLUE)))
        self.play(Write(label_a))
        self.wait(1)
        
        # 显示余弦定理公式
        formula = MathTex("c^2 = a^2 + b^2 - 2ab\\cos(C)")
        formula.next_to(triangle, DOWN, buff=1)
        self.play(Write(formula))
        self.wait(1)
        
        # 代入数值
        calculation1 = MathTex(f"c^2 = {a}^2 + {b}^2 - 2 \\cdot {a} \\cdot {b} \\cdot \\cos(60^\\circ)")
        calculation1.next_to(formula, DOWN)
        self.play(Write(calculation1))
        self.wait(1)
        
        calculation2 = MathTex(f"c^2 = {a**2} + {b**2} - 2 \\cdot {a} \\cdot {b} \\cdot 0.5")
        calculation2.next_to(calculation1, DOWN)
        self.play(Write(calculation2))
        self.wait(1)
        
        calculation3 = MathTex(f"c^2 = {a**2 + b**2} - {a * b}")
        calculation3.next_to(calculation2, DOWN)
        self.play(Write(calculation3))
        self.wait(1)
        
        calculation4 = MathTex(f"c^2 = {a**2 + b**2 - a*b}")
        calculation4.next_to(calculation3, DOWN)
        self.play(Write(calculation4))
        self.wait(1)
        
        calculation5 = MathTex(f"c = \\sqrt{{{a**2 + b**2 - a*b}}} \\approx {c:.2f}")
        calculation5.next_to(calculation4, DOWN)
        self.play(Write(calculation5))
        self.wait(1)
        
        # 最终答案
        answer = Text(f"第三边长度为 {c:.2f}cm", font_size=32, color=YELLOW)
        answer.to_edge(DOWN)
        self.play(Write(answer))
        self.wait(2)
        
        # 淡出所有元素
        self.play(*[FadeOut(obj) for obj in self.mobjects])
        self.wait(1)
"""
    else:
        # 默认的Manim代码模板
        manim_code = f"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from manim import *

class {problem_name.capitalize()}Solution(Scene):
    def construct(self):
        # 设置标题
        title = Text("数学问题", font_size=40)
        title.to_edge(UP)
        self.play(Write(title))
        
        # 显示问题
        problem = Text("{problem_text}", font_size=24)
        problem.next_to(title, DOWN, buff=0.5)
        self.play(Write(problem))
        self.wait(2)
        
        # 显示解题步骤
        steps = solution.split('\n')
        current_step = None
        
        for i, step in enumerate(steps):
            if not step.strip():
                continue
                
            new_step = Text(step, font_size=24)
            
            if current_step:
                new_step.next_to(current_step, DOWN, aligned_edge=LEFT)
                self.play(FadeOut(current_step), Write(new_step))
            else:
                new_step.next_to(problem, DOWN, buff=1)
                self.play(Write(new_step))
                
            current_step = new_step
            self.wait(1)
        
        # 最终答案（假设最后一步是答案）
        if steps and steps[-1].strip():
            answer = Text(steps[-1], font_size=32, color=YELLOW)
            answer.to_edge(DOWN)
            self.play(Write(answer))
            
        self.wait(2)
        
        # 淡出所有元素
        self.play(*[FadeOut(obj) for obj in self.mobjects])
        self.wait(1)
"""
    
    return manim_code

def generate_manim_script(problem_name, problem_text, solution):
    """
    生成Manim脚本并渲染视频
    
    Args:
        problem_name: 问题名称
        problem_text: 问题文本
        solution: 解题步骤
        
    Returns:
        video_path: 生成的视频路径
    """
    logger.info(f"开始为问题 '{problem_name}' 生成Manim脚本")
    
    # 确保输出目录存在
    VIDEO_DIR.mkdir(exist_ok=True, parents=True)
    
    # 生成Manim代码
    manim_code = generate_manim_code(problem_name, problem_text, solution)
    
    # 创建临时脚本文件
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w', encoding='utf-8') as f:
        f.write(manim_code)
        temp_script_path = f.name
    
    logger.info(f"Manim脚本已生成: {temp_script_path}")
    
    try:
        # 设置输出视频路径
        output_file = VIDEO_DIR / f"{problem_name}.mp4"
        
        # 构建Manim命令
        class_name = f"{problem_name.capitalize()}Solution"
        cmd = [
            sys.executable, "-m", "manim",
            temp_script_path, class_name,
            "-o", str(output_file.name),
            "--media_dir", str(VIDEO_DIR.parent),
            "-q", "h"  # 高质量渲染
        ]
        
        logger.info(f"执行Manim命令: {' '.join(cmd)}")
        
        # 执行Manim命令
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        logger.info("Manim渲染完成")
        logger.debug(process.stdout)
        
        # 检查输出文件是否存在
        expected_output = VIDEO_DIR / f"{class_name}.mp4"
        if expected_output.exists():
            # 如果文件名与预期不同，重命名
            if expected_output != output_file:
                expected_output.rename(output_file)
            return str(output_file)
        else:
            # 查找可能的输出文件
            possible_outputs = list(VIDEO_DIR.glob(f"*{class_name}*.mp4"))
            if possible_outputs:
                # 使用找到的第一个文件
                if possible_outputs[0] != output_file:
                    possible_outputs[0].rename(output_file)
                return str(output_file)
            else:
                logger.error(f"未找到Manim输出视频文件")
                return None
    
    except Exception as e:
        logger.error(f"Manim渲染失败: {e}")
        return None
    
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_script_path)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

# 测试代码
if __name__ == "__main__":
    test_problem_name = "triangle_problem"
    test_problem_text = "某三角形两边长为5cm和7cm，夹角为60度，求第三边长度。"
    test_solution = """使用余弦定理求解：
已知两边长 a = 5cm, b = 7cm, 夹角 C = 60°
根据余弦定理: c² = a² + b² - 2ab·cos(C)
c² = 5² + 7² - 2·5·7·cos(60°)
c² = 25 + 49 - 2·5·7·0.5
c² = 74 - 35
c² = 39
c = √39 ≈ 6.24cm
所以第三边长度为 6.24cm"""
    
    video_path = generate_manim_script(test_problem_name, test_problem_text, test_solution)
    print(f"生成的视频路径: {video_path}")