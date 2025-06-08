"""Utility functions for TradingAgents GUI application."""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import threading
from dataclasses import dataclass

@dataclass
class MarketData:
    """Market data structure."""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime
    
@dataclass
class TechnicalIndicators:
    """Technical indicators structure."""
    rsi: float
    macd: float
    macd_signal: float
    bollinger_upper: float
    bollinger_lower: float
    sma_20: float
    sma_50: float
    volume_avg: float

class DataProvider:
    """Base class for data providers."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TradingAgents-GUI/1.0'
        })
    
    def get_quote(self, symbol: str) -> Optional[MarketData]:
        """Get current quote for symbol."""
        raise NotImplementedError
    
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get market data for symbol (alias for get_quote)."""
        return self.get_quote(symbol)
    
    def get_historical_data(self, symbol: str, days: int = 30) -> List[Dict]:
        """Get historical price data."""
        raise NotImplementedError
    
    def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """Get company information."""
        raise NotImplementedError

class FinnHubProvider(DataProvider):
    """FinnHub data provider implementation."""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def get_quote(self, symbol: str) -> Optional[MarketData]:
        """Get current quote from FinnHub."""
        try:
            url = f"{self.BASE_URL}/quote"
            params = {
                'symbol': symbol,
                'token': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'c' in data:  # current price
                return MarketData(
                    symbol=symbol,
                    price=data['c'],
                    change=data.get('d', 0),
                    change_percent=data.get('dp', 0),
                    volume=0,  # FinnHub doesn't provide volume in quote
                    timestamp=datetime.now()
                )
            
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
            
        return None
    
    def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """Get company profile from FinnHub."""
        try:
            url = f"{self.BASE_URL}/stock/profile2"
            params = {
                'symbol': symbol,
                'token': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"Error fetching company info for {symbol}: {e}")
            return {}
    
    def get_news(self, symbol: str, days: int = 7) -> List[Dict]:
        """Get company news from FinnHub."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            url = f"{self.BASE_URL}/company-news"
            params = {
                'symbol': symbol,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'token': self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()[:10]  # Limit to 10 news items
            
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
            return []

class MockDataProvider(DataProvider):
    """Mock data provider for testing without API keys."""
    
    def __init__(self, api_key: str = "mock"):
        super().__init__(api_key)
        self.mock_prices = {
            'NVDA': 850.0,
            'AAPL': 175.0,
            'TSLA': 250.0,
            'MSFT': 420.0,
            'GOOGL': 140.0,
            'AMZN': 155.0
        }
    
    def get_quote(self, symbol: str) -> Optional[MarketData]:
        """Get mock quote data."""
        import random
        
        base_price = self.mock_prices.get(symbol.upper(), 100.0)
        
        # Add some random variation
        price_change = random.uniform(-0.05, 0.05)  # ±5%
        current_price = base_price * (1 + price_change)
        change = current_price - base_price
        change_percent = (change / base_price) * 100
        
        return MarketData(
            symbol=symbol,
            price=round(current_price, 2),
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            volume=random.randint(1000000, 10000000),
            timestamp=datetime.now()
        )
    
    def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """Get mock company information."""
        companies = {
            'NVDA': {
                'name': 'NVIDIA Corporation',
                'industry': 'Semiconductors',
                'marketCapitalization': 2100000,
                'country': 'US',
                'currency': 'USD'
            },
            'AAPL': {
                'name': 'Apple Inc.',
                'industry': 'Technology Hardware',
                'marketCapitalization': 2800000,
                'country': 'US',
                'currency': 'USD'
            }
        }
        
        return companies.get(symbol.upper(), {
            'name': f'{symbol.upper()} Corporation',
            'industry': 'Technology',
            'marketCapitalization': 50000,
            'country': 'US',
            'currency': 'USD'
        })
    
    def get_news(self, symbol: str, days: int = 7) -> List[Dict]:
        """Get mock news data."""
        import random
        
        mock_news = [
            {
                'headline': f'{symbol} reports strong quarterly earnings',
                'summary': f'{symbol} exceeded analyst expectations with strong revenue growth.',
                'datetime': int(time.time()) - random.randint(0, 86400 * days),
                'source': 'Financial News',
                'url': 'https://example.com/news1'
            },
            {
                'headline': f'Analysts upgrade {symbol} price target',
                'summary': f'Multiple analysts have raised their price targets for {symbol}.',
                'datetime': int(time.time()) - random.randint(0, 86400 * days),
                'source': 'Market Watch',
                'url': 'https://example.com/news2'
            },
            {
                'headline': f'{symbol} announces new product launch',
                'summary': f'{symbol} unveils innovative new product line.',
                'datetime': int(time.time()) - random.randint(0, 86400 * days),
                'source': 'Tech News',
                'url': 'https://example.com/news3'
            }
        ]
        
        return mock_news

class TechnicalAnalysis:
    """Technical analysis utilities."""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return sum(prices) / len(prices) if prices else 0.0
        
        return sum(prices[-period:]) / period
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands (upper, middle, lower)."""
        if len(prices) < period:
            avg = sum(prices) / len(prices) if prices else 0.0
            return avg, avg, avg
        
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period
        
        variance = sum((price - sma) ** 2 for price in recent_prices) / period
        std = variance ** 0.5
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return round(upper, 2), round(sma, 2), round(lower, 2)
    
    @staticmethod
    def generate_mock_indicators(symbol: str) -> TechnicalIndicators:
        """Generate mock technical indicators for testing."""
        import random
        
        return TechnicalIndicators(
            rsi=random.uniform(30, 70),
            macd=random.uniform(-2, 2),
            macd_signal=random.uniform(-2, 2),
            bollinger_upper=random.uniform(180, 200),
            bollinger_lower=random.uniform(160, 180),
            sma_20=random.uniform(170, 190),
            sma_50=random.uniform(165, 185),
            volume_avg=random.uniform(1000000, 5000000)
        )

class SentimentAnalyzer:
    """Sentiment analysis utilities."""
    
    @staticmethod
    def analyze_text_sentiment(text: str) -> float:
        """Analyze sentiment of text. Returns score between -1 (negative) and 1 (positive)."""
        # Simple keyword-based sentiment analysis
        positive_words = [
            'good', 'great', 'excellent', 'positive', 'bullish', 'up', 'gain', 'profit',
            'strong', 'growth', 'increase', 'buy', 'upgrade', 'outperform', 'beat'
        ]
        
        negative_words = [
            'bad', 'poor', 'negative', 'bearish', 'down', 'loss', 'decline',
            'weak', 'decrease', 'sell', 'downgrade', 'underperform', 'miss'
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = len(text.split())
        if total_words == 0:
            return 0.0
        
        sentiment_score = (positive_count - negative_count) / max(total_words, 1)
        return max(-1.0, min(1.0, sentiment_score * 10))  # Scale and clamp
    
    @staticmethod
    def analyze_news_sentiment(news_items: List[Dict]) -> float:
        """Analyze overall sentiment from news items."""
        if not news_items:
            return 0.0
        
        sentiments = []
        for item in news_items:
            headline_sentiment = SentimentAnalyzer.analyze_text_sentiment(item.get('headline', ''))
            summary_sentiment = SentimentAnalyzer.analyze_text_sentiment(item.get('summary', ''))
            
            # Weight headline more than summary
            combined_sentiment = (headline_sentiment * 0.7) + (summary_sentiment * 0.3)
            sentiments.append(combined_sentiment)
        
        return sum(sentiments) / len(sentiments)

class PortfolioTracker:
    """Portfolio tracking utilities."""
    
    def __init__(self, initial_balance: float = 100000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions = {}  # symbol -> quantity
        self.trade_history = []
        self.daily_pnl = []
    
    def execute_trade(self, symbol: str, action: str, quantity: int, price: float) -> bool:
        """Execute a trade and update portfolio."""
        trade_value = quantity * price
        
        if action.upper() == 'BUY':
            if trade_value <= self.current_balance:
                self.current_balance -= trade_value
                self.positions[symbol] = self.positions.get(symbol, 0) + quantity
                
                self.trade_history.append({
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'action': 'BUY',
                    'quantity': quantity,
                    'price': price,
                    'value': trade_value
                })
                return True
        
        elif action.upper() == 'SELL':
            if self.positions.get(symbol, 0) >= quantity:
                self.current_balance += trade_value
                self.positions[symbol] -= quantity
                
                if self.positions[symbol] == 0:
                    del self.positions[symbol]
                
                self.trade_history.append({
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'action': 'SELL',
                    'quantity': quantity,
                    'price': price,
                    'value': trade_value
                })
                return True
        
        return False
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate current portfolio value."""
        portfolio_value = self.current_balance
        
        for symbol, quantity in self.positions.items():
            if symbol in current_prices:
                portfolio_value += quantity * current_prices[symbol]
        
        return portfolio_value
    
    def get_performance_metrics(self, current_prices: Dict[str, float]) -> Dict[str, float]:
        """Calculate portfolio performance metrics."""
        current_value = self.get_portfolio_value(current_prices)
        total_return = (current_value - self.initial_balance) / self.initial_balance
        
        # Calculate daily P&L (mock for now)
        daily_pnl = current_value - self.initial_balance
        daily_return = daily_pnl / self.initial_balance
        
        return {
            'total_value': current_value,
            'total_return': total_return,
            'daily_pnl': daily_pnl,
            'daily_return': daily_return,
            'cash_balance': self.current_balance,
            'positions_count': len(self.positions)
        }
    
    def get_summary(self, current_prices: Dict[str, float] = None) -> Dict[str, float]:
        """Get portfolio summary - alias for get_performance_metrics."""
        if current_prices is None:
            current_prices = {}
        return self.get_performance_metrics(current_prices)

def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"${amount:,.2f}"

def format_percentage(value: float) -> str:
    """Format value as percentage."""
    return f"{value:.2%}"

def validate_symbol(symbol: str) -> bool:
    """Validate stock symbol format."""
    if not symbol or len(symbol) > 10:
        return False
    
    return symbol.replace('.', '').replace('-', '').isalpha()

def get_data_provider(api_key: str = None) -> DataProvider:
    """Get appropriate data provider based on API key availability."""
    if api_key and api_key.strip():
        return FinnHubProvider(api_key)
    else:
        return MockDataProvider()

def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

class ThreadSafeLogger:
    """Thread-safe logger for GUI applications."""
    
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self.entries = []
        self.lock = threading.Lock()
    
    def log(self, level: str, message: str) -> None:
        """Add log entry."""
        with self.lock:
            entry = {
                'timestamp': datetime.now(),
                'level': level,
                'message': message
            }
            
            self.entries.append(entry)
            
            # Keep only the most recent entries
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[-self.max_entries:]
    
    def get_entries(self, level: str = None) -> List[Dict]:
        """Get log entries, optionally filtered by level."""
        with self.lock:
            if level:
                return [entry for entry in self.entries if entry['level'] == level]
            return self.entries.copy()
    
    def clear(self) -> None:
        """Clear all log entries."""
        with self.lock:
            self.entries.clear()
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.log('INFO', message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.log('WARNING', message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.log('ERROR', message)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.log('DEBUG', message)