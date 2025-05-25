"""配置文件，用于存储应用程序的默认设置和常量。"""

# 默认股票列表
DEFAULT_STOCKS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

# 默认日期范围（相对于当前日期的天数）
DEFAULT_START_DAYS = 365  # 一年前
DEFAULT_END_DAYS = 0      # 今天

# 智能体配置
AGENTS = {
    "Warren Buffett": {
        "name": "Warren Buffett",
        "description": "价值投资专家，寻找优质公司的合理价格",
        "icon": "💼",
        "enabled": True
    },
    "Cathie Wood": {
        "name": "Cathie Wood",
        "description": "成长投资专家，关注创新和颠覆性技术",
        "icon": "🚀",
        "enabled": True
    },
    "Technical Analyst": {
        "name": "Technical Analyst",
        "description": "技术分析专家，基于价格走势和技术指标",
        "icon": "📊",
        "enabled": True
    }
}

# UI配置
UI_CONFIG = {
    "title": "AI Hedge Fund GUI",
    "width": 1200,
    "height": 800,
    "theme": "default",  # 可选: "default", "dark", "light"
    "font": {
        "family": "Arial",
        "size": 10,
        "title_size": 14,
        "header_size": 12
    },
    "colors": {
        "primary": "#3498db",
        "secondary": "#2ecc71",
        "accent": "#9b59b6",
        "background": "#f9f9f9",
        "text": "#333333"
    }
}

# API配置
API_CONFIG = {
    "openai": {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000
    },
    "ollama": {
        "model": "llama3",
        "temperature": 0.7,
        "max_tokens": 2000
    },
    "deepseek": {
        "model": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 2000
    },
    "claude": {
        "model": "claude-3-opus-20240229",
        "temperature": 0.7,
        "max_tokens": 2000
    },
    "gemini": {
        "model": "gemini-pro",
        "temperature": 0.7,
        "max_tokens": 2000
    }
}

# 图表配置
CHART_CONFIG = {
    "line_width": 2,
    "marker_size": 5,
    "dpi": 100,
    "figsize": (10, 6),
    "colors": ["#3498db", "#2ecc71", "#e74c3c", "#f39c12", "#9b59b6"]
}

# 缓存配置
CACHE_CONFIG = {
    "enable": True,
    "max_age": 86400,  # 缓存有效期（秒），默认1天
    "directory": "cache"
}