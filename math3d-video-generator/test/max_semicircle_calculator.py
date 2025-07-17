#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长方形中任意角度最大半圆计算器 - Python版本
基于HTML版本的算法实现

功能:
1. 计算长方形中能放置的最大半圆
2. 支持任意角度的半圆放置
3. 高精度优化算法
4. 可视化显示
5. 数据导出功能
"""

import math
import time
import json
import csv
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SemicircleResult:
    """半圆计算结果"""
    radius: float
    angle: float
    center_x: float
    center_y: float
    perimeter: float
    area: float


class MaxSemicircleCalculator:
    """最大半圆计算器"""
    
    def __init__(self, length: float = 8.0, width: float = 6.0):
        """
        初始化计算器
        
        Args:
            length: 长方形长度
            width: 长方形宽度
        """
        self.length = length
        self.width = width
        self.calculation_history: List[SemicircleResult] = []
        self.optimal_result: Optional[SemicircleResult] = None
        
    def check_semicircle_in_rectangle(self, center_x: float, center_y: float, 
                                     radius: float, angle: float) -> bool:
        """
        检查半圆是否完全在长方形内
        
        Args:
            center_x: 半圆中心X坐标
            center_y: 半圆中心Y坐标
            radius: 半圆半径
            angle: 半圆角度（度）
            
        Returns:
            bool: 是否在长方形内
        """
        angle_rad = math.radians(angle)
        num_points = 100  # 检查点数量
        
        # 检查半圆弧上的点
        for i in range(num_points + 1):
            t = i * math.pi / num_points
            
            # 半圆上的点（未旋转）
            x = radius * math.cos(t)
            y = radius * math.sin(t)
            
            # 应用旋转
            rotated_x = x * math.cos(angle_rad) - y * math.sin(angle_rad)
            rotated_y = x * math.sin(angle_rad) + y * math.cos(angle_rad)
            
            # 平移到中心位置
            final_x = center_x + rotated_x
            final_y = center_y + rotated_y
            
            # 检查是否在长方形内
            if final_x < 0 or final_x > self.length or final_y < 0 or final_y > self.width:
                return False
        
        # 检查直径端点
        diameter_end_x1 = center_x + radius * math.cos(angle_rad)
        diameter_end_y1 = center_y + radius * math.sin(angle_rad)
        diameter_end_x2 = center_x - radius * math.cos(angle_rad)
        diameter_end_y2 = center_y - radius * math.sin(angle_rad)
        
        return (0 <= diameter_end_x1 <= self.length and 
                0 <= diameter_end_y1 <= self.width and
                0 <= diameter_end_x2 <= self.length and 
                0 <= diameter_end_y2 <= self.width)
    
    def find_max_radius_for_angle(self, angle: float, center_step: float = 0.1, 
                                 radius_precision: float = 0.001) -> Dict:
        """
        为给定角度找到最大半径
        
        Args:
            angle: 半圆角度（度）
            center_step: 中心搜索步长
            radius_precision: 半径精度
            
        Returns:
            Dict: 包含最大半径和最佳中心位置的字典
        """
        max_radius = 0
        best_center = {'x': 0, 'y': 0}
        
        # 遍历可能的中心位置
        cx = 0
        while cx <= self.length:
            cy = 0
            while cy <= self.width:
                # 二分查找最大半径
                left = 0
                right = min(self.length, self.width)
                
                while right - left > radius_precision:
                    mid = (left + right) / 2
                    if self.check_semicircle_in_rectangle(cx, cy, mid, angle):
                        left = mid
                    else:
                        right = mid
                
                if left > max_radius:
                    max_radius = left
                    best_center = {'x': cx, 'y': cy}
                
                cy += center_step
            cx += center_step
        
        return {'radius': max_radius, 'center': best_center}
    
    def find_optimal_semicircle(self, precision: float = 1.0, 
                               center_step: float = 0.1,
                               radius_precision: float = 0.001,
                               progress_callback=None) -> SemicircleResult:
        """
        寻找最优半圆解
        
        Args:
            precision: 角度搜索精度（度）
            center_step: 中心搜索步长
            radius_precision: 半径精度
            progress_callback: 进度回调函数
            
        Returns:
            SemicircleResult: 最优解
        """
        start_time = time.time()
        
        best_radius = 0
        best_angle = 0
        best_center = {'x': 0, 'y': 0}
        
        total_angles = int(180 / precision) + 1
        tested_count = 0
        
        self.calculation_history.clear()
        
        angle = 0
        while angle <= 180:
            result = self.find_max_radius_for_angle(angle, center_step, radius_precision)
            
            # 计算周长和面积
            perimeter = result['radius'] * (math.pi + 2)
            area = result['radius'] ** 2 * math.pi / 2
            
            # 保存结果
            semicircle_result = SemicircleResult(
                radius=result['radius'],
                angle=angle,
                center_x=result['center']['x'],
                center_y=result['center']['y'],
                perimeter=perimeter,
                area=area
            )
            self.calculation_history.append(semicircle_result)
            
            if result['radius'] > best_radius:
                best_radius = result['radius']
                best_angle = angle
                best_center = result['center']
            
            tested_count += 1
            
            # 调用进度回调
            if progress_callback:
                progress = tested_count / total_angles * 100
                progress_callback(angle, result['radius'], progress, tested_count, total_angles)
            
            angle += precision
        
        compute_time = time.time() - start_time
        
        # 创建最优解
        optimal_perimeter = best_radius * (math.pi + 2)
        optimal_area = best_radius ** 2 * math.pi / 2
        
        self.optimal_result = SemicircleResult(
            radius=best_radius,
            angle=best_angle,
            center_x=best_center['x'],
            center_y=best_center['y'],
            perimeter=optimal_perimeter,
            area=optimal_area
        )
        
        print(f"\n优化完成！")
        print(f"计算时间: {compute_time:.3f}秒")
        print(f"测试角度数: {tested_count}")
        print(f"最优解: 半径={best_radius:.4f}, 角度={best_angle:.1f}°, 周长={optimal_perimeter:.4f}")
        
        return self.optimal_result
    
    def get_comparison_data(self) -> Dict:
        """
        获取方案对比数据
        
        Returns:
            Dict: 对比数据
        """
        # 水平放置 (0°)
        horizontal = self.find_max_radius_for_angle(0)
        horizontal_perimeter = horizontal['radius'] * (math.pi + 2)
        
        # 垂直放置 (90°)
        vertical = self.find_max_radius_for_angle(90)
        vertical_perimeter = vertical['radius'] * (math.pi + 2)
        
        # 最优解
        if self.optimal_result:
            optimal_perimeter = self.optimal_result.perimeter
            
            # 计算改进幅度
            best_standard = max(horizontal['radius'], vertical['radius'])
            best_standard_perimeter = max(horizontal_perimeter, vertical_perimeter)
            
            radius_improvement = max(0, (self.optimal_result.radius - best_standard) / best_standard * 100)
            perimeter_improvement = max(0, (optimal_perimeter - best_standard_perimeter) / best_standard_perimeter * 100)
        else:
            radius_improvement = 0
            perimeter_improvement = 0
        
        return {
            'horizontal': {
                'radius': horizontal['radius'],
                'perimeter': horizontal_perimeter,
                'center': horizontal['center']
            },
            'vertical': {
                'radius': vertical['radius'],
                'perimeter': vertical_perimeter,
                'center': vertical['center']
            },
            'optimal': {
                'radius': self.optimal_result.radius if self.optimal_result else 0,
                'perimeter': self.optimal_result.perimeter if self.optimal_result else 0,
                'angle': self.optimal_result.angle if self.optimal_result else 0
            },
            'improvement': {
                'radius': radius_improvement,
                'perimeter': perimeter_improvement
            }
        }
    
    def visualize(self, show_optimal: bool = True, show_manual: bool = False, 
                 manual_angle: float = 0, save_path: Optional[str] = None):
        """
        可视化显示
        
        Args:
            show_optimal: 是否显示最优解
            show_manual: 是否显示手动角度
            manual_angle: 手动角度
            save_path: 保存路径
        """
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        # 绘制长方形
        rect = patches.Rectangle((0, 0), self.length, self.width, 
                               linewidth=2, edgecolor='black', facecolor='none')
        ax.add_patch(rect)
        
        # 绘制坐标轴
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        ax.axvline(x=0, color='gray', linestyle='-', alpha=0.3)
        
        # 绘制网格
        ax.grid(True, alpha=0.3)
        
        # 绘制手动角度半圆
        if show_manual:
            manual_result = self.find_max_radius_for_angle(manual_angle)
            if manual_result['radius'] > 0:
                self._draw_semicircle(ax, manual_result['center']['x'], manual_result['center']['y'],
                                    manual_result['radius'], manual_angle, 'red', 
                                    f'手动调整 ({manual_angle}°)')
        
        # 绘制最优解半圆
        if show_optimal and self.optimal_result:
            self._draw_semicircle(ax, self.optimal_result.center_x, self.optimal_result.center_y,
                                self.optimal_result.radius, self.optimal_result.angle, 'green', 
                                f'最优解 ({self.optimal_result.angle}°)')
        
        # 设置图形属性
        ax.set_xlim(-1, self.length + 1)
        ax.set_ylim(-1, self.width + 1)
        ax.set_xlabel('X轴', fontsize=12)
        ax.set_ylabel('Y轴', fontsize=12)
        ax.set_title(f'长方形中最大半圆优化 (长={self.length}, 宽={self.width})', fontsize=14)
        ax.set_aspect('equal')
        ax.legend()
        
        # 添加尺寸标注
        ax.text(self.length/2, -0.5, f'长: {self.length}', ha='center', fontsize=10)
        ax.text(-0.5, self.width/2, f'宽: {self.width}', ha='center', rotation=90, fontsize=10)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图像已保存到: {save_path}")
        
        plt.show()
    
    def _draw_semicircle(self, ax, center_x: float, center_y: float, radius: float, 
                        angle: float, color: str, label: str):
        """
        绘制半圆
        
        Args:
            ax: matplotlib轴对象
            center_x: 中心X坐标
            center_y: 中心Y坐标
            radius: 半径
            angle: 角度（度）
            color: 颜色
            label: 标签
        """
        angle_rad = math.radians(angle)
        
        # 生成半圆弧上的点
        t = np.linspace(0, np.pi, 100)
        x = radius * np.cos(t)
        y = radius * np.sin(t)
        
        # 应用旋转
        rotated_x = x * math.cos(angle_rad) - y * math.sin(angle_rad)
        rotated_y = x * math.sin(angle_rad) + y * math.cos(angle_rad)
        
        # 平移到中心位置
        final_x = center_x + rotated_x
        final_y = center_y + rotated_y
        
        # 绘制半圆弧
        ax.plot(final_x, final_y, color=color, linewidth=2, label=label)
        
        # 绘制直径
        diameter_x = [center_x - radius * math.cos(angle_rad), 
                     center_x + radius * math.cos(angle_rad)]
        diameter_y = [center_y - radius * math.sin(angle_rad), 
                     center_y + radius * math.sin(angle_rad)]
        ax.plot(diameter_x, diameter_y, color=color, linewidth=2)
        
        # 绘制中心点
        ax.plot(center_x, center_y, 'o', color=color, markersize=5)
        
        # 填充半圆
        vertices = list(zip(final_x, final_y))
        vertices.append((center_x - radius * math.cos(angle_rad), 
                        center_y - radius * math.sin(angle_rad)))
        polygon = patches.Polygon(vertices, alpha=0.3, facecolor=color)
        ax.add_patch(polygon)
    
    def export_to_csv(self, filename: str = 'semicircle_results.csv'):
        """
        导出结果到CSV文件
        
        Args:
            filename: 文件名
        """
        if not self.calculation_history:
            print("没有计算历史数据可导出")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['angle', 'radius', 'perimeter', 'area', 'center_x', 'center_y']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.calculation_history:
                writer.writerow({
                    'angle': result.angle,
                    'radius': result.radius,
                    'perimeter': result.perimeter,
                    'area': result.area,
                    'center_x': result.center_x,
                    'center_y': result.center_y
                })
        
        print(f"结果已导出到: {filename}")
    
    def export_to_json(self, filename: str = 'semicircle_optimization_data.json'):
        """
        导出数据到JSON文件
        
        Args:
            filename: 文件名
        """
        data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'rectangle': {
                'length': self.length,
                'width': self.width
            },
            'optimal': {
                'radius': self.optimal_result.radius if self.optimal_result else 0,
                'angle': self.optimal_result.angle if self.optimal_result else 0,
                'center_x': self.optimal_result.center_x if self.optimal_result else 0,
                'center_y': self.optimal_result.center_y if self.optimal_result else 0,
                'perimeter': self.optimal_result.perimeter if self.optimal_result else 0,
                'area': self.optimal_result.area if self.optimal_result else 0
            },
            'results': [
                {
                    'angle': result.angle,
                    'radius': result.radius,
                    'perimeter': result.perimeter,
                    'area': result.area,
                    'center_x': result.center_x,
                    'center_y': result.center_y
                }
                for result in self.calculation_history
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"数据已导出到: {filename}")
    
    def print_detailed_report(self):
        """
        打印详细报告
        """
        if not self.optimal_result:
            print("请先运行优化计算")
            return
        
        print("\n" + "="*60)
        print("           长方形中最大半圆优化报告")
        print("="*60)
        
        print(f"\n📐 长方形尺寸:")
        print(f"   长度: {self.length}")
        print(f"   宽度: {self.width}")
        print(f"   面积: {self.length * self.width}")
        
        print(f"\n🎯 最优解:")
        print(f"   半径: {self.optimal_result.radius:.4f}")
        print(f"   角度: {self.optimal_result.angle:.1f}°")
        print(f"   中心: ({self.optimal_result.center_x:.2f}, {self.optimal_result.center_y:.2f})")
        print(f"   周长: {self.optimal_result.perimeter:.4f}")
        print(f"   面积: {self.optimal_result.area:.4f}")
        
        # 空间利用率
        rectangle_area = self.length * self.width
        efficiency = (self.optimal_result.area / rectangle_area) * 100
        print(f"   空间利用率: {efficiency:.1f}%")
        
        # 对比数据
        comparison = self.get_comparison_data()
        print(f"\n🔍 方案对比:")
        print(f"   水平放置 (0°): 半径={comparison['horizontal']['radius']:.4f}, 周长={comparison['horizontal']['perimeter']:.4f}")
        print(f"   垂直放置 (90°): 半径={comparison['vertical']['radius']:.4f}, 周长={comparison['vertical']['perimeter']:.4f}")
        print(f"   最优角度: 半径={comparison['optimal']['radius']:.4f}, 周长={comparison['optimal']['perimeter']:.4f}")
        print(f"   改进幅度: 半径+{comparison['improvement']['radius']:.2f}%, 周长+{comparison['improvement']['perimeter']:.2f}%")
        
        # 前5个最佳结果
        print(f"\n📊 前5个最佳结果:")
        sorted_results = sorted(self.calculation_history, key=lambda x: x.radius, reverse=True)[:5]
        for i, result in enumerate(sorted_results, 1):
            print(f"   {i}. 角度={result.angle:.1f}°, 半径={result.radius:.4f}, 周长={result.perimeter:.4f}")
        
        print("\n" + "="*60)


def progress_callback(angle: float, radius: float, progress: float, tested: int, total: int):
    """
    进度回调函数
    
    Args:
        angle: 当前角度
        radius: 当前半径
        progress: 进度百分比
        tested: 已测试数量
        total: 总数量
    """
    print(f"\r进度: {progress:.1f}% | 角度: {angle:.1f}° | 半径: {radius:.4f} | {tested}/{total}", end="")


def main():
    """
    主函数 - 演示程序使用
    """
    print("长方形中任意角度最大半圆计算器 - Python版本")
    print("基于HTML版本的算法实现\n")
    
    # 创建计算器实例（默认长方形：长8，宽6）
    calculator = MaxSemicircleCalculator(length=8.0, width=6.0)
    
    # 寻找最优解
    print("开始优化计算...")
    optimal = calculator.find_optimal_semicircle(
        precision=1.0,  # 角度精度
        center_step=0.1,  # 中心搜索步长
        radius_precision=0.001,  # 半径精度
        progress_callback=progress_callback
    )
    
    # 打印详细报告
    calculator.print_detailed_report()
    
    # 可视化显示
    print("\n生成可视化图像...")
    calculator.visualize(show_optimal=True, show_manual=True, manual_angle=0)
    
    # 导出数据
    print("\n导出数据...")
    calculator.export_to_csv()
    calculator.export_to_json()
    
    print("\n计算完成！")


if __name__ == "__main__":
    main()