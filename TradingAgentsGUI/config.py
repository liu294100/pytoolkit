"""Configuration settings for TradingAgents GUI application."""

import os
import json
from typing import Dict, Any

# Default configuration for TradingAgents
DEFAULT_CONFIG = {
    # LLM Configuration
    "deep_think_llm": "gpt-4o",
    "quick_think_llm": "gpt-4o-mini", 
    "temperature": 0.1,
    "max_tokens": 4000,
    
    # Agent Configuration
    "max_debate_rounds": 2,
    "online_tools": True,
    "enable_risk_management": True,
    "enable_portfolio_tracking": True,
    
    # Data Sources
    "data_provider": "finnhub",
    "use_cached_data": False,
    "cache_duration_hours": 24,
    
    # Trading Parameters
    "default_position_size": 100,
    "max_position_size": 1000,
    "risk_tolerance": "medium",  # low, medium, high
    "stop_loss_percentage": 0.05,  # 5%
    "take_profit_percentage": 0.15,  # 15%
    
    # GUI Settings
    "theme": "dark",
    "language": "en",  # Default language: en (English), zh (Chinese)
    "auto_refresh_interval": 5,  # seconds
    "log_level": "INFO",
    "max_log_entries": 1000,
    
    # API Settings
    "api_timeout": 30,  # seconds
    "max_retries": 3,
    "retry_delay": 1,  # seconds
}

# Available LLM models
AVAILABLE_MODELS = [
    "gpt-4o",
    "gpt-4o-mini", 
    "o1-preview",
    "o1-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo"
]

# Risk tolerance levels
RISK_LEVELS = {
    "low": {
        "max_position_percentage": 0.05,  # 5% of portfolio
        "stop_loss_percentage": 0.03,     # 3%
        "take_profit_percentage": 0.08,   # 8%
        "max_drawdown_limit": 0.02        # 2%
    },
    "medium": {
        "max_position_percentage": 0.10,  # 10% of portfolio
        "stop_loss_percentage": 0.05,     # 5%
        "take_profit_percentage": 0.15,   # 15%
        "max_drawdown_limit": 0.05        # 5%
    },
    "high": {
        "max_position_percentage": 0.20,  # 20% of portfolio
        "stop_loss_percentage": 0.08,     # 8%
        "take_profit_percentage": 0.25,   # 25%
        "max_drawdown_limit": 0.10        # 10%
    }
}

# Agent roles and descriptions
AGENT_ROLES = {
    "fundamental_analyst": {
        "name": "📈 Fundamental Analyst",
        "description": "Analyzes company financials, earnings, and fundamental metrics",
        "tools": ["financial_data", "earnings_reports", "balance_sheet"],
        "priority": 1
    },
    "sentiment_analyst": {
        "name": "😊 Sentiment Analyst", 
        "description": "Analyzes market sentiment from social media and news",
        "tools": ["social_media", "sentiment_scoring", "news_sentiment"],
        "priority": 1
    },
    "news_analyst": {
        "name": "📰 News Analyst",
        "description": "Monitors news events and macroeconomic indicators",
        "tools": ["news_feeds", "economic_calendar", "event_analysis"],
        "priority": 1
    },
    "technical_analyst": {
        "name": "📊 Technical Analyst",
        "description": "Performs technical analysis using charts and indicators",
        "tools": ["price_data", "technical_indicators", "chart_patterns"],
        "priority": 1
    },
    "bull_researcher": {
        "name": "🐂 Bull Researcher",
        "description": "Researches bullish factors and growth opportunities",
        "tools": ["growth_analysis", "opportunity_assessment"],
        "priority": 2
    },
    "bear_researcher": {
        "name": "🐻 Bear Researcher",
        "description": "Researches bearish factors and potential risks",
        "tools": ["risk_analysis", "threat_assessment"],
        "priority": 2
    },
    "trader": {
        "name": "💼 Trader Agent",
        "description": "Makes trading decisions based on all analysis",
        "tools": ["decision_engine", "position_sizing", "timing_analysis"],
        "priority": 3
    },
    "risk_manager": {
        "name": "🛡️ Risk Manager",
        "description": "Manages portfolio risk and validates decisions",
        "tools": ["risk_metrics", "portfolio_analysis", "exposure_limits"],
        "priority": 4
    }
}

# GUI Color scheme
COLOR_SCHEME = {
    "background": "#1e1e1e",
    "secondary_bg": "#2d2d2d",
    "tertiary_bg": "#3d3d3d",
    "text_primary": "#ffffff",
    "text_secondary": "#cccccc",
    "text_muted": "#888888",
    "accent_green": "#00ff00",
    "accent_yellow": "#ffff00",
    "accent_red": "#ff0000",
    "accent_blue": "#00ffff",
    "success": "#4CAF50",
    "warning": "#ff9800",
    "error": "#f44336",
    "info": "#2196F3"
}

# Status colors for agents
STATUS_COLORS = {
    "idle": COLOR_SCHEME["text_muted"],
    "running": COLOR_SCHEME["accent_yellow"],
    "completed": COLOR_SCHEME["accent_green"],
    "error": COLOR_SCHEME["accent_red"],
    "warning": COLOR_SCHEME["warning"]
}

# Log level colors
LOG_COLORS = {
    "INFO": COLOR_SCHEME["accent_green"],
    "WARNING": COLOR_SCHEME["accent_yellow"],
    "ERROR": COLOR_SCHEME["accent_red"],
    "SUCCESS": COLOR_SCHEME["accent_blue"],
    "DEBUG": COLOR_SCHEME["text_secondary"]
}

# Language translations
LANGUAGE_TEXTS = {
    "en": {
        # Main tabs
        "agents": "Agents",
        "trading_analysis": "Trading Analysis",
        "portfolio": "Portfolio",
        "logs": "Logs",
        "settings": "Settings",
        
        # Settings tabs
        "api_keys": "API Keys",
        "trading": "Trading",
        "agents_tab": "Agents",
        "language_tab": "Language",
        
        # API Settings
        "api_configuration": "API Configuration",
        "openai_api_key": "OpenAI API Key:",
        "finnhub_api_key": "FinnHub API Key:",
        "save_api_keys": "Save API Keys",
        "load_api_keys": "Load API Keys",
        "test_connections": "Test Connections",
        "use_mock_data": "Use Mock Data (for testing without API keys)",
        
        # Trading Settings
        "trading_parameters": "Trading Parameters",
        "risk_tolerance": "Risk Tolerance:",
        "update_interval": "Update Interval (seconds):",
        "max_positions": "Max Positions:",
        
        # Agent Settings
        "agent_configuration": "Agent Configuration",
        "enable": "Enable",
        
        # Language Settings
        "language_configuration": "Language Configuration",
        "select_language": "Select Language:",
        "english": "English",
        "chinese": "中文",
        "apply_language": "Apply Language",
        "restart_required": "Language change will take effect after restarting the application.",
        
        # Trading controls
        "start_trading": "Start Trading",
        "stop_trading": "Stop Trading",
        "symbol": "Symbol:",
        
        # Status
        "status": "Status",
        "connected": "Connected",
        "disconnected": "Disconnected",
        "idle": "Idle",
        "active": "Active",
        
        # Messages
        "success": "Success",
        "error": "Error",
        "warning": "Warning",
        "info": "Info"
    },
    "zh": {
        # Main tabs
        "agents": "智能体",
        "trading_analysis": "交易分析",
        "portfolio": "投资组合",
        "logs": "日志",
        "settings": "设置",
        
        # Settings tabs
        "api_keys": "API密钥",
        "trading": "交易",
        "agents_tab": "智能体",
        "language_tab": "语言",
        
        # API Settings
        "api_configuration": "API配置",
        "openai_api_key": "OpenAI API密钥：",
        "finnhub_api_key": "FinnHub API密钥：",
        "save_api_keys": "保存API密钥",
        "load_api_keys": "加载API密钥",
        "test_connections": "测试连接",
        "use_mock_data": "使用模拟数据（无需API密钥测试）",
        
        # Trading Settings
        "trading_parameters": "交易参数",
        "risk_tolerance": "风险承受度：",
        "update_interval": "更新间隔（秒）：",
        "max_positions": "最大持仓数：",
        
        # Agent Settings
        "agent_configuration": "智能体配置",
        "enable": "启用",
        
        # Language Settings
        "language_configuration": "语言配置",
        "select_language": "选择语言：",
        "english": "English",
        "chinese": "中文",
        "apply_language": "应用语言",
        "restart_required": "语言更改将在重启应用程序后生效。",
        
        # Trading controls
        "start_trading": "开始交易",
        "stop_trading": "停止交易",
        "symbol": "股票代码：",
        
        # Status
        "status": "状态",
        "connected": "已连接",
        "disconnected": "已断开",
        "idle": "空闲",
        "active": "活跃",
        
        # Messages
        "success": "成功",
        "error": "错误",
        "warning": "警告",
        "info": "信息"
    }
}

class Config:
    """Configuration manager for the application."""
    
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.api_keys_file = os.path.join(os.path.dirname(__file__), 'api_keys.json')
        self.load_config_from_file()  # Load saved config first
        self.load_api_keys_from_file()
        self.load_environment_variables()
    
    def load_environment_variables(self):
        """Load configuration from environment variables."""
        # API Keys - environment variables override file settings
        env_openai_key = os.getenv('OPENAI_API_KEY')
        env_finnhub_key = os.getenv('FINNHUB_API_KEY')
        
        if env_openai_key:
            self.openai_api_key = env_openai_key
        if env_finnhub_key:
            self.finnhub_api_key = env_finnhub_key
        
        # Override config with environment variables if present
        env_mappings = {
            'TRADING_AGENTS_DEEP_THINK_LLM': 'deep_think_llm',
            'TRADING_AGENTS_QUICK_THINK_LLM': 'quick_think_llm',
            'TRADING_AGENTS_MAX_DEBATE_ROUNDS': 'max_debate_rounds',
            'TRADING_AGENTS_RISK_TOLERANCE': 'risk_tolerance',
            'TRADING_AGENTS_LOG_LEVEL': 'log_level'
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert to appropriate type
                if config_key in ['max_debate_rounds']:
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                elif config_key in ['temperature', 'stop_loss_percentage', 'take_profit_percentage']:
                    try:
                        value = float(value)
                    except ValueError:
                        continue
                        
                self.config[config_key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values."""
        self.config.update(updates)
    
    def get_text(self, key: str, language: str = None) -> str:
        """Get translated text for the given key."""
        if language is None:
            language = self.get('language', 'en')
        
        return LANGUAGE_TEXTS.get(language, LANGUAGE_TEXTS['en']).get(key, key)
    
    def set_language(self, language: str) -> None:
        """Set the application language."""
        if language in LANGUAGE_TEXTS:
            self.set('language', language)
            # Save language setting to config file if needed
            self.save_config_to_file()
    
    def save_config_to_file(self) -> None:
        """Save current configuration to file."""
        config_file = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'language': self.get('language', 'en'),
                    'theme': self.get('theme', 'dark')
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def load_config_from_file(self) -> None:
        """Load configuration from file."""
        config_file = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def get_risk_settings(self, risk_level: str = None) -> Dict[str, float]:
        """Get risk settings for specified level."""
        if risk_level is None:
            risk_level = self.get('risk_tolerance', 'medium')
        return RISK_LEVELS.get(risk_level, RISK_LEVELS['medium'])
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are present."""
        return {
            'openai': bool(self.openai_api_key),
            'finnhub': bool(self.finnhub_api_key)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.config.copy()
    
    def load_api_keys_from_file(self) -> None:
        """Load API keys from local file."""
        try:
            if os.path.exists(self.api_keys_file):
                with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Check if file is not empty
                        api_keys = json.loads(content)
                        self.openai_api_key = api_keys.get('openai_api_key', '')
                        self.finnhub_api_key = api_keys.get('finnhub_api_key', '')
                    else:
                        # File exists but is empty
                        self.openai_api_key = ''
                        self.finnhub_api_key = ''
            else:
                self.openai_api_key = ''
                self.finnhub_api_key = ''
        except (json.JSONDecodeError, FileNotFoundError) as e:
            # Silently handle JSON decode errors and file not found
            self.openai_api_key = ''
            self.finnhub_api_key = ''
        except Exception as e:
            print(f"Error loading API keys from file: {e}")
            self.openai_api_key = ''
            self.finnhub_api_key = ''
    
    def save_api_keys_to_file(self) -> bool:
        """Save API keys to local file."""
        try:
            api_keys = {
                'openai_api_key': self.openai_api_key,
                'finnhub_api_key': self.finnhub_api_key
            }
            with open(self.api_keys_file, 'w', encoding='utf-8') as f:
                json.dump(api_keys, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving API keys to file: {e}")
            return False
    
    def set_api_key(self, provider: str, api_key: str) -> bool:
        """Set API key for a provider and save to file."""
        if provider.lower() == 'openai':
            self.openai_api_key = api_key
        elif provider.lower() == 'finnhub':
            self.finnhub_api_key = api_key
        else:
            return False
        
        return self.save_api_keys_to_file()

# Global configuration instance
config = Config()