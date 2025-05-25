#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Hedge Fund Core Module
简化版的AI对冲基金核心逻辑

基于原始ai-hedge-fund项目的简化实现
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import yfinance as yf
import pandas as pd
import numpy as np

# 导入LLM提供商模块
from llm_providers import get_provider, list_available_providers

@dataclass
class AgentDecision:
    """智能体决策结果"""
    agent_name: str
    ticker: str
    decision: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0-1
    reasoning: str
    target_price: Optional[float] = None
    risk_level: str = 'MEDIUM'  # 'LOW', 'MEDIUM', 'HIGH'

@dataclass
class MarketData:
    """市场数据"""
    ticker: str
    current_price: float
    price_change: float
    price_change_percent: float
    volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None

class SimpleAgent:
    """简化的智能体基类"""
    
    def __init__(self, name: str, strategy: str):
        self.name = name
        self.strategy = strategy
        
    def analyze(self, market_data: MarketData, historical_data: pd.DataFrame) -> AgentDecision:
        """分析并做出决策"""
        raise NotImplementedError
        
    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict:
        """计算技术指标"""
        indicators = {}
        
        # 简单移动平均线
        if len(data) >= 20:
            indicators['sma_20'] = data['Close'].rolling(window=20).mean().iloc[-1]
        if len(data) >= 50:
            indicators['sma_50'] = data['Close'].rolling(window=50).mean().iloc[-1]
            
        # RSI
        if len(data) >= 14:
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            indicators['rsi'] = 100 - (100 / (1 + rs)).iloc[-1]
            
        return indicators

class WarrenBuffettAgent(SimpleAgent):
    """沃伦·巴菲特风格的价值投资智能体"""
    
    def __init__(self):
        super().__init__("Warren Buffett", "Value Investing")
        
    def analyze(self, market_data: MarketData, historical_data: pd.DataFrame) -> AgentDecision:
        """基于价值投资原则分析"""
        reasoning_parts = []
        confidence = 0.5
        decision = "HOLD"
        
        # PE比率分析
        if market_data.pe_ratio:
            if market_data.pe_ratio < 15:
                reasoning_parts.append(f"PE比率 {market_data.pe_ratio:.2f} 较低，显示潜在价值")
                confidence += 0.2
                decision = "BUY"
            elif market_data.pe_ratio > 25:
                reasoning_parts.append(f"PE比率 {market_data.pe_ratio:.2f} 较高，可能被高估")
                confidence += 0.1
                decision = "SELL"
            else:
                reasoning_parts.append(f"PE比率 {market_data.pe_ratio:.2f} 处于合理范围")
                
        # 股息收益率分析
        if market_data.dividend_yield:
            if market_data.dividend_yield > 0.03:  # 3%以上
                reasoning_parts.append(f"股息收益率 {market_data.dividend_yield*100:.2f}% 具有吸引力")
                confidence += 0.15
                
        # 价格趋势分析
        if len(historical_data) >= 252:  # 一年数据
            year_return = (market_data.current_price / historical_data['Close'].iloc[-252] - 1) * 100
            if year_return < -20:
                reasoning_parts.append(f"年度回报 {year_return:.1f}% 显示可能的买入机会")
                confidence += 0.1
                if decision != "SELL":
                    decision = "BUY"
                    
        reasoning = f"巴菲特价值投资分析: {'; '.join(reasoning_parts)}"
        
        return AgentDecision(
            agent_name=self.name,
            ticker=market_data.ticker,
            decision=decision,
            confidence=min(confidence, 1.0),
            reasoning=reasoning,
            risk_level="LOW"
        )

class CathieWoodAgent(SimpleAgent):
    """凯西·伍德风格的成长投资智能体"""
    
    def __init__(self):
        super().__init__("Cathie Wood", "Growth Investing")
        
    def analyze(self, market_data: MarketData, historical_data: pd.DataFrame) -> AgentDecision:
        """基于成长投资原则分析"""
        reasoning_parts = []
        confidence = 0.5
        decision = "HOLD"
        
        # 技术指标分析
        indicators = self._calculate_technical_indicators(historical_data)
        
        # RSI分析
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if rsi < 30:
                reasoning_parts.append(f"RSI {rsi:.1f} 显示超卖，可能反弹")
                confidence += 0.2
                decision = "BUY"
            elif rsi > 70:
                reasoning_parts.append(f"RSI {rsi:.1f} 显示超买，可能回调")
                confidence += 0.1
                decision = "SELL"
                
        # 移动平均线分析
        if 'sma_20' in indicators and 'sma_50' in indicators:
            if indicators['sma_20'] > indicators['sma_50']:
                reasoning_parts.append("短期均线上穿长期均线，显示上升趋势")
                confidence += 0.15
                if decision != "SELL":
                    decision = "BUY"
                    
        # 成交量分析
        if len(historical_data) >= 20:
            avg_volume = historical_data['Volume'].rolling(window=20).mean().iloc[-1]
            if market_data.volume > avg_volume * 1.5:
                reasoning_parts.append("成交量放大，显示市场关注度增加")
                confidence += 0.1
                
        reasoning = f"凯西·伍德成长投资分析: {'; '.join(reasoning_parts)}"
        
        return AgentDecision(
            agent_name=self.name,
            ticker=market_data.ticker,
            decision=decision,
            confidence=min(confidence, 1.0),
            reasoning=reasoning,
            risk_level="HIGH"
        )

class TechnicalAgent(SimpleAgent):
    """技术分析智能体"""
    
    def __init__(self):
        super().__init__("Technical Analyst", "Technical Analysis")
        
    def analyze(self, market_data: MarketData, historical_data: pd.DataFrame) -> AgentDecision:
        """基于技术分析"""
        reasoning_parts = []
        confidence = 0.5
        decision = "HOLD"
        
        indicators = self._calculate_technical_indicators(historical_data)
        
        # 价格动量分析
        if market_data.price_change_percent > 5:
            reasoning_parts.append(f"日涨幅 {market_data.price_change_percent:.2f}% 显示强劲动量")
            confidence += 0.2
            decision = "BUY"
        elif market_data.price_change_percent < -5:
            reasoning_parts.append(f"日跌幅 {abs(market_data.price_change_percent):.2f}% 显示弱势")
            confidence += 0.2
            decision = "SELL"
            
        # 支撑阻力分析
        if len(historical_data) >= 20:
            recent_high = historical_data['High'].rolling(window=20).max().iloc[-1]
            recent_low = historical_data['Low'].rolling(window=20).min().iloc[-1]
            
            if market_data.current_price >= recent_high * 0.98:
                reasoning_parts.append("价格接近近期高点，可能突破")
                confidence += 0.1
            elif market_data.current_price <= recent_low * 1.02:
                reasoning_parts.append("价格接近近期低点，可能反弹")
                confidence += 0.1
                
        reasoning = f"技术分析: {'; '.join(reasoning_parts)}"
        
        return AgentDecision(
            agent_name=self.name,
            ticker=market_data.ticker,
            decision=decision,
            confidence=min(confidence, 1.0),
            reasoning=reasoning,
            risk_level="MEDIUM"
        )

class AIHedgeFund:
    """AI对冲基金主类"""
    
    def __init__(self, llm_provider="openai", llm_config=None):
        self.agents = {
            'warren_buffett': WarrenBuffettAgent(),
            'cathie_wood': CathieWoodAgent(),
            'technical': TechnicalAgent()
        }
        
        # 设置LLM提供商
        self.llm_provider_name = llm_provider
        self.llm_config = llm_config or {}
        self.llm_provider = None
        
        # 尝试初始化LLM提供商
        try:
            self.llm_provider = get_provider(llm_provider, self.llm_config)
        except Exception as e:
            print(f"警告: 无法初始化LLM提供商 {llm_provider}: {str(e)}")
            print("将使用内置的规则引擎进行分析")
        
    def get_market_data(self, ticker: str) -> Tuple[MarketData, pd.DataFrame]:
        """获取市场数据"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1y")
            
            if hist.empty:
                raise ValueError(f"无法获取 {ticker} 的历史数据")
                
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            price_change = current_price - prev_price
            price_change_percent = (price_change / prev_price) * 100
            
            market_data = MarketData(
                ticker=ticker,
                current_price=current_price,
                price_change=price_change,
                price_change_percent=price_change_percent,
                volume=int(hist['Volume'].iloc[-1]),
                market_cap=info.get('marketCap'),
                pe_ratio=info.get('trailingPE'),
                dividend_yield=info.get('dividendYield')
            )
            
            return market_data, hist
            
        except Exception as e:
            raise Exception(f"获取 {ticker} 市场数据失败: {str(e)}")
    
    def analyze_stock(self, ticker: str, selected_agents: List[str] = None, use_llm: bool = False) -> Dict:
        """分析股票"""
        if selected_agents is None:
            selected_agents = list(self.agents.keys())
            
        try:
            # 获取市场数据
            market_data, historical_data = self.get_market_data(ticker)
            
            # 运行选定的智能体
            decisions = []
            
            # 如果启用LLM分析且LLM提供商可用
            if use_llm and self.llm_provider and self.llm_provider.is_available():
                llm_decisions = self._get_llm_analysis(ticker, market_data, historical_data, selected_agents)
                decisions.extend(llm_decisions)
            else:
                # 使用内置规则引擎
                for agent_key in selected_agents:
                    if agent_key in self.agents:
                        agent = self.agents[agent_key]
                        decision = agent.analyze(market_data, historical_data)
                        decisions.append(decision)
                    
            # 综合决策
            final_decision = self._make_final_decision(decisions)
            
            return {
                'ticker': ticker,
                'market_data': market_data,
                'agent_decisions': decisions,
                'final_decision': final_decision,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'ticker': ticker,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_llm_analysis(self, ticker: str, market_data: MarketData, historical_data: pd.DataFrame, 
                         selected_agents: List[str]) -> List[AgentDecision]:
        """使用LLM进行分析"""
        decisions = []
        
        # 为每个选定的智能体生成LLM分析
        for agent_key in selected_agents:
            if agent_key not in self.agents:
                continue
                
            agent = self.agents[agent_key]
            
            # 准备市场数据摘要
            market_summary = f"""
            股票代码: {ticker}
            当前价格: ${market_data.current_price:.2f}
            价格变化: ${market_data.price_change:.2f} ({market_data.price_change_percent:.2f}%)
            成交量: {market_data.volume}
            市值: {market_data.market_cap if market_data.market_cap else '未知'}
            市盈率: {market_data.pe_ratio if market_data.pe_ratio else '未知'}
            股息收益率: {market_data.dividend_yield*100 if market_data.dividend_yield else '未知'}%
            """
            
            # 准备技术指标摘要
            tech_indicators = agent._calculate_technical_indicators(historical_data)
            indicators_summary = "技术指标:\n"
            for key, value in tech_indicators.items():
                indicators_summary += f"{key}: {value:.2f}\n"
            
            # 构建提示
            prompt = f"""
            你是一个名为{agent.name}的投资分析师，专注于{agent.strategy}策略。
            请分析以下股票并给出买入、卖出或持有的建议，以及你的置信度（0-1之间的数字）。
            
            {market_summary}
            
            {indicators_summary}
            
            请按以下格式回答：
            决策: [BUY/SELL/HOLD]
            置信度: [0-1之间的数字]
            理由: [你的分析理由]
            风险等级: [LOW/MEDIUM/HIGH]
            """
            
            try:
                # 调用LLM获取分析
                response = self.llm_provider.generate(prompt)
                
                # 解析响应
                decision_text = "HOLD"
                confidence = 0.5
                reasoning = "无法解析LLM响应"
                risk_level = "MEDIUM"
                
                # 简单解析响应（实际应用中可能需要更复杂的解析逻辑）
                for line in response.split('\n'):
                    line = line.strip()
                    if line.startswith("决策:") or line.startswith("决策："):
                        decision_part = line.split(":", 1)[1].strip() if ":" in line else line.split("：", 1)[1].strip()
                        if "BUY" in decision_part.upper():
                            decision_text = "BUY"
                        elif "SELL" in decision_part.upper():
                            decision_text = "SELL"
                    elif line.startswith("置信度:") or line.startswith("置信度："):
                        confidence_part = line.split(":", 1)[1].strip() if ":" in line else line.split("：", 1)[1].strip()
                        try:
                            confidence = float(confidence_part)
                        except:
                            pass
                    elif line.startswith("理由:") or line.startswith("理由："):
                        reasoning = line.split(":", 1)[1].strip() if ":" in line else line.split("：", 1)[1].strip()
                    elif line.startswith("风险等级:") or line.startswith("风险等级："):
                        risk_part = line.split(":", 1)[1].strip() if ":" in line else line.split("：", 1)[1].strip()
                        if "LOW" in risk_part.upper():
                            risk_level = "LOW"
                        elif "HIGH" in risk_part.upper():
                            risk_level = "HIGH"
                
                # 如果没有找到理由，使用整个响应作为理由
                if reasoning == "无法解析LLM响应":
                    reasoning = response
                
                # 创建决策对象
                decision = AgentDecision(
                    agent_name=agent.name,
                    ticker=ticker,
                    decision=decision_text,
                    confidence=confidence,
                    reasoning=reasoning,
                    risk_level=risk_level
                )
                
                decisions.append(decision)
                
            except Exception as e:
                print(f"LLM分析错误 ({agent.name}): {str(e)}")
                # 回退到规则引擎
                decision = agent.analyze(market_data, historical_data)
                decisions.append(decision)
        
        return decisions
            
    def _make_final_decision(self, decisions: List[AgentDecision]) -> Dict:
        """基于所有智能体的决策做出最终决策"""
        if not decisions:
            return {'decision': 'HOLD', 'confidence': 0.0, 'reasoning': '无有效决策'}
            
        # 计算加权决策
        buy_weight = sum(d.confidence for d in decisions if d.decision == 'BUY')
        sell_weight = sum(d.confidence for d in decisions if d.decision == 'SELL')
        hold_weight = sum(d.confidence for d in decisions if d.decision == 'HOLD')
        
        total_weight = buy_weight + sell_weight + hold_weight
        
        if total_weight == 0:
            final_decision = 'HOLD'
            final_confidence = 0.0
        elif buy_weight > sell_weight and buy_weight > hold_weight:
            final_decision = 'BUY'
            final_confidence = buy_weight / total_weight
        elif sell_weight > hold_weight:
            final_decision = 'SELL'
            final_confidence = sell_weight / total_weight
        else:
            final_decision = 'HOLD'
            final_confidence = hold_weight / total_weight
            
        # 生成综合推理
        reasoning_summary = []
        for decision in decisions:
            reasoning_summary.append(f"{decision.agent_name}: {decision.decision} (置信度: {decision.confidence:.2f})")
            
        return {
            'decision': final_decision,
            'confidence': final_confidence,
            'reasoning': '; '.join(reasoning_summary),
            'agent_count': len(decisions)
        }
        
    def analyze_portfolio(self, tickers: List[str], selected_agents: List[str] = None, use_llm: bool = False) -> Dict:
        """分析投资组合"""
        results = {}
        
        for ticker in tickers:
            print(f"正在分析 {ticker}...")
            results[ticker] = self.analyze_stock(ticker, selected_agents, use_llm)
            
        # 生成投资组合摘要
        portfolio_summary = self._generate_portfolio_summary(results)
        
        return {
            'individual_analysis': results,
            'portfolio_summary': portfolio_summary,
            'timestamp': datetime.now().isoformat()
        }
        
    def _generate_portfolio_summary(self, results: Dict) -> Dict:
        """生成投资组合摘要"""
        buy_recommendations = []
        sell_recommendations = []
        hold_recommendations = []
        
        for ticker, analysis in results.items():
            if 'error' in analysis:
                continue
                
            final_decision = analysis['final_decision']['decision']
            confidence = analysis['final_decision']['confidence']
            
            if final_decision == 'BUY':
                buy_recommendations.append((ticker, confidence))
            elif final_decision == 'SELL':
                sell_recommendations.append((ticker, confidence))
            else:
                hold_recommendations.append((ticker, confidence))
                
        # 按置信度排序
        buy_recommendations.sort(key=lambda x: x[1], reverse=True)
        sell_recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'buy_recommendations': buy_recommendations,
            'sell_recommendations': sell_recommendations,
            'hold_recommendations': hold_recommendations,
            'total_analyzed': len(results)
        }

def main():
    """测试函数"""
    fund = AIHedgeFund()
    
    # 测试单个股票分析
    result = fund.analyze_stock('AAPL')
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()