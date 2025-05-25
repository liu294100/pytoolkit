#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Hedge Fund GUI

图形用户界面，用于AI对冲基金分析工具
"""

import os
import sys
import time
import threading
import logging
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 导入项目模块
from hedge_fund_core import AIHedgeFund
from utils import format_currency, format_percentage, parse_tickers
from config import DEFAULT_STOCKS, DEFAULT_START_DAYS, DEFAULT_END_DAYS, AGENTS, API_CONFIG
from visualization import generate_stock_chart, generate_comparison_chart, generate_agent_confidence_chart

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

class AIHedgeFundGUI:
    """AI对冲基金GUI类"""
    
    def __init__(self, root):
        
        self.root = root
        self.root.title("AI Hedge Fund GUI")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # 设置图标
        try:
            # 尝试加载PNG图标
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
            if os.path.exists(icon_path):
                try:
                    # 使用PIL打开图像以验证其有效性
                    test_img = Image.open(icon_path)
                    test_img.verify()  # 验证图像
                    # 重新打开图像（因为verify会消耗文件指针）
                    icon = ImageTk.PhotoImage(Image.open(icon_path))
                    self.root.iconphoto(True, icon)
                except Exception as e:
                    # 如果PNG无效，尝试使用SVG图标
                    logger.warning(f"PNG图标无效，尝试使用默认图标: {e}")
                    self.root.title("AI Hedge Fund GUI 📈")
            else:
                # 如果图标文件不存在，使用文本图标
                self.root.title("AI Hedge Fund GUI 📈")
        except Exception as e:
            logger.error(f"加载图标时出错: {e}")
            self.root.title("AI Hedge Fund GUI 📈")
            
        # 设置matplotlib中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'NSimSun', 'FangSong', 'Arial Unicode MS']  # 用来正常显示中文标签
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧控制面板
        self.control_frame = ttk.LabelFrame(self.main_frame, text="配置", padding="10")
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 创建右侧结果面板
        self.result_frame = ttk.LabelFrame(self.main_frame, text="结果", padding="10")
        self.result_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 初始化控制面板
        self._init_control_panel()
        
        # 初始化结果面板
        self._init_result_panel()
        
        # 分析进程
        self.analysis_process = None
        self.analysis_thread = None
        self.stop_event = threading.Event()
        
    def _init_control_panel(self):
        
        # 股票输入
        ttk.Label(self.control_frame, text="股票代码 (逗号分隔):").grid(column=0, row=0, sticky=tk.W, pady=5)
        self.stocks_var = tk.StringVar(value=",".join(DEFAULT_STOCKS))
        self.stocks_entry = ttk.Entry(self.control_frame, textvariable=self.stocks_var, width=30)
        self.stocks_entry.grid(column=0, row=1, sticky=(tk.W, tk.E), pady=2)
        
        # 日期范围
        ttk.Label(self.control_frame, text="开始日期 (天数):").grid(column=0, row=2, sticky=tk.W, pady=5)
        self.start_days_var = tk.StringVar(value=str(DEFAULT_START_DAYS))
        self.start_days_entry = ttk.Entry(self.control_frame, textvariable=self.start_days_var, width=10)
        self.start_days_entry.grid(column=0, row=3, sticky=tk.W, pady=2)
        
        ttk.Label(self.control_frame, text="结束日期 (天数):").grid(column=0, row=4, sticky=tk.W, pady=5)
        self.end_days_var = tk.StringVar(value=str(DEFAULT_END_DAYS))
        self.end_days_entry = ttk.Entry(self.control_frame, textvariable=self.end_days_var, width=10)
        self.end_days_entry.grid(column=0, row=5, sticky=tk.W, pady=2)
        
        # 智能体选择
        ttk.Label(self.control_frame, text="选择智能体:").grid(column=0, row=6, sticky=tk.W, pady=5)
        
        self.agent_vars = {}
        row = 7
        for agent_key, agent_info in AGENTS.items():
            var = tk.BooleanVar(value=agent_info["enabled"])
            self.agent_vars[agent_key] = var
            cb = ttk.Checkbutton(
                self.control_frame, 
                text=f"{agent_info['icon']} {agent_info['name']}", 
                variable=var
            )
            cb.grid(column=0, row=row, sticky=tk.W, pady=2)
            row += 1
            
        # API密钥输入
        ttk.Label(self.control_frame, text="OpenAI API密钥 (可选):").grid(column=0, row=row, sticky=tk.W, pady=5)
        row += 1
        self.api_key_var = tk.StringVar(value=os.environ.get("OPENAI_API_KEY", ""))
        self.api_key_entry = ttk.Entry(self.control_frame, textvariable=self.api_key_var, width=30, show="*")
        self.api_key_entry.grid(column=0, row=row, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # 模型选择
        ttk.Label(self.control_frame, text="选择LLM模型:").grid(column=0, row=row, sticky=tk.W, pady=5)
        row += 1
        
        self.model_var = tk.StringVar(value="openai")
        models = [("OpenAI", "openai"), 
                 ("DeepSeek", "deepseek"), 
                 ("Claude", "claude"), 
                 ("Gemini", "gemini"),
                 ("Ollama (本地)", "ollama")]
        
        for i, (model_name, model_value) in enumerate(models):
            rb = ttk.Radiobutton(
                self.control_frame,
                text=model_name,
                variable=self.model_var,
                value=model_value
            )
            rb.grid(column=0, row=row+i, sticky=tk.W, pady=2)
        
        row += len(models)
        
        # 显示推理过程选项
        self.show_reasoning_var = tk.BooleanVar(value=True)
        reasoning_cb = ttk.Checkbutton(
            self.control_frame, 
            text="显示推理过程", 
            variable=self.show_reasoning_var
        )
        reasoning_cb.grid(column=0, row=row, sticky=tk.W, pady=5)
        row += 1
        
        # 使用LLM选项
        self.use_llm_var = tk.BooleanVar(value=False)
        llm_cb = ttk.Checkbutton(
            self.control_frame, 
            text="使用LLM进行分析", 
            variable=self.use_llm_var
        )
        llm_cb.grid(column=0, row=row, sticky=tk.W, pady=5)
        row += 1
        
        # 运行按钮
        self.run_button = ttk.Button(self.control_frame, text="运行分析", command=self._run_analysis)
        self.run_button.grid(column=0, row=row, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # 停止按钮
        self.stop_button = ttk.Button(self.control_frame, text="停止分析", command=self._stop_analysis, state=tk.DISABLED)
        self.stop_button.grid(column=0, row=row, sticky=(tk.W, tk.E), pady=5)
        
    def _init_result_panel(self):
        
        # 创建选项卡
        self.notebook = ttk.Notebook(self.result_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 摘要选项卡
        self.summary_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.summary_frame, text="摘要")
        
        # 详细信息选项卡
        self.details_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.details_frame, text="详细信息")
        
        # 图表选项卡
        self.chart_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.chart_frame, text="图表")
        
        # 摘要选项卡内容
        self.summary_text = scrolledtext.ScrolledText(self.summary_frame, wrap=tk.WORD, height=20)
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        self.summary_text.insert(tk.END, "运行分析以查看结果摘要...")
        self.summary_text.config(state=tk.DISABLED)
        
        # 详细信息选项卡内容
        self.details_text = scrolledtext.ScrolledText(self.details_frame, wrap=tk.WORD, height=20)
        self.details_text.pack(fill=tk.BOTH, expand=True)
        self.details_text.insert(tk.END, "运行分析以查看详细结果...")
        self.details_text.config(state=tk.DISABLED)
        
        # 图表选项卡内容
        self.chart_container = ttk.Frame(self.chart_frame)
        self.chart_container.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(self.result_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def _validate_inputs(self):
        
        # 验证股票代码
        stocks = self.stocks_var.get().strip()
        if not stocks:
            messagebox.showerror("输入错误", "请输入至少一个股票代码")
            return False
            
        # 验证日期范围
        try:
            start_days = int(self.start_days_var.get())
            end_days = int(self.end_days_var.get())
            
            if start_days < 0 or end_days < 0:
                messagebox.showerror("输入错误", "日期范围必须为非负整数")
                return False
                
            if start_days < end_days:
                messagebox.showerror("输入错误", "开始日期必须大于或等于结束日期")
                return False
                
        except ValueError:
            messagebox.showerror("输入错误", "日期范围必须为整数")
            return False
            
        # 验证智能体选择
        selected_agents = [agent for agent, var in self.agent_vars.items() if var.get()]
        if not selected_agents:
            messagebox.showerror("输入错误", "请选择至少一个智能体")
            return False
            
        return True
        
    def _run_analysis(self):
        
        # 验证输入
        if not self._validate_inputs():
            return
            
        # 禁用运行按钮，启用停止按钮
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 重置停止事件
        self.stop_event.clear()
        
        # 清空结果
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, "分析中...")
        self.summary_text.config(state=tk.DISABLED)
        
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, "分析中...")
        self.details_text.config(state=tk.DISABLED)
        
        # 清空图表
        for widget in self.chart_container.winfo_children():
            widget.destroy()
            
        # 更新状态
        self.status_var.set("分析中...")
        
        # 在新线程中运行分析
        self.analysis_thread = threading.Thread(target=self._run_analysis_thread)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        
    def _run_analysis_thread(self):
        
        try:
            # 获取输入参数
            stocks = parse_tickers(self.stocks_var.get())
            start_days = int(self.start_days_var.get())
            end_days = int(self.end_days_var.get())
            
            # 获取选定的智能体
            selected_agents = [agent_key for agent_key, var in self.agent_vars.items() if var.get()]
            
            # 获取API密钥
            api_key = self.api_key_var.get().strip()
            if api_key:
                # 设置环境变量
                model_type = self.model_var.get()
                if model_type == "openai":
                    os.environ["OPENAI_API_KEY"] = api_key
                elif model_type == "deepseek":
                    os.environ["DEEPSEEK_API_KEY"] = api_key
                elif model_type == "claude":
                    os.environ["CLAUDE_API_KEY"] = api_key
                elif model_type == "gemini":
                    os.environ["GOOGLE_API_KEY"] = api_key
            
            # 获取LLM选项
            use_llm = self.use_llm_var.get()
            show_reasoning = self.show_reasoning_var.get()
            
            # 获取选择的模型
            model_type = self.model_var.get()
            model_config = API_CONFIG.get(model_type, {})
            
            # 创建AIHedgeFund实例
            fund = AIHedgeFund(llm_provider=model_type, llm_config=model_config)
            
            # 更新状态
            self.root.after(0, lambda: self.status_var.set(f"正在分析 {len(stocks)} 只股票..."))
            
            # 分析投资组合
            results = fund.analyze_portfolio(stocks, selected_agents, use_llm)
            
            # 检查是否被停止
            if self.stop_event.is_set():
                self.root.after(0, lambda: self.status_var.set("分析已停止"))
                self.root.after(0, self._reset_buttons)
                return
                
            # 生成摘要
            summary = self._generate_summary(results)
            
            # 生成详细信息
            details = self._generate_details(results, show_reasoning)
            
            # 生成图表
            self.root.after(0, lambda: self._generate_charts(results))
            
            # 更新UI
            self.root.after(0, lambda: self._update_results(summary, details))
            
            # 更新状态
            self.root.after(0, lambda: self.status_var.set("分析完成"))
            
        except Exception as e:
            error_msg = f"分析过程中出错: {str(e)}"
            
            logger.error(error_msg)
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
            self.root.after(0, lambda: self.status_var.set("分析失败"))
            
        finally:
            # 重置按钮状态
            self.root.after(0, self._reset_buttons)
            
    def _stop_analysis(self):
        
        # 设置停止事件
        self.stop_event.set()
        
        # 如果有正在运行的分析进程，终止它
        if self.analysis_process and self.analysis_process.poll() is None:
            self.analysis_process.terminate()
            
        # 更新状态
        self.status_var.set("正在停止分析...")
        
    def _reset_buttons(self):
        
        # 启用运行按钮，禁用停止按钮
        self.run_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
    def _generate_summary(self, results):
        
        portfolio_summary = results["portfolio_summary"]
        
        summary_lines = ["# 投资组合分析摘要\n"]
        
        # 买入建议
        summary_lines.append("## 买入建议")
        if portfolio_summary["buy_recommendations"]:
            for ticker, confidence in portfolio_summary["buy_recommendations"]:
                summary_lines.append(f"- {ticker}: 置信度 {format_percentage(confidence)}")
        else:
            summary_lines.append("- 无买入建议")
            
        summary_lines.append("\n")
        
        # 卖出建议
        summary_lines.append("## 卖出建议")
        if portfolio_summary["sell_recommendations"]:
            for ticker, confidence in portfolio_summary["sell_recommendations"]:
                summary_lines.append(f"- {ticker}: 置信度 {format_percentage(confidence)}")
        else:
            summary_lines.append("- 无卖出建议")
            
        summary_lines.append("\n")
        
        # 持有建议
        summary_lines.append("## 持有建议")
        if portfolio_summary["hold_recommendations"]:
            for ticker, confidence in portfolio_summary["hold_recommendations"]:
                summary_lines.append(f"- {ticker}: 置信度 {format_percentage(confidence)}")
        else:
            summary_lines.append("- 无持有建议")
            
        return "\n".join(summary_lines)
        
    def _generate_details(self, results, show_reasoning=True):
        
        individual_analysis = results["individual_analysis"]
        
        details_lines = ["# 个股详细分析\n"]
        
        for ticker, analysis in individual_analysis.items():
            details_lines.append(f"## {ticker}\n")
            
            if "error" in analysis:
                details_lines.append(f"分析错误: {analysis['error']}\n")
                continue
                
            # 市场数据
            market_data = analysis["market_data"]
            details_lines.append("### 市场数据")
            details_lines.append(f"- 当前价格: {format_currency(market_data.current_price)}")
            details_lines.append(f"- 价格变化: {format_currency(market_data.price_change)} ({format_percentage(market_data.price_change_percent/100)})")
            details_lines.append(f"- 成交量: {market_data.volume:,}")
            
            if market_data.market_cap:
                details_lines.append(f"- 市值: {format_currency(market_data.market_cap)}")
                
            if market_data.pe_ratio:
                details_lines.append(f"- 市盈率: {market_data.pe_ratio:.2f}")
                
            if market_data.dividend_yield:
                details_lines.append(f"- 股息收益率: {format_percentage(market_data.dividend_yield)}")
                
            details_lines.append("\n")
            
            # 智能体决策
            details_lines.append("### 智能体决策")
            
            for decision in analysis["agent_decisions"]:
                details_lines.append(f"#### {decision.agent_name}")
                details_lines.append(f"- 决策: {decision.decision}")
                details_lines.append(f"- 置信度: {format_percentage(decision.confidence)}")
                details_lines.append(f"- 风险等级: {decision.risk_level}")
                
                if show_reasoning:
                    details_lines.append(f"- 推理: {decision.reasoning}")
                    
                details_lines.append("\n")
                
            # 最终决策
            final_decision = analysis["final_decision"]
            details_lines.append("### 最终决策")
            details_lines.append(f"- 决策: {final_decision['decision']}")
            details_lines.append(f"- 置信度: {format_percentage(final_decision['confidence'])}")
            details_lines.append(f"- 基于: {final_decision['agent_count']} 个智能体")
            details_lines.append(f"- 综合推理: {final_decision['reasoning']}")
            
            details_lines.append("\n---\n")
            
        return "\n".join(details_lines)
        
    def _generate_charts(self, results):
        
        individual_analysis = results["individual_analysis"]
        
        # 清空图表容器
        for widget in self.chart_container.winfo_children():
            widget.destroy()
            
        # 创建选项卡
        chart_notebook = ttk.Notebook(self.chart_container)
        chart_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 股票价格图表
        for ticker, analysis in individual_analysis.items():
            if "error" in analysis:
                continue
                
            # 创建股票价格图表选项卡
            price_frame = ttk.Frame(chart_notebook)
            chart_notebook.add(price_frame, text=f"{ticker} 价格")
            
            try:
                # 生成股票价格图表
                fig = generate_stock_chart(ticker)
                
                # 将图表添加到选项卡
                canvas = FigureCanvasTkAgg(fig, master=price_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                
            except Exception as e:
                error_label = ttk.Label(price_frame, text=f"生成图表时出错: {str(e)}")
                error_label.pack(pady=20)
                
        # 如果有多个股票，添加比较图表
        if len(individual_analysis) > 1:
            tickers = [ticker for ticker in individual_analysis.keys() if "error" not in individual_analysis[ticker]]
            
            if tickers:
                # 创建比较图表选项卡
                comparison_frame = ttk.Frame(chart_notebook)
                chart_notebook.add(comparison_frame, text="股票比较")
                
                try:
                    # 生成比较图表
                    fig = generate_comparison_chart(tickers)
                    
                    # 将图表添加到选项卡
                    canvas = FigureCanvasTkAgg(fig, master=comparison_frame)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                    
                except Exception as e:
                    error_label = ttk.Label(comparison_frame, text=f"生成比较图表时出错: {str(e)}")
                    error_label.pack(pady=20)
                    
        # 添加智能体置信度图表
        confidence_frame = ttk.Frame(chart_notebook)
        chart_notebook.add(confidence_frame, text="智能体置信度")
        
        try:
            # 收集智能体决策数据
            agent_data = {}
            
            for ticker, analysis in individual_analysis.items():
                if "error" in analysis:
                    continue
                    
                for decision in analysis["agent_decisions"]:
                    agent_name = decision.agent_name
                    
                    if agent_name not in agent_data:
                        agent_data[agent_name] = {"BUY": [], "SELL": [], "HOLD": []}
                        
                    agent_data[agent_name][decision.decision].append((ticker, decision.confidence))
                    
            # 生成智能体置信度图表
            fig = generate_agent_confidence_chart(agent_data)
            
            # 将图表添加到选项卡
            canvas = FigureCanvasTkAgg(fig, master=confidence_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            error_label = ttk.Label(confidence_frame, text=f"生成智能体置信度图表时出错: {str(e)}")
            error_label.pack(pady=20)
            
    def _update_results(self, summary, details):
        
        # 更新摘要
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, summary)
        self.summary_text.config(state=tk.DISABLED)
        
        # 更新详细信息
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, details)
        self.details_text.config(state=tk.DISABLED)
        
        # 切换到摘要选项卡
        self.notebook.select(0)

def start_app():
    
    try:
        root = tk.Tk()
        app = AIHedgeFundGUI(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"启动应用程序时出错: {e}")
        messagebox.showerror("启动错误", f"启动应用程序时出错: {str(e)}")
        
        sys.exit(1)

if __name__ == "__main__":
    
    try:
        start_app()
    except Exception as e:
        logger.error(f"未处理的异常: {e}")
        sys.exit(1)