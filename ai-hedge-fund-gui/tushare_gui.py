import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
from datetime import datetime, timedelta
import numpy as np

class TushareGUIClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Tushare股票数据分析客户端")
        self.root.geometry("1200x800")
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 初始化Tushare (需要用户设置token)
        self.pro = None
        self.current_data = None
        
        self.create_widgets()
        self.setup_layout()
        
    def create_widgets(self):
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        
        # 顶部工具栏
        self.toolbar = ttk.Frame(self.main_frame)
        
        # Token设置
        ttk.Label(self.toolbar, text="Tushare Token:").pack(side=tk.LEFT, padx=5)
        self.token_var = tk.StringVar()
        self.token_entry = ttk.Entry(self.toolbar, textvariable=self.token_var, width=40, show="*")
        self.token_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(self.toolbar, text="设置Token", command=self.set_token).pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        self.status_var = tk.StringVar(value="请先设置Tushare Token")
        self.status_label = ttk.Label(self.toolbar, textvariable=self.status_var, foreground="red")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # 创建Notebook（标签页）
        self.notebook = ttk.Notebook(self.main_frame)
        
        # 标签页1: 股票基础信息
        self.stock_info_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stock_info_frame, text="股票信息")
        self.create_stock_info_tab()
        
        # 标签页2: 历史行情
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="历史行情")
        self.create_history_tab()
        
        # 标签页3: 实时行情
        self.realtime_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.realtime_frame, text="实时行情")
        self.create_realtime_tab()
        
        # 标签页4: 财务数据
        self.finance_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.finance_frame, text="财务数据")
        self.create_finance_tab()
        
        # 标签页5: 数据分析
        self.analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_frame, text="数据分析")
        self.create_analysis_tab()
        
    def setup_layout(self):
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.toolbar.pack(fill=tk.X, pady=(0, 10))
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
    def set_token(self):
        """设置Tushare Token"""
        token = self.token_var.get().strip()
        if not token:
            messagebox.showerror("错误", "请输入有效的Token")
            return
            
        try:
            ts.set_token(token)
            self.pro = ts.pro_api()
            # 测试连接
            test_data = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name')
            self.status_var.set("Token设置成功，连接正常")
            self.status_label.config(foreground="green")
            messagebox.showinfo("成功", "Token设置成功！")
        except Exception as e:
            messagebox.showerror("错误", f"Token设置失败: {str(e)}")
            self.status_var.set("Token设置失败")
            self.status_label.config(foreground="red")
    
    def create_stock_info_tab(self):
        """创建股票信息标签页"""
        # 搜索框架
        search_frame = ttk.LabelFrame(self.stock_info_frame, text="股票搜索")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="股票代码/名称:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="搜索", command=self.search_stock).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="获取股票列表", command=self.get_stock_list).pack(side=tk.LEFT, padx=5)
        
        # 结果显示
        result_frame = ttk.LabelFrame(self.stock_info_frame, text="股票列表")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建树形视图
        columns = ('代码', '名称', '地区', '行业', '市场', '上市日期')
        self.stock_tree = ttk.Treeview(result_frame, columns=columns, show='headings')
        
        for col in columns:
            self.stock_tree.heading(col, text=col)
            self.stock_tree.column(col, width=100)
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        scrollbar_x = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self.stock_tree.xview)
        self.stock_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_history_tab(self):
        """创建历史行情标签页"""
        # 参数设置框架
        param_frame = ttk.LabelFrame(self.history_frame, text="查询参数")
        param_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 第一行：股票代码和日期
        row1 = ttk.Frame(param_frame)
        row1.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(row1, text="股票代码:").pack(side=tk.LEFT)
        self.hist_code_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.hist_code_var, width=15).pack(side=tk.LEFT, padx=(5,20))
        
        ttk.Label(row1, text="开始日期:").pack(side=tk.LEFT)
        self.start_date_var = tk.StringVar(value=(datetime.now() - timedelta(days=365)).strftime('%Y%m%d'))
        ttk.Entry(row1, textvariable=self.start_date_var, width=15).pack(side=tk.LEFT, padx=(5,20))
        
        ttk.Label(row1, text="结束日期:").pack(side=tk.LEFT)
        self.end_date_var = tk.StringVar(value=datetime.now().strftime('%Y%m%d'))
        ttk.Entry(row1, textvariable=self.end_date_var, width=15).pack(side=tk.LEFT, padx=5)
        
        # 第二行：按钮
        row2 = ttk.Frame(param_frame)
        row2.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(row2, text="获取日线数据", command=self.get_daily_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="获取周线数据", command=self.get_weekly_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="获取月线数据", command=self.get_monthly_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="导出数据", command=self.export_data).pack(side=tk.LEFT, padx=5)
        
        # 数据显示区域
        data_frame = ttk.LabelFrame(self.history_frame, text="历史数据")
        data_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建数据表格
        hist_columns = ('日期', '开盘', '最高', '最低', '收盘', '成交量', '成交额', '涨跌幅')
        self.hist_tree = ttk.Treeview(data_frame, columns=hist_columns, show='headings', height=10)
        
        for col in hist_columns:
            self.hist_tree.heading(col, text=col)
            self.hist_tree.column(col, width=80)
        
        hist_scroll_y = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.hist_tree.yview)
        hist_scroll_x = ttk.Scrollbar(data_frame, orient=tk.HORIZONTAL, command=self.hist_tree.xview)
        self.hist_tree.configure(yscrollcommand=hist_scroll_y.set, xscrollcommand=hist_scroll_x.set)
        
        self.hist_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        hist_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_realtime_tab(self):
        """创建实时行情标签页"""
        # 参数框架
        rt_param_frame = ttk.LabelFrame(self.realtime_frame, text="实时行情")
        rt_param_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(rt_param_frame, text="股票代码:").pack(side=tk.LEFT, padx=5)
        self.rt_code_var = tk.StringVar()
        ttk.Entry(rt_param_frame, textvariable=self.rt_code_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(rt_param_frame, text="获取实时行情", command=self.get_realtime_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(rt_param_frame, text="获取今日行情", command=self.get_today_data).pack(side=tk.LEFT, padx=5)
        
        # 实时数据显示
        rt_data_frame = ttk.LabelFrame(self.realtime_frame, text="行情数据")
        rt_data_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        rt_columns = ('代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交量', '成交额', '换手率')
        self.rt_tree = ttk.Treeview(rt_data_frame, columns=rt_columns, show='headings')
        
        for col in rt_columns:
            self.rt_tree.heading(col, text=col)
            self.rt_tree.column(col, width=100)
        
        rt_scroll = ttk.Scrollbar(rt_data_frame, orient=tk.VERTICAL, command=self.rt_tree.yview)
        self.rt_tree.configure(yscrollcommand=rt_scroll.set)
        
        self.rt_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rt_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_finance_tab(self):
        """创建财务数据标签页"""
        # 参数框架
        fin_param_frame = ttk.LabelFrame(self.finance_frame, text="财务数据查询")
        fin_param_frame.pack(fill=tk.X, padx=5, pady=5)
        
        row1 = ttk.Frame(fin_param_frame)
        row1.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(row1, text="股票代码:").pack(side=tk.LEFT)
        self.fin_code_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.fin_code_var, width=15).pack(side=tk.LEFT, padx=(5,20))
        
        ttk.Label(row1, text="报告期:").pack(side=tk.LEFT)
        self.fin_period_var = tk.StringVar(value="20231231")
        ttk.Entry(row1, textvariable=self.fin_period_var, width=15).pack(side=tk.LEFT, padx=5)
        
        row2 = ttk.Frame(fin_param_frame)
        row2.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(row2, text="资产负债表", command=self.get_balance_sheet).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="利润表", command=self.get_income_statement).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="现金流量表", command=self.get_cashflow_statement).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="财务指标", command=self.get_financial_indicators).pack(side=tk.LEFT, padx=5)
        
        # 财务数据显示
        fin_data_frame = ttk.LabelFrame(self.finance_frame, text="财务数据")
        fin_data_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.fin_tree = ttk.Treeview(fin_data_frame, show='tree headings')
        fin_scroll = ttk.Scrollbar(fin_data_frame, orient=tk.VERTICAL, command=self.fin_tree.yview)
        self.fin_tree.configure(yscrollcommand=fin_scroll.set)
        
        self.fin_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fin_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_analysis_tab(self):
        """创建数据分析标签页"""
        # 分析参数
        analysis_param_frame = ttk.LabelFrame(self.analysis_frame, text="技术分析")
        analysis_param_frame.pack(fill=tk.X, padx=5, pady=5)
        
        row1 = ttk.Frame(analysis_param_frame)
        row1.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(row1, text="股票代码:").pack(side=tk.LEFT)
        self.ana_code_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.ana_code_var, width=15).pack(side=tk.LEFT, padx=(5,20))
        
        ttk.Button(row1, text="K线图", command=self.plot_kline).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="移动平均线", command=self.plot_ma).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="成交量分析", command=self.plot_volume).pack(side=tk.LEFT, padx=5)
        
        # 图表显示区域
        self.chart_frame = ttk.LabelFrame(self.analysis_frame, text="图表分析")
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def check_connection(self):
        """检查连接状态"""
        if self.pro is None:
            messagebox.showerror("错误", "请先设置Tushare Token")
            return False
        return True
        
    def search_stock(self):
        """搜索股票"""
        if not self.check_connection():
            return
            
        search_term = self.search_var.get().strip()
        if not search_term:
            messagebox.showwarning("警告", "请输入搜索内容")
            return
            
        try:
            # 获取股票基础信息
            df = self.pro.stock_basic(exchange='', list_status='L', 
                                    fields='ts_code,symbol,name,area,industry,market,list_date')
            
            # 搜索匹配的股票
            mask = (df['ts_code'].str.contains(search_term, case=False, na=False) | 
                   df['symbol'].str.contains(search_term, case=False, na=False) |
                   df['name'].str.contains(search_term, case=False, na=False))
            
            result_df = df[mask].head(50)  # 限制结果数量
            
            # 清空现有数据
            for item in self.stock_tree.get_children():
                self.stock_tree.delete(item)
            
            # 填充数据
            for _, row in result_df.iterrows():
                self.stock_tree.insert('', 'end', values=(
                    row['ts_code'], row['name'], row['area'], 
                    row['industry'], row['market'], row['list_date']
                ))
                
        except Exception as e:
            messagebox.showerror("错误", f"搜索失败: {str(e)}")
    
    def get_stock_list(self):
        """获取股票列表"""
        if not self.check_connection():
            return
            
        def fetch_data():
            try:
                df = self.pro.stock_basic(exchange='', list_status='L',
                                        fields='ts_code,symbol,name,area,industry,market,list_date')
                
                # 在主线程中更新UI
                self.root.after(0, lambda: self.update_stock_tree(df))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"获取数据失败: {str(e)}"))
        
        threading.Thread(target=fetch_data, daemon=True).start()
    
    def update_stock_tree(self, df):
        """更新股票树形视图"""
        # 清空现有数据
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        
        # 填充数据（限制显示数量以提高性能）
        for _, row in df.head(1000).iterrows():
            self.stock_tree.insert('', 'end', values=(
                row['ts_code'], row['name'], row['area'], 
                row['industry'], row['market'], row['list_date']
            ))
    
    def get_daily_data(self):
        """获取日线数据"""
        self._get_hist_data('D')
        
    def get_weekly_data(self):
        """获取周线数据"""
        self._get_hist_data('W')
        
    def get_monthly_data(self):
        """获取月线数据"""
        self._get_hist_data('M')
    
    def _get_hist_data(self, freq='D'):
        """获取历史数据的通用方法"""
        if not self.check_connection():
            return
            
        ts_code = self.hist_code_var.get().strip()
        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()
        
        if not ts_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        def fetch_data():
            try:
                if freq == 'D':
                    df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
                elif freq == 'W':
                    df = self.pro.weekly(ts_code=ts_code, start_date=start_date, end_date=end_date)
                else:  # 'M'
                    df = self.pro.monthly(ts_code=ts_code, start_date=start_date, end_date=end_date)
                
                df = df.sort_values('trade_date')
                self.current_data = df
                
                self.root.after(0, lambda: self.update_hist_tree(df))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"获取数据失败: {str(e)}"))
        
        threading.Thread(target=fetch_data, daemon=True).start()
    
    def update_hist_tree(self, df):
        """更新历史数据树形视图"""
        # 清空现有数据
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
        
        # 填充数据
        for _, row in df.iterrows():
            # 计算涨跌幅
            pct_chg = row.get('pct_chg', 0)
            
            self.hist_tree.insert('', 'end', values=(
                row['trade_date'], 
                f"{row['open']:.2f}" if pd.notna(row['open']) else '',
                f"{row['high']:.2f}" if pd.notna(row['high']) else '',
                f"{row['low']:.2f}" if pd.notna(row['low']) else '',
                f"{row['close']:.2f}" if pd.notna(row['close']) else '',
                f"{row['vol']:.0f}" if pd.notna(row['vol']) else '',
                f"{row['amount']:.2f}" if pd.notna(row['amount']) else '',
                f"{pct_chg:.2f}%" if pd.notna(pct_chg) else ''
            ))
    
    def get_realtime_data(self):
        """获取实时行情（使用日线数据模拟）"""
        if not self.check_connection():
            return
            
        ts_code = self.rt_code_var.get().strip()
        if not ts_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        def fetch_data():
            try:
                # 获取最新交易日数据
                today = datetime.now().strftime('%Y%m%d')
                df = self.pro.daily(ts_code=ts_code, start_date=today, end_date=today)
                
                if df.empty:
                    # 如果今天没有数据，获取最近的数据
                    df = self.pro.daily(ts_code=ts_code, limit=1)
                
                self.root.after(0, lambda: self.update_rt_tree(df))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"获取数据失败: {str(e)}"))
        
        threading.Thread(target=fetch_data, daemon=True).start()
    
    def get_today_data(self):
        """获取今日行情"""
        self.get_realtime_data()
    
    def update_rt_tree(self, df):
        """更新实时数据树形视图"""
        # 清空现有数据
        for item in self.rt_tree.get_children():  
            self.rt_tree.delete(item)
        
        if df.empty:
            messagebox.showinfo("提示", "没有找到相关数据")
            return
        
        # 获取股票名称
        try:
            stock_info = self.pro.stock_basic(ts_code=df.iloc[0]['ts_code'])
            stock_name = stock_info.iloc[0]['name'] if not stock_info.empty else ''
        except:
            stock_name = ''
        
        # 填充数据
        for _, row in df.iterrows():
            self.rt_tree.insert('', 'end', values=(
                row['ts_code'],
                stock_name,
                f"{row['close']:.2f}" if pd.notna(row['close']) else '',
                f"{row.get('pct_chg', 0):.2f}%" if pd.notna(row.get('pct_chg', 0)) else '',
                f"{row.get('change', 0):.2f}" if pd.notna(row.get('change', 0)) else '',
                f"{row['vol']:.0f}" if pd.notna(row['vol']) else '',
                f"{row['amount']:.2f}" if pd.notna(row['amount']) else '',
                f"{row.get('turnover_rate', 0):.2f}%" if pd.notna(row.get('turnover_rate', 0)) else ''
            ))
    
    def get_balance_sheet(self):
        """获取资产负债表"""
        self._get_financial_data('balancesheet')
    
    def get_income_statement(self):
        """获取利润表"""
        self._get_financial_data('income')
    
    def get_cashflow_statement(self):
        """获取现金流量表"""
        self._get_financial_data('cashflow')
    
    def get_financial_indicators(self):
        """获取财务指标"""
        self._get_financial_data('fina_indicator')
    
    def _get_financial_data(self, data_type):
        """获取财务数据的通用方法"""
        if not self.check_connection():
            return
            
        ts_code = self.fin_code_var.get().strip()
        period = self.fin_period_var.get().strip()
        
        if not ts_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        def fetch_data():
            try:
                if data_type == 'balancesheet':
                    df = self.pro.balancesheet(ts_code=ts_code, period=period)
                elif data_type == 'income':
                    df = self.pro.income(ts_code=ts_code, period=period)
                elif data_type == 'cashflow':
                    df = self.pro.cashflow(ts_code=ts_code, period=period)
                else:  # fina_indicator
                    df = self.pro.fina_indicator(ts_code=ts_code, period=period)
                
                self.root.after(0, lambda: self.update_fin_tree(df, data_type))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"获取财务数据失败: {str(e)}"))
        
        threading.Thread(target=fetch_data, daemon=True).start()
    
    def update_fin_tree(self, df, data_type):
        """更新财务数据树形视图"""
        # 清空现有数据
        for item in self.fin_tree.get_children():
            self.fin_tree.delete(item)
        
        if df.empty:
            messagebox.showinfo("提示", "没有找到财务数据")
            return
        
        # 配置列
        columns = list(df.columns)
        self.fin_tree['columns'] = columns
        self.fin_tree['show'] = 'headings'
        
        for col in columns:
            self.fin_tree.heading(col, text=col)
            self.fin_tree.column(col, width=100)
        
        # 填充数据
        for _, row in df.iterrows():
            values = []
            for col in columns:
                val = row[col]
                if pd.isna(val):
                    values.append('')
                elif isinstance(val, (int, float)):
                    values.append(f"{val:.2f}")
                else:
                    values.append(str(val))
            
            self.fin_tree.insert('', 'end', values=values)
    
    def plot_kline(self):
        """绘制K线图"""
        self._plot_chart('kline')
    
    def plot_ma(self):
        """绘制移动平均线"""
        self._plot_chart('ma')
    
    def plot_volume(self):
        """绘制成交量"""
        self._plot_chart('volume')
    
    def _plot_chart(self, chart_type):
        """绘制图表的通用方法"""
        if not self.check_connection():
            return
            
        ts_code = self.ana_code_var.get().strip()
        if not ts_code:
            messagebox.showwarning("警告", "请输入股票代码")
            return
        
        def fetch_and_plot():
            try:
                # 获取最近一年的数据
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
                
                df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
                df = df.sort_values('trade_date')
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                self.root.after(0, lambda: self.create_chart(df, chart_type, ts_code))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"获取数据失败: {str(e)}"))
        
        threading.Thread(target=fetch_and_plot, daemon=True).start()
    
    def create_chart(self, df, chart_type, ts_code):
        """创建图表"""
        # 清除之前的图表
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        if df.empty:
            messagebox.showinfo("提示", "没有数据可以绘制")
            return
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if chart_type == 'kline':
            self.plot_candlestick(ax, df, ts_code)
        elif chart_type == 'ma':
            self.plot_moving_average(ax, df, ts_code)
        elif chart_type == 'volume':
            self.plot_volume_chart(ax, df, ts_code)
        
        # 嵌入图表到Tkinter
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 添加工具栏
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(canvas, self.chart_frame)
        toolbar.update()
    
    def plot_candlestick(self, ax, df, ts_code):
        """绘制K线图"""
        # 简化的K线图（用线条表示）
        ax.plot(df['trade_date'], df['close'], label='收盘价', linewidth=1)
        ax.fill_between(df['trade_date'], df['low'], df['high'], alpha=0.3, label='最高最低价区间')
        
        ax.set_title(f'{ts_code} K线图')
        ax.set_xlabel('日期')
        ax.set_ylabel('价格')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 旋转日期标签
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    def plot_moving_average(self, ax, df, ts_code):
        """绘制移动平均线"""
        # 计算移动平均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        
        ax.plot(df['trade_date'], df['close'], label='收盘价', linewidth=1)
        ax.plot(df['trade_date'], df['MA5'], label='MA5', linewidth=1)
        ax.plot(df['trade_date'], df['MA10'], label='MA10', linewidth=1)
        ax.plot(df['trade_date'], df['MA20'], label='MA20', linewidth=1)
        ax.plot(df['trade_date'], df['MA60'], label='MA60', linewidth=1)
        
        ax.set_title(f'{ts_code} 移动平均线')
        ax.set_xlabel('日期')
        ax.set_ylabel('价格')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    def plot_volume_chart(self, ax, df, ts_code):
        """绘制成交量图"""
        # 创建双Y轴
        ax2 = ax.twinx()
        
        # 绘制价格
        ax.plot(df['trade_date'], df['close'], 'b-', label='收盘价')
        ax.set_xlabel('日期')
        ax.set_ylabel('价格', color='b')
        ax.tick_params(axis='y', labelcolor='b')
        
        # 绘制成交量
        ax2.bar(df['trade_date'], df['vol'], alpha=0.3, color='r', label='成交量')
        ax2.set_ylabel('成交量', color='r')
        ax2.tick_params(axis='y', labelcolor='r')
        
        ax.set_title(f'{ts_code} 价格与成交量')
        ax.grid(True, alpha=0.3)
        
        # 添加图例
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    def export_data(self):
        """导出数据"""
        if self.current_data is None or self.current_data.empty:
            messagebox.showwarning("警告", "没有数据可以导出")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                if file_path.endswith('.xlsx'):
                    self.current_data.to_excel(file_path, index=False)
                else:
                    self.current_data.to_csv(file_path, index=False, encoding='utf-8-sig')
                
                messagebox.showinfo("成功", f"数据已导出到: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")

def main():
    """主函数"""
    root = tk.Tk()
    app = TushareGUIClient(root)
    
    # 设置窗口图标（如果有的话）
    try:
        root.iconbitmap('icon.ico')
    except:
        pass
    
    # 设置窗口关闭事件
    def on_closing():
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 居中显示窗口
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()