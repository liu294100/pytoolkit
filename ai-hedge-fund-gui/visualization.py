#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化模块，用于生成图表和报告
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from config import CHART_CONFIG


def generate_stock_chart(stock_data: pd.DataFrame, ticker: str) -> Figure:
    """
    生成股票价格走势图
    
    Args:
        stock_data: 包含股票历史数据的DataFrame
        ticker: 股票代码
        
    Returns:
        matplotlib Figure对象
    """
    # 设置图表样式
    sns.set_style("whitegrid")
    
    # 创建图表
    fig, ax = plt.subplots(figsize=CHART_CONFIG["figsize"], dpi=CHART_CONFIG["dpi"])
    
    # 绘制收盘价
    ax.plot(
        stock_data.index, 
        stock_data["Close"], 
        linewidth=CHART_CONFIG["line_width"],
        color=CHART_CONFIG["colors"][0],
        label=f"{ticker} 收盘价"
    )
    
    # 添加移动平均线
    if len(stock_data) >= 20:
        sma20 = stock_data["Close"].rolling(window=20).mean()
        ax.plot(
            stock_data.index,
            sma20,
            linewidth=CHART_CONFIG["line_width"] - 0.5,
            color=CHART_CONFIG["colors"][1],
            linestyle="--",
            label="20日均线"
        )
    
    if len(stock_data) >= 50:
        sma50 = stock_data["Close"].rolling(window=50).mean()
        ax.plot(
            stock_data.index,
            sma50,
            linewidth=CHART_CONFIG["line_width"] - 0.5,
            color=CHART_CONFIG["colors"][2],
            linestyle="-.",
            label="50日均线"
        )
    
    # 设置标题和标签
    ax.set_title(f"{ticker} 价格走势", fontsize=CHART_CONFIG["figsize"][0] * 1.5)
    ax.set_xlabel("日期")
    ax.set_ylabel("价格 ($)")
    
    # 格式化x轴日期
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=45)
    
    # 添加图例
    ax.legend(loc="best")
    
    # 添加网格线
    ax.grid(True, linestyle="--", alpha=0.7)
    
    # 自动调整布局
    fig.tight_layout()
    
    return fig


def create_volume_chart(stock_data: pd.DataFrame, ticker: str) -> Figure:
    """
    创建成交量图表
    
    Args:
        stock_data: 包含股票历史数据的DataFrame
        ticker: 股票代码
        
    Returns:
        matplotlib Figure对象
    """
    # 设置图表样式
    sns.set_style("whitegrid")
    
    # 创建图表
    fig, ax = plt.subplots(figsize=CHART_CONFIG["figsize"], dpi=CHART_CONFIG["dpi"])
    
    # 计算成交量变化颜色
    colors = [CHART_CONFIG["colors"][3] if stock_data["Close"].iloc[i] > stock_data["Close"].iloc[i-1] 
             else CHART_CONFIG["colors"][4] for i in range(1, len(stock_data))]
    colors.insert(0, CHART_CONFIG["colors"][3])  # 第一天默认为上涨颜色
    
    # 绘制成交量柱状图
    ax.bar(
        stock_data.index,
        stock_data["Volume"],
        color=colors,
        alpha=0.7,
        width=0.8
    )
    
    # 添加20日平均成交量
    if len(stock_data) >= 20:
        vol_sma20 = stock_data["Volume"].rolling(window=20).mean()
        ax.plot(
            stock_data.index,
            vol_sma20,
            linewidth=CHART_CONFIG["line_width"],
            color=CHART_CONFIG["colors"][0],
            linestyle="--",
            label="20日均量"
        )
    
    # 设置标题和标签
    ax.set_title(f"{ticker} 成交量", fontsize=CHART_CONFIG["figsize"][0] * 1.5)
    ax.set_xlabel("日期")
    ax.set_ylabel("成交量")
    
    # 格式化y轴为易读格式
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{int(x/1000000)}M" if x >= 1000000 else f"{int(x/1000)}K"))
    
    # 格式化x轴日期
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=45)
    
    # 添加图例
    if len(stock_data) >= 20:
        ax.legend(loc="best")
    
    # 添加网格线
    ax.grid(True, linestyle="--", alpha=0.7)
    
    # 自动调整布局
    fig.tight_layout()
    
    return fig


def generate_comparison_chart(data: Dict[str, pd.DataFrame]) -> Figure:
    """
    创建多只股票的比较图表
    
    Args:
        data: 字典，键为股票代码，值为包含价格数据的DataFrame
        
    Returns:
        matplotlib Figure对象
    """
    # 设置图表样式
    sns.set_style("whitegrid")
    
    # 创建图表
    fig, ax = plt.subplots(figsize=CHART_CONFIG["figsize"], dpi=CHART_CONFIG["dpi"])
    
    # 对每只股票进行归一化处理，使其起始价格为100
    for i, (ticker, df) in enumerate(data.items()):
        if not df.empty:
            # 确保数据有相同的起始日期
            normalized = df.copy()
            first_price = normalized["Close"].iloc[0]
            normalized["Close"] = normalized["Close"] / first_price * 100
            
            # 绘制归一化后的价格
            color_idx = i % len(CHART_CONFIG["colors"])
            ax.plot(
                normalized.index, 
                normalized["Close"], 
                linewidth=CHART_CONFIG["line_width"],
                color=CHART_CONFIG["colors"][color_idx],
                label=ticker
            )
    
    # 设置标题和标签
    ax.set_title("股票表现比较 (基准=100)", fontsize=CHART_CONFIG["figsize"][0] * 1.5)
    ax.set_xlabel("日期")
    ax.set_ylabel("归一化价格 (起始=100)")
    
    # 格式化x轴日期
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=45)
    
    # 添加图例
    ax.legend(loc="best")
    
    # 添加网格线
    ax.grid(True, linestyle="--", alpha=0.7)
    
    # 自动调整布局
    fig.tight_layout()
    
    return fig


def generate_agent_confidence_chart(decisions: List[Dict]) -> Figure:
    """
    创建智能体决策可视化图表
    
    Args:
        decisions: 包含智能体决策的列表
        
    Returns:
        matplotlib Figure对象
    """
    # 设置图表样式
    sns.set_style("whitegrid")
    
    # 提取数据
    agent_names = [d["agent_name"] for d in decisions]
    confidences = [d["confidence"] * 100 for d in decisions]
    decisions_type = [d["decision"] for d in decisions]
    
    # 设置决策颜色
    colors = ["#2ecc71" if d == "BUY" else "#e74c3c" if d == "SELL" else "#3498db" for d in decisions_type]
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(8, 5), dpi=CHART_CONFIG["dpi"])
    
    # 绘制水平条形图
    bars = ax.barh(agent_names, confidences, color=colors, alpha=0.7)
    
    # 在条形上添加决策标签
    for i, bar in enumerate(bars):
        ax.text(
            bar.get_width() + 1, 
            bar.get_y() + bar.get_height()/2, 
            decisions_type[i],
            va="center", 
            fontweight="bold",
            fontfamily="SimHei"  # 指定使用黑体字体
        )
    
    # 设置标题和标签
    ax.set_title("智能体决策信心度", fontsize=14, fontfamily="SimHei")
    ax.set_xlabel("信心度 (%)", fontfamily="SimHei")
    ax.set_xlim(0, 105)  # 留出空间显示决策标签
    
    # 设置Y轴标签字体
    for tick in ax.get_yticklabels():
        tick.set_fontfamily("SimHei")
    
    # 添加网格线
    ax.grid(True, linestyle="--", alpha=0.7, axis="x")
    
    # 自动调整布局
    fig.tight_layout()
    
    return fig


def embed_figure_in_tk(figure: Figure, container) -> FigureCanvasTkAgg:
    """
    将matplotlib图表嵌入到Tkinter容器中
    
    Args:
        figure: matplotlib Figure对象
        container: Tkinter容器
        
    Returns:
        FigureCanvasTkAgg对象
    """
    canvas = FigureCanvasTkAgg(figure, master=container)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
    return canvas


def generate_analysis_report(analysis_results: Dict) -> str:
    """
    生成分析报告
    
    Args:
        analysis_results: 分析结果字典
        
    Returns:
        格式化的报告文本
    """
    ticker = analysis_results["ticker"]
    market_data = analysis_results["market_data"]
    agent_decisions = analysis_results["agent_decisions"]
    final_decision = analysis_results["final_decision"]
    
    # 格式化市场数据
    market_info = f"### {ticker} 市场数据\n\n"
    market_info += f"- 当前价格: ${market_data.current_price:.2f}\n"
    market_info += f"- 价格变动: ${market_data.price_change:.2f} ({market_data.price_change_percent:.2f}%)\n"
    market_info += f"- 成交量: {market_data.volume:,}\n"
    
    if market_data.market_cap:
        market_info += f"- 市值: ${market_data.market_cap/1000000000:.2f}B\n"
    if market_data.pe_ratio:
        market_info += f"- PE比率: {market_data.pe_ratio:.2f}\n"
    if market_data.dividend_yield:
        market_info += f"- 股息收益率: {market_data.dividend_yield*100:.2f}%\n"
    
    # 格式化智能体决策
    decisions_info = f"\n### 智能体决策\n\n"
    for decision in agent_decisions:
        confidence_percent = decision.confidence * 100
        decisions_info += f"#### {decision.agent_name}\n"
        decisions_info += f"- 决策: **{decision.decision}**\n"
        decisions_info += f"- 信心度: {confidence_percent:.1f}%\n"
        decisions_info += f"- 风险级别: {decision.risk_level}\n"
        decisions_info += f"- 分析理由: {decision.reasoning}\n\n"
    
    # 格式化最终决策
    final_info = f"\n### 最终投资建议\n\n"
    final_info += f"- 决策: **{final_decision['decision']}**\n"
    final_info += f"- 信心度: {final_decision['confidence']*100:.1f}%\n"
    final_info += f"- 风险评估: {final_decision['risk_level']}\n\n"
    final_info += f"**分析摘要:**\n{final_decision['summary']}\n"
    
    # 组合完整报告
    report = f"# {ticker} 股票分析报告\n\n"
    report += f"*分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    report += market_info + decisions_info + final_info
    
    return report


def generate_portfolio_report(portfolio_results: Dict[str, Dict]) -> str:
    """
    生成投资组合报告
    
    Args:
        portfolio_results: 多只股票的分析结果字典
        
    Returns:
        格式化的报告文本
    """
    # 投资组合概览
    report = "# 投资组合分析报告\n\n"
    report += f"*分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    
    # 汇总表格
    report += "## 投资建议汇总\n\n"
    report += "| 股票代码 | 当前价格 | 建议 | 信心度 | 风险级别 |\n"
    report += "|---------|----------|------|--------|----------|\n"
    
    for ticker, result in portfolio_results.items():
        if "error" in result:
            report += f"| {ticker} | N/A | 分析失败 | N/A | N/A |\n"
            continue
            
        market_data = result["market_data"]
        final_decision = result["final_decision"]
        
        report += f"| {ticker} | ${market_data.current_price:.2f} | {final_decision['decision']} | "
        report += f"{final_decision['confidence']*100:.1f}% | {final_decision['risk_level']} |\n"
    
    # 投资组合建议
    report += "\n## 投资组合策略建议\n\n"
    
    # 计算买入、卖出、持有的股票数量
    buy_count = sum(1 for r in portfolio_results.values() if "final_decision" in r and r["final_decision"]["decision"] == "BUY")
    sell_count = sum(1 for r in portfolio_results.values() if "final_decision" in r and r["final_decision"]["decision"] == "SELL")
    hold_count = sum(1 for r in portfolio_results.values() if "final_decision" in r and r["final_decision"]["decision"] == "HOLD")
    
    total = buy_count + sell_count + hold_count
    if total > 0:
        buy_percent = buy_count / total * 100
        sell_percent = sell_count / total * 100
        hold_percent = hold_count / total * 100
        
        report += f"- 买入建议: {buy_count}只股票 ({buy_percent:.1f}%)\n"
        report += f"- 卖出建议: {sell_count}只股票 ({sell_percent:.1f}%)\n"
        report += f"- 持有建议: {hold_count}只股票 ({hold_percent:.1f}%)\n\n"
        
        # 市场情绪判断
        if buy_percent > 60:
            report += "**市场情绪:** 看涨 🚀 - 多数股票显示买入信号，市场整体看涨。\n\n"
        elif sell_percent > 60:
            report += "**市场情绪:** 看跌 📉 - 多数股票显示卖出信号，市场整体看跌。\n\n"
        else:
            report += "**市场情绪:** 中性 ⚖️ - 市场信号混合，建议谨慎操作。\n\n"
    
    # 添加免责声明
    report += "\n---\n\n"
    report += "*免责声明: 本报告仅供教育和研究目的，不构成投资建议。投资决策请咨询专业财务顾问。*\n"
    
    return report