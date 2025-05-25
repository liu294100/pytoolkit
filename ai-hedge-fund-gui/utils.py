"""工具函数模块，提供各种辅助功能。"""

import os
import json
import pickle
import hashlib
import datetime
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from config import CACHE_CONFIG, CHART_CONFIG


def format_currency(value: float) -> str:
    """将数值格式化为货币字符串。"""
    return f"${value:,.2f}"


def format_percentage(value: float) -> str:
    """将数值格式化为百分比字符串。"""
    return f"{value:.2f}%"


def format_date(date_str: str) -> str:
    """格式化日期字符串为更易读的格式。"""
    try:
        date_obj = pd.to_datetime(date_str)
        return date_obj.strftime("%Y年%m月%d日")
    except:
        return date_str


def get_relative_date(days_ago: int) -> str:
    """获取相对于今天的日期字符串，格式为YYYY-MM-DD。"""
    today = datetime.datetime.now()
    target_date = today - datetime.timedelta(days=days_ago)
    return target_date.strftime("%Y-%m-%d")


def create_cache_key(params: Dict[str, Any]) -> str:
    """根据参数创建缓存键。"""
    # 将参数转换为排序后的JSON字符串
    param_str = json.dumps(params, sort_keys=True)
    # 创建MD5哈希
    return hashlib.md5(param_str.encode()).hexdigest()


def get_from_cache(cache_key: str) -> Optional[Any]:
    """从缓存中获取数据。"""
    if not CACHE_CONFIG["enable"]:
        return None
        
    # 确保缓存目录存在
    cache_dir = CACHE_CONFIG["directory"]
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        
    cache_file = os.path.join(cache_dir, f"{cache_key}.pkl")
    
    # 检查缓存文件是否存在且未过期
    if os.path.exists(cache_file):
        file_age = datetime.datetime.now().timestamp() - os.path.getmtime(cache_file)
        if file_age < CACHE_CONFIG["max_age"]:
            try:
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception:
                # 如果加载失败，返回None
                return None
    return None


def save_to_cache(cache_key: str, data: Any) -> None:
    """将数据保存到缓存。"""
    if not CACHE_CONFIG["enable"]:
        return
        
    # 确保缓存目录存在
    cache_dir = CACHE_CONFIG["directory"]
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        
    cache_file = os.path.join(cache_dir, f"{cache_key}.pkl")
    
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)
    except Exception:
        # 如果保存失败，忽略错误
        pass


def create_stock_chart(stock_data: pd.DataFrame, title: str = "股票价格走势") -> Figure:
    """创建股票价格走势图。
    
    Args:
        stock_data: 包含日期和价格数据的DataFrame
        title: 图表标题
        
    Returns:
        matplotlib Figure对象
    """
    fig, ax = plt.subplots(figsize=CHART_CONFIG["figsize"], dpi=CHART_CONFIG["dpi"])
    
    # 绘制收盘价
    ax.plot(
        stock_data.index, 
        stock_data["Close"], 
        linewidth=CHART_CONFIG["line_width"],
        color=CHART_CONFIG["colors"][0],
        marker="o",
        markersize=CHART_CONFIG["marker_size"]
    )
    
    # 设置标题和标签
    ax.set_title(title, fontsize=CHART_CONFIG["figsize"][0] * 1.5)
    ax.set_xlabel("日期")
    ax.set_ylabel("价格 ($)")
    
    # 设置网格
    ax.grid(True, linestyle="--", alpha=0.7)
    
    # 旋转x轴标签以避免重叠
    plt.xticks(rotation=45)
    
    # 自动调整布局
    fig.tight_layout()
    
    return fig


def create_comparison_chart(data: Dict[str, pd.DataFrame], title: str = "股票比较") -> Figure:
    """创建多只股票的比较图表。
    
    Args:
        data: 字典，键为股票代码，值为包含价格数据的DataFrame
        title: 图表标题
        
    Returns:
        matplotlib Figure对象
    """
    fig, ax = plt.subplots(figsize=CHART_CONFIG["figsize"], dpi=CHART_CONFIG["dpi"])
    
    # 对每只股票进行归一化处理，使其起始价格为100
    normalized_data = {}
    for ticker, df in data.items():
        if not df.empty:
            normalized = df.copy()
            first_price = normalized["Close"].iloc[0]
            normalized["Close"] = normalized["Close"] / first_price * 100
            normalized_data[ticker] = normalized
    
    # 绘制每只股票的归一化价格
    for i, (ticker, df) in enumerate(normalized_data.items()):
        color_idx = i % len(CHART_CONFIG["colors"])
        ax.plot(
            df.index, 
            df["Close"], 
            linewidth=CHART_CONFIG["line_width"],
            color=CHART_CONFIG["colors"][color_idx],
            label=ticker
        )
    
    # 设置标题和标签
    ax.set_title(title, fontsize=CHART_CONFIG["figsize"][0] * 1.5)
    ax.set_xlabel("日期")
    ax.set_ylabel("归一化价格 (起始=100)")
    
    # 添加图例
    ax.legend()
    
    # 设置网格
    ax.grid(True, linestyle="--", alpha=0.7)
    
    # 旋转x轴标签以避免重叠
    plt.xticks(rotation=45)
    
    # 自动调整布局
    fig.tight_layout()
    
    return fig


def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本，确保不超过最大长度。"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def validate_api_key(api_key: str, api_type: str = "openai") -> bool:
    """验证API密钥格式是否有效。
    
    注意：此函数仅验证格式，不验证API密钥是否能正常工作。
    """
    if not api_key or len(api_key.strip()) == 0:
        return False
        
    if api_type == "openai":
        # OpenAI API密钥通常以sk-开头
        return api_key.startswith("sk-") and len(api_key) > 20
    
    # 对于其他API类型，只要不为空即可
    return True


def parse_tickers(ticker_input: str) -> List[str]:
    """解析用户输入的股票代码字符串，返回规范化的股票代码列表。"""
    if not ticker_input or len(ticker_input.strip()) == 0:
        return []
        
    # 分割输入字符串，支持逗号、空格、分号等分隔符
    tickers = [t.strip() for t in ticker_input.replace(",", " ").replace(";", " ").split()]
    
    # 过滤空字符串并转换为大写
    tickers = [t.upper() for t in tickers if t]
    
    # 去重
    return list(dict.fromkeys(tickers))


def parse_stock_tickers(ticker_input: str) -> List[str]:
    """解析用户输入的股票代码字符串，返回规范化的股票代码列表。"""
    if not ticker_input or len(ticker_input.strip()) == 0:
        return []
        
    # 分割输入字符串，支持逗号、空格、分号等分隔符
    tickers = [t.strip() for t in ticker_input.replace(",", " ").replace(";", " ").split()]
    
    # 过滤空字符串并转换为大写
    tickers = [t.upper() for t in tickers if t]
    
    # 去重
    return list(dict.fromkeys(tickers))