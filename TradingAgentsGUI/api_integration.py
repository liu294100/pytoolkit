#!/usr/bin/env python3
"""
API Integration Module for TradingAgents GUI

This module handles real API integrations for:
- OpenAI/LLM providers for agent intelligence
- Financial data providers (FinnHub, Alpha Vantage, etc.)
- News and sentiment data sources
- Real-time market data feeds

Author: TradingAgents GUI Team
Version: 1.0.0
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import openai
from dataclasses import dataclass

@dataclass
class APICredentials:
    """Store API credentials securely."""
    openai_key: str = ""
    finnhub_key: str = ""
    alpha_vantage_key: str = ""
    news_api_key: str = ""
    
    @classmethod
    def from_env(cls):
        """Load credentials from environment variables."""
        return cls(
            openai_key=os.getenv('OPENAI_API_KEY', ''),
            finnhub_key=os.getenv('FINNHUB_API_KEY', ''),
            alpha_vantage_key=os.getenv('ALPHA_VANTAGE_API_KEY', ''),
            news_api_key=os.getenv('NEWS_API_KEY', '')
        )
    
    def validate(self) -> Dict[str, bool]:
        """Validate that required credentials are present."""
        return {
            'openai': bool(self.openai_key),
            'finnhub': bool(self.finnhub_key),
            'alpha_vantage': bool(self.alpha_vantage_key),
            'news_api': bool(self.news_api_key)
        }

class LLMProvider:
    """Enhanced LLM provider with multiple model support."""
    
    def __init__(self, credentials: APICredentials):
        self.credentials = credentials
        self.client = None
        if credentials.openai_key:
            openai.api_key = credentials.openai_key
            self.client = openai
    
    async def generate_analysis(self, prompt: str, model: str = "gpt-4o-mini", 
                              temperature: float = 0.1) -> Optional[str]:
        """Generate analysis using LLM."""
        if not self.client:
            return None
            
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=model,
                messages=[
                    {"role": "system", "content": "You are a professional financial analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM API error: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test LLM API connection."""
        if not self.client:
            return False
            
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
        except Exception:
            return False

class EnhancedDataProvider:
    """Enhanced data provider with multiple sources."""
    
    def __init__(self, credentials: APICredentials):
        self.credentials = credentials
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_real_time_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time quote from FinnHub."""
        if not self.credentials.finnhub_key or not self.session:
            return None
            
        try:
            url = "https://finnhub.io/api/v1/quote"
            params = {
                'symbol': symbol,
                'token': self.credentials.finnhub_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'symbol': symbol,
                        'price': data.get('c', 0),
                        'change': data.get('d', 0),
                        'change_percent': data.get('dp', 0),
                        'high': data.get('h', 0),
                        'low': data.get('l', 0),
                        'open': data.get('o', 0),
                        'previous_close': data.get('pc', 0),
                        'timestamp': datetime.now()
                    }
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
        
        return None
    
    async def get_company_news(self, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get company news from FinnHub."""
        if not self.credentials.finnhub_key or not self.session:
            return []
            
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            url = "https://finnhub.io/api/v1/company-news"
            params = {
                'symbol': symbol,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'token': self.credentials.finnhub_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
        
        return []
    
    async def get_financial_metrics(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get financial metrics from FinnHub."""
        if not self.credentials.finnhub_key or not self.session:
            return None
            
        try:
            url = "https://finnhub.io/api/v1/stock/metric"
            params = {
                'symbol': symbol,
                'metric': 'all',
                'token': self.credentials.finnhub_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            print(f"Error fetching metrics for {symbol}: {e}")
        
        return None
    
    def test_connection(self) -> bool:
        """Test data provider connection."""
        if not self.credentials.finnhub_key:
            return False
            
        try:
            import requests
            response = requests.get(
                "https://finnhub.io/api/v1/quote",
                params={'symbol': 'AAPL', 'token': self.credentials.finnhub_key},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

class TradingStrategy:
    """Enhanced trading strategy with customizable parameters."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.signals = []
        
    def add_signal(self, signal_type: str, strength: float, reason: str):
        """Add a trading signal."""
        self.signals.append({
            'type': signal_type,  # 'buy', 'sell', 'hold'
            'strength': strength,  # 0.0 to 1.0
            'reason': reason,
            'timestamp': datetime.now()
        })
    
    def get_consensus_signal(self) -> Dict[str, Any]:
        """Get consensus signal from all agents."""
        if not self.signals:
            return {'action': 'hold', 'confidence': 0.0, 'reasons': []}
        
        # Calculate weighted average
        buy_weight = sum(s['strength'] for s in self.signals if s['type'] == 'buy')
        sell_weight = sum(s['strength'] for s in self.signals if s['type'] == 'sell')
        hold_weight = sum(s['strength'] for s in self.signals if s['type'] == 'hold')
        
        total_weight = buy_weight + sell_weight + hold_weight
        if total_weight == 0:
            return {'action': 'hold', 'confidence': 0.0, 'reasons': []}
        
        # Determine action
        if buy_weight > sell_weight and buy_weight > hold_weight:
            action = 'buy'
            confidence = buy_weight / total_weight
        elif sell_weight > buy_weight and sell_weight > hold_weight:
            action = 'sell'
            confidence = sell_weight / total_weight
        else:
            action = 'hold'
            confidence = hold_weight / total_weight
        
        reasons = [s['reason'] for s in self.signals if s['type'] == action]
        
        return {
            'action': action,
            'confidence': confidence,
            'reasons': reasons,
            'signal_count': len(self.signals)
        }
    
    def clear_signals(self):
        """Clear all signals."""
        self.signals.clear()

class PerformanceOptimizer:
    """Performance optimization utilities."""
    
    def __init__(self):
        self.metrics = {}
        self.cache = {}
        self.cache_ttl = {}
    
    def cache_data(self, key: str, data: Any, ttl_seconds: int = 300):
        """Cache data with TTL."""
        self.cache[key] = data
        self.cache_ttl[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data if not expired."""
        if key in self.cache and key in self.cache_ttl:
            if datetime.now() < self.cache_ttl[key]:
                return self.cache[key]
            else:
                # Remove expired data
                del self.cache[key]
                del self.cache_ttl[key]
        return None
    
    def record_metric(self, name: str, value: float):
        """Record performance metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append({
            'value': value,
            'timestamp': datetime.now()
        })
        
        # Keep only last 100 measurements
        if len(self.metrics[name]) > 100:
            self.metrics[name] = self.metrics[name][-100:]
    
    def get_average_metric(self, name: str, minutes: int = 5) -> Optional[float]:
        """Get average metric value for last N minutes."""
        if name not in self.metrics:
            return None
            
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_values = [
            m['value'] for m in self.metrics[name] 
            if m['timestamp'] > cutoff_time
        ]
        
        return sum(recent_values) / len(recent_values) if recent_values else None

class APIIntegrationManager:
    """Main API integration manager."""
    
    def __init__(self):
        self.credentials = APICredentials.from_env()
        self.llm_provider = LLMProvider(self.credentials)
        self.optimizer = PerformanceOptimizer()
        self.strategies = {}
    
    def add_strategy(self, name: str, config: Dict[str, Any]):
        """Add a trading strategy."""
        self.strategies[name] = TradingStrategy(name, config)
    
    def get_strategy(self, name: str) -> Optional[TradingStrategy]:
        """Get a trading strategy."""
        return self.strategies.get(name)
    
    async def get_comprehensive_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive analysis for a symbol."""
        # Check cache first
        cache_key = f"analysis_{symbol}"
        cached = self.optimizer.get_cached_data(cache_key)
        if cached:
            return cached
        
        analysis = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'market_data': None,
            'news': [],
            'metrics': None,
            'ai_analysis': None
        }
        
        async with EnhancedDataProvider(self.credentials) as provider:
            # Get market data
            analysis['market_data'] = await provider.get_real_time_quote(symbol)
            
            # Get news
            analysis['news'] = await provider.get_company_news(symbol)
            
            # Get financial metrics
            analysis['metrics'] = await provider.get_financial_metrics(symbol)
        
        # Generate AI analysis
        if analysis['market_data'] and self.llm_provider.client:
            prompt = f"""
            Analyze the following data for {symbol}:
            
            Current Price: ${analysis['market_data']['price']}
            Change: {analysis['market_data']['change']} ({analysis['market_data']['change_percent']}%)
            
            Recent News Headlines:
            {chr(10).join([news.get('headline', '') for news in analysis['news'][:5]])}
            
            Provide a brief technical and fundamental analysis with trading recommendation.
            """
            
            analysis['ai_analysis'] = await self.llm_provider.generate_analysis(prompt)
        
        # Cache the result
        self.optimizer.cache_data(cache_key, analysis, 300)  # 5 minutes TTL
        
        return analysis
    
    def test_all_connections(self) -> Dict[str, bool]:
        """Test all API connections."""
        results = {
            'credentials': self.credentials.validate(),
            'llm': self.llm_provider.test_connection(),
            'data': False
        }
        
        # Test data provider
        async def test_data():
            async with EnhancedDataProvider(self.credentials) as provider:
                return provider.test_connection()
        
        try:
            results['data'] = asyncio.run(test_data())
        except Exception:
            results['data'] = False
        
        return results