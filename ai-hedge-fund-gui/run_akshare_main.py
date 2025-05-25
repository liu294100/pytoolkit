#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 金融数据GUI客户端 - 优化版
功能包括：股票数据、基金数据、期货数据、经济数据等查询
优化：多线程处理、进度条显示、异常处理改进
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import akshare as ak
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import threading
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import queue
import time

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ProgressDialog:
    """进度条对话框"""
    def __init__(self, parent, title="数据加载中..."):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("300x100")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # 进度条
        ttk.Label(self.dialog, text="正在获取数据，请稍候...").pack(pady=10)
        self.progress = ttk.Progressbar(self.dialog, mode='indeterminate')
        self.progress.pack(pady=10, padx=20, fill=tk.X)
        self.progress.start()
        
        # 取消按钮
        self.cancel_button = ttk.Button(self.dialog, text="取消", command=self.cancel)
        self.cancel_button.pack(pady=5)
        
        self.cancelled = False
        
    def cancel(self):
        self.cancelled = True
        self.close()
        
    def close(self):
        self.progress.stop()
        self.dialog.destroy()

class AKShareGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AKShare 金融数据查询客户端 - 优化版")
        self.root.geometry("1300x900")
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.data_queue = queue.Queue()
        
        # 创建主框架
        self.setup_ui()
        
        # 数据存储
        self.current_data = None
        self.progress_dialog = None
        
        # 启动数据处理队列监听
        self.process_data_queue()
        
    def setup_ui(self):
        """设置用户界面"""
        # 创建菜单栏
        self.create_menu()
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建笔记本控件（标签页）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建各个功能标签页
        self.create_stock_tab()
        self.create_fund_tab()
        self.create_futures_tab()
        self.create_economics_tab()
        self.create_news_tab()
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导出数据", command=self.export_to_excel)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
        
    def show_about(self):
        """显示关于对话框"""
        messagebox.showinfo("关于", "AKShare 金融数据查询客户端\n版本: 2.0\n优化版本，支持多线程处理")
        
    def create_stock_tab(self):
        """创建股票数据标签页"""
        stock_frame = ttk.Frame(self.notebook)
        self.notebook.add(stock_frame, text="股票数据")
        
        # 创建主容器
        main_container = ttk.PanedWindow(stock_frame, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧控制面板
        left_frame = ttk.LabelFrame(main_container, text="查询参数", padding=10)
        main_container.add(left_frame, weight=1)
        
        # 股票代码输入
        ttk.Label(left_frame, text="股票代码:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.stock_code_var = tk.StringVar(value="000001")
        ttk.Entry(left_frame, textvariable=self.stock_code_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # 时间范围选择
        ttk.Label(left_frame, text="时间范围:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.stock_period_var = tk.StringVar(value="daily")
        period_combo = ttk.Combobox(left_frame, textvariable=self.stock_period_var, width=12)
        period_combo['values'] = ('daily', 'weekly', 'monthly')
        period_combo.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # 日期选择
        ttk.Label(left_frame, text="开始日期:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.stock_start_date = tk.StringVar(value="20240101")
        ttk.Entry(left_frame, textvariable=self.stock_start_date, width=15).grid(row=2, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(left_frame, text="结束日期:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.stock_end_date = tk.StringVar(value=datetime.now().strftime("%Y%m%d"))
        ttk.Entry(left_frame, textvariable=self.stock_end_date, width=15).grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # 功能按钮
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky=tk.EW)
        
        ttk.Button(button_frame, text="获取历史数据", 
                  command=lambda: self.async_get_stock_data('hist')).pack(pady=2, fill=tk.X)
        ttk.Button(button_frame, text="获取实时行情", 
                  command=lambda: self.async_get_stock_data('realtime')).pack(pady=2, fill=tk.X)
        ttk.Button(button_frame, text="获取财务数据", 
                  command=lambda: self.async_get_stock_data('financial')).pack(pady=2, fill=tk.X)
        ttk.Button(button_frame, text="获取股票列表", 
                  command=lambda: self.async_get_stock_data('list')).pack(pady=2, fill=tk.X)
        
        # 右侧显示区域
        right_frame = ttk.LabelFrame(main_container, text="数据显示", padding=5)
        main_container.add(right_frame, weight=3)
        
        # 创建垂直分割面板
        v_paned = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        v_paned.pack(fill=tk.BOTH, expand=True)
        
        # 数据表格区域
        table_frame = ttk.Frame(v_paned)
        v_paned.add(table_frame, weight=2)
        
        self.stock_tree = ttk.Treeview(table_frame, show='headings')
        stock_scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        stock_scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.stock_tree.xview)
        self.stock_tree.configure(yscrollcommand=stock_scrollbar_y.set, xscrollcommand=stock_scrollbar_x.set)
        
        self.stock_tree.grid(row=0, column=0, sticky='nsew')
        stock_scrollbar_y.grid(row=0, column=1, sticky='ns')
        stock_scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        
        # 图表区域
        chart_frame = ttk.Frame(v_paned)
        v_paned.add(chart_frame, weight=1)
        
        self.stock_fig, self.stock_ax = plt.subplots(figsize=(8, 4))
        self.stock_canvas = FigureCanvasTkAgg(self.stock_fig, chart_frame)
        self.stock_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_fund_tab(self):
        """创建基金数据标签页"""
        fund_frame = ttk.Frame(self.notebook)
        self.notebook.add(fund_frame, text="基金数据")
        
        # 创建主容器
        main_container = ttk.PanedWindow(fund_frame, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧控制面板
        left_frame = ttk.LabelFrame(main_container, text="查询参数", padding=10)
        main_container.add(left_frame, weight=1)
        
        # 基金代码输入
        ttk.Label(left_frame, text="基金代码:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.fund_code_var = tk.StringVar(value="000001")
        ttk.Entry(left_frame, textvariable=self.fund_code_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # 功能按钮
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky=tk.EW)
        
        ttk.Button(button_frame, text="获取基金净值", 
                  command=lambda: self.async_get_fund_data('nav')).pack(pady=2, fill=tk.X)
        ttk.Button(button_frame, text="获取基金信息", 
                  command=lambda: self.async_get_fund_data('info')).pack(pady=2, fill=tk.X)
        ttk.Button(button_frame, text="获取基金排行", 
                  command=lambda: self.async_get_fund_data('rank')).pack(pady=2, fill=tk.X)
        
        # 右侧显示区域
        right_frame = ttk.LabelFrame(main_container, text="数据显示", padding=5)
        main_container.add(right_frame, weight=3)
        
        self.fund_tree = ttk.Treeview(right_frame, show='headings')
        fund_scrollbar_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.fund_tree.yview)
        fund_scrollbar_x = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.fund_tree.xview)
        self.fund_tree.configure(yscrollcommand=fund_scrollbar_y.set, xscrollcommand=fund_scrollbar_x.set)
        
        self.fund_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fund_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_futures_tab(self):
        """创建期货数据标签页"""
        futures_frame = ttk.Frame(self.notebook)
        self.notebook.add(futures_frame, text="期货数据")
        
        # 创建主容器
        main_container = ttk.PanedWindow(futures_frame, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧控制面板
        left_frame = ttk.LabelFrame(main_container, text="查询参数", padding=10)
        main_container.add(left_frame, weight=1)
        
        # 期货品种选择
        ttk.Label(left_frame, text="期货品种:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.futures_symbol_var = tk.StringVar(value="rb")
        futures_entry = ttk.Entry(left_frame, textvariable=self.futures_symbol_var, width=15)
        futures_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # 功能按钮
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky=tk.EW)
        
        ttk.Button(button_frame, text="获取期货行情", 
                  command=lambda: self.async_get_futures_data('realtime')).pack(pady=2, fill=tk.X)
        ttk.Button(button_frame, text="获取历史数据", 
                  command=lambda: self.async_get_futures_data('history')).pack(pady=2, fill=tk.X)
        
        # 右侧显示区域
        right_frame = ttk.LabelFrame(main_container, text="数据显示", padding=5)
        main_container.add(right_frame, weight=3)
        
        self.futures_tree = ttk.Treeview(right_frame, show='headings')
        futures_scrollbar_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.futures_tree.yview)
        futures_scrollbar_x = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.futures_tree.xview)
        self.futures_tree.configure(yscrollcommand=futures_scrollbar_y.set, xscrollcommand=futures_scrollbar_x.set)
        
        self.futures_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        futures_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_economics_tab(self):
        """创建经济数据标签页"""
        econ_frame = ttk.Frame(self.notebook)
        self.notebook.add(econ_frame, text="经济数据")
        
        # 创建主容器
        main_container = ttk.PanedWindow(econ_frame, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧控制面板
        left_frame = ttk.LabelFrame(main_container, text="查询参数", padding=10)
        main_container.add(left_frame, weight=1)
        
        # 数据类型选择
        ttk.Label(left_frame, text="数据类型:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.econ_type_var = tk.StringVar(value="GDP")
        econ_combo = ttk.Combobox(left_frame, textvariable=self.econ_type_var, width=12)
        econ_combo['values'] = ('GDP', 'CPI', 'PPI', '社会融资规模', '货币供应量')
        econ_combo.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # 功能按钮
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky=tk.EW)
        
        ttk.Button(button_frame, text="获取宏观数据", 
                  command=lambda: self.async_get_economics_data('macro')).pack(pady=2, fill=tk.X)
        ttk.Button(button_frame, text="获取央行数据", 
                  command=lambda: self.async_get_economics_data('central_bank')).pack(pady=2, fill=tk.X)
        
        # 右侧显示区域
        right_frame = ttk.LabelFrame(main_container, text="数据显示", padding=5)
        main_container.add(right_frame, weight=3)
        
        self.econ_tree = ttk.Treeview(right_frame, show='headings')
        econ_scrollbar_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.econ_tree.yview)
        econ_scrollbar_x = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.econ_tree.xview)
        self.econ_tree.configure(yscrollcommand=econ_scrollbar_y.set, xscrollcommand=econ_scrollbar_x.set)
        
        self.econ_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        econ_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_news_tab(self):
        """创建新闻资讯标签页"""
        news_frame = ttk.Frame(self.notebook)
        self.notebook.add(news_frame, text="新闻资讯")
        
        # 创建主容器
        main_container = ttk.PanedWindow(news_frame, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧控制面板
        left_frame = ttk.LabelFrame(main_container, text="查询参数", padding=10)
        main_container.add(left_frame, weight=1)
        
        # 新闻类型选择
        ttk.Label(left_frame, text="新闻类型:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.news_type_var = tk.StringVar(value="财经新闻")
        news_combo = ttk.Combobox(left_frame, textvariable=self.news_type_var, width=12)
        news_combo['values'] = ('财经新闻', '热点新闻', '公司资讯')
        news_combo.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # 功能按钮
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky=tk.EW)
        
        ttk.Button(button_frame, text="获取财经新闻", 
                  command=lambda: self.async_get_news_data('financial')).pack(pady=2, fill=tk.X)
        ttk.Button(button_frame, text="获取热点资讯", 
                  command=lambda: self.async_get_news_data('hot')).pack(pady=2, fill=tk.X)
        
        # 右侧显示区域
        right_frame = ttk.LabelFrame(main_container, text="新闻内容", padding=5)
        main_container.add(right_frame, weight=3)
        
        # 新闻列表
        self.news_listbox = tk.Listbox(right_frame, height=10)
        news_list_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.news_listbox.yview)
        self.news_listbox.configure(yscrollcommand=news_list_scrollbar.set)
        
        self.news_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        news_list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 新闻详情
        ttk.Label(right_frame, text="新闻详情:").pack(anchor=tk.W, pady=(10,0))
        self.news_text = tk.Text(right_frame, wrap=tk.WORD, height=15)
        news_text_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.news_text.yview)
        self.news_text.configure(yscrollcommand=news_text_scrollbar.set)
        
        self.news_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        news_text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定列表选择事件
        self.news_listbox.bind('<<ListboxSelect>>', self.on_news_select)
        
    def process_data_queue(self):
        """处理数据队列"""
        try:
            while True:
                callback, data, error = self.data_queue.get_nowait()
                if callback:
                    callback(data, error)
                self.data_queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_data_queue)
            
    def show_progress(self, title="数据加载中..."):
        """显示进度条"""
        if self.progress_dialog:
            self.progress_dialog.close()
        self.progress_dialog = ProgressDialog(self.root, title)
        self.status_var.set("正在获取数据...")
        
    def hide_progress(self):
        """隐藏进度条"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.status_var.set("就绪")
        
    def async_get_stock_data(self, data_type):
        """异步获取股票数据"""
        self.show_progress("获取股票数据中...")
        
        def callback(data, error):
            self.hide_progress()
            if error:
                messagebox.showerror("错误", f"获取股票数据失败: {str(error)}")
            else:
                self.display_data_in_tree(self.stock_tree, data)
                if data_type == 'hist' and data is not None and not data.empty:
                    self.plot_stock_chart(data)
                self.current_data = data
                
        future = self.executor.submit(self.get_stock_data, data_type)
        self.monitor_future(future, callback)
        
    def async_get_fund_data(self, data_type):
        """异步获取基金数据"""
        self.show_progress("获取基金数据中...")
        
        def callback(data, error):
            self.hide_progress()
            if error:
                messagebox.showerror("错误", f"获取基金数据失败: {str(error)}")
            else:
                self.display_data_in_tree(self.fund_tree, data)
                self.current_data = data
                
        future = self.executor.submit(self.get_fund_data, data_type)
        self.monitor_future(future, callback)
        
    def async_get_futures_data(self, data_type):
        """异步获取期货数据"""
        self.show_progress("获取期货数据中...")
        
        def callback(data, error):
            self.hide_progress()
            if error:
                messagebox.showerror("错误", f"获取期货数据失败: {str(error)}")
            else:
                self.display_data_in_tree(self.futures_tree, data)
                self.current_data = data
                
        future = self.executor.submit(self.get_futures_data, data_type)
        self.monitor_future(future, callback)
        
    def async_get_economics_data(self, data_type):
        """异步获取经济数据"""
        self.show_progress("获取经济数据中...")
        
        def callback(data, error):
            self.hide_progress()
            if error:
                messagebox.showerror("错误", f"获取经济数据失败: {str(error)}")
            else:
                self.display_data_in_tree(self.econ_tree, data)
                self.current_data = data
                
        future = self.executor.submit(self.get_economics_data, data_type)
        self.monitor_future(future, callback)
        
    def async_get_news_data(self, data_type):
        """异步获取新闻数据"""
        self.show_progress("获取新闻数据中...")
        
        def callback(data, error):
            self.hide_progress()
            if error:
                messagebox.showerror("错误", f"获取新闻数据失败: {str(error)}")
            else:
                self.display_news_data(data)
                self.current_data = data
                
        future = self.executor.submit(self.get_news_data, data_type)
        self.monitor_future(future, callback)
        
    def monitor_future(self, future, callback):
        """监控异步任务"""
        def check_future():
            if future.done():
                try:
                    data = future.result()
                    self.data_queue.put((callback, data, None))
                except Exception as e:
                    self.data_queue.put((callback, None, e))
            else:
                self.root.after(100, check_future)
        
        check_future()
        
    def get_stock_data(self, data_type):
        """获取股票数据（在后台线程中执行）"""
        stock_code = self.stock_code_var.get()
        
        if data_type == 'hist':
            start_date = self.stock_start_date.get()
            end_date = self.stock_end_date.get()
            period = self.stock_period_var.get()
            return ak.stock_zh_a_hist(symbol=stock_code, period=period, 
                                    start_date=start_date, end_date=end_date)
        elif data_type == 'realtime':
            data = ak.stock_zh_a_spot_em()
            if stock_code:
                data = data[data['代码'].str.contains(stock_code)]
            return data
        elif data_type == 'financial':
            return ak.stock_financial_abstract(symbol=stock_code)
        elif data_type == 'list':
            return ak.stock_zh_a_spot_em().head(100)
            
    def get_fund_data(self, data_type):
        """获取基金数据（在后台线程中执行）"""
        fund_code = self.fund_code_var.get()
        
        if data_type == 'nav':
            return ak.fund_etf_hist_em(symbol=fund_code, period="daily", 
                                     start_date="20240101", end_date="20241231")
        elif data_type == 'info':
            return ak.fund_individual_basic_info_xq(symbol=fund_code)
        elif data_type == 'rank':
            return ak.fund_em_open_fund_rank().head(50)
            
    def get_futures_data(self, data_type):
        """获取期货数据（在后台线程中执行）"""
        symbol = self.futures_symbol_var.get()
        
        if data_type == 'realtime':
            return ak.futures_zh_spot()
        elif data_type == 'history':
            return ak.futures_zh_daily_sina(symbol=symbol)
            
    def get_economics_data(self, data_type):
        """获取经济数据（在后台线程中执行）"""
        econ_type = self.econ_type_var.get()
        
        if data_type == 'macro':
            if econ_type == 'GDP':
                return ak.macro_china_gdp()
            elif econ_type == 'CPI':
                return ak.macro_china_cpi()
            elif econ_type == 'PPI':
                return ak.macro_china_ppi()
            else:
                return ak.macro_china_gdp()
        elif data_type == 'central_bank':
            return ak.macro_china_money_supply()
            
    def get_news_data(self, data_type):
        """获取新闻数据（在后台线程中执行）"""
        try:
            if data_type == 'financial':
                # 使用更稳定的新闻接口
                return ak.stock_news_em()
            elif data_type == 'hot':
                # 获取热点新闻
                return ak.stock_news_em()
        except Exception as e:
            # 如果主接口失败，尝试备用接口
            try:
                return ak.news_cctv()
            except:
                # 返回示例数据
                sample_data = pd.DataFrame({
                    '标题': ['财经新闻1', '财经新闻2', '财经新闻3'],
                    '时间': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')] * 3,
                    '内容': ['示例新闻内容1', '示例新闻内容2', '示例新闻内容3'],
                    '链接': ['#'] * 3
                })
                return sample_data
            
    def display_data_in_tree(self, tree, data):
        """在树形控件中显示数据"""
        # 清空现有数据
        for item in tree.get_children():
            tree.delete(item)
            
        if data is None or data.empty:
            return
            
        # 设置列
        columns = list(data.columns)
        tree['columns'] = columns
        
        # 设置列标题和宽度
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor=tk.CENTER)
            
        # 插入数据（限制显示条数以提高性能）
        max_rows = 1000
        for index, row in data.head(max_rows).iterrows():
            values = [str(row[col])[:50] for col in columns]  # 限制字符长度
            tree.insert('', tk.END, values=values)
            
    def display_news_data(self, data):
        """显示新闻数据"""
        # 清空现有数据
        self.news_listbox.delete(0, tk.END)
        self.news_text.delete('1.0', tk.END)
        
        if data is None or data.empty:
            self.news_listbox.insert(tk.END, "暂无新闻数据")
            return
            
        # 存储新闻数据
        self.news_data = data
        
        # 在列表框中显示新闻标题
        title_col = None
        for col in data.columns:
            if '标题' in col or 'title' in col.lower() or '新闻' in col:
                title_col = col
                break
        
        if title_col:
            for index, row in data.head(20).iterrows():  # 显示前20条
                title = str(row[title_col])[:80]  # 限制标题长度
                self.news_listbox.insert(tk.END, f"{index}: {title}")
        else:
            # 如果没有找到标题列，显示第一列
            first_col = data.columns[0]
            for index, row in data.head(20).iterrows():
                content = str(row[first_col])[:80]
                self.news_listbox.insert(tk.END, f"{index}: {content}")
                
    def on_news_select(self, event):
        """新闻列表选择事件"""
        selection = self.news_listbox.curselection()
        if not selection or not hasattr(self, 'news_data'):
            return
            
        index = int(self.news_listbox.get(selection[0]).split(':')[0])
        if index < len(self.news_data):
            news_item = self.news_data.iloc[index]
            
            # 显示新闻详情
            self.news_text.delete('1.0', tk.END)
            
            for col in self.news_data.columns:
                content = f"{col}: {str(news_item[col])}\n"
                self.news_text.insert(tk.END, content)
            self.news_text.insert(tk.END, "\n" + "-"*50 + "\n")
            
    def plot_stock_chart(self, data):
        """绘制股票图表"""
        if data is None or data.empty:
            return
            
        self.stock_ax.clear()
        
        try:
            # 查找日期和价格列
            date_col = None
            price_col = None
            
            for col in data.columns:
                if '日期' in col or 'date' in col.lower():
                    date_col = col
                if '收盘' in col or 'close' in col.lower() or '价格' in col:
                    price_col = col
                    
            if date_col and price_col:
                dates = pd.to_datetime(data[date_col])
                prices = pd.to_numeric(data[price_col], errors='coerce')
                
                # 过滤无效数据
                valid_data = ~(pd.isna(dates) | pd.isna(prices))
                dates = dates[valid_data]
                prices = prices[valid_data]
                
                if len(dates) > 0 and len(prices) > 0:
                    self.stock_ax.plot(dates, prices, linewidth=2, color='blue')
                    self.stock_ax.set_title(f"股票价格走势 - {self.stock_code_var.get()}")
                    self.stock_ax.set_xlabel("日期")
                    self.stock_ax.set_ylabel("价格")
                    
                    # 格式化x轴日期
                    if len(dates) > 10:
                        self.stock_ax.xaxis.set_major_locator(mdates.MonthLocator())
                        self.stock_ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                    else:
                        self.stock_ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    
                    plt.setp(self.stock_ax.xaxis.get_majorticklabels(), rotation=45)
                    self.stock_fig.tight_layout()
                    
        except Exception as e:
            print(f"绘图错误: {e}")
            self.stock_ax.text(0.5, 0.5, f"图表绘制失败\n{str(e)}", 
                             ha='center', va='center', transform=self.stock_ax.transAxes)
            
        self.stock_canvas.draw()
        
    def export_to_excel(self):
        """导出数据到Excel"""
        if self.current_data is None or self.current_data.empty:
            messagebox.showwarning("警告", "没有数据可导出")
            return
            
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filename:
                if filename.endswith('.csv'):
                    self.current_data.to_csv(filename, index=False, encoding='utf-8-sig')
                else:
                    self.current_data.to_excel(filename, index=False)
                messagebox.showinfo("成功", f"数据已导出到: {filename}")
                
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
            
    def __del__(self):
        """析构函数，清理线程池"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

def main():
    """主函数"""
    try:
        root = tk.Tk()
        
        # 设置窗口图标（如果有的话）
        try:
            root.iconbitmap('icon.ico')
        except:
            pass
            
        app = AKShareGUI(root)
        
        # 设置窗口关闭事件
        def on_closing():
            if hasattr(app, 'executor'):
                app.executor.shutdown(wait=False)
            root.destroy()
            
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        messagebox.showerror("错误", f"程序启动失败: {str(e)}")

if __name__ == "__main__":
    main()