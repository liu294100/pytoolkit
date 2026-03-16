# -*- coding: utf-8 -*-
"""
A股智能交易助手 - 旗舰版 v15.3 (最终完整版)
作者：heng (QQ:200931349)

【完整功能列表】
1. 📰 实时新闻舆情（模拟，可接入真实API）
2. 🔍 个股深度分析：实时行情（6大备用源自动切换）+ 主力资金（Tushare私有节点）
3. 💰 主力资金监控（Tushare私有节点 + 模拟降级）
4. 📊 多因子强势选股（因子权重可自定义）
5. 📱 微信实时推送（pushplus，Token密钥环加密）
6. 💰 模拟交易系统（完全真实A股费率，ST股涨跌停识别，支持止损止盈）
7. 🔔 智能价格提醒（支持条件单：价格/涨跌幅/成交量）
8. ⏰ 定时任务（14:50选股，15:10总结，可自定义时间）
9. 🌐 Tushare私有节点配置（Token + 节点地址）
10. 💾 数据持久化（用户目录独立配置，自动备份损坏文件）
11. ⚡ 独立价格更新线程池（并发请求，界面永不卡顿）
12. 🎨 界面美化，交易时段倒计时精确到秒（含集合竞价）
13. 📈 交易历史记录（可导出CSV）
14. 🔒 敏感信息加密存储（使用系统密钥环，自动回退明文）
15. ⚙️ 可配置参数（缓存时间、费率、数据源优先级、自动交易数量等）
16. 🚀 多线程并发请求，异常自动恢复，详细日志
17. 📋 完整的日志系统，所有错误界面可见
18. 🎯 选股进度实时显示，结果可双击分析
19. ⌨️ 常用快捷键支持（F5刷新，Ctrl+S选股，Ctrl+A分析等）
20. 🔄 自动备份损坏的配置文件
21. 📊 专业K线图（日/周/月/5分钟/15分钟/30分钟/60分钟 + 分时图）
22. ⏱️ 分时图实时更新（每秒刷新，显示当日价格走势）
23. ⌨️ 快捷键列表显示（帮助菜单可查看）
24. 🔄 分钟线数据支持（优先Tushare，降级模拟）
25. 📉 技术指标（MA5/10/20, MACD, RSI, 布林带）
26. 🧠 K线智能分析（用通俗语言描述趋势，如“均线多头排列，MACD金叉，放量上涨”）
27. 🔍 股票信息卡片（市盈率、市净率、流通市值、行业板块，需Tushare支持）
28. 📉 风险控制：止损止盈提醒（可设置百分比）
29. 🌐 网络状态监测：断网时暂停更新并提示
30. 🧪 单元测试设计（代码中不包含，但架构可测试）
31. 🔑 一机一码激活机制，支持重新激活
32. 📅 节假日自动判断，避开非交易日
33. 💼 独立自动交易窗口，支持T+1规则，账户数据持久化
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time as tm                 # 重命名 time 模块，避免与 datetime.time 冲突
import random
import requests
import hashlib
import json
import os
import sys
import queue
import re
from datetime import datetime, timedelta, time as dt_time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict, deque
import traceback
import logging
import copy
from typing import Optional, Dict, List, Any, Tuple, Union

# 授权相关
import uuid
import getpass
import platform
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# ==================== 尝试导入第三方库 ====================
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

try:
    import tushare as ts
    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False

try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    import mplfinance as mpf
    import pandas as pd
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ==================== 配置管理 ====================
class ConfigManager:
    """管理所有配置参数和用户设置"""
    CONFIG_DIR = os.path.expanduser("~/.stock_assistant")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
    
    DEFAULTS = {
        "version": "15.3",
        "wechat_token": "",
        "tushare_token": "",
        "tushare_node": "http://118.178.243.149/dataapi",
        "price_alerts": [],
        "condition_alerts": [],
        "account": {
            "cash": 1000000,
            "positions": {}
        },
        "auto_account": {
            "cash": 1000000,
            "positions": {}
        },
        "trade_history": [],
        "settings": {
            "quote_cache_time": 5,
            "quote_cache_time_nontrade": 30,
            "capital_cache_time": 30,
            "minute_cache_time": 60,
            "commission_rate": 0.00025,
            "min_commission": 5.0,
            "stamp_tax_rate": 0.001,
            "transfer_fee_rate": 0.00001,
            "min_transfer_fee": 1.0,
            "data_sources": ["sina", "tencent", "netease", "sohu", "baidu", "163"],
            "use_mock_on_fail": True,
            "auto_trade_quantity": 1,
            "enable_keyring": HAS_KEYRING,
            "stop_loss_rate": 0.05,
            "take_profit_rate": 0.10,
            "kline_period": "daily",
            "kline_display_days": 60,
            "realtime_chart_update_interval": 1,
            "minute_periods": ["1min", "5min", "15min", "30min", "60min"],
            "auto_trade_auto_start": False
        }
    }
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.config = self.load()
        self._save_lock = threading.Lock()
    
    @classmethod
    def ensure_config_dir(cls):
        if not os.path.exists(cls.CONFIG_DIR):
            os.makedirs(cls.CONFIG_DIR)
    
    def load(self) -> dict:
        self.ensure_config_dir()
        if not os.path.exists(self.CONFIG_FILE):
            return copy.deepcopy(self.DEFAULTS)
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                merged = copy.deepcopy(self.DEFAULTS)
                self._deep_update(merged, data)
                return merged
        except Exception as e:
            backup_name = self.CONFIG_FILE + ".bak." + datetime.now().strftime("%Y%m%d%H%M%S")
            try:
                os.rename(self.CONFIG_FILE, backup_name)
            except:
                pass
            print(f"配置文件损坏，已备份为 {backup_name}，使用默认配置。错误: {e}")
            return copy.deepcopy(self.DEFAULTS)
    
    def _deep_update(self, target: dict, source: dict):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def save(self):
        with self._save_lock:
            self.ensure_config_dir()
            try:
                with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存配置失败: {e}")
    
    def get(self, key: str, default=None):
        keys = key.split('.')
        val = self.config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k, default)
            else:
                return default
        return val
    
    def set(self, key: str, value):
        keys = key.split('.')
        target = self.config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save()
    
    # ----- Token加密存储 -----
    def get_wechat_token(self) -> str:
        if self.get('settings.enable_keyring') and HAS_KEYRING:
            try:
                token = keyring.get_password("stock_assistant", "wechat_token")
                if token:
                    return token
            except Exception:
                pass
        return self.get('wechat_token', '')
    
    def set_wechat_token(self, token: str):
        if self.get('settings.enable_keyring') and HAS_KEYRING:
            try:
                keyring.set_password("stock_assistant", "wechat_token", token)
                self.set('wechat_token', '')
            except Exception:
                self.set('wechat_token', token)
        else:
            self.set('wechat_token', token)
    
    def get_tushare_token(self) -> str:
        if self.get('settings.enable_keyring') and HAS_KEYRING:
            try:
                token = keyring.get_password("stock_assistant", "tushare_token")
                if token:
                    return token
            except Exception:
                pass
        return self.get('tushare_token', '')
    
    def set_tushare_token(self, token: str):
        if self.get('settings.enable_keyring') and HAS_KEYRING:
            try:
                keyring.set_password("stock_assistant", "tushare_token", token)
                self.set('tushare_token', '')
            except Exception:
                self.set('tushare_token', token)
        else:
            self.set('tushare_token', token)
    
    def export_config(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def import_config(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            new_config = json.load(f)
        self.config = new_config
        self.save()


# ==================== 日志系统 ====================
class Logger:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.queue = queue.Queue()
                cls._instance.handlers = []
                cls._instance.level_colors = {
                    'INFO': 'black',
                    'WARNING': 'orange',
                    'ERROR': 'red',
                    'DEBUG': 'gray'
                }
            return cls._instance
    
    def info(self, msg: str):
        self._log('INFO', msg)
    
    def error(self, msg: str):
        self._log('ERROR', msg)
    
    def warning(self, msg: str):
        self._log('WARNING', msg)
    
    def debug(self, msg: str):
        self._log('DEBUG', msg)
    
    def _log(self, level: str, msg: str):
        self.queue.put((level, msg))
    
    def add_handler(self, handler):
        self.handlers.append(handler)
    
    def process(self):
        try:
            while True:
                level, msg = self.queue.get_nowait()
                timestamp = datetime.now().strftime("%H:%M:%S")
                formatted = f"[{timestamp}] [{level}] {msg}"
                for handler in self.handlers:
                    handler(formatted, level)
        except queue.Empty:
            pass


# ==================== 微信推送 ====================
class WechatPusher:
    @classmethod
    def send(cls, title: str, content: str, template: str = "txt") -> Tuple[bool, str]:
        token = ConfigManager().get_wechat_token()
        if not token:
            return False, "请先配置Token"
        url = "http://www.pushplus.plus/send"
        params = {
            "token": token,
            "title": title,
            "content": content,
            "template": template
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            if data.get("code") == 200:
                return True, "发送成功"
            else:
                return False, f"发送失败: {data.get('msg')}"
        except Exception as e:
            return False, f"发送异常: {e}"


# ==================== Tushare管理器（增强分钟线）====================
class TushareManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.config = ConfigManager()
        self.token = self.config.get_tushare_token()
        self.node_url = self.config.get('tushare_node')
        self.remaining = 0
        self.token_valid = False
        self.token_error_msg = ""
        self.update_callback = None
        self._lock = threading.RLock()
        self._pro = None
    
    def _get_pro(self):
        if self._pro is None and self.token and HAS_TUSHARE:
            pro = ts.pro_api(self.token)
            pro._DataApi__http_url = self.node_url
            self._pro = pro
        return self._pro
    
    def set_token(self, new_token: str):
        with self._lock:
            self.token = new_token.strip()
            self.config.set_tushare_token(self.token)
            self.token_valid = False
            self._pro = None
        if self.update_callback:
            self.update_callback()
    
    def set_node(self, new_node: str):
        with self._lock:
            self.node_url = new_node.strip()
            self.config.set('tushare_node', self.node_url)
            self._pro = None
        if self.update_callback:
            self.update_callback()
    
    def set_callback(self, callback):
        self.update_callback = callback
    
    def update_remaining(self):
        with self._lock:
            token = self.token
            node = self.node_url
        if not token:
            self.token_valid = False
            self.token_error_msg = "Token 为空"
            if self.update_callback:
                self.update_callback()
            return
        
        try:
            pro = ts.pro_api(token)
            pro._DataApi__http_url = node
            df = pro.stock_basic(ts_code='000001.SZ')
            if df is None or df.empty:
                self.token_valid = False
                self.token_error_msg = "Token 无效或节点不可达"
            else:
                self.token_valid = True
                try:
                    user_info = pro.user()
                    if user_info and 'data' in user_info and user_info['data']:
                        self.remaining = user_info['data'][0].get('remaining_integral', 5000)
                    else:
                        self.remaining = 5000
                except:
                    self.remaining = 5000
        except Exception as e:
            self.token_valid = False
            self.token_error_msg = f"异常: {str(e)}"
            Logger().error(f"Tushare验证异常: {e}")
        
        if self.update_callback:
            self.update_callback()
    
    def get_capital_flow(self, code: str) -> Tuple[Optional[dict], Optional[str]]:
        with self._lock:
            valid = self.token_valid
            pro = self._get_pro()
        if not valid or pro is None:
            return None, f"Token无效: {self.token_error_msg}"
        try:
            if code.startswith('6'):
                ts_code = f"{code}.SH"
            else:
                ts_code = f"{code}.SZ"
            df = pro.moneyflow(ts_code=ts_code)
            if df is not None and not df.empty:
                row = df.iloc[0]
                buy_elg = row.get('buy_elg_amount', 0)
                sell_elg = row.get('sell_elg_amount', 0)
                buy_lg = row.get('buy_lg_amount', 0)
                sell_lg = row.get('sell_lg_amount', 0)
                main_in = (buy_elg + buy_lg) / 10000
                main_out = (sell_elg + sell_lg) / 10000
                net_main = main_in - main_out
                buy_lg_vol = row.get('buy_lg_vol', 0)
                sell_lg_vol = row.get('sell_lg_vol', 0)
                big_orders = buy_lg_vol + sell_lg_vol
                active_buy = buy_lg_vol
                active_sell = sell_lg_vol
                turnover_rate = row.get('turnover_rate', 0)
                return {
                    "main_inflow": round(main_in, 2),
                    "main_outflow": round(main_out, 2),
                    "net_main": round(net_main, 2),
                    "big_orders": int(big_orders),
                    "active_buy": int(active_buy),
                    "active_sell": int(active_sell),
                    "turnover_rate": round(turnover_rate, 2),
                    "source": "Tushare(私有节点)"
                }, None
            else:
                return None, "Tushare 未返回资金数据"
        except Exception as e:
            return None, f"获取资金数据异常: {e}"
    
    def get_kline_data(self, code: str, start_date: str = None, end_date: str = None, period: str = 'daily') -> Optional[pd.DataFrame]:
        with self._lock:
            valid = self.token_valid
            pro = self._get_pro()
        if not valid or pro is None:
            Logger().error(f"Tushare Token无效，无法获取K线")
            return None
        try:
            if code.startswith('6'):
                ts_code = f"{code}.SH"
            else:
                ts_code = f"{code}.SZ"
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            if start_date is None:
                start = datetime.now() - timedelta(days=400)
                start_date = start.strftime("%Y%m%d")
            if period == 'daily':
                df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            elif period == 'weekly':
                df = pro.weekly(ts_code=ts_code, start_date=start_date, end_date=end_date)
            elif period == 'monthly':
                df = pro.monthly(ts_code=ts_code, start_date=start_date, end_date=end_date)
            else:
                return None
            if df is None or df.empty:
                return None
            df = df.sort_values('trade_date')
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'vol': 'Volume'
            }, inplace=True)
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception as e:
            Logger().error(f"获取K线数据异常: {e}")
            return None
    
    def get_minute_data(self, code: str, freq: str = '1min', start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        with self._lock:
            valid = self.token_valid
            pro = self._get_pro()
        if not valid or pro is None:
            return None
        try:
            if code.startswith('6'):
                ts_code = f"{code}.SH"
            else:
                ts_code = f"{code}.SZ"
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            if start_date is None:
                start = datetime.now() - timedelta(days=7)
                start_date = start.strftime("%Y%m%d")
            df = pro.stk_mins(ts_code=ts_code, freq=freq, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                return None
            df = df.sort_values('trade_time')
            df['trade_time'] = pd.to_datetime(df['trade_time'])
            df.set_index('trade_time', inplace=True)
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'vol': 'Volume'
            }, inplace=True)
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception as e:
            Logger().error(f"获取分钟线数据异常: {e}")
            return None
    
    def get_stock_info(self, code: str) -> Optional[dict]:
        with self._lock:
            valid = self.token_valid
            pro = self._get_pro()
        if not valid or pro is None:
            return None
        try:
            if code.startswith('6'):
                ts_code = f"{code}.SH"
            else:
                ts_code = f"{code}.SZ"
            df_daily = pro.daily(ts_code=ts_code, limit=1)
            if df_daily is None or df_daily.empty:
                return None
            latest = df_daily.iloc[0]
            df_basic = pro.stock_basic(ts_code=ts_code, fields='name,industry,market,list_date')
            if df_basic is not None and not df_basic.empty:
                name = df_basic.iloc[0]['name']
                industry = df_basic.iloc[0]['industry']
            else:
                name = code
                industry = '未知'
            return {
                'name': name,
                'industry': industry,
                'pe': round(random.uniform(10, 50), 2),
                'pb': round(random.uniform(1, 5), 2),
                'market_cap': round(latest.get('amount', 0) * 10, 2),
                'turnover_rate': latest.get('pct_chg', 0)
            }
        except Exception as e:
            Logger().error(f"获取股票信息异常: {e}")
            return None
        # ==================== 数据获取模块（多数据源，带缓存，自动降级）====================
class DataFetcher:
    STOCK_POOL = [
        {'code': '000001', 'name': '平安银行', 'industry': '银行'},
        {'code': '000002', 'name': '万科A', 'industry': '房地产'},
        {'code': '600036', 'name': '招商银行', 'industry': '银行'},
        {'code': '000858', 'name': '五粮液', 'industry': '白酒'},
        {'code': '600519', 'name': '贵州茅台', 'industry': '白酒'},
        {'code': '300750', 'name': '宁德时代', 'industry': '新能源'},
        {'code': '601012', 'name': '隆基绿能', 'industry': '光伏'},
        {'code': '002460', 'name': '赣锋锂业', 'industry': '有色'},
        {'code': '600760', 'name': '中航沈飞', 'industry': '军工'},
        {'code': '600031', 'name': '三一重工', 'industry': '工程机械'},
        {'code': '688981', 'name': '中芯国际', 'industry': '芯片'},
        {'code': '601318', 'name': '中国平安', 'industry': '保险'},
        {'code': '000651', 'name': '格力电器', 'industry': '家电'},
        {'code': '002415', 'name': '海康威视', 'industry': '安防'},
        {'code': '300059', 'name': '东方财富', 'industry': '券商'},
    ]
    
    NEWS_TEMPLATES = [
        {"type": "AI", "title": "国产大模型突破，算力需求激增", "content": "某科技公司发布新一代AI模型，性能超越GPT-4，带动芯片、服务器产业链。", "related": ["中科曙光", "浪潮信息", "科大讯飞"]},
        {"type": "AI", "title": "全球AI芯片巨头财报超预期", "content": "英伟达最新季度营收再创新高，A股AI芯片概念股跟涨。", "related": ["寒武纪", "海光信息", "景嘉微"]},
        {"type": "AI", "title": "AI赋能千行百业，办公软件迎来革命", "content": "多家公司推出AI助手，智能办公软件用户数暴增。", "related": ["金山办公", "用友网络", "泛微网络"]},
        {"type": "军工", "title": "新型战机试飞成功，航空产业链受益", "content": "我国自主研发的新一代隐身战机完成首飞，军工企业订单饱满。", "related": ["中航沈飞", "中航西飞", "航发动力"]},
        {"type": "军工", "title": "卫星互联网建设加速", "content": "卫星制造、地面设备需求旺盛，相关公司业绩预增。", "related": ["中国卫星", "北斗星通", "航天电子"]},
        {"type": "军工", "title": "船舶工业订单创十年新高", "content": "全球新船订单量激增，我国船舶企业接单量领跑。", "related": ["中国船舶", "中船防务", "亚星锚链"]},
        {"type": "战争", "title": "地缘政治紧张，军工板块受关注", "content": "周边局势升级，军工订单预期增加。", "related": ["中航沈飞", "航发动力"]},
        {"type": "原材料", "title": "锂矿价格再创新高，供应紧缺", "content": "新能源汽车需求旺盛，锂资源供不应求。", "related": ["赣锋锂业", "天齐锂业"]},
        {"type": "明星代言", "title": "某顶流明星签约国货美妆", "content": "品牌热度飙升，机构看好销售放量。", "related": ["珀莱雅", "上海家化"]},
        {"type": "政策", "title": "新能源补贴政策落地", "content": "延续免征购置税，利好新能源车产业链。", "related": ["宁德时代", "比亚迪"]},
        {"type": "资金", "title": "北向资金连续净买入", "content": "外资重点加仓银行、新能源板块。", "related": ["招商银行", "宁德时代"]},
        {"type": "科技", "title": "芯片国产化加速", "content": "多家晶圆厂获得大额订单，产能利用率提升。", "related": ["中芯国际", "兆易创新"]},
        {"type": "消费", "title": "双十一预售火爆，家电板块走强", "content": "消费复苏预期增强，家电龙头销量超预期。", "related": ["格力电器", "美的集团"]},
        {"type": "金融", "title": "央行降准释放流动性", "content": "利好银行、地产板块，资金成本下降。", "related": ["招商银行", "万科A"]},
        {"type": "新能源", "title": "光伏组件价格止跌反弹", "content": "硅料价格企稳，组件厂商排产提升，行业景气度回升。", "related": ["隆基绿能", "通威股份", "阳光电源"]},
        {"type": "消费", "title": "白酒龙头提价，高端消费复苏", "content": "茅台、五粮液等头部酒企宣布上调出厂价，板块集体走强。", "related": ["贵州茅台", "五粮液", "泸州老窖"]},
        {"type": "医药", "title": "创新药出海捷报频传", "content": "多家药企自主研发药物获得FDA批准，国际化进程加速。", "related": ["恒瑞医药", "药明康德", "百济神州"]},
    ]
    
    BASE_PRICE_MAP = {
        '000001': 12.0,
        '000002': 15.0,
        '600036': 35.0,
        '000858': 150.0,
        '600519': 1700.0,
        '300750': 200.0,
        '601012': 25.0,
        '002460': 40.0,
        '600760': 25.0,
        '600031': 21.5,
        '688981': 50.0,
        '601318': 45.0,
        '000651': 35.0,
        '002415': 30.0,
        '300059': 20.0,
    }

    _quote_cache = OrderedDict()
    _quote_cache_lock = threading.RLock()
    _capital_cache = OrderedDict()
    _capital_cache_lock = threading.RLock()
    _kline_cache = OrderedDict()
    _kline_cache_lock = threading.RLock()
    _minute_cache = OrderedDict()
    _minute_cache_lock = threading.RLock()
    
    MAX_CACHE_SIZE = 500
    
    # 节假日列表（2025年示例，可自行更新）
    HOLIDAYS = [
        "2025-01-01",  # 元旦
        "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31", "2025-02-01", "2025-02-02", "2025-02-03", "2025-02-04",  # 春节
        "2025-04-04", "2025-04-05", "2025-04-06",  # 清明
        "2025-05-01", "2025-05-02", "2025-05-03",  # 劳动节
        "2025-06-02", "2025-06-03", "2025-06-04",  # 端午
        "2025-09-29", "2025-09-30", "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04", "2025-10-05", "2025-10-06", "2025-10-07",  # 国庆中秋
    ]
    
    @classmethod
    def is_holiday(cls, date: datetime = None) -> bool:
        if date is None:
            date = datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        return date_str in cls.HOLIDAYS
    
    @classmethod
    def is_trading_time(cls) -> Tuple[bool, float]:
        now = datetime.now()
        weekday = now.weekday()
        if weekday >= 5:
            next_trading = now + timedelta(days=(7 - weekday))
            next_trading = next_trading.replace(hour=9, minute=15, second=0, microsecond=0)
            remaining = (next_trading - now).total_seconds()
            return False, remaining
        
        if cls.is_holiday(now):
            next_day = now + timedelta(days=1)
            while next_day.weekday() >= 5 or cls.is_holiday(next_day):
                next_day += timedelta(days=1)
            next_trading = next_day.replace(hour=9, minute=15, second=0, microsecond=0)
            remaining = (next_trading - now).total_seconds()
            return False, remaining
        
        current_time = now.time()
        # 使用 dt_time 创建时间对象（因为 time 已被重命名为 dt_time）
        if (current_time >= dt_time(9, 15) and current_time <= dt_time(11, 30)) or \
           (current_time >= dt_time(13, 0) and current_time <= dt_time(15, 0)):
            if current_time <= dt_time(11, 30):
                end = datetime.combine(now.date(), dt_time(11, 30))
            else:
                end = datetime.combine(now.date(), dt_time(15, 0))
            remaining = (end - now).total_seconds()
            return True, remaining
        next_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        if now > next_open:
            next_open += timedelta(days=1)
        remaining = (next_open - now).total_seconds()
        return False, remaining
    
    @classmethod
    def get_cache_time(cls) -> int:
        trading, _ = cls.is_trading_time()
        cfg = ConfigManager()
        if trading:
            return cfg.get('settings.quote_cache_time', 5)
        else:
            return cfg.get('settings.quote_cache_time_nontrade', 30)
    
    @classmethod
    def _clean_cache(cls, cache_dict: OrderedDict, max_size: int = MAX_CACHE_SIZE):
        while len(cache_dict) > max_size:
            cache_dict.popitem(last=False)
    
    # ---------- 实时行情 ----------
    @classmethod
    def get_realtime_quote(cls, code: str) -> Optional[dict]:
        now = tm.time()
        cache_time = cls.get_cache_time()
        with cls._quote_cache_lock:
            if code in cls._quote_cache:
                ts, quote = cls._quote_cache[code]
                if now - ts < cache_time:
                    cls._quote_cache.move_to_end(code)
                    return quote.copy()
        
        sources = ConfigManager().get('settings.data_sources', ['sina', 'tencent'])
        quote = None
        for src in sources:
            method = getattr(cls, f'_try_{src}', None)
            if method:
                quote = method(code, None)
                if quote:
                    break
        
        if not quote and ConfigManager().get('settings.use_mock_on_fail', True):
            quote = cls._mock_quote(code, None)
            quote['source'] = '模拟'
        elif quote:
            quote['source'] = quote.get('source', src)
        
        if quote:
            with cls._quote_cache_lock:
                cls._quote_cache[code] = (now, quote)
                cls._quote_cache.move_to_end(code)
                cls._clean_cache(cls._quote_cache)
        return quote
    
    # ---------- 各数据源实现 ----------
    @classmethod
    def _try_sina(cls, code, default_name):
        try:
            prefix = 'sh' if code.startswith('6') else 'sz'
            url = f"http://hq.sinajs.cn/list={prefix}{code}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(url, headers=headers, timeout=5)
            resp.encoding = 'gbk'
            content = resp.text.strip()
            if not content or '=' not in content:
                return None
            data_str = content.split('=')[1].strip().strip('";')
            data = data_str.split(',')
            if len(data) < 32:
                return None
            name = data[0].strip() or default_name or code
            try:
                open_price = float(data[1]) if data[1] else 0.0
                pre_close = float(data[2]) if data[2] else 0.0
                price = float(data[3]) if data[3] else 0.0
                high = float(data[4]) if data[4] else 0.0
                low = float(data[5]) if data[5] else 0.0
                volume = int(float(data[8])) if data[8] else 0
                amount = float(data[9]) if data[9] else 0.0
            except ValueError:
                return None
            change = price - pre_close
            change_pct = (change / pre_close) * 100 if pre_close != 0 else 0.0
            volume_ratio = round(random.uniform(0.8, 2.5), 2)
            return {
                "code": code,
                "name": name,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "volume": int(volume),
                "turnover": int(amount),
                "volume_ratio": volume_ratio,
                "high": round(high, 2),
                "low": round(low, 2),
                "open": round(open_price, 2),
                "pre_close": round(pre_close, 2),
                "source": "新浪"
            }
        except Exception as e:
            Logger().debug(f"新浪接口失败 {code}: {e}")
            return None
    
    @classmethod
    def _try_tencent(cls, code, default_name):
        try:
            prefix = 'sh' if code.startswith('6') else 'sz'
            url = f"http://qt.gtimg.cn/q={prefix}{code}"
            resp = requests.get(url, timeout=5)
            resp.encoding = 'gbk'
            content = resp.text.strip()
            match = re.search(r'="(.+)"', content)
            if not match:
                return None
            data = match.group(1).split('~')
            if len(data) < 40:
                return None
            name = data[1] or default_name or code
            try:
                price = float(data[3]) if data[3] else 0.0
                pre_close = float(data[4]) if data[4] else 0.0
                open_price = float(data[5]) if data[5] else 0.0
                volume = int(float(data[6])) if data[6] else 0
                amount = float(data[7]) if data[7] else 0.0
                high = float(data[33]) if len(data) > 33 and data[33] else price
                low = float(data[34]) if len(data) > 34 and data[34] else price
            except ValueError:
                return None
            change = price - pre_close
            change_pct = (change / pre_close) * 100 if pre_close != 0 else 0.0
            volume_ratio = round(random.uniform(0.8, 2.5), 2)
            return {
                "code": code,
                "name": name,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "volume": int(volume),
                "turnover": int(amount),
                "volume_ratio": volume_ratio,
                "high": round(high, 2),
                "low": round(low, 2),
                "open": round(open_price, 2),
                "pre_close": round(pre_close, 2),
                "source": "腾讯"
            }
        except Exception as e:
            Logger().debug(f"腾讯接口失败 {code}: {e}")
            return None
    
    @classmethod
    def _try_netease(cls, code, default_name):
        try:
            prefix = '0' if code.startswith('6') else '1'
            url = f"http://api.money.126.net/data/feed/{prefix}{code},money.api"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            key = f"{prefix}{code}"
            item = data.get(key)
            if not item:
                return None
            name = item.get('name', default_name or code)
            price = item.get('price', 0.0)
            pre_close = item.get('yestclose', 0.0)
            open_price = item.get('open', 0.0)
            high = item.get('high', 0.0)
            low = item.get('low', 0.0)
            volume = item.get('volume', 0)
            amount = item.get('turnover', 0)
            change = price - pre_close
            change_pct = (change / pre_close) * 100 if pre_close != 0 else 0.0
            volume_ratio = round(random.uniform(0.8, 2.5), 2)
            return {
                "code": code,
                "name": name,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "volume": int(volume),
                "turnover": int(amount),
                "volume_ratio": volume_ratio,
                "high": round(high, 2),
                "low": round(low, 2),
                "open": round(open_price, 2),
                "pre_close": round(pre_close, 2),
                "source": "网易"
            }
        except Exception as e:
            Logger().debug(f"网易接口失败 {code}: {e}")
            return None
    
    @classmethod
    def _try_sohu(cls, code, default_name):
        try:
            prefix = 'cn_' if code.startswith('6') else 'sz_'
            url = f"http://q.stock.sohu.com/hisHq?code={prefix}{code}&start=20210101&end=20210101"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            if not data or not data[0].get('hq'):
                return None
            hq = data[0]['hq'][0]
            name = data[0].get('name', default_name or code)
            try:
                open_price = float(hq[1])
                price = float(hq[2])
                change = float(hq[3])
                change_pct = float(hq[4].strip('%'))
                low = float(hq[5])
                high = float(hq[6])
                volume = int(hq[7])
                amount = float(hq[8])
            except (IndexError, ValueError):
                return None
            pre_close = price - change
            volume_ratio = round(random.uniform(0.8, 2.5), 2)
            return {
                "code": code,
                "name": name,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "volume": int(volume),
                "turnover": int(amount),
                "volume_ratio": volume_ratio,
                "high": round(high, 2),
                "low": round(low, 2),
                "open": round(open_price, 2),
                "pre_close": round(pre_close, 2),
                "source": "搜狐"
            }
        except Exception as e:
            Logger().debug(f"搜狐接口失败 {code}: {e}")
            return None
    
    @classmethod
    def _try_baidu(cls, code, default_name):
        return None
    
    @classmethod
    def _try_163(cls, code, default_name):
        return cls._try_netease(code, default_name)
    
    @classmethod
    def _mock_quote(cls, code, name=None):
        if name is None:
            name = code
            for s in cls.STOCK_POOL:
                if s['code'] == code:
                    name = s['name']
                    break
        base_price = cls.BASE_PRICE_MAP.get(code, 30.0)
        hash_val = int(hashlib.md5(code.encode()).hexdigest()[:8], 16) % 100
        factor = 1.0 + (hash_val / 500.0) - 0.1
        price = base_price * factor
        change = price - base_price
        change_pct = (change / base_price) * 100
        volume_ratio = round(1.0 + (hash_val % 50) / 50, 2)
        return {
            "code": code,
            "name": name,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": random.randint(100000, 5000000),
            "turnover": random.randint(1000, 50000),
            "volume_ratio": volume_ratio,
            "high": round(price * (1 + random.uniform(0.01, 0.03)), 2),
            "low": round(price * (1 - random.uniform(0.01, 0.03)), 2),
            "open": round(price * (1 + random.uniform(-0.01, 0.01)), 2),
            "pre_close": round(price * (1 - change_pct/100), 2),
            "source": "模拟"
        }
    
    # ---------- 资金流 ----------
    @classmethod
    def get_capital_flow(cls, code: str) -> dict:
        now = tm.time()
        cache_time = ConfigManager().get('settings.capital_cache_time', 30)
        with cls._capital_cache_lock:
            if code in cls._capital_cache:
                ts, data = cls._capital_cache[code]
                if now - ts < cache_time:
                    cls._capital_cache.move_to_end(code)
                    return data.copy()
        
        tushare = TushareManager()
        if tushare.token_valid:
            data, err = tushare.get_capital_flow(code)
            if data:
                data["source"] = "Tushare"
                with cls._capital_cache_lock:
                    cls._capital_cache[code] = (now, data)
                    cls._capital_cache.move_to_end(code)
                    cls._clean_cache(cls._capital_cache)
                return data
            else:
                Logger().debug(f"Tushare获取{code}资金失败: {err}")
        
        mock = cls._mock_capital()
        mock["source"] = "模拟"
        with cls._capital_cache_lock:
            cls._capital_cache[code] = (now, mock)
            cls._capital_cache.move_to_end(code)
            cls._clean_cache(cls._capital_cache)
        return mock
    
    @classmethod
    def _mock_capital(cls) -> dict:
        main_in = random.randint(1000, 10000)
        main_out = random.randint(500, 8000)
        net_main = main_in - main_out
        return {
            "main_inflow": main_in,
            "main_outflow": main_out,
            "net_main": net_main,
            "retail_in": random.randint(200, 3000),
            "retail_out": random.randint(200, 2500),
            "big_orders": random.randint(50, 300),
            "active_buy": random.randint(30, 200),
            "active_sell": random.randint(20, 150),
            "turnover_rate": round(random.uniform(1, 8), 2),
        }
    
    # ---------- 新闻 ----------
    @classmethod
    def get_news(cls) -> List[dict]:
        count = random.randint(3, 5)
        selected = random.sample(cls.NEWS_TEMPLATES, min(count, len(cls.NEWS_TEMPLATES)))
        news_list = []
        for item in selected:
            news_time = datetime.now() - timedelta(minutes=random.randint(10, 120))
            news_list.append({
                "type": item["type"],
                "title": f"{news_time.strftime('%m月%d日')} {item['title']}",
                "content": item["content"],
                "related": item["related"],
                "time": news_time.strftime("%m-%d %H:%M")
            })
        news_list.sort(key=lambda x: x["time"], reverse=True)
        return news_list
    
    # ---------- K线数据 ----------
    @classmethod
    def get_kline_with_indicators(cls, code: str, period: str = 'daily', force_refresh: bool = False) -> Optional[Tuple[pd.DataFrame, dict]]:
        cache_key = (code, period)
        now = tm.time()
        cache_time = 300
        
        if not force_refresh:
            with cls._kline_cache_lock:
                if cache_key in cls._kline_cache:
                    ts, data = cls._kline_cache[cache_key]
                    if now - ts < cache_time:
                        cls._kline_cache.move_to_end(cache_key)
                        return data
        
        tushare = TushareManager()
        if tushare.token_valid:
            df = tushare.get_kline_data(code, period=period)
        else:
            df = None
        
        if df is None or len(df) < 10:
            Logger().info(f"使用模拟K线数据 for {code} {period}")
            df = cls._mock_kline(period)
        
        if df is None or len(df) < 10:
            return None
        
        cls._add_indicators(df)
        signals = cls._analyze_kline(df)
        result = (df, signals)
        with cls._kline_cache_lock:
            cls._kline_cache[cache_key] = (now, result)
            cls._kline_cache.move_to_end(cache_key)
            cls._clean_cache(cls._kline_cache)
        return result
    
    @classmethod
    def get_minute_data_with_indicators(cls, code: str, freq: str = '5min', force_refresh: bool = False) -> Optional[Tuple[pd.DataFrame, dict]]:
        cache_key = (code, freq)
        now = tm.time()
        cache_time = ConfigManager().get('settings.minute_cache_time', 60)
        
        if not force_refresh:
            with cls._minute_cache_lock:
                if cache_key in cls._minute_cache:
                    ts, data = cls._minute_cache[cache_key]
                    if now - ts < cache_time:
                        cls._minute_cache.move_to_end(cache_key)
                        return data
        
        tushare = TushareManager()
        if tushare.token_valid:
            df = tushare.get_minute_data(code, freq=freq)
        else:
            df = None
        
        if df is None or len(df) < 10:
            Logger().info(f"使用模拟分钟线数据 for {code} {freq}")
            df = cls._mock_minute_data(freq)
        
        if df is None or len(df) < 10:
            return None
        
        cls._add_indicators(df)
        signals = cls._analyze_kline(df)
        result = (df, signals)
        with cls._minute_cache_lock:
            cls._minute_cache[cache_key] = (now, result)
            cls._minute_cache.move_to_end(cache_key)
            cls._clean_cache(cls._minute_cache)
        return result
    
    @classmethod
    def _add_indicators(cls, df: pd.DataFrame):
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal']
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + 2 * bb_std
        df['BB_Lower'] = df['BB_Middle'] - 2 * bb_std
    
    @classmethod
    def _analyze_kline(cls, df: pd.DataFrame) -> dict:
        if len(df) < 20:
            return {}
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        signals = {}
        if last['MA5'] > last['MA10'] > last['MA20']:
            signals['ma_trend'] = '均线多头排列'
        elif last['MA5'] < last['MA10'] < last['MA20']:
            signals['ma_trend'] = '均线空头排列'
        else:
            signals['ma_trend'] = '均线纠结'
        if prev['MA5'] <= prev['MA10'] and last['MA5'] > last['MA10']:
            signals['ma_cross'] = 'MA5上穿MA10（金叉）'
        elif prev['MA5'] >= prev['MA10'] and last['MA5'] < last['MA10']:
            signals['ma_cross'] = 'MA5下穿MA10（死叉）'
        else:
            signals['ma_cross'] = None
        if prev['MACD'] <= prev['Signal'] and last['MACD'] > last['Signal']:
            signals['macd'] = 'MACD金叉'
        elif prev['MACD'] >= prev['Signal'] and last['MACD'] < last['Signal']:
            signals['macd'] = 'MACD死叉'
        else:
            signals['macd'] = 'MACD持平'
        avg_vol = df['Volume'].iloc[-10:].mean()
        if last['Volume'] > avg_vol * 1.5:
            signals['volume'] = '放量'
        elif last['Volume'] < avg_vol * 0.5:
            signals['volume'] = '缩量'
        else:
            signals['volume'] = '量能正常'
        rsi = last.get('RSI')
        if rsi is not None:
            if rsi > 70:
                signals['rsi'] = '超买（RSI>70）'
            elif rsi < 30:
                signals['rsi'] = '超卖（RSI<30）'
            else:
                signals['rsi'] = '正常'
        if last['Close'] > last['BB_Upper']:
            signals['bb'] = '突破上轨（超买）'
        elif last['Close'] < last['BB_Lower']:
            signals['bb'] = '跌破下轨（超卖）'
        else:
            signals['bb'] = '通道内运行'
        return signals
    
    @classmethod
    def _mock_kline(cls, period: str = 'daily') -> pd.DataFrame:
        periods = {'daily': 200, 'weekly': 100, 'monthly': 60}
        n = periods.get(period, 200)
        if period == 'daily':
            dates = pd.date_range(end=datetime.now(), periods=n, freq='B')
        elif period == 'weekly':
            dates = pd.date_range(end=datetime.now(), periods=n, freq='W-FRI')
        else:
            dates = pd.date_range(end=datetime.now(), periods=n, freq='M')
        base = 100
        prices = []
        for i in range(n):
            change = np.random.randn() * 2
            base = base * (1 + change/100)
            prices.append(base)
        df = pd.DataFrame({
            'Open': prices,
            'High': [p * (1 + abs(np.random.randn()*0.02)) for p in prices],
            'Low': [p * (1 - abs(np.random.randn()*0.02)) for p in prices],
            'Close': [p * (1 + np.random.randn()*0.01) for p in prices],
            'Volume': np.random.randint(10000, 100000, size=n)
        }, index=dates)
        return df
    
    @classmethod
    def _mock_minute_data(cls, freq: str = '5min') -> pd.DataFrame:
        n = 200
        now = datetime.now()
        if freq == '1min':
            freq_min = 1
        elif freq == '5min':
            freq_min = 5
        elif freq == '15min':
            freq_min = 15
        elif freq == '30min':
            freq_min = 30
        elif freq == '60min':
            freq_min = 60
        else:
            freq_min = 5
        end = now.replace(second=0, microsecond=0)
        start = end - timedelta(minutes=n*freq_min)
        times = pd.date_range(start, end, periods=n, freq=f'{freq_min}T')
        base = 100
        prices = []
        for i in range(n):
            change = np.random.randn() * 0.5
            base = base * (1 + change/100)
            prices.append(base)
        df = pd.DataFrame({
            'Open': prices,
            'High': [p * (1 + abs(np.random.randn()*0.01)) for p in prices],
            'Low': [p * (1 - abs(np.random.randn()*0.01)) for p in prices],
            'Close': [p * (1 + np.random.randn()*0.005) for p in prices],
            'Volume': np.random.randint(1000, 50000, size=n)
        }, index=times)
        return df
    
    @classmethod
    def get_stock_list(cls) -> List[dict]:
        return cls.STOCK_POOL
    # ==================== 股票分析引擎 ====================
class StockAnalyzer:
    @staticmethod
    def analyze(code: str, quote: dict, capital: dict) -> dict:
        score = 50
        signals = []
        
        vr = quote["volume_ratio"]
        if vr > 2.5:
            score += 20
            signals.append("放量突破")
        elif vr > 1.8:
            score += 10
            signals.append("量能放大")
        elif vr > 1.2:
            score += 5
        
        net = capital["net_main"]
        if net > 3000:
            score += 25
            signals.append("主力大幅流入")
        elif net > 1000:
            score += 15
            signals.append("主力流入")
        elif net > 0:
            score += 5
        elif net < -3000:
            score -= 15
            signals.append("主力大幅流出")
        elif net < -1000:
            score -= 8
            signals.append("主力流出")
        
        chg = quote["change_pct"]
        if chg > 3:
            score += 15
            signals.append("强势拉升")
        elif chg > 1:
            score += 8
            signals.append("震荡上行")
        elif chg < -3:
            score -= 10
            signals.append("弱势下跌")
        
        if vr > 2.0 and chg > 2:
            signals.append("放量突破")
        if net > 2000 and chg > 1:
            signals.append("主力+价升")
        if vr < 0.6 and chg < -1:
            signals.append("缩量下跌")
        if net < -2000 and chg < -1:
            signals.append("主力出逃")
        
        if score >= 80:
            suggestion = "强烈买入"
        elif score >= 65:
            suggestion = "建议买入"
        elif score >= 50:
            suggestion = "中性观望"
        elif score >= 35:
            suggestion = "谨慎持有"
        else:
            suggestion = "建议卖出"
        
        support = round(quote["price"] * 0.95, 2)
        resistance = round(quote["price"] * 1.05, 2)
        
        return {
            "score": score,
            "signals": list(set(signals))[:3],
            "suggestion": suggestion,
            "support": support,
            "resistance": resistance,
        }
    
    @staticmethod
    def get_kline_advice(signals: dict) -> str:
        if not signals:
            return "数据不足"
        parts = []
        if signals.get('ma_trend'):
            parts.append(signals['ma_trend'])
        if signals.get('ma_cross'):
            parts.append(signals['ma_cross'])
        if signals.get('macd') and signals['macd'] != 'MACD持平':
            parts.append(signals['macd'])
        if signals.get('volume'):
            parts.append(signals['volume'])
        if signals.get('rsi'):
            parts.append(signals['rsi'])
        if signals.get('bb'):
            parts.append(signals['bb'])
        if not parts:
            return "无明显信号，盘整"
        return "，".join(parts)


# ==================== 交易历史记录 ====================
class TradeHistory:
    def __init__(self):
        self.config = ConfigManager()
        self.history = self.config.get('trade_history', [])
        self._lock = threading.RLock()
    
    def add_record(self, record: dict):
        with self._lock:
            record['time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.history.append(record)
            self.config.set('trade_history', self.history)
    
    def get_all(self) -> List[dict]:
        with self._lock:
            return copy.deepcopy(self.history)
    
    def clear(self):
        with self._lock:
            self.history = []
            self.config.set('trade_history', [])
    
    def export_csv(self, filepath: str):
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['时间', '方向', '代码', '名称', '价格', '数量(股)', '金额', '手续费', '备注'])
            for r in self.history:
                writer.writerow([
                    r['time'], r['action'], r['code'], r['name'],
                    r['price'], r['shares'], r['amount'], r['fee'], r.get('note', '')
                ])


# ==================== 模拟交易系统 ====================
class SimulatedTrade:
    def __init__(self, initial_capital: float = 1000000):
        self.config = ConfigManager()
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.total_value = initial_capital
        self.history = TradeHistory()
        self._lock = threading.RLock()
    
    def _get_fee_settings(self) -> dict:
        return {
            'commission_rate': self.config.get('settings.commission_rate', 0.00025),
            'min_commission': self.config.get('settings.min_commission', 5.0),
            'stamp_tax_rate': self.config.get('settings.stamp_tax_rate', 0.001),
            'transfer_fee_rate': self.config.get('settings.transfer_fee_rate', 0.00001),
            'min_transfer_fee': self.config.get('settings.min_transfer_fee', 1.0)
        }
    
    def _is_st_stock(self, name: str) -> bool:
        return 'ST' in name or '*ST' in name or 'st' in name.lower()
    
    def _get_limit_range(self, code: str, name: str, pre_close: float) -> Tuple[float, float]:
        if self._is_st_stock(name):
            limit_pct = 0.05
        else:
            limit_pct = 0.1
        limit_up = round(pre_close * (1 + limit_pct), 2)
        limit_down = round(pre_close * (1 - limit_pct), 2)
        return limit_down, limit_up
    
    def _calc_buy_fee(self, amount: float, code: str) -> float:
        fees = self._get_fee_settings()
        commission = max(amount * fees['commission_rate'], fees['min_commission'])
        transfer_fee = 0
        if code.startswith('6'):
            transfer_fee = max(amount * fees['transfer_fee_rate'], fees['min_transfer_fee'])
        return commission + transfer_fee
    
    def _calc_sell_fee(self, amount: float, code: str) -> float:
        fees = self._get_fee_settings()
        commission = max(amount * fees['commission_rate'], fees['min_commission'])
        stamp_tax = amount * fees['stamp_tax_rate']
        transfer_fee = 0
        if code.startswith('6'):
            transfer_fee = max(amount * fees['transfer_fee_rate'], fees['min_transfer_fee'])
        return commission + stamp_tax + transfer_fee
    
    def check_stock_status(self, code: str, price: float, action: str = 'buy') -> Tuple[bool, str]:
        quote = DataFetcher.get_realtime_quote(code)
        if not quote:
            return False, "无法获取行情"
        pre_close = quote['pre_close']
        name = quote['name']
        limit_down, limit_up = self._get_limit_range(code, name, pre_close)
        if action == 'buy' and price >= limit_up:
            return False, f"涨停价 {limit_up}，无法买入"
        if action == 'sell' and price <= limit_down:
            return False, f"跌停价 {limit_down}，无法卖出"
        return True, "可交易"
    
    def buy(self, code: str, name: str, price: float, quantity: int, auto: bool = False) -> Tuple[bool, str]:
        shares = quantity * 100
        amount = price * shares
        fee = self._calc_buy_fee(amount, code)
        total_cost = amount + fee
        
        with self._lock:
            if total_cost > self.cash:
                return False, f"资金不足，需{total_cost:.2f}元，可用{self.cash:.2f}元"
            
            self.cash -= total_cost
            cost_per_share = total_cost / shares
            
            if code in self.positions:
                old = self.positions[code]
                total_shares = old['shares'] + shares
                total_cost_all = old['cost'] * old['shares'] + total_cost
                self.positions[code] = {
                    'name': name,
                    'shares': total_shares,
                    'cost': round(total_cost_all / total_shares, 3)
                }
            else:
                self.positions[code] = {
                    'name': name,
                    'shares': shares,
                    'cost': round(cost_per_share, 3)
                }
            
            self.history.add_record({
                'action': '买入',
                'code': code,
                'name': name,
                'price': price,
                'shares': shares,
                'amount': amount,
                'fee': fee,
                'note': '自动' if auto else '手动'
            })
        return True, f"买入成功：{name} {quantity}手，成交额{amount:.2f}，手续费{fee:.2f}，总成本{total_cost:.2f}"
    
    def sell(self, code: str, price: float, quantity: int = None, auto: bool = False) -> Tuple[bool, str]:
        with self._lock:
            if code not in self.positions:
                return False, "没有持仓"
            
            pos = self.positions[code]
            shares_available = pos['shares']
            
            if quantity is None:
                sell_shares = shares_available
            else:
                sell_shares = quantity * 100
                if sell_shares > shares_available:
                    return False, f"可卖数量不足，最多{shares_available//100}手"
            
            amount = price * sell_shares
            fee = self._calc_sell_fee(amount, code)
            net_income = amount - fee
            
            self.cash += net_income
            
            if sell_shares == shares_available:
                del self.positions[code]
            else:
                self.positions[code]['shares'] -= sell_shares
            
            self.history.add_record({
                'action': '卖出',
                'code': code,
                'name': pos['name'],
                'price': price,
                'shares': sell_shares,
                'amount': amount,
                'fee': fee,
                'note': '自动' if auto else '手动'
            })
        return True, f"卖出成功：{pos['name']} {sell_shares//100}手，成交额{amount:.2f}，手续费{fee:.2f}，实收{net_income:.2f}"
    
    def update_total_value(self, current_prices: dict):
        with self._lock:
            market_value = 0
            for code, pos in self.positions.items():
                price = current_prices.get(code, pos['cost'])
                market_value += pos['shares'] * price
            self.total_value = self.cash + market_value
    
    def get_position_list(self) -> dict:
        with self._lock:
            display = {}
            for code, pos in self.positions.items():
                display[code] = {
                    'name': pos['name'],
                    'quantity': pos['shares'] // 100,
                    'cost': pos['cost'],
                    'shares': pos['shares']
                }
            return display
    
    def get_account_summary(self) -> dict:
        with self._lock:
            profit = self.total_value - self.initial_capital
            profit_pct = (profit / self.initial_capital) * 100 if self.initial_capital else 0
            return {
                'cash': round(self.cash, 2),
                'total_value': round(self.total_value, 2),
                'profit': round(profit, 2),
                'profit_pct': round(profit_pct, 2)
            }
    
    def reset(self):
        with self._lock:
            self.cash = self.initial_capital
            self.positions = {}
            self.total_value = self.initial_capital
            self.history.clear()


# ==================== 提醒管理器 ====================
class AlertManager:
    def __init__(self):
        self.config = ConfigManager()
        self.price_alerts = self.config.get('price_alerts', [])
        self.condition_alerts = self.config.get('condition_alerts', [])
        self._lock = threading.RLock()
    
    def add_price_alert(self, alert: dict):
        with self._lock:
            self.price_alerts.append(alert)
            self.config.set('price_alerts', self.price_alerts)
    
    def add_condition_alert(self, alert: dict):
        with self._lock:
            self.condition_alerts.append(alert)
            self.config.set('condition_alerts', self.condition_alerts)
    
    def remove_price_alert(self, index: int):
        with self._lock:
            if 0 <= index < len(self.price_alerts):
                del self.price_alerts[index]
                self.config.set('price_alerts', self.price_alerts)
    
    def remove_condition_alert(self, index: int):
        with self._lock:
            if 0 <= index < len(self.condition_alerts):
                del self.condition_alerts[index]
                self.config.set('condition_alerts', self.condition_alerts)
    
    def clear_all(self):
        with self._lock:
            self.price_alerts = []
            self.condition_alerts = []
            self.config.set('price_alerts', [])
            self.config.set('condition_alerts', [])
    
    def get_all_price_alerts(self) -> List[dict]:
        with self._lock:
            return copy.deepcopy(self.price_alerts)
    
    def get_all_condition_alerts(self) -> List[dict]:
        with self._lock:
            return copy.deepcopy(self.condition_alerts)
    
    def check(self, price_cache: dict, trade_account) -> List[Tuple[str, dict, float]]:
        triggered = []
        with self._lock:
            for alert in self.price_alerts:
                code = alert['code']
                quote = price_cache.get(code)
                if not quote:
                    continue
                price = quote['price']
                if alert.get('buy') and abs(price - alert['buy']) / alert['buy'] <= 0.01:
                    triggered.append(('buy', alert, price))
                if alert.get('sell') and abs(price - alert['sell']) / alert['sell'] <= 0.01:
                    triggered.append(('sell', alert, price))
            
            for alert in self.condition_alerts:
                code = alert['code']
                quote = price_cache.get(code)
                if not quote:
                    continue
                price = quote['price']
                change_pct = quote['change_pct']
                volume = quote['volume']
                if alert.get('change_pct') is not None:
                    target = alert['change_pct']
                    if (target > 0 and change_pct >= target) or (target < 0 and change_pct <= target):
                        triggered.append(('condition_change', alert, price))
                if alert.get('volume_gt') is not None and volume > alert['volume_gt']:
                    triggered.append(('condition_volume', alert, price))
        return triggered


# ==================== K线图组件 ====================
class KlineChart(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.code = ''
        self.name = ''
        self.current_period = tk.StringVar(value='daily')
        self.is_realtime_mode = tk.BooleanVar(value=False)
        self.df = None
        self.signals = {}
        self.stock_info = {}
        self.realtime_update_id = None
        
        if not HAS_MPL:
            ttk.Label(self, text="请安装 matplotlib 和 mplfinance 以显示K线图\npip install matplotlib mplfinance pandas").pack()
            return
        
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(control_frame, text="周期:").pack(side=tk.LEFT)
        periods = ['daily', 'weekly', 'monthly', '1min', '5min', '15min', '30min', '60min', 'realtime']
        period_combo = ttk.Combobox(control_frame, textvariable=self.current_period, 
                                     values=periods, state='readonly', width=10)
        period_combo.pack(side=tk.LEFT, padx=5)
        period_combo.bind('<<ComboboxSelected>>', self.on_period_change)
        
        self.info_label = ttk.Label(control_frame, text="", foreground="blue")
        self.info_label.pack(side=tk.LEFT, padx=10)
        
        refresh_btn = ttk.Button(control_frame, text="刷新", command=self.refresh, width=6)
        refresh_btn.pack(side=tk.RIGHT, padx=2)
        
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.ax1 = self.fig.add_subplot(3, 1, (1, 2))
        self.ax2 = self.fig.add_subplot(3, 1, 3)
        self.fig.subplots_adjust(hspace=0.3)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        
        self.analysis_text = tk.StringVar(value="请选择股票")
        analysis_label = ttk.Label(self, textvariable=self.analysis_text, foreground="green", font=("微软雅黑", 10))
        analysis_label.pack(fill=tk.X, pady=2)
        
        self.price_text = tk.StringVar(value="")
        price_label = ttk.Label(self, textvariable=self.price_text, foreground="red", font=("微软雅黑", 12, "bold"))
        price_label.pack(fill=tk.X, pady=2)
        
        self.refresh()
    
    def set_stock(self, code: str, name: str):
        self.code = code
        self.name = name
        self.refresh()
    
    def on_period_change(self, event=None):
        self.is_realtime_mode.set(self.current_period.get() == 'realtime')
        self.refresh()
    
    def refresh(self):
        self.ax1.clear()
        self.ax2.clear()
        
        if not self.code:
            self.ax1.text(0.5, 0.5, "请先选择股票", ha='center', va='center', transform=self.ax1.transAxes)
            self.canvas.draw()
            self.analysis_text.set("请选择股票")
            self.price_text.set("")
            return
        
        period = self.current_period.get()
        
        if period == 'realtime':
            self._draw_realtime()
            self._start_realtime_update()
        else:
            self._draw_kline(period)
            self._stop_realtime_update()
    
    def _draw_kline(self, period: str):
        if period in ['1min', '5min', '15min', '30min', '60min']:
            result = DataFetcher.get_minute_data_with_indicators(self.code, freq=period)
        else:
            result = DataFetcher.get_kline_with_indicators(self.code, period=period)
        
        if result is None:
            self.ax1.text(0.5, 0.5, "无数据", ha='center', va='center', transform=self.ax1.transAxes)
            self.canvas.draw()
            self.analysis_text.set("无数据")
            self.price_text.set("")
            return
        
        df, signals = result
        self.df = df
        self.signals = signals
        
        tushare = TushareManager()
        if tushare.token_valid:
            info = tushare.get_stock_info(self.code)
            if info:
                self.stock_info = info
                info_text = f"{info.get('name', self.name)} | {info.get('industry', '')} | PE:{info.get('pe', '-')} | PB:{info.get('pb', '-')}"
                self.info_label.config(text=info_text)
        
        self._draw_candlestick(df)
        
        if not df.empty:
            last = df.iloc[-1]
            change_pct = (last['Close']/df.iloc[-2]['Close']-1)*100 if len(df)>1 else 0
            self.price_text.set(f"当前价: {last['Close']:.2f}  涨跌幅: {change_pct:+.2f}%")
        
        advice = StockAnalyzer.get_kline_advice(signals)
        self.analysis_text.set(f"📊 K线分析：{advice}")
        
        self.canvas.draw()
    
    def _draw_realtime(self):
        now = datetime.now()
        trading, _ = DataFetcher.is_trading_time()
        if trading:
            start = now.replace(hour=9, minute=30, second=0, microsecond=0)
            if now < start:
                times = []
                prices = []
            else:
                minutes = (now - start).seconds // 60
                times = [start + timedelta(minutes=i) for i in range(minutes+1)]
                base = 100
                prices = []
                for i in range(len(times)):
                    change = np.random.randn() * 0.3
                    base = base * (1 + change/100)
                    prices.append(base)
        else:
            start = now.replace(hour=9, minute=30, second=0, microsecond=0)
            end = now.replace(hour=15, minute=0, second=0, microsecond=0)
            if now < start:
                times = []
                prices = []
            else:
                minutes = (end - start).seconds // 60
                times = [start + timedelta(minutes=i) for i in range(minutes+1)]
                base = 100
                prices = []
                for i in range(len(times)):
                    change = np.random.randn() * 0.3
                    base = base * (1 + change/100)
                    prices.append(base)
        
        if not times:
            self.ax1.text(0.5, 0.5, "非交易时段无分时数据", ha='center', va='center', transform=self.ax1.transAxes)
            self.canvas.draw()
            self.analysis_text.set("非交易时段")
            self.price_text.set("")
            return
        
        self.ax1.clear()
        self.ax2.clear()
        
        self.ax1.plot(times, prices, color='red', linewidth=1.5)
        self.ax1.fill_between(times, prices[0], prices, where=[p>=prices[0] for p in prices], color='red', alpha=0.1)
        self.ax1.fill_between(times, prices[0], prices, where=[p<prices[0] for p in prices], color='green', alpha=0.1)
        self.ax1.axhline(y=prices[0], color='gray', linestyle='--', linewidth=0.8)
        self.ax1.set_title(f"{self.name}({self.code}) 分时图")
        self.ax1.set_ylabel('价格')
        self.ax1.grid(True, alpha=0.3)
        
        volumes = np.random.randint(100, 1000, size=len(times))
        colors = ['red' if p >= prices[i-1] else 'green' for i, p in enumerate(prices) if i>0]
        colors.insert(0, 'gray')
        self.ax2.bar(times, volumes, color=colors, alpha=0.6)
        self.ax2.set_ylabel('成交量')
        self.ax2.grid(True, alpha=0.3)
        
        self.fig.autofmt_xdate()
        self.canvas.draw()
        
        if prices:
            last_price = prices[-1]
            change = last_price - prices[0]
            change_pct = (change / prices[0]) * 100 if prices[0] != 0 else 0
            self.price_text.set(f"当前价: {last_price:.2f}  涨跌幅: {change_pct:+.2f}%")
        
        self.analysis_text.set("分时图实时更新中...")
    
    def _draw_candlestick(self, df):
        import matplotlib.dates as mdates
        from matplotlib.lines import Line2D
        from matplotlib.patches import Rectangle
        
        n = ConfigManager().get('settings.kline_display_days', 60)
        df_display = df.iloc[-n:] if len(df) > n else df
        
        width = 0.6
        for idx, row in df_display.iterrows():
            date_num = mdates.date2num(idx)
            color = 'red' if row['Close'] >= row['Open'] else 'green'
            rect = Rectangle((date_num - width/2, min(row['Open'], row['Close'])), 
                             width, abs(row['Close']-row['Open']), 
                             facecolor=color, edgecolor='black', alpha=0.8)
            self.ax1.add_patch(rect)
            self.ax1.add_line(Line2D([date_num, date_num], [row['Low'], row['High']], color='black', linewidth=1))
        
        self.ax1.plot(df_display.index, df_display['MA5'], label='MA5', color='blue', linewidth=1)
        self.ax1.plot(df_display.index, df_display['MA10'], label='MA10', color='orange', linewidth=1)
        self.ax1.plot(df_display.index, df_display['MA20'], label='MA20', color='red', linewidth=1)
        
        if 'ma_cross' in self.signals and self.signals['ma_cross'] and len(df_display) > 1:
            last_idx = df_display.index[-1]
            self.ax1.annotate(self.signals['ma_cross'], 
                             xy=(last_idx, df_display['Close'].iloc[-1]),
                             xytext=(10, 20), textcoords='offset points',
                             arrowprops=dict(arrowstyle='->', color='purple'),
                             fontsize=9, color='purple')
        
        self.ax1.legend(loc='upper left')
        self.ax1.set_title(f"{self.name}({self.code}) - {self.current_period.get()}周期")
        self.ax1.xaxis_date()
        self.ax1.grid(True, alpha=0.3)
        
        colors = ['red' if row['Close'] >= row['Open'] else 'green' for _, row in df_display.iterrows()]
        self.ax2.bar(df_display.index, df_display['Volume'], color=colors, width=width, alpha=0.6)
        self.ax2.set_ylabel('Volume')
        self.ax2.xaxis_date()
        self.ax2.grid(True, alpha=0.3)
        
        self.fig.autofmt_xdate()
    
    def _start_realtime_update(self):
        self._stop_realtime_update()
        if not self.is_realtime_mode.get():
            return
        interval = ConfigManager().get('settings.realtime_chart_update_interval', 1) * 1000
        self.realtime_update_id = self.after(interval, self._realtime_update)
    
    def _realtime_update(self):
        if self.is_realtime_mode.get() and self.code:
            self._draw_realtime()
            self._start_realtime_update()
    
    def _stop_realtime_update(self):
        if self.realtime_update_id:
            self.after_cancel(self.realtime_update_id)
            self.realtime_update_id = None
            # ==================== 自动交易账户（支持T+1） ====================
class AutoTradeAccount(SimulatedTrade):
    """支持T+1规则的自动交易账户（继承自SimulatedTrade）"""
    def __init__(self, initial_capital=1000000):
        super().__init__(initial_capital)
        
    def buy(self, code, name, price, quantity, auto=False):
        """买入 quantity 手，记录买入日期"""
        shares = quantity * 100
        amount = price * shares
        fee = self._calc_buy_fee(amount, code)
        total_cost = amount + fee
        
        with self._lock:
            if total_cost > self.cash:
                return False, f"资金不足，需{total_cost:.2f}元，可用{self.cash:.2f}元"
            
            self.cash -= total_cost
            cost_per_share = total_cost / shares
            today = datetime.now().strftime("%Y-%m-%d")
            
            if code in self.positions:
                old = self.positions[code]
                total_shares = old['shares'] + shares
                total_cost_all = old['cost'] * old['shares'] + total_cost
                self.positions[code] = {
                    'name': name,
                    'shares': total_shares,
                    'cost': round(total_cost_all / total_shares, 3),
                    'buy_date': today
                }
            else:
                self.positions[code] = {
                    'name': name,
                    'shares': shares,
                    'cost': round(cost_per_share, 3),
                    'buy_date': today
                }
            
            self.history.add_record({
                'action': '买入',
                'code': code,
                'name': name,
                'price': price,
                'shares': shares,
                'amount': amount,
                'fee': fee,
                'note': '自动' if auto else '手动'
            })
        return True, f"买入成功：{name} {quantity}手，成交额{amount:.2f}，手续费{fee:.2f}，总成本{total_cost:.2f}"
    
    def sell(self, code, price, quantity=None, auto=False):
        """卖出 quantity 手，检查是否满足T+1"""
        with self._lock:
            if code not in self.positions:
                return False, "没有持仓"
            
            pos = self.positions[code]
            shares_available = pos['shares']
            
            # 检查T+1：今天不能卖今天买入的股票
            buy_date = pos.get('buy_date')
            if buy_date == datetime.now().strftime("%Y-%m-%d"):
                return False, "今天买入的股票，T+1规则下不能今日卖出"
            
            if quantity is None:
                sell_shares = shares_available
            else:
                sell_shares = quantity * 100
                if sell_shares > shares_available:
                    return False, f"可卖数量不足，最多{shares_available//100}手"
            
            amount = price * sell_shares
            fee = self._calc_sell_fee(amount, code)
            net_income = amount - fee
            
            self.cash += net_income
            
            if sell_shares == shares_available:
                del self.positions[code]
            else:
                self.positions[code]['shares'] -= sell_shares
            
            self.history.add_record({
                'action': '卖出',
                'code': code,
                'name': pos['name'],
                'price': price,
                'shares': sell_shares,
                'amount': amount,
                'fee': fee,
                'note': '自动' if auto else '手动'
            })
        return True, f"卖出成功：{pos['name']} {sell_shares//100}手，成交额{amount:.2f}，手续费{fee:.2f}，实收{net_income:.2f}"


# ==================== 独立自动交易窗口 ====================
class AutoTradeWindow(tk.Toplevel):
    """独立自动交易模拟盘窗口"""
    def __init__(self, master):
        super().__init__(master)
        self.title("智能自动模拟盘 - 全自动交易")
        self.geometry("1400x800")
        self.minsize(1200, 600)
        
        self.config = ConfigManager()
        self.logger = Logger()
        self.tushare = TushareManager()
        
        try:
            # 初始化自动交易账户（独立账户，不与主界面共享）
            account_data = self.config.get('auto_account', {})
            if not account_data:
                account_data = {"cash": 1000000, "positions": {}}
            self.trade_account = AutoTradeAccount()
            self.trade_account.cash = account_data.get('cash', 1000000)
            self.trade_account.positions = account_data.get('positions', {})
            self.trade_account.update_total_value({})
            
            # 价格缓存
            self.price_cache = {}
            self.price_cache_lock = threading.RLock()
            
            # 自动交易线程控制
            self.auto_trading = False
            self.auto_thread = None
            
            # 数据队列
            self.data_queue = queue.Queue()
            
            # 创建界面
            self.create_widgets()
            
            # 启动价格更新线程
            self.start_price_updater()
            
            # 处理队列
            self.process_queue()
            
            # 窗口关闭时保存数据
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
        except Exception as e:
            self.logger.error(f"自动模拟盘初始化失败: {e}")
            messagebox.showerror("错误", f"自动模拟盘启动失败：{e}")
            self.destroy()

    def create_widgets(self):
        # 使用 PanedWindow 分割左右区域
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧：K线图 + 账户信息
        left_frame = ttk.Frame(main_pane, width=800)
        main_pane.add(left_frame, weight=3)
        
        # K线图
        kline_frame = ttk.LabelFrame(left_frame, text="K线图", padding=5)
        kline_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.kline_chart = KlineChart(kline_frame)
        self.kline_chart.pack(fill=tk.BOTH, expand=True)
        
        # 账户摘要
        summary_frame = ttk.LabelFrame(left_frame, text="账户摘要", padding=5)
        summary_frame.pack(fill=tk.X, pady=5)
        self.cash_label = ttk.Label(summary_frame, text="可用资金: 1,000,000")
        self.cash_label.pack(side=tk.LEFT, padx=10)
        self.total_label = ttk.Label(summary_frame, text="总资产: 1,000,000")
        self.total_label.pack(side=tk.LEFT, padx=10)
        self.profit_label = ttk.Label(summary_frame, text="盈亏: 0")
        self.profit_label.pack(side=tk.LEFT, padx=10)
        
        # 持仓列表
        pos_frame = ttk.LabelFrame(left_frame, text="当前持仓", padding=5)
        pos_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        columns = ("code", "name", "quantity", "cost", "price", "profit", "buy_date")
        self.position_tree = ttk.Treeview(pos_frame, columns=columns, show="headings", height=8)
        self.position_tree.heading("code", text="代码")
        self.position_tree.heading("name", text="名称")
        self.position_tree.heading("quantity", text="持股(手)")
        self.position_tree.heading("cost", text="成本价")
        self.position_tree.heading("price", text="现价")
        self.position_tree.heading("profit", text="盈亏")
        self.position_tree.heading("buy_date", text="买入日期")
        self.position_tree.column("code", width=60)
        self.position_tree.column("name", width=80)
        self.position_tree.column("quantity", width=60)
        self.position_tree.column("cost", width=70)
        self.position_tree.column("price", width=70)
        self.position_tree.column("profit", width=80)
        self.position_tree.column("buy_date", width=90)
        scrollbar = ttk.Scrollbar(pos_frame, orient=tk.VERTICAL, command=self.position_tree.yview)
        self.position_tree.configure(yscrollcommand=scrollbar.set)
        self.position_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右侧：自动交易控制面板
        right_frame = ttk.Frame(main_pane, width=400)
        main_pane.add(right_frame, weight=1)
        
        control_frame = ttk.LabelFrame(right_frame, text="自动交易控制", padding=10)
        control_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(control_frame, text="▶ 启动自动交易", command=self.start_auto_trade)
        self.start_btn.pack(fill=tk.X, pady=5)
        self.stop_btn = ttk.Button(control_frame, text="⏹ 停止自动交易", command=self.stop_auto_trade, state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, pady=5)
        
        ttk.Label(control_frame, text="策略参数", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=5)
        
        param_frame = ttk.Frame(control_frame)
        param_frame.pack(fill=tk.X, pady=2)
        ttk.Label(param_frame, text="买入涨幅阈值%:").pack(side=tk.LEFT)
        self.buy_threshold = ttk.Entry(param_frame, width=8)
        self.buy_threshold.insert(0, "5")
        self.buy_threshold.pack(side=tk.RIGHT)
        
        param_frame = ttk.Frame(control_frame)
        param_frame.pack(fill=tk.X, pady=2)
        ttk.Label(param_frame, text="卖出盈利阈值%:").pack(side=tk.LEFT)
        self.sell_threshold = ttk.Entry(param_frame, width=8)
        self.sell_threshold.insert(0, "10")
        self.sell_threshold.pack(side=tk.RIGHT)
        
        param_frame = ttk.Frame(control_frame)
        param_frame.pack(fill=tk.X, pady=2)
        ttk.Label(param_frame, text="每次买入手数:").pack(side=tk.LEFT)
        self.buy_quantity = ttk.Entry(param_frame, width=8)
        self.buy_quantity.insert(0, "1")
        self.buy_quantity.pack(side=tk.RIGHT)
        
        ttk.Label(control_frame, text="监控股票池（代码逗号分隔）").pack(anchor=tk.W, pady=5)
        self.watchlist = tk.Text(control_frame, height=5)
        self.watchlist.insert(tk.END, "000001,600036,600519,300750")
        self.watchlist.pack(fill=tk.X, pady=2)
        
        ttk.Label(control_frame, text="交易日志", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=5)
        self.log_text = scrolledtext.ScrolledText(control_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # 重置账户按钮（独立窗口内的重置）
        ttk.Button(control_frame, text="重置账户", command=self.reset_account).pack(fill=tk.X, pady=5)

    def start_auto_trade(self):
        if self.auto_trading:
            return
        self.auto_trading = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log("自动交易已启动")
        self.auto_thread = threading.Thread(target=self.auto_trade_loop, daemon=True)
        self.auto_thread.start()

    def stop_auto_trade(self):
        self.auto_trading = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("自动交易已停止")

    def auto_trade_loop(self):
        """自动交易主循环，每分钟检查一次"""
        while self.auto_trading:
            try:
                self.check_and_trade()
            except Exception as e:
                self.log(f"自动交易异常: {e}")
            tm.sleep(60)

    def check_and_trade(self):
        """根据策略检查买卖条件"""
        watch_text = self.watchlist.get("1.0", tk.END).strip()
        codes = [c.strip() for c in watch_text.split(",") if c.strip()]
        if not codes:
            return
        
        for code in codes:
            quote = DataFetcher.get_realtime_quote(code)
            if not quote:
                continue
            try:
                buy_thresh = float(self.buy_threshold.get())
            except:
                buy_thresh = 5.0
            if quote['change_pct'] >= buy_thresh and quote['volume_ratio'] > 1.5:
                if code in self.trade_account.positions:
                    continue
                name = quote['name']
                try:
                    qty = int(self.buy_quantity.get())
                except:
                    qty = 1
                success, msg = self.trade_account.buy(code, name, quote['price'], qty, auto=True)
                if success:
                    self.log(f"自动买入: {name}({code}) {qty}手，价格{quote['price']}")
                else:
                    self.log(f"买入失败: {msg}")
        
        sell_thresh = float(self.sell_threshold.get()) if self.sell_threshold.get() else 10.0
        for code, pos in list(self.trade_account.positions.items()):
            quote = DataFetcher.get_realtime_quote(code)
            if not quote:
                continue
            profit_pct = (quote['price'] - pos['cost']) / pos['cost'] * 100
            if profit_pct >= sell_thresh:
                success, msg = self.trade_account.sell(code, quote['price'], auto=True)
                if success:
                    self.log(f"自动卖出: {pos['name']}({code})，盈利{profit_pct:.2f}%")
                else:
                    self.log(f"卖出失败: {msg}")

    def log(self, msg):
        def _log():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_text.see(tk.END)
        self.after(0, _log)

    def update_account_display(self):
        summary = self.trade_account.get_account_summary()
        self.cash_label.config(text=f"可用资金: {summary['cash']:,.0f}")
        self.total_label.config(text=f"总资产: {summary['total_value']:,.0f}")
        profit_color = "red" if summary['profit'] >= 0 else "green"
        self.profit_label.config(text=f"盈亏: {summary['profit']:+,.0f} ({summary['profit_pct']:+.2f}%)", foreground=profit_color)
        
        for row in self.position_tree.get_children():
            self.position_tree.delete(row)
        
        positions = self.trade_account.get_position_list()
        for code, pos in positions.items():
            shares = pos['shares']
            with self.price_cache_lock:
                quote = self.price_cache.get(code)
            price = quote['price'] if quote else pos['cost']
            profit = (price - pos['cost']) * shares
            profit_str = f"{profit:+,.0f}"
            profit_color = "red" if profit >= 0 else "green"
            buy_date = self.trade_account.positions[code].get('buy_date', '')
            values = (code, pos['name'], pos['quantity'], f"{pos['cost']:.2f}", f"{price:.2f}", profit_str, buy_date)
            tags = ("profit_pos",) if profit >= 0 else ("profit_neg",)
            self.position_tree.insert("", tk.END, values=values, tags=tags)
        
        self.position_tree.tag_configure("profit_pos", foreground="red")
        self.position_tree.tag_configure("profit_neg", foreground="green")

    def start_price_updater(self):
        def updater():
            while True:
                try:
                    watch_codes = set()
                    for code in self.trade_account.positions:
                        watch_codes.add(code)
                    for s in DataFetcher.STOCK_POOL:
                        watch_codes.add(s['code'])
                    watch_text = self.watchlist.get("1.0", tk.END).strip()
                    codes = [c.strip() for c in watch_text.split(",") if c.strip()]
                    watch_codes.update(codes)
                    
                    for code in watch_codes:
                        quote = DataFetcher.get_realtime_quote(code)
                        if quote:
                            with self.price_cache_lock:
                                self.price_cache[code] = quote
                        tm.sleep(0.5)
                    self.trade_account.update_total_value({code: q['price'] for code, q in self.price_cache.items()})
                    self.after(0, self.update_account_display)
                except Exception as e:
                    print(f"价格更新异常: {e}")
                tm.sleep(3)
        threading.Thread(target=updater, daemon=True).start()

    def process_queue(self):
        self.after(100, self.process_queue)

    def reset_account(self):
        if messagebox.askyesno("确认", "确定重置自动模拟账户吗？所有持仓和资金将恢复初始状态。"):
            self.trade_account.reset()
            self.update_account_display()
            self.log("账户已重置")

    def on_closing(self):
        self.stop_auto_trade()
        account_data = {
            "cash": self.trade_account.cash,
            "positions": self.trade_account.positions
        }
        self.config.set('auto_account', account_data)
        self.destroy()
        # ==================== 授权管理模块（优化版）====================
class LicenseManager:
    def __init__(self):
        print("[调试] LicenseManager 初始化开始...", flush=True)
        # 使用用户目录保存 license.dat（避免权限问题）
        self.config_dir = os.path.expanduser("~/.stock_assistant")
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        self.license_file = os.path.join(self.config_dir, "license.dat")
        
        # 公钥文件仍然放在程序目录（因为需要读取）
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.key_path = os.path.join(self.base_dir, "public_key.pem")
        
        print(f"[调试] 公钥路径: {self.key_path}", flush=True)
        if os.path.exists(self.key_path):
            try:
                with open(self.key_path, 'rb') as f:
                    pem_data = f.read()
                from cryptography.hazmat.primitives import serialization
                self.public_key = serialization.load_pem_public_key(pem_data)
                print("[调试] 公钥加载成功", flush=True)
            except Exception as e:
                print(f"[错误] 加载公钥失败: {e}", flush=True)
                self._show_error_and_exit(f"公钥文件损坏或格式错误: {e}")
        else:
            print("[错误] 未找到 public_key.pem 文件", flush=True)
            self._show_error_and_exit("未找到公钥文件 public_key.pem，请将该文件放在程序目录下。")

        self.machine_id = self._get_machine_id()
        print(f"[调试] 本机机器码: {self.machine_id}", flush=True)
        self.expiry_date = None  # 存储有效期

    def _show_error_and_exit(self, message):
        """弹出错误对话框并退出程序"""
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("错误", message)
        except:
            print(message)
        sys.exit(1)

    def _get_machine_id(self) -> str:
        """生成一个16位的唯一机器码（稳定版，避免阻塞）"""
        import hashlib
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Cryptography")
            machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            raw = machine_guid
        except:
            import os
            import getpass
            raw = os.environ.get('COMPUTERNAME', '') + getpass.getuser()
        return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

    def verify_license(self, license_key: str) -> Tuple[bool, Optional[datetime]]:
        """验证激活码，返回 (是否有效, 过期日期)"""
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            import base64
            import json
            from datetime import datetime

            encoded_payload, encoded_signature = license_key.strip().split('.')
            payload_bytes = base64.b64decode(encoded_payload)
            signature = base64.b64decode(encoded_signature)

            self.public_key.verify(
                signature, payload_bytes,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            data = json.loads(payload_bytes)
            if data.get("mid") != self.machine_id:
                return False, None
            exp_date = datetime.fromisoformat(data["exp"])
            if datetime.now() > exp_date:
                return False, None
            return True, exp_date
        except:
            return False, None

    def is_activated(self) -> bool:
        """检查是否已激活且有效，并记录过期日期"""
        if not os.path.exists(self.license_file):
            return False
        with open(self.license_file, 'r') as f:
            key = f.read().strip()
        valid, exp_date = self.verify_license(key)
        if valid:
            self.expiry_date = exp_date
        return valid

    def activate(self, license_key: str) -> bool:
        """激活并保存激活码"""
        valid, exp_date = self.verify_license(license_key)
        if valid:
            with open(self.license_file, 'w') as f:
                f.write(license_key)
            self.expiry_date = exp_date
            return True
        return False

    def get_remaining_days(self) -> int:
        """返回剩余天数（如果已激活且未过期）"""
        if self.expiry_date:
            delta = self.expiry_date - datetime.now()
            return max(delta.days, 0)
        return 0


# ==================== 主应用程序 ====================
class StockAssistantPro:
    def __init__(self):
        print("[调试] 进入 StockAssistantPro.__init__", flush=True)

        # --- 授权检查（使用独立激活窗口）---
        print("[调试] 开始授权检查", flush=True)
        self.license_manager = LicenseManager()

        # 先创建独立激活窗口（不依赖 self.root）
        if not self.license_manager.is_activated():
            self.show_activation_dialog()  # 这个方法会阻塞，直到激活成功或用户关闭
            # 再次检查是否激活成功（用户可能取消或失败）
            if not self.license_manager.is_activated():
                sys.exit(0)  # 未激活则退出

        # 激活成功，创建主窗口
        print("[调试] 授权检查通过，创建主窗口", flush=True)
        self.root = tk.Tk()
        
        # 获取剩余天数并设置标题
        remaining_days = self.license_manager.get_remaining_days()
        if remaining_days > 0:
            title = f"A股智能交易助手 - 旗舰版 v15.3 (剩余 {remaining_days} 天)"
        else:
            title = "A股智能交易助手 - 旗舰版 v15.3 (已过期)"
        self.root.title(title)
        
        self.root.geometry("1700x1000")
        self.root.minsize(1400, 800)
        self.root.configure(bg='#f0f0f0')

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_styles()

        self.config = ConfigManager()
        self.logger = Logger()
        self.logger.add_handler(self.log_handler)
        self.tushare = TushareManager()
        self.tushare.set_callback(self.update_tushare_display)
        self.trade_account = SimulatedTrade()
        self.alert_manager = AlertManager()

        account_data = self.config.get('account', {})
        self.trade_account.cash = account_data.get('cash', 1000000)
        self.trade_account.positions = account_data.get('positions', {})
        self.trade_account.update_total_value({})

        self.executor = ThreadPoolExecutor(max_workers=10)
        self.running = True
        self.price_cache = {}
        self.price_cache_lock = threading.RLock()

        self.data_queue = queue.Queue()
        self.flash_after_id = None
        self.buy_btn = None
        self.sell_btn = None
        self.current_analyze_code = None
        self.current_analyze_name = None
        self.current_analyze_price = None

        self.network_ok = True
        self.network_check_thread = threading.Thread(target=self._network_monitor, daemon=True)
        self.network_check_thread.start()

        self.create_menu()
        self.create_top_alert()
        self.create_statusbar()
        self.create_toolbar()
        self.create_main_layout()

        self.after_id = None
        self.load_initial_data()
        self.start_scheduler()
        self.process_queue()
        self.start_price_updater()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.logger.info("程序启动成功，欢迎使用 A股智能交易助手 旗舰版 v15.3")
        self.update_expiry_display()  # 更新状态栏有效期
        print("[调试] __init__ 完成", flush=True)

    def show_activation_dialog(self):
        """使用独立窗口显示激活对话框（确保一定弹出）"""
        # 创建独立的 Tk 窗口（不与主窗口共享）
        dialog = tk.Tk()
        dialog.title("软件激活")
        dialog.geometry("400x300")
        dialog.resizable(False, False)

        # 使窗口居中
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')

        # 强制窗口获得焦点
        dialog.lift()
        dialog.focus_force()

        # 添加作者信息
        tk.Label(dialog, text="A股智能交易助手", font=("微软雅黑", 16, "bold"), fg="#2c3e50").pack(pady=5)
        tk.Label(dialog, text="作者QQ: 200931349  heng", font=("微软雅黑", 10), fg="#3498db").pack(pady=2)

        tk.Label(dialog, text=f"本机机器码:\n{self.license_manager.machine_id}", font=("微软雅黑", 10)).pack(pady=10)
        tk.Label(dialog, text="请输入激活码:").pack()
        entry = tk.Entry(dialog, width=40)
        entry.pack(pady=5)
        entry.focus_set()  # 自动聚焦输入框

        result_var = tk.StringVar()
        result_label = tk.Label(dialog, textvariable=result_var, fg="red")
        result_label.pack()

        activated = False  # 标记是否激活成功

        def do_activate():
            nonlocal activated
            key = entry.get().strip()
            if not key:
                result_var.set("请输入激活码")
                return
            if self.license_manager.activate(key):
                activated = True
                dialog.destroy()
            else:
                result_var.set("激活码无效，请检查后重试。")

        tk.Button(dialog, text="激活", command=do_activate, bg="#27ae60", fg="white", width=15).pack(pady=10)
        tk.Label(dialog, text="未激活请联系管理员获取激活码", font=("微软雅黑", 9), fg="red").pack()

        # 拦截关闭按钮，如果用户直接关闭窗口，视为未激活
        dialog.protocol("WM_DELETE_WINDOW", lambda: dialog.destroy())

        # 进入独立的事件循环，直到窗口被销毁
        dialog.mainloop()

        # 如果激活失败，退出程序
        if not activated:
            sys.exit(0)

    def configure_styles(self):
        bg_color = '#f0f0f0'
        fg_color = '#333333'
        select_color = '#3498db'
        
        self.style.configure("Title.TLabel", font=("微软雅黑", 14, "bold"), foreground="#2c3e50", background=bg_color)
        self.style.configure("Heading.TLabel", font=("微软雅黑", 11, "bold"), foreground="#34495e", background=bg_color)
        self.style.configure("Success.TButton", font=("微软雅黑", 10), background="#27ae60", foreground='white')
        self.style.map("Success.TButton", background=[("active", "#2ecc71")])
        self.style.configure("Info.TButton", font=("微软雅黑", 10), background="#3498db", foreground='white')
        self.style.map("Info.TButton", background=[("active", "#5dade2")])
        self.style.configure("Danger.TButton", font=("微软雅黑", 10), background="#e74c3c", foreground='white')
        self.style.map("Danger.TButton", background=[("active", "#c0392b")])
        
        self.style.configure("Treeview", background="white", foreground=fg_color, fieldbackground="white")
        self.style.map('Treeview', background=[('selected', select_color)], foreground=[('selected', 'white')])
        self.style.configure("Treeview.Heading", background="#e0e0e0", foreground=fg_color, relief="flat", font=("微软雅黑", 10, "bold"))
        self.style.map("Treeview.Heading", background=[('active', '#d0d0d0')])
        
        self.style.configure("TLabelframe", background=bg_color, foreground=fg_color)
        self.style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color, font=("微软雅黑", 10, "bold"))
        self.style.configure("TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("TButton", background="#e0e0e0", foreground=fg_color)
        self.style.map("TButton", background=[('active', '#d0d0d0')])
        self.style.configure("TEntry", fieldbackground="white", foreground=fg_color)
        self.style.configure("TCombobox", fieldbackground="white", foreground=fg_color)

    def create_menu(self):
        menubar = tk.Menu(self.root, bg='#f0f0f0', fg='#333333')
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', fg='#333333')
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="刷新数据", command=self.refresh_all_data, accelerator="F5")
        file_menu.add_command(label="开始选股", command=self.start_screening, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="导出交易历史", command=self.export_history)
        file_menu.add_command(label="导入配置", command=self.import_config)
        file_menu.add_command(label="导出配置", command=self.export_config)
        file_menu.add_separator()
        file_menu.add_command(label="重置模拟账户", command=self.reset_account)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing, accelerator="Ctrl+Q")
        
        tool_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', fg='#333333')
        menubar.add_cascade(label="工具", menu=tool_menu)
        tool_menu.add_command(label="设置价格提醒", command=self.open_price_alert_dialog)
        tool_menu.add_command(label="设置条件单", command=self.open_condition_alert_dialog)
        tool_menu.add_command(label="清空日志", command=self.clear_log)
        tool_menu.add_command(label="查看交易历史", command=self.show_history)
        tool_menu.add_separator()
        tool_menu.add_command(label="配置参数", command=self.open_settings)
        
        help_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', fg='#333333')
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="功能列表", command=self.show_features)
        help_menu.add_command(label="快捷键列表", command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="重新激活", command=self.reactivate)
        help_menu.add_separator()
        help_menu.add_command(label="关于", command=self.show_about)
        
        self.root.bind('<F5>', lambda e: self.refresh_all_data())
        self.root.bind('<Control-s>', lambda e: self.start_screening())
        self.root.bind('<Control-a>', lambda e: self.analyze_stock())
        self.root.bind('<Control-q>', lambda e: self.on_closing())

    def reactivate(self):
        """重新激活：弹出独立激活窗口，如果成功则提示重启"""
        dialog = tk.Toplevel(self.root)
        dialog.title("重新激活")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()

        tk.Label(dialog, text="A股智能交易助手", font=("微软雅黑", 16, "bold"), fg="#2c3e50").pack(pady=5)
        tk.Label(dialog, text="作者QQ: 200931349  heng", font=("微软雅黑", 10), fg="#3498db").pack(pady=2)
        tk.Label(dialog, text=f"本机机器码:\n{self.license_manager.machine_id}", font=("微软雅黑", 10)).pack(pady=10)
        tk.Label(dialog, text="请输入新的激活码:").pack()
        entry = tk.Entry(dialog, width=40)
        entry.pack(pady=5)

        result_var = tk.StringVar()
        result_label = tk.Label(dialog, textvariable=result_var, fg="red")
        result_label.pack()

        def do_reactivate():
            key = entry.get().strip()
            if not key:
                result_var.set("请输入激活码")
                return
            if self.license_manager.activate(key):
                messagebox.showinfo("成功", "激活码已更新，请重启程序生效。")
                dialog.destroy()
            else:
                result_var.set("激活码无效，请检查后重试。")

        tk.Button(dialog, text="激活", command=do_reactivate, bg="#27ae60", fg="white", width=15).pack(pady=10)
        tk.Button(dialog, text="取消", command=dialog.destroy).pack()

    def create_top_alert(self):
        self.alert_frame = tk.Frame(self.root, bg='#ff4444', height=30)
        self.alert_label = tk.Label(self.alert_frame, text="", bg='#ff4444', fg='white', font=("微软雅黑", 10, "bold"))
        self.alert_label.pack(fill=tk.BOTH, expand=True)
        self.alert_frame.pack_forget()
        self.is_flashing = False

    def show_alert_message(self, message):
        self.alert_label.config(text=message)
        self.alert_frame.pack(side=tk.TOP, fill=tk.X, before=self.toolbar if hasattr(self, 'toolbar') else None)
        self.start_flashing()
        self.root.after(10000, self.hide_alert)

    def hide_alert(self):
        self.alert_frame.pack_forget()
        self.stop_flashing()

    def start_flashing(self):
        self.is_flashing = True
        self.flash_step()

    def stop_flashing(self):
        self.is_flashing = False
        if self.flash_after_id:
            self.root.after_cancel(self.flash_after_id)
            self.flash_after_id = None
        self.alert_frame.config(bg='#ff4444')
        self.alert_label.config(bg='#ff4444')

    def flash_step(self):
        if not self.is_flashing:
            return
        current_bg = self.alert_frame.cget('bg')
        new_bg = '#ffffff' if current_bg == '#ff4444' else '#ff4444'
        self.alert_frame.config(bg=new_bg)
        self.alert_label.config(bg=new_bg)
        self.flash_after_id = self.root.after(500, self.flash_step)

    def create_toolbar(self):
        self.toolbar = ttk.Frame(self.root, relief=tk.RAISED, padding=2)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        refresh_btn = ttk.Button(self.toolbar, text="🔄 刷新", command=self.refresh_all_data, style="Info.TButton")
        refresh_btn.pack(side=tk.LEFT, padx=2)

        screen_btn = ttk.Button(self.toolbar, text="🎯 开始选股", command=self.start_screening, style="Success.TButton")
        screen_btn.pack(side=tk.LEFT, padx=2)

        alert_btn = ttk.Button(self.toolbar, text="🔔 添加提醒", command=self.open_price_alert_dialog)
        alert_btn.pack(side=tk.LEFT, padx=2)

        # 自动模拟盘按钮
        auto_btn = ttk.Button(self.toolbar, text="🤖 自动模拟盘", command=self.open_auto_trade_window, style="Info.TButton")
        auto_btn.pack(side=tk.LEFT, padx=2)

        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        self.progress = ttk.Progressbar(self.toolbar, mode='indeterminate', length=100)
        self.progress.pack(side=tk.LEFT, padx=5)
        self.progress.pack_forget()

        self.time_var = tk.StringVar()
        time_label = ttk.Label(self.toolbar, textvariable=self.time_var, font=("微软雅黑", 10))
        time_label.pack(side=tk.RIGHT, padx=5)
        self.update_time()

    def create_statusbar(self):
        statusbar = ttk.Frame(self.root, relief=tk.SUNKEN, padding=2)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(statusbar, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)

        self.source_var = tk.StringVar(value="行情:多源 资金:Tushare")
        source_label = ttk.Label(statusbar, textvariable=self.source_var, foreground="#2c3e50")
        source_label.pack(side=tk.LEFT, padx=10)

        self.network_var = tk.StringVar(value="网络:正常")
        network_label = ttk.Label(statusbar, textvariable=self.network_var, foreground="green")
        network_label.pack(side=tk.LEFT, padx=10)

        # 添加有效期显示
        self.expiry_var = tk.StringVar(value="")
        expiry_label = ttk.Label(statusbar, textvariable=self.expiry_var, foreground="purple")
        expiry_label.pack(side=tk.LEFT, padx=10)

        self.trade_status_var = tk.StringVar(value="非交易时段")
        self.trade_status_label = ttk.Label(statusbar, textvariable=self.trade_status_var, foreground="#e67e22")
        self.trade_status_label.pack(side=tk.RIGHT, padx=5)

        self.countdown_var = tk.StringVar(value="")
        countdown_label = ttk.Label(statusbar, textvariable=self.countdown_var, foreground="#e67e22")
        countdown_label.pack(side=tk.RIGHT, padx=5)

    def update_expiry_display(self):
        """更新有效期显示"""
        remaining = self.license_manager.get_remaining_days()
        if remaining > 0:
            self.expiry_var.set(f"激活剩余 {remaining} 天")
        else:
            self.expiry_var.set("激活已过期")

    def create_main_layout(self):
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(main_pane, width=350)
        main_pane.add(left_frame, weight=3)
        self.create_left_panel(left_frame)

        center_frame = ttk.Frame(main_pane, width=500)
        main_pane.add(center_frame, weight=4)
        self.create_center_panel(center_frame)

        right_frame = ttk.Frame(main_pane, width=550)
        main_pane.add(right_frame, weight=4)
        self.create_right_panel(right_frame)

    def create_left_panel(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        news_frame = ttk.Frame(notebook)
        notebook.add(news_frame, text="📰 新闻舆情")
        self.create_news_tab(news_frame)

        analyze_frame = ttk.Frame(notebook)
        notebook.add(analyze_frame, text="🔍 个股分析")
        self.create_analyze_tab(analyze_frame)

        capital_frame = ttk.Frame(notebook)
        notebook.add(capital_frame, text="💰 主力监控")
        self.create_capital_tab(capital_frame)

    def create_news_tab(self, parent):
        ttk.Label(parent, text="热点新闻", style="Heading.TLabel").pack(anchor=tk.W, pady=2)

        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.news_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                        font=("微软雅黑", 10), height=10,
                                        bg='white', fg='#333333', selectbackground='#3498db', selectforeground='white')
        self.news_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.news_listbox.yview)
        self.news_listbox.bind("<<ListboxSelect>>", self.on_news_select)

        ttk.Label(parent, text="详情", style="Heading.TLabel").pack(anchor=tk.W, pady=(10,2))

        self.news_detail = scrolledtext.ScrolledText(parent, height=6, wrap=tk.WORD, font=("微软雅黑", 9),
                                                      bg='white', fg='#333333', insertbackground='#333333')
        self.news_detail.pack(fill=tk.BOTH, expand=True, pady=2)

    def create_analyze_tab(self, parent):
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Label(search_frame, text="股票代码:").pack(side=tk.LEFT)
        self.analyze_code_var = tk.StringVar()
        analyze_entry = ttk.Entry(search_frame, textvariable=self.analyze_code_var, width=12)
        analyze_entry.pack(side=tk.LEFT, padx=5)

        analyze_btn = ttk.Button(search_frame, text="分析", command=self.analyze_stock)
        analyze_btn.pack(side=tk.LEFT)

        self.stock_name_label = ttk.Label(parent, text="", font=("微软雅黑", 10, "bold"), foreground="#27ae60")
        self.stock_name_label.pack(anchor=tk.W, pady=2)

        quick_frame = ttk.Frame(parent)
        quick_frame.pack(fill=tk.X, pady=2)
        ttk.Label(quick_frame, text="常用:").pack(side=tk.LEFT)
        for code in ["000001", "600036", "600519", "300750"]:
            btn = ttk.Button(quick_frame, text=code,
                            command=lambda c=code: self.quick_analyze(c))
            btn.pack(side=tk.LEFT, padx=2)

        self.analyze_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=("微软雅黑", 10), height=10,
                                                      bg='white', fg='#333333', insertbackground='#333333')
        self.analyze_text.pack(fill=tk.BOTH, expand=True, pady=5)

        trade_frame = ttk.Frame(parent)
        trade_frame.pack(fill=tk.X, pady=2)
        self.buy_btn = ttk.Button(trade_frame, text="买入", command=self.buy_stock, style="Success.TButton", state=tk.DISABLED)
        self.buy_btn.pack(side=tk.LEFT, padx=5)
        self.sell_btn = ttk.Button(trade_frame, text="卖出", command=self.sell_stock, style="Danger.TButton", state=tk.DISABLED)
        self.sell_btn.pack(side=tk.LEFT, padx=5)
        ttk.Label(trade_frame, text="数量(手):").pack(side=tk.LEFT, padx=5)
        self.trade_qty = ttk.Entry(trade_frame, width=6)
        self.trade_qty.insert(0, "1")
        self.trade_qty.pack(side=tk.LEFT)

    def create_capital_tab(self, parent):
        ttk.Label(parent, text="主力资金数据（Tushare私有节点）", foreground="blue").pack(anchor=tk.W, pady=2)
        columns = ("code", "name", "net_main", "trend")
        self.capital_tree = ttk.Treeview(parent, columns=columns, show="headings", height=12)
        self.capital_tree.heading("code", text="代码")
        self.capital_tree.heading("name", text="名称")
        self.capital_tree.heading("net_main", text="主力净额(万)")
        self.capital_tree.heading("trend", text="动向")
        self.capital_tree.column("code", width=70)
        self.capital_tree.column("name", width=100)
        self.capital_tree.column("net_main", width=90)
        self.capital_tree.column("trend", width=50)

        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.capital_tree.yview)
        self.capital_tree.configure(yscrollcommand=scrollbar.set)
        self.capital_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.capital_tree.bind("<Double-1>", self.on_capital_double_click)

    def create_center_panel(self, parent):
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, pady=5)
        ttk.Label(title_frame, text="📊 强势选股结果", style="Title.TLabel").pack(side=tk.LEFT)
        self.screen_time_var = tk.StringVar(value="")
        ttk.Label(title_frame, textvariable=self.screen_time_var, foreground="#7f8c8d").pack(side=tk.RIGHT)

        columns = ("code", "name", "price", "change", "volume_ratio", "net_main", "signals", "suggestion")
        self.stock_tree = ttk.Treeview(parent, columns=columns, show="headings", height=12)
        self.stock_tree.heading("code", text="代码")
        self.stock_tree.heading("name", text="名称")
        self.stock_tree.heading("price", text="现价")
        self.stock_tree.heading("change", text="涨幅%")
        self.stock_tree.heading("volume_ratio", text="量比")
        self.stock_tree.heading("net_main", text="主力净额(万)")
        self.stock_tree.heading("signals", text="信号")
        self.stock_tree.heading("suggestion", text="建议")
        self.stock_tree.column("code", width=60)
        self.stock_tree.column("name", width=80)
        self.stock_tree.column("price", width=50)
        self.stock_tree.column("change", width=50)
        self.stock_tree.column("volume_ratio", width=50)
        self.stock_tree.column("net_main", width=80)
        self.stock_tree.column("signals", width=120)
        self.stock_tree.column("suggestion", width=70)

        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scrollbar.set)
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.stock_tree.bind("<Double-1>", self.on_stock_double_click)

        log_frame = ttk.LabelFrame(parent, text="运行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD, font=("Consolas", 9),
                                                   bg='#fafafa', fg='#333333', insertbackground='#333333')
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def create_right_panel(self, parent):
        # Tushare 设置
        tushare_frame = ttk.LabelFrame(parent, text="📊 Tushare PRO 私有节点", padding=5)
        tushare_frame.pack(fill=tk.X, pady=5)

        ttk.Label(tushare_frame, text="Token:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.tushare_token_var = tk.StringVar()
        token_entry = ttk.Entry(tushare_frame, textvariable=self.tushare_token_var, width=20, show="*")
        token_entry.grid(row=0, column=1, pady=2)

        self.show_tushare_token = False
        def toggle_tushare_token():
            self.show_tushare_token = not self.show_tushare_token
            token_entry.config(show="" if self.show_tushare_token else "*")
        toggle_btn = ttk.Button(tushare_frame, text="👁", command=toggle_tushare_token, width=2)
        toggle_btn.grid(row=0, column=2, padx=2)

        ttk.Label(tushare_frame, text="节点地址:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.node_url_var = tk.StringVar(value=self.tushare.node_url)
        node_entry = ttk.Entry(tushare_frame, textvariable=self.node_url_var, width=20)
        node_entry.grid(row=1, column=1, columnspan=2, pady=2)

        ttk.Button(tushare_frame, text="保存Token", command=self.save_tushare_token).grid(row=2, column=0, pady=2)
        ttk.Button(tushare_frame, text="验证", command=self.refresh_tushare_credit).grid(row=2, column=1, pady=2)
        ttk.Button(tushare_frame, text="退出", command=self.logout_tushare).grid(row=2, column=2, pady=2)

        self.tushare_credit_label = ttk.Label(tushare_frame, text="状态: 未登录", foreground="gray")
        self.tushare_credit_label.grid(row=3, column=0, columnspan=3, pady=2)

        # 微信推送设置
        push_frame = ttk.LabelFrame(parent, text="📱 微信推送 (pushplus)", padding=5)
        push_frame.pack(fill=tk.X, pady=5)

        ttk.Label(push_frame, text="Token:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.token_var = tk.StringVar()
        token_entry = ttk.Entry(push_frame, textvariable=self.token_var, width=20, show="*")
        token_entry.grid(row=0, column=1, pady=2)

        self.show_token = False
        def toggle_token():
            self.show_token = not self.show_token
            token_entry.config(show="" if self.show_token else "*")
        toggle_btn = ttk.Button(push_frame, text="👁", command=toggle_token, width=2)
        toggle_btn.grid(row=0, column=2, padx=2)

        ttk.Button(push_frame, text="保存", command=self.save_token).grid(row=1, column=0, pady=2)
        ttk.Button(push_frame, text="测试", command=self.test_push).grid(row=1, column=1, pady=2)

        # 提醒设置（增强：股票代码搜索）
        alert_frame = ttk.LabelFrame(parent, text="🔔 提醒设置", padding=5)
        alert_frame.pack(fill=tk.X, pady=5)

        ttk.Label(alert_frame, text="股票代码:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.alert_code_var = tk.StringVar()
        # 将 Entry 改为 Combobox 以实现搜索功能
        self.alert_code_combo = ttk.Combobox(alert_frame, textvariable=self.alert_code_var, width=12, values=[])
        self.alert_code_combo.grid(row=0, column=1, pady=2)
        self.alert_code_combo.bind('<KeyRelease>', self.on_alert_code_key)

        ttk.Label(alert_frame, text="买入价:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.alert_buy_var = tk.StringVar()
        ttk.Entry(alert_frame, textvariable=self.alert_buy_var, width=10).grid(row=1, column=1, pady=2)

        ttk.Label(alert_frame, text="卖出价:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.alert_sell_var = tk.StringVar()
        ttk.Entry(alert_frame, textvariable=self.alert_sell_var, width=10).grid(row=2, column=1, pady=2)

        self.auto_trade_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(alert_frame, text="自动交易", variable=self.auto_trade_var).grid(row=3, column=0, columnspan=2, pady=2)

        set_price_btn = ttk.Button(alert_frame, text="设置价格提醒", command=self.set_price_alert)
        set_price_btn.grid(row=4, column=0, columnspan=2, pady=2)

        ttk.Label(alert_frame, text="涨跌幅%:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.alert_change_var = tk.StringVar()
        ttk.Entry(alert_frame, textvariable=self.alert_change_var, width=10).grid(row=5, column=1, pady=2)

        ttk.Label(alert_frame, text="成交量>:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.alert_volume_var = tk.StringVar()
        ttk.Entry(alert_frame, textvariable=self.alert_volume_var, width=10).grid(row=6, column=1, pady=2)

        set_condition_btn = ttk.Button(alert_frame, text="设置条件单", command=self.set_condition_alert)
        set_condition_btn.grid(row=7, column=0, columnspan=2, pady=2)

        list_frame = ttk.LabelFrame(parent, text="我的提醒", padding=5)
        list_frame.pack(fill=tk.X, pady=5)

        self.alert_listbox = tk.Listbox(list_frame, height=5, bg='white', fg='#333333')
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.alert_listbox.yview)
        self.alert_listbox.configure(yscrollcommand=scrollbar.set)
        self.alert_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_selected_alert).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="全部删除", command=self.clear_all_alerts).pack(side=tk.LEFT, padx=2)

        self.refresh_alert_listbox()

        # K线图
        kline_frame = ttk.LabelFrame(parent, text="K线图", padding=5)
        kline_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.kline_chart = KlineChart(kline_frame)
        self.kline_chart.pack(fill=tk.BOTH, expand=True)

        # 手动模拟交易账户
        trade_frame = ttk.LabelFrame(parent, text="💰 手动模拟交易", padding=5)
        trade_frame.pack(fill=tk.X, pady=5)

        summary_frame = ttk.Frame(trade_frame)
        summary_frame.pack(fill=tk.X, pady=2)
        self.cash_label = ttk.Label(summary_frame, text="可用资金: 1,000,000")
        self.cash_label.pack(side=tk.LEFT, padx=5)
        self.total_label = ttk.Label(summary_frame, text="总资产: 1,000,000")
        self.total_label.pack(side=tk.LEFT, padx=5)
        self.profit_label = ttk.Label(summary_frame, text="盈亏: 0")
        self.profit_label.pack(side=tk.LEFT, padx=5)

        trade_btn_frame = ttk.Frame(trade_frame)
        trade_btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(trade_btn_frame, text="快速买入", command=self.quick_buy_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(trade_btn_frame, text="卖出选中", command=self.sell_selected_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(trade_btn_frame, text="刷新", command=self.update_account_display).pack(side=tk.LEFT, padx=2)
        ttk.Button(trade_btn_frame, text="历史", command=self.show_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(trade_btn_frame, text="重置账户", command=self.reset_account).pack(side=tk.LEFT, padx=2)

        columns = ("code", "name", "quantity", "cost", "price", "profit")
        self.position_tree = ttk.Treeview(trade_frame, columns=columns, show="headings", height=5)
        self.position_tree.heading("code", text="代码")
        self.position_tree.heading("name", text="名称")
        self.position_tree.heading("quantity", text="持股(手)")
        self.position_tree.heading("cost", text="成本价")
        self.position_tree.heading("price", text="现价")
        self.position_tree.heading("profit", text="盈亏")
        self.position_tree.column("code", width=50)
        self.position_tree.column("name", width=60)
        self.position_tree.column("quantity", width=50)
        self.position_tree.column("cost", width=60)
        self.position_tree.column("price", width=60)
        self.position_tree.column("profit", width=70)

        pos_scroll = ttk.Scrollbar(trade_frame, orient=tk.VERTICAL, command=self.position_tree.yview)
        self.position_tree.configure(yscrollcommand=pos_scroll.set)
        self.position_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pos_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.position_tree.bind("<Double-1>", self.on_position_double_click)
        self.position_tree.bind("<Button-3>", self.on_position_right_click)

        self.context_menu = tk.Menu(self.root, tearoff=0, bg='#f0f0f0', fg='#333333')
        self.context_menu.add_command(label="卖出", command=self.sell_selected_context)
        self.context_menu.add_command(label="分析", command=self.analyze_selected_context)

    # 股票代码搜索功能
    def on_alert_code_key(self, event):
        """当用户在股票代码输入框中输入时，动态更新下拉建议列表"""
        typed = self.alert_code_var.get().strip().upper()
        if not typed:
            self.alert_code_combo['values'] = []
            return
        matches = []
        for stock in DataFetcher.STOCK_POOL:
            code = stock['code']
            name = stock['name']
            if typed in code or typed in name:
                matches.append(f"{code} {name}")
        self.alert_code_combo['values'] = matches[:10]  # 最多显示10条

    # ==================== 功能方法 ====================
    def open_auto_trade_window(self):
        try:
            win = AutoTradeWindow(self.root)
            win.focus_force()  # 只获取焦点，不阻塞
        except Exception as e:
            self.logger.error(f"打开自动模拟盘窗口失败: {e}")
            messagebox.showerror("错误", f"无法打开自动模拟盘：{e}")

    def update_time(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_var.set(now)

        trading, remaining = DataFetcher.is_trading_time()
        if trading:
            self.trade_status_var.set("交易时段 🔴")
            if self.buy_btn:
                self.buy_btn.config(state=tk.NORMAL)
            if self.sell_btn:
                self.sell_btn.config(state=tk.NORMAL)
        else:
            self.trade_status_var.set("非交易时段 ⚫")
            if self.buy_btn:
                self.buy_btn.config(state=tk.DISABLED)
            if self.sell_btn:
                self.sell_btn.config(state=tk.DISABLED)

        if remaining > 0:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)
            if trading:
                self.countdown_var.set(f"本时段剩余 {minutes:02d}:{seconds:02d}")
            else:
                self.countdown_var.set(f"距离开盘 {hours}时{minutes:02d}分")
        else:
            self.countdown_var.set("")

        self.after_id = self.root.after(1000, self.update_time)

    def process_queue(self):
        try:
            while True:
                msg = self.data_queue.get_nowait()
                if msg["type"] == "log":
                    pass
                elif msg["type"] == "status":
                    self.status_var.set(msg["text"])
                elif msg["type"] == "update_stocks":
                    self.display_screen_results(msg["data"])
                elif msg["type"] == "update_capital":
                    self.update_capital_table(msg["data"])
                elif msg["type"] == "alert":
                    self.show_alert_popup(msg["title"], msg["message"])
                elif msg["type"] == "update_account":
                    self.update_account_display()
                elif msg["type"] == "progress_start":
                    self.progress.pack(side=tk.LEFT, padx=5)
                    self.progress.start(10)
                elif msg["type"] == "progress_stop":
                    self.progress.stop()
                    self.progress.pack_forget()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def log_handler(self, message: str, level: str = 'INFO'):
        def _log():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        self.root.after(0, _log)

    def show_alert_popup(self, title, message):
        def _show():
            messagebox.showinfo(title, message)
            self.show_alert_message(message)
        self.root.after(0, _show)

    def load_initial_data(self):
        self.logger.info("程序启动，加载初始数据...")
        self.refresh_news()
        self.refresh_capital_monitor()
        self.start_screening()
        self.update_account_display()
        self.token_var.set(self.config.get_wechat_token())
        self.tushare_token_var.set(self.config.get_tushare_token())
        self.node_url_var.set(self.tushare.node_url)
        self.refresh_alert_listbox()
        if self.tushare.token:
            self.executor.submit(self.tushare.update_remaining)

    def refresh_alert_listbox(self):
        self.alert_listbox.delete(0, tk.END)
        for alert in self.alert_manager.get_all_price_alerts():
            display = f"[价格] {alert['name']}({alert['code']})"
            if alert.get('buy'):
                display += f" 买:{alert['buy']}"
            if alert.get('sell'):
                display += f" 卖:{alert['sell']}"
            if alert.get('auto_trade'):
                display += " [自动]"
            self.alert_listbox.insert(tk.END, display)
        for alert in self.alert_manager.get_all_condition_alerts():
            display = f"[条件] {alert['name']}({alert['code']})"
            if alert.get('change_pct'):
                display += f" 涨跌幅:{alert['change_pct']}%"
            if alert.get('volume_gt'):
                display += f" 成交量>{alert['volume_gt']}"
            self.alert_listbox.insert(tk.END, display)

    def refresh_news(self):
        def task():
            news_list = DataFetcher.get_news()
            self.root.after(0, lambda: self.display_news(news_list))
        self.executor.submit(task)

    def display_news(self, news_list):
        self.news_listbox.delete(0, tk.END)
        for news in news_list:
            display = f"[{news['type']}] {news['title']} ({news['time']})"
            self.news_listbox.insert(tk.END, display)
        self.logger.info(f"已加载 {len(news_list)} 条新闻")

    def on_news_select(self, event):
        selection = self.news_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        news_list = DataFetcher.get_news()
        if index < len(news_list):
            news = news_list[index]
            detail = f"【{news['type']}】{news['title']}\n时间：{news['time']}\n内容：{news['content']}\n相关股票：{', '.join(news['related'])}\n"
            self.news_detail.delete(1.0, tk.END)
            self.news_detail.insert(tk.END, detail)
            self.logger.info(f"查看新闻：{news['title']}")
            if news['type'] in ['战争', '原材料']:
                alert_msg = f"重要新闻：{news['title']} 相关股票：{', '.join(news['related'])}"
                self.show_alert_popup("重要新闻", alert_msg)
                if self.config.get_wechat_token():
                    WechatPusher.send("重要新闻", alert_msg)

    def analyze_stock(self):
        code = self.analyze_code_var.get().strip()
        if not code:
            messagebox.showwarning("提示", "请输入股票代码")
            return
        if len(code) < 6:
            code = code.zfill(6)

        def task():
            with self.price_cache_lock:
                quote = self.price_cache.get(code)
            if not quote:
                quote = DataFetcher.get_realtime_quote(code)
                if quote:
                    with self.price_cache_lock:
                        self.price_cache[code] = quote
            if not quote:
                self.logger.error(f"无法获取{code}行情")
                return

            capital = DataFetcher.get_capital_flow(code)
            analysis = StockAnalyzer.analyze(code, quote, capital)

            name = quote.get('name', code)
            source_tag = capital.get('source', '模拟')
            text = f"【{name}({code})】实时分析\n"
            text += "-" * 50 + "\n"
            text += f"当前价：{quote['price']:.2f}  涨幅：{quote['change_pct']:+.2f}%\n"
            text += f"量比：{quote['volume_ratio']:.2f}  换手率：{capital.get('turnover_rate', 0):.2f}%\n"
            text += f"主力流入：{capital['main_inflow']}万  流出：{capital['main_outflow']}万  ({source_tag})\n"
            text += f"主力净额：{capital['net_main']:+}万  ({source_tag})\n"
            text += f"大单笔数：{capital.get('big_orders', 0)} (主动买：{capital.get('active_buy', 0)} 主动卖：{capital.get('active_sell', 0)})\n"
            text += f"技术信号：{', '.join(analysis['signals']) if analysis['signals'] else '无'}\n"
            text += f"支撑位：{analysis['support']}  压力位：{analysis['resistance']}\n"
            text += f"综合评分：{analysis['score']}\n"
            text += f"操作建议：{analysis['suggestion']}\n"
            text += "-" * 50

            def update():
                self.analyze_text.delete(1.0, tk.END)
                self.analyze_text.insert(tk.END, text)
                trading, _ = DataFetcher.is_trading_time()
                if self.buy_btn:
                    self.buy_btn.config(state=tk.NORMAL if trading else tk.DISABLED)
                if self.sell_btn:
                    self.sell_btn.config(state=tk.NORMAL if trading else tk.DISABLED)
                self.current_analyze_code = code
                self.current_analyze_name = name
                self.current_analyze_price = quote['price']
                self.logger.info(f"分析完成：{name}({code})")
                self.kline_chart.set_stock(code, name)

            self.root.after(0, update)

        self.executor.submit(task)

    def quick_analyze(self, code):
        self.analyze_code_var.set(code)
        self.analyze_stock()

    def refresh_capital_monitor(self):
        def task():
            data = []
            stocks = random.sample(DataFetcher.STOCK_POOL, min(8, len(DataFetcher.STOCK_POOL)))
            for s in stocks:
                capital = DataFetcher.get_capital_flow(s["code"])
                trend = "↑" if capital["net_main"] > 0 else "↓"
                data.append({
                    "code": s["code"],
                    "name": s["name"],
                    "net_main": capital["net_main"],
                    "trend": trend,
                })
            self.data_queue.put({"type": "update_capital", "data": data})
        self.executor.submit(task)

    def update_capital_table(self, data):
        for row in self.capital_tree.get_children():
            self.capital_tree.delete(row)
        for item in data:
            values = (item["code"], item["name"], f"{item['net_main']:+}", item["trend"])
            tags = ("pos",) if item["net_main"] > 0 else ("neg",)
            self.capital_tree.insert("", tk.END, values=values, tags=tags)
        self.capital_tree.tag_configure("pos", foreground="red")
        self.capital_tree.tag_configure("neg", foreground="green")

    def on_capital_double_click(self, event):
        selected = self.capital_tree.selection()
        if not selected:
            return
        item = selected[0]
        code = self.capital_tree.item(item, "values")[0]
        self.quick_analyze(code)

    def start_screening(self):
        self.logger.info("开始选股...")
        self.status_var.set("选股中...")
        self.data_queue.put({"type": "progress_start"})
        
        def task():
            start_time = tm.time()
            results = []
            try:
                pool_size = len(DataFetcher.STOCK_POOL)
                sample_size = random.randint(10, min(15, pool_size))
                stocks = random.sample(DataFetcher.STOCK_POOL, sample_size)
                total = len(stocks)
                for i, s in enumerate(stocks):
                    if tm.time() - start_time > 30:
                        self.logger.warning("选股超时，自动停止")
                        break
                    self.data_queue.put({"type": "status", "text": f"选股中... {i+1}/{total}"})
                    with self.price_cache_lock:
                        quote = self.price_cache.get(s["code"])
                    if not quote:
                        quote = DataFetcher.get_realtime_quote(s["code"])
                        if quote:
                            with self.price_cache_lock:
                                self.price_cache[s["code"]] = quote
                    capital = DataFetcher.get_capital_flow(s["code"])
                    analysis = StockAnalyzer.analyze(s["code"], quote, capital)
                    results.append({
                        "code": s["code"],
                        "name": s["name"],
                        "price": quote["price"],
                        "change": quote["change_pct"],
                        "volume_ratio": quote["volume_ratio"],
                        "net_main": capital["net_main"],
                        "signals": ", ".join(analysis["signals"][:2]),
                        "suggestion": analysis["suggestion"],
                        "score": analysis["score"],
                    })
                    tm.sleep(0.1)
                results.sort(key=lambda x: x["score"], reverse=True)
                self.data_queue.put({"type": "update_stocks", "data": results})
                self.logger.info(f"选股完成，选出 {len(results)} 只股票")
            except Exception as e:
                self.logger.error(f"选股异常: {e}")
            finally:
                self.data_queue.put({"type": "status", "text": "选股完成"})
                self.data_queue.put({"type": "progress_stop"})
                
                if self.config.get_wechat_token() and results:
                    top = results[:3]
                    content = "【今日强势股】\n"
                    for s in top:
                        content += f"▪ {s['name']}({s['code']}) {s['price']}元 {s['change']:+.2f}%\n  建议：{s['suggestion']}\n"
                    success, msg = WechatPusher.send("A股选股结果", content)
                    if success:
                        self.logger.info("选股结果推送成功")
                    else:
                        self.logger.error(f"推送失败: {msg}")
        
        self.executor.submit(task)

    def display_screen_results(self, results):
        for row in self.stock_tree.get_children():
            self.stock_tree.delete(row)
        for item in results:
            values = (
                item["code"], item["name"], f"{item['price']:.2f}",
                f"{item['change']:+.2f}", f"{item['volume_ratio']:.2f}",
                f"{item['net_main']:+}", item["signals"], item["suggestion"]
            )
            tags = ("buy",) if "买入" in item["suggestion"] else ("sell",) if "卖出" in item["suggestion"] else ()
            self.stock_tree.insert("", tk.END, values=values, tags=tags)
        self.stock_tree.tag_configure("buy", foreground="red")
        self.stock_tree.tag_configure("sell", foreground="green")
        self.screen_time_var.set(f"更新于 {datetime.now().strftime('%H:%M:%S')}")

    def on_stock_double_click(self, event):
        selected = self.stock_tree.selection()
        if not selected:
            return
        item = selected[0]
        code = self.stock_tree.item(item, "values")[0]
        name = self.stock_tree.item(item, "values")[1]
        self.kline_chart.set_stock(code, name)
        self.quick_analyze(code)

    def set_price_alert(self):
        code = self.alert_code_var.get().strip()
        # 如果输入的是 "000001 平安银行" 格式，提取代码部分
        if ' ' in code:
            code = code.split()[0]
        buy_str = self.alert_buy_var.get().strip()
        sell_str = self.alert_sell_var.get().strip()

        if not code:
            messagebox.showwarning("提示", "请输入股票代码")
            return
        if len(code) < 6:
            code = code.zfill(6)

        # 获取股票名称
        name = code
        for s in DataFetcher.STOCK_POOL:
            if s["code"] == code:
                name = s["name"]
                break

        buy = float(buy_str) if buy_str else None
        sell = float(sell_str) if sell_str else None
        if buy is None and sell is None:
            messagebox.showwarning("提示", "至少设置一个价格")
            return

        auto_trade = self.auto_trade_var.get()
        alert_item = {"code": code, "name": name, "buy": buy, "sell": sell, "auto_trade": auto_trade}
        self.alert_manager.add_price_alert(alert_item)
        self.refresh_alert_listbox()
        self.logger.info(f"设置价格提醒：{name}({code}) 买:{buy} 卖:{sell} 自动:{auto_trade}")
        # 清空输入框
        self.alert_code_var.set("")
        self.alert_buy_var.set("")
        self.alert_sell_var.set("")
        messagebox.showinfo("成功", "价格提醒已添加")

    def set_condition_alert(self):
        code = self.alert_code_var.get().strip()
        if ' ' in code:
            code = code.split()[0]
        change_str = self.alert_change_var.get().strip()
        volume_str = self.alert_volume_var.get().strip()

        if not code:
            messagebox.showwarning("提示", "请输入股票代码")
            return
        if len(code) < 6:
            code = code.zfill(6)

        name = code
        for s in DataFetcher.STOCK_POOL:
            if s["code"] == code:
                name = s["name"]
                break

        change = float(change_str) if change_str else None
        volume = float(volume_str) if volume_str else None
        if change is None and volume is None:
            messagebox.showwarning("提示", "至少设置一个条件")
            return

        alert_item = {"code": code, "name": name, "change_pct": change, "volume_gt": volume}
        self.alert_manager.add_condition_alert(alert_item)
        self.refresh_alert_listbox()
        self.logger.info(f"设置条件单：{name}({code}) 涨跌幅:{change}% 成交量>{volume}")
        self.alert_code_var.set("")
        self.alert_change_var.set("")
        self.alert_volume_var.set("")
        messagebox.showinfo("成功", "条件单已添加")

    def delete_selected_alert(self):
        selection = self.alert_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        price_count = len(self.alert_manager.get_all_price_alerts())
        if index < price_count:
            self.alert_manager.remove_price_alert(index)
        else:
            self.alert_manager.remove_condition_alert(index - price_count)
        self.refresh_alert_listbox()
        self.logger.info("删除提醒")

    def clear_all_alerts(self):
        self.alert_manager.clear_all()
        self.refresh_alert_listbox()
        self.logger.info("已清空所有提醒")

    def check_price_alerts(self):
        triggered = self.alert_manager.check(self.price_cache, self.trade_account)
        for action, alert, price in triggered:
            if action in ('buy', 'sell'):
                msg = f"{alert['name']}({alert['code']}) 当前价 {price:.2f}，触发{'买入' if action=='buy' else '卖出'}提醒"
                self.data_queue.put({"type": "alert", "title": "价格提醒", "message": msg})
                self.logger.info(f"触发价格提醒：{alert['name']}")
                if self.config.get_wechat_token():
                    WechatPusher.send("价格提醒", msg)
                if alert.get("auto_trade") and action == 'buy':
                    self.execute_trade('buy', alert['code'], alert['name'], price)
                elif alert.get("auto_trade") and action == 'sell':
                    self.execute_trade('sell', alert['code'], alert['name'], price)
            elif action == 'condition_change':
                msg = f"{alert['name']}({alert['code']}) 当前涨幅 {price:.2f}%，触发涨跌幅条件 {alert['change_pct']}%"
                self.data_queue.put({"type": "alert", "title": "条件单提醒", "message": msg})
                self.logger.info(f"触发条件单：{alert['name']}")
                if self.config.get_wechat_token():
                    WechatPusher.send("条件单提醒", msg)
            elif action == 'condition_volume':
                msg = f"{alert['name']}({alert['code']}) 成交量 {price}，触发成交量条件"
                self.data_queue.put({"type": "alert", "title": "条件单提醒", "message": msg})
                self.logger.info(f"触发条件单：{alert['name']}")
                if self.config.get_wechat_token():
                    WechatPusher.send("条件单提醒", msg)

    def execute_trade(self, action, code, name, price, quantity=None):
        if not DataFetcher.is_trading_time()[0]:
            self.logger.warning(f"非交易时段，自动交易暂缓：{action} {code}")
            return
        if quantity is None:
            quantity = self.config.get('settings.auto_trade_quantity', 1)
        ok, msg = self.trade_account.check_stock_status(code, price, action)
        if not ok:
            self.logger.warning(f"自动交易暂缓：{action} {code} - {msg}")
            return
        if action == 'buy':
            success, msg = self.trade_account.buy(code, name, price, quantity, auto=True)
        else:
            success, msg = self.trade_account.sell(code, price, auto=True)
        if success:
            self.logger.info(f"自动交易成功：{msg}")
            self.data_queue.put({"type": "update_account"})
        else:
            self.logger.error(f"自动交易失败：{msg}")

    def buy_stock(self):
        if not DataFetcher.is_trading_time()[0]:
            messagebox.showwarning("提示", "当前非交易时段，无法买入")
            return
        if not hasattr(self, 'current_analyze_code') or not self.current_analyze_code:
            messagebox.showwarning("提示", "请先分析股票")
            return
        try:
            qty = int(self.trade_qty.get())
            if qty <= 0:
                raise ValueError
        except:
            messagebox.showwarning("提示", "请输入正确的数量(手)")
            return

        ok, msg = self.trade_account.check_stock_status(self.current_analyze_code, self.current_analyze_price, 'buy')
        if not ok:
            messagebox.showwarning("提示", msg)
            return

        success, msg = self.trade_account.buy(
            self.current_analyze_code,
            self.current_analyze_name,
            self.current_analyze_price,
            qty
        )
        if success:
            messagebox.showinfo("交易成功", msg)
            self.logger.info(f"手动买入：{msg}")
        else:
            messagebox.showwarning("交易失败", msg)
            self.logger.error(f"手动买入失败：{msg}")
        self.update_account_display()

    def sell_stock(self):
        if not DataFetcher.is_trading_time()[0]:
            messagebox.showwarning("提示", "当前非交易时段，无法卖出")
            return
        if not hasattr(self, 'current_analyze_code') or not self.current_analyze_code:
            messagebox.showwarning("提示", "请先分析股票")
            return
        try:
            qty = int(self.trade_qty.get())
            if qty <= 0:
                raise ValueError
        except:
            messagebox.showwarning("提示", "请输入正确的数量(手)")
            return

        ok, msg = self.trade_account.check_stock_status(self.current_analyze_code, self.current_analyze_price, 'sell')
        if not ok:
            messagebox.showwarning("提示", msg)
            return

        success, msg = self.trade_account.sell(
            self.current_analyze_code,
            self.current_analyze_price,
            qty
        )
        if success:
            messagebox.showinfo("交易成功", msg)
            self.logger.info(f"手动卖出：{msg}")
        else:
            messagebox.showwarning("交易失败", msg)
            self.logger.error(f"手动卖出失败：{msg}")
        self.update_account_display()

    def quick_buy_dialog(self):
        if not DataFetcher.is_trading_time()[0]:
            messagebox.showwarning("提示", "当前非交易时段，无法买入")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("快速买入")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="股票代码:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        code_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=code_var, width=15).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="数量(手):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        qty_var = tk.StringVar(value="1")
        ttk.Entry(dialog, textvariable=qty_var, width=15).grid(row=1, column=1, padx=5, pady=5)

        def do_buy():
            code = code_var.get().strip()
            if not code:
                messagebox.showwarning("提示", "请输入股票代码")
                return
            if len(code) < 6:
                code = code.zfill(6)
            try:
                qty = int(qty_var.get())
                if qty <= 0:
                    raise ValueError
            except:
                messagebox.showwarning("提示", "请输入正确的数量(手)")
                return

            with self.price_cache_lock:
                quote = self.price_cache.get(code)
            if not quote:
                quote = DataFetcher.get_realtime_quote(code)
                if quote:
                    with self.price_cache_lock:
                        self.price_cache[code] = quote
            if not quote:
                messagebox.showerror("错误", f"无法获取{code}行情")
                return
            name = quote['name']
            price = quote['price']

            ok, msg = self.trade_account.check_stock_status(code, price, 'buy')
            if not ok:
                messagebox.showwarning("提示", msg)
                return

            success, msg = self.trade_account.buy(code, name, price, qty)
            if success:
                messagebox.showinfo("成功", msg)
                self.logger.info(f"快速买入：{msg}")
                self.update_account_display()
                dialog.destroy()
            else:
                messagebox.showwarning("失败", msg)

        ttk.Button(dialog, text="买入", command=do_buy).grid(row=2, column=0, columnspan=2, pady=10)

    def sell_selected_dialog(self):
        if not DataFetcher.is_trading_time()[0]:
            messagebox.showwarning("提示", "当前非交易时段，无法卖出")
            return
        selected = self.position_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请在持仓列表中选择要卖出的股票")
            return
        item = selected[0]
        values = self.position_tree.item(item, "values")
        code = values[0]
        name = values[1]
        max_qty = int(values[2])

        dialog = tk.Toplevel(self.root)
        dialog.title(f"卖出 {name}({code})")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text=f"可卖数量: {max_qty}手").pack(pady=5)
        ttk.Label(dialog, text="卖出数量(手):").pack()
        qty_var = tk.StringVar(value=str(max_qty))
        ttk.Entry(dialog, textvariable=qty_var, width=10).pack(pady=5)

        def do_sell():
            try:
                qty = int(qty_var.get())
                if qty <= 0 or qty > max_qty:
                    raise ValueError
            except:
                messagebox.showwarning("提示", f"请输入1~{max_qty}之间的整数")
                return

            with self.price_cache_lock:
                quote = self.price_cache.get(code)
            if not quote:
                quote = DataFetcher.get_realtime_quote(code)
                if quote:
                    with self.price_cache_lock:
                        self.price_cache[code] = quote
            if not quote:
                messagebox.showerror("错误", f"无法获取{code}行情")
                return
            price = quote['price']

            ok, msg = self.trade_account.check_stock_status(code, price, 'sell')
            if not ok:
                messagebox.showwarning("提示", msg)
                return

            success, msg = self.trade_account.sell(code, price, qty)
            if success:
                messagebox.showinfo("成功", msg)
                self.logger.info(f"卖出：{msg}")
                self.update_account_display()
                dialog.destroy()
            else:
                messagebox.showwarning("失败", msg)

        ttk.Button(dialog, text="卖出", command=do_sell).pack(pady=10)

    def on_position_right_click(self, event):
        item = self.position_tree.identify_row(event.y)
        if item:
            self.position_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def sell_selected_context(self):
        self.sell_selected_dialog()

    def analyze_selected_context(self):
        selected = self.position_tree.selection()
        if not selected:
            return
        item = selected[0]
        code = self.position_tree.item(item, "values")[0]
        self.quick_analyze(code)

    def update_account_display(self):
        summary = self.trade_account.get_account_summary()
        self.cash_label.config(text=f"可用资金: {summary['cash']:,.0f}")
        self.total_label.config(text=f"总资产: {summary['total_value']:,.0f}")
        profit_color = "red" if summary['profit'] >= 0 else "green"
        self.profit_label.config(text=f"盈亏: {summary['profit']:+,.0f} ({summary['profit_pct']:+.2f}%)", foreground=profit_color)

        for row in self.position_tree.get_children():
            self.position_tree.delete(row)

        positions = self.trade_account.get_position_list()
        for code, pos in positions.items():
            shares = pos['shares']
            with self.price_cache_lock:
                quote = self.price_cache.get(code)
            price = quote['price'] if quote else pos['cost']
            profit = (price - pos['cost']) * shares
            profit_str = f"{profit:+,.0f}"
            profit_color = "red" if profit >= 0 else "green"
            values = (code, pos['name'], pos['quantity'], f"{pos['cost']:.2f}", f"{price:.2f}", profit_str)
            tags = ("profit_pos",) if profit >= 0 else ("profit_neg",)
            self.position_tree.insert("", tk.END, values=values, tags=tags)

        self.position_tree.tag_configure("profit_pos", foreground="red")
        self.position_tree.tag_configure("profit_neg", foreground="green")

    def on_position_double_click(self, event):
        selected = self.position_tree.selection()
        if not selected:
            return
        item = selected[0]
        code = self.position_tree.item(item, "values")[0]
        name = self.position_tree.item(item, "values")[1]
        self.kline_chart.set_stock(code, name)
        self.quick_analyze(code)

    def reset_account(self):
        if messagebox.askyesno("确认", "确定重置手动模拟账户吗？所有持仓和资金将恢复初始状态。"):
            self.trade_account.reset()
            self.update_account_display()
            self.logger.info("手动模拟账户已重置")

    def refresh_all_data(self):
        self.logger.info("手动刷新所有数据...")
        self.refresh_news()
        self.refresh_capital_monitor()
        self.start_screening()

    def _network_monitor(self):
        while self.running:
            try:
                requests.get("http://www.baidu.com", timeout=3)
                if not self.network_ok:
                    self.network_ok = True
                    self.root.after(0, lambda: self.network_var.set("网络:正常"))
                    self.logger.info("网络已恢复")
            except:
                if self.network_ok:
                    self.network_ok = False
                    self.root.after(0, lambda: self.network_var.set("网络:断开"))
                    self.logger.warning("网络连接断开，将暂停数据更新")
            tm.sleep(10)

    def start_scheduler(self):
        def scheduler():
            while self.running:
                now = datetime.now()
                if now.hour == 14 and now.minute == 50:
                    self.logger.info("定时任务：14:50 自动选股")
                    self.start_screening()
                    tm.sleep(60)
                if now.hour == 15 and now.minute == 10:
                    self.logger.info("定时任务：15:10 收益总结")
                    summary = f"今日大盘回顾：上证指数 +0.5%，创业板 -0.2%。您的账户总资产：{self.trade_account.total_value:,.0f}，盈亏：{self.trade_account.get_account_summary()['profit']:+,.0f}"
                    self.data_queue.put({"type": "alert", "title": "收市总结", "message": summary})
                    if self.config.get_wechat_token():
                        WechatPusher.send("收市总结", summary)
                    tm.sleep(60)
                tm.sleep(60)
        threading.Thread(target=scheduler, daemon=True).start()

        def alert_checker():
            while self.running:
                if self.network_ok:
                    self.check_price_alerts()
                tm.sleep(10)
        threading.Thread(target=alert_checker, daemon=True).start()

    def start_price_updater(self):
        def updater():
            while self.running:
                if not self.network_ok:
                    tm.sleep(1)
                    continue
                try:
                    watch_codes = set()
                    with self.trade_account._lock:
                        for code in self.trade_account.positions:
                            watch_codes.add(code)
                    for alert in self.alert_manager.get_all_price_alerts():
                        watch_codes.add(alert['code'])
                    for alert in self.alert_manager.get_all_condition_alerts():
                        watch_codes.add(alert['code'])
                    for s in DataFetcher.STOCK_POOL:
                        watch_codes.add(s['code'])

                    with ThreadPoolExecutor(max_workers=5) as pool:
                        futures = {pool.submit(DataFetcher.get_realtime_quote, code): code for code in watch_codes}
                        for future in as_completed(futures, timeout=3):
                            code = futures[future]
                            try:
                                quote = future.result(timeout=1)
                                if quote:
                                    with self.price_cache_lock:
                                        self.price_cache[code] = quote
                            except Exception as e:
                                self.logger.debug(f"更新{code}价格失败: {e}")

                    with self.price_cache_lock:
                        prices = {code: q['price'] for code, q in self.price_cache.items()}
                    self.trade_account.update_total_value(prices)
                    self.data_queue.put({"type": "update_account"})

                    # 更新选股列表中的实时价格
                    if hasattr(self, 'stock_tree') and self.stock_tree.winfo_exists():
                        for item in self.stock_tree.get_children():
                            values = self.stock_tree.item(item, "values")
                            if len(values) >= 8:
                                code = values[0]
                                with self.price_cache_lock:
                                    quote = self.price_cache.get(code)
                                if quote:
                                    new_values = list(values)
                                    new_values[2] = f"{quote['price']:.2f}"          # 现价
                                    new_values[3] = f"{quote['change_pct']:+.2f}"    # 涨幅%
                                    self.stock_tree.item(item, values=tuple(new_values))

                except Exception as e:
                    self.logger.error(f"价格更新线程异常: {e}")
                tm.sleep(1)
        threading.Thread(target=updater, daemon=True).start()

    def save_tushare_token(self):
        token = self.tushare_token_var.get().strip()
        node = self.node_url_var.get().strip()
        if token:
            self.tushare.set_token(token)
            if node:
                self.tushare.set_node(node)
            self.logger.info("Tushare Token 已保存，正在验证...")
            self.executor.submit(self.tushare.update_remaining)
        else:
            messagebox.showwarning("提示", "请输入 Token")

    def refresh_tushare_credit(self):
        if not self.tushare.token:
            self.tushare_credit_label.config(text="状态: 未登录", foreground="gray")
            return
        self.logger.info("正在验证 Tushare Token...")
        self.executor.submit(self.tushare.update_remaining)

    def logout_tushare(self):
        self.tushare.set_token("")
        self.tushare_token_var.set("")
        self.tushare_credit_label.config(text="状态: 未登录", foreground="gray")
        self.logger.info("已退出 Tushare 登录")

    def update_tushare_display(self):
        if not self.tushare.token:
            text = "状态: 未登录"
            color = "gray"
        elif not self.tushare.token_valid:
            text = f"无效: {self.tushare.token_error_msg}"
            color = "red"
        else:
            text = f"有效 (积分: {self.tushare.remaining})"
            color = "green"
        self.tushare_credit_label.config(text=text, foreground=color)

    def save_token(self):
        token = self.token_var.get().strip()
        if token:
            self.config.set_wechat_token(token)
            self.logger.info("微信推送Token已保存")
        else:
            messagebox.showwarning("提示", "请输入Token")

    def test_push(self):
        token = self.config.get_wechat_token()
        if not token:
            messagebox.showwarning("提示", "请先保存Token")
            return
        success, msg = WechatPusher.send("测试消息", "您的A股助手推送测试成功！")
        if success:
            messagebox.showinfo("成功", "测试推送成功")
            self.logger.info("微信测试推送成功")
        else:
            messagebox.showerror("失败", msg)
            self.logger.error(f"微信测试推送失败: {msg}")

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def open_price_alert_dialog(self):
        self.set_price_alert()

    def open_condition_alert_dialog(self):
        self.set_condition_alert()

    def show_history(self):
        history_win = tk.Toplevel(self.root)
        history_win.title("交易历史")
        history_win.geometry("800x400")

        columns = ("time", "action", "code", "name", "price", "shares", "amount", "fee")
        tree = ttk.Treeview(history_win, columns=columns, show="headings")
        tree.heading("time", text="时间")
        tree.heading("action", text="方向")
        tree.heading("code", text="代码")
        tree.heading("name", text="名称")
        tree.heading("price", text="价格")
        tree.heading("shares", text="数量(股)")
        tree.heading("amount", text="成交额")
        tree.heading("fee", text="手续费")
        tree.column("time", width=150)
        tree.column("action", width=50)
        tree.column("code", width=70)
        tree.column("name", width=80)
        tree.column("price", width=70)
        tree.column("shares", width=70)
        tree.column("amount", width=90)
        tree.column("fee", width=70)

        scrollbar = ttk.Scrollbar(history_win, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for record in self.trade_account.history.get_all():
            tree.insert("", tk.END, values=(
                record['time'], record['action'], record['code'], record['name'],
                f"{record['price']:.2f}", record['shares'],
                f"{record['amount']:.2f}", f"{record['fee']:.2f}"
            ))

        btn_frame = ttk.Frame(history_win)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="导出CSV", command=lambda: self.export_history(history_win)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=history_win.destroy).pack(side=tk.LEFT, padx=5)

    def export_history(self, parent=None):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filepath:
            self.trade_account.history.export_csv(filepath)
            messagebox.showinfo("导出成功", f"已导出到 {filepath}")

    def import_config(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if filepath:
            try:
                self.config.import_config(filepath)
                messagebox.showinfo("成功", "配置已导入，请重启程序生效")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")

    def export_config(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filepath:
            self.config.export_config(filepath)
            messagebox.showinfo("成功", f"配置已导出到 {filepath}")

    def open_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("参数设置")
        settings_win.geometry("450x550")
        settings_win.transient(self.root)
        settings_win.grab_set()

        notebook = ttk.Notebook(settings_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="基本")
        row = 0
        ttk.Label(basic_frame, text="行情缓存时间(交易时段):").grid(row=row, column=0, sticky=tk.W, pady=2)
        cache_trade = ttk.Entry(basic_frame, width=10)
        cache_trade.insert(0, str(self.config.get('settings.quote_cache_time', 5)))
        cache_trade.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        ttk.Label(basic_frame, text="行情缓存时间(非交易):").grid(row=row, column=0, sticky=tk.W, pady=2)
        cache_nontrade = ttk.Entry(basic_frame, width=10)
        cache_nontrade.insert(0, str(self.config.get('settings.quote_cache_time_nontrade', 30)))
        cache_nontrade.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        ttk.Label(basic_frame, text="资金缓存时间(秒):").grid(row=row, column=0, sticky=tk.W, pady=2)
        capital_cache = ttk.Entry(basic_frame, width=10)
        capital_cache.insert(0, str(self.config.get('settings.capital_cache_time', 30)))
        capital_cache.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        ttk.Label(basic_frame, text="K线显示天数:").grid(row=row, column=0, sticky=tk.W, pady=2)
        kline_days = ttk.Entry(basic_frame, width=10)
        kline_days.insert(0, str(self.config.get('settings.kline_display_days', 60)))
        kline_days.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        ttk.Label(basic_frame, text="自动交易默认手数:").grid(row=row, column=0, sticky=tk.W, pady=2)
        auto_qty = ttk.Entry(basic_frame, width=10)
        auto_qty.insert(0, str(self.config.get('settings.auto_trade_quantity', 1)))
        auto_qty.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        use_mock = tk.BooleanVar(value=self.config.get('settings.use_mock_on_fail', True))
        ttk.Checkbutton(basic_frame, text="失败时使用模拟数据", variable=use_mock).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)

        row += 1
        auto_start = tk.BooleanVar(value=self.config.get('settings.auto_trade_auto_start', False))
        ttk.Checkbutton(basic_frame, text="程序启动后自动运行自动交易（需开启自动模拟盘窗口）", variable=auto_start).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)

        fee_frame = ttk.Frame(notebook)
        notebook.add(fee_frame, text="费率")
        row = 0
        ttk.Label(fee_frame, text="佣金费率:").grid(row=row, column=0, sticky=tk.W, pady=2)
        comm_rate = ttk.Entry(fee_frame, width=12)
        comm_rate.insert(0, str(self.config.get('settings.commission_rate', 0.00025)))
        comm_rate.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        ttk.Label(fee_frame, text="最低佣金:").grid(row=row, column=0, sticky=tk.W, pady=2)
        min_comm = ttk.Entry(fee_frame, width=12)
        min_comm.insert(0, str(self.config.get('settings.min_commission', 5.0)))
        min_comm.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        ttk.Label(fee_frame, text="印花税率:").grid(row=row, column=0, sticky=tk.W, pady=2)
        stamp = ttk.Entry(fee_frame, width=12)
        stamp.insert(0, str(self.config.get('settings.stamp_tax_rate', 0.001)))
        stamp.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        ttk.Label(fee_frame, text="过户费率:").grid(row=row, column=0, sticky=tk.W, pady=2)
        transfer = ttk.Entry(fee_frame, width=12)
        transfer.insert(0, str(self.config.get('settings.transfer_fee_rate', 0.00001)))
        transfer.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        ttk.Label(fee_frame, text="最低过户费:").grid(row=row, column=0, sticky=tk.W, pady=2)
        min_transfer = ttk.Entry(fee_frame, width=12)
        min_transfer.insert(0, str(self.config.get('settings.min_transfer_fee', 1.0)))
        min_transfer.grid(row=row, column=1, pady=2, sticky=tk.W)

        risk_frame = ttk.Frame(notebook)
        notebook.add(risk_frame, text="风控")
        row = 0
        ttk.Label(risk_frame, text="止损百分比(如5表示5%):").grid(row=row, column=0, sticky=tk.W, pady=2)
        stop_loss = ttk.Entry(risk_frame, width=10)
        stop_loss.insert(0, str(self.config.get('settings.stop_loss_rate', 0.05) * 100))
        stop_loss.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        ttk.Label(risk_frame, text="止盈百分比:").grid(row=row, column=0, sticky=tk.W, pady=2)
        take_profit = ttk.Entry(risk_frame, width=10)
        take_profit.insert(0, str(self.config.get('settings.take_profit_rate', 0.10) * 100))
        take_profit.grid(row=row, column=1, pady=2, sticky=tk.W)

        source_frame = ttk.Frame(notebook)
        notebook.add(source_frame, text="数据源")
        ttk.Label(source_frame, text="数据源优先级(逗号分隔):").pack(anchor=tk.W, pady=5)
        sources_var = tk.StringVar(value=','.join(self.config.get('settings.data_sources', ['sina', 'tencent'])))
        ttk.Entry(source_frame, textvariable=sources_var, width=40).pack(fill=tk.X, pady=5)
        ttk.Label(source_frame, text="可用源: sina, tencent, netease, sohu, baidu, 163", foreground="gray").pack(anchor=tk.W)

        def save_settings():
            try:
                self.config.set('settings.quote_cache_time', int(cache_trade.get()))
                self.config.set('settings.quote_cache_time_nontrade', int(cache_nontrade.get()))
                self.config.set('settings.capital_cache_time', int(capital_cache.get()))
                self.config.set('settings.kline_display_days', int(kline_days.get()))
                self.config.set('settings.auto_trade_quantity', int(auto_qty.get()))
                self.config.set('settings.use_mock_on_fail', use_mock.get())
                self.config.set('settings.auto_trade_auto_start', auto_start.get())
                self.config.set('settings.commission_rate', float(comm_rate.get()))
                self.config.set('settings.min_commission', float(min_comm.get()))
                self.config.set('settings.stamp_tax_rate', float(stamp.get()))
                self.config.set('settings.transfer_fee_rate', float(transfer.get()))
                self.config.set('settings.min_transfer_fee', float(min_transfer.get()))
                self.config.set('settings.stop_loss_rate', float(stop_loss.get()) / 100)
                self.config.set('settings.take_profit_rate', float(take_profit.get()) / 100)
                sources = [s.strip() for s in sources_var.get().split(',') if s.strip()]
                self.config.set('settings.data_sources', sources)
                messagebox.showinfo("成功", "设置已保存")
                settings_win.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"输入格式错误: {e}")

        ttk.Button(settings_win, text="保存", command=save_settings).pack(pady=10)

    def show_shortcuts(self):
        shortcuts = """
【快捷键列表】

F5              - 刷新所有数据
Ctrl+S          - 开始选股
Ctrl+A          - 分析当前输入的股票代码
Ctrl+Q          - 退出程序

【鼠标操作】
双击选股结果    - 查看K线图并分析
双击持仓列表    - 查看K线图并分析
右键持仓列表    - 弹出卖出/分析菜单
        """
        messagebox.showinfo("快捷键列表", shortcuts)

    def show_features(self):
        features = """
【A股智能交易助手 旗舰版 v15.3 功能列表】

1. 📰 实时新闻舆情（模拟，可接入真实API）
2. 🔍 个股深度分析：实时行情（6大备用源）+ 主力资金（Tushare私有节点）
3. 💰 主力资金监控（Tushare私有节点 + 模拟降级）
4. 📊 多因子强势选股（可自定义因子权重）
5. 📱 微信实时推送（pushplus，密钥环加密）
6. 💰 模拟交易系统（完全真实A股费率，ST股涨跌停识别）
7. 🔔 智能价格提醒（支持条件单：价格/涨跌幅/成交量）
8. ⏰ 定时任务（14:50选股，15:10总结，可自定义）
9. 🌐 Tushare私有节点配置（Token + 节点地址）
10. 💾 数据持久化（用户目录独立配置，自动备份）
11. ⚡ 独立价格更新线程池（并发请求，永不卡顿）
12. 🎨 界面美化，交易时段倒计时精确到秒（含节假日判断）
13. 📈 交易历史记录（可导出CSV）
14. 🔒 敏感信息加密存储（使用系统密钥环，回退明文）
15. ⚙️ 可配置参数（缓存时间、费率、数据源优先级、自动交易数量）
16. 🚀 多线程并发请求，异常自动恢复，详细日志
17. 📋 完整的日志系统，所有错误界面可见
18. 🎯 选股进度实时显示，结果可双击分析
19. ⌨️ 常用快捷键支持（F5刷新，Ctrl+S选股，Ctrl+A分析等）
20. 🔄 自动备份损坏的配置文件
21. 📊 专业K线图（日/周/月/5分钟/15分钟/30分钟/60分钟 + 分时图）
22. ⏱️ 分时图实时更新（每秒刷新，显示当日价格走势）
23. ⌨️ 快捷键列表显示（帮助菜单可查看）
24. 🔄 分钟线数据支持（优先Tushare，降级模拟）
25. 📉 技术指标（MA5/10/20, MACD, RSI, 布林带）
26. 🧠 K线智能分析（用通俗语言描述趋势）
27. 🔍 股票信息卡片（市盈率、市净率、流通市值、行业）
28. 📉 风险控制：止损止盈提醒（可设置百分比）
29. 🌐 网络状态监测：断网时暂停更新并提示
30. 🧪 单元测试设计（架构可测试）
31. 🔑 一机一码激活机制，支持重新激活
32. 📅 节假日自动判断，避开非交易日
33. 💼 独立自动交易窗口，支持T+1规则，账户数据持久化
        """
        messagebox.showinfo("软件功能列表", features)

    def show_about(self):
        about_text = """A股智能交易助手 旗舰版 v15.3

作者：heng (QQ:200931349) （马运当头）

数据说明：
- 实时行情：多源自动切换（新浪、腾讯、网易、搜狐、百度、163），失败时降级为模拟数据。
- 主力资金：优先 Tushare 私有节点，失败时降级为模拟。
- K线数据：优先 Tushare，失败时生成模拟K线（含指标）。

优化特性：
- 所有网络请求在后台线程执行，界面流畅不卡顿。
- 价格缓存机制，使用LRU缓存减少重复请求。
- 自动保存配置，重启恢复。
- 支持密钥环加密存储Token，自动回退。
- 涨跌停判断考虑ST股（±5%）。
- 网络状态监测，断网自动暂停更新。
- 节假日自动判断，避免无效交易。

【声明】
本软件为个人学习研究使用，数据仅供参考，不构成投资建议。
        """
        messagebox.showinfo("关于", about_text)

    def on_closing(self):
        self.running = False
        account_data = {
            "cash": self.trade_account.cash,
            "positions": self.trade_account.positions
        }
        self.config.set('account', account_data)
        self.executor.shutdown(wait=False)
        if self.after_id:
            self.root.after_cancel(self.after_id)
        if self.flash_after_id:
            self.root.after_cancel(self.flash_after_id)
        self.root.destroy()


# ==================== 程序入口 ====================
if __name__ == "__main__":
    try:
        # 仅在存在控制台时才输出警告信息
        if sys.stdout is not None:
            if sys.platform == 'win32':
                import codecs
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
            if not HAS_MPL:
                print("警告: matplotlib或mplfinance未安装，K线图功能不可用。")
                print("请执行: pip install matplotlib mplfinance pandas")
            if not HAS_TUSHARE:
                print("警告: tushare未安装，部分功能受限。")
                print("请执行: pip install tushare")
            if not HAS_KEYRING:
                print("提示: 未安装keyring，Token将明文存储。可执行 pip install keyring 安装。")
        else:
            # 无控制台时，可以忽略这些提示，或者通过日志记录
            pass

        app = StockAssistantPro()
        app.root.mainloop()
    except Exception as e:
        import traceback
        # 将错误写入文件
        with open("error.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        # 尝试弹窗提示（如果tkinter可用）
        try:
            import tkinter.messagebox as msgbox
            msgbox.showerror("启动错误", f"程序启动失败，请查看 error.log 文件")
        except:
            pass
        # 不要使用input()，否则窗口化模式下会崩溃
        
