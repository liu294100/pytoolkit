#!/usr/bin/env python3
"""
Strategy Customization Module for TradingAgents GUI

This module provides advanced strategy customization capabilities:
- Custom trading strategies with configurable parameters
- Agent behavior customization
- Risk management rules
- Signal weighting and combination logic
- Backtesting and strategy validation

Author: TradingAgents GUI Team
Version: 1.0.0
"""

import json
import numpy as np
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

class SignalType(Enum):
    """Types of trading signals."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"

class AgentRole(Enum):
    """Agent roles in the trading system."""
    FUNDAMENTAL = "fundamental_analyst"
    TECHNICAL = "technical_analyst"
    SENTIMENT = "sentiment_analyst"
    NEWS = "news_analyst"
    BULL_RESEARCHER = "bull_researcher"
    BEAR_RESEARCHER = "bear_researcher"
    TRADER = "trader"
    RISK_MANAGER = "risk_manager"

@dataclass
class TradingSignal:
    """Represents a trading signal from an agent."""
    agent_role: AgentRole
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class StrategyParameters:
    """Configurable strategy parameters."""
    # Risk Management
    max_position_size: float = 0.1  # 10% of portfolio
    stop_loss_percentage: float = 0.05  # 5%
    take_profit_percentage: float = 0.15  # 15%
    max_daily_loss: float = 0.02  # 2%
    
    # Signal Processing
    min_confidence_threshold: float = 0.6  # Minimum confidence to act
    consensus_threshold: float = 0.7  # Threshold for consensus signals
    signal_decay_hours: int = 24  # Hours before signals expire
    
    # Agent Weights
    agent_weights: Dict[str, float] = None
    
    # Technical Indicators
    rsi_oversold: float = 30
    rsi_overbought: float = 70
    macd_sensitivity: float = 0.5
    bollinger_std: float = 2.0
    
    # Fundamental Analysis
    pe_ratio_max: float = 25
    debt_to_equity_max: float = 0.5
    roe_min: float = 0.15
    
    def __post_init__(self):
        if self.agent_weights is None:
            self.agent_weights = {
                "fundamental_analyst": 1.0,
                "technical_analyst": 1.0,
                "sentiment_analyst": 0.8,
                "news_analyst": 0.8,
                "bull_researcher": 0.6,
                "bear_researcher": 0.6,
                "trader": 1.2,
                "risk_manager": 1.5
            }

class CustomStrategy:
    """Customizable trading strategy."""
    
    def __init__(self, name: str, parameters: StrategyParameters = None):
        self.name = name
        self.parameters = parameters or StrategyParameters()
        self.signals: List[TradingSignal] = []
        self.performance_history = []
        self.custom_rules: List[Callable] = []
        
    def add_signal(self, signal: TradingSignal):
        """Add a new trading signal."""
        # Remove expired signals
        cutoff_time = datetime.now() - timedelta(hours=self.parameters.signal_decay_hours)
        self.signals = [s for s in self.signals if s.timestamp > cutoff_time]
        
        # Add new signal
        self.signals.append(signal)
    
    def add_custom_rule(self, rule_function: Callable[[List[TradingSignal], Dict], bool]):
        """Add a custom trading rule."""
        self.custom_rules.append(rule_function)
    
    def calculate_consensus(self, market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate consensus signal from all agents."""
        if not self.signals:
            return {
                'action': SignalType.HOLD,
                'confidence': 0.0,
                'reasoning': 'No signals available',
                'contributing_signals': []
            }
        
        # Filter signals by minimum confidence
        valid_signals = [
            s for s in self.signals 
            if s.confidence >= self.parameters.min_confidence_threshold
        ]
        
        if not valid_signals:
            return {
                'action': SignalType.HOLD,
                'confidence': 0.0,
                'reasoning': 'No signals meet confidence threshold',
                'contributing_signals': []
            }
        
        # Calculate weighted scores for each signal type
        signal_scores = {signal_type: 0.0 for signal_type in SignalType}
        total_weight = 0.0
        
        for signal in valid_signals:
            agent_weight = self.parameters.agent_weights.get(signal.agent_role.value, 1.0)
            weighted_confidence = signal.confidence * agent_weight
            signal_scores[signal.signal_type] += weighted_confidence
            total_weight += agent_weight
        
        # Normalize scores
        if total_weight > 0:
            for signal_type in signal_scores:
                signal_scores[signal_type] /= total_weight
        
        # Find dominant signal
        dominant_signal = max(signal_scores.items(), key=lambda x: x[1])
        action, confidence = dominant_signal
        
        # Apply custom rules
        for rule in self.custom_rules:
            if not rule(valid_signals, market_data or {}):
                return {
                    'action': SignalType.HOLD,
                    'confidence': 0.0,
                    'reasoning': 'Custom rule prevented action',
                    'contributing_signals': []
                }
        
        # Check consensus threshold
        if confidence < self.parameters.consensus_threshold:
            action = SignalType.HOLD
            reasoning = f"Consensus confidence {confidence:.2f} below threshold {self.parameters.consensus_threshold}"
        else:
            contributing_signals = [s for s in valid_signals if s.signal_type == action]
            reasoning = f"Consensus from {len(contributing_signals)} agents: {', '.join([s.agent_role.value for s in contributing_signals])}"
        
        return {
            'action': action,
            'confidence': confidence,
            'reasoning': reasoning,
            'contributing_signals': [asdict(s) for s in valid_signals if s.signal_type == action],
            'all_scores': {st.value: score for st, score in signal_scores.items()}
        }
    
    def validate_trade(self, action: SignalType, symbol: str, 
                      current_price: float, portfolio_value: float) -> Dict[str, Any]:
        """Validate a potential trade against risk management rules."""
        validation_result = {
            'approved': True,
            'reasons': [],
            'suggested_position_size': 0.0,
            'stop_loss_price': None,
            'take_profit_price': None
        }
        
        if action in [SignalType.BUY, SignalType.STRONG_BUY]:
            # Calculate position size
            max_position_value = portfolio_value * self.parameters.max_position_size
            suggested_shares = int(max_position_value / current_price)
            validation_result['suggested_position_size'] = suggested_shares
            
            # Set stop loss and take profit
            stop_loss_price = current_price * (1 - self.parameters.stop_loss_percentage)
            take_profit_price = current_price * (1 + self.parameters.take_profit_percentage)
            
            validation_result['stop_loss_price'] = stop_loss_price
            validation_result['take_profit_price'] = take_profit_price
            validation_result['reasons'].append(f"Position size: {suggested_shares} shares")
            validation_result['reasons'].append(f"Stop loss: ${stop_loss_price:.2f}")
            validation_result['reasons'].append(f"Take profit: ${take_profit_price:.2f}")
        
        elif action in [SignalType.SELL, SignalType.STRONG_SELL]:
            validation_result['reasons'].append("Sell signal validated")
        
        return validation_result
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get strategy performance summary."""
        if not self.performance_history:
            return {'total_trades': 0, 'win_rate': 0.0, 'avg_return': 0.0}
        
        total_trades = len(self.performance_history)
        winning_trades = sum(1 for trade in self.performance_history if trade.get('return', 0) > 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_return = np.mean([trade.get('return', 0) for trade in self.performance_history])
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return': sum(trade.get('return', 0) for trade in self.performance_history)
        }
    
    def save_to_file(self, filepath: str):
        """Save strategy configuration to file."""
        config = {
            'name': self.name,
            'parameters': asdict(self.parameters),
            'performance_history': self.performance_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2, default=str)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'CustomStrategy':
        """Load strategy configuration from file."""
        with open(filepath, 'r') as f:
            config = json.load(f)
        
        parameters = StrategyParameters(**config['parameters'])
        strategy = cls(config['name'], parameters)
        strategy.performance_history = config.get('performance_history', [])
        
        return strategy

class AgentCustomizer:
    """Customize individual agent behaviors."""
    
    def __init__(self):
        self.agent_configs = {}
        self.custom_prompts = {}
        self.analysis_weights = {}
    
    def set_agent_config(self, agent_role: AgentRole, config: Dict[str, Any]):
        """Set custom configuration for an agent."""
        self.agent_configs[agent_role.value] = config
    
    def set_custom_prompt(self, agent_role: AgentRole, prompt_template: str):
        """Set custom prompt template for an agent."""
        self.custom_prompts[agent_role.value] = prompt_template
    
    def set_analysis_weights(self, agent_role: AgentRole, weights: Dict[str, float]):
        """Set analysis weights for different factors."""
        self.analysis_weights[agent_role.value] = weights
    
    def get_agent_prompt(self, agent_role: AgentRole, context: Dict[str, Any]) -> str:
        """Get customized prompt for an agent."""
        base_prompts = {
            AgentRole.FUNDAMENTAL: """
            You are a fundamental analyst. Analyze the following company data:
            
            Financial Metrics: {financial_data}
            Recent Earnings: {earnings_data}
            
            Provide a fundamental analysis with buy/sell/hold recommendation.
            """,
            
            AgentRole.TECHNICAL: """
            You are a technical analyst. Analyze the following price data:
            
            Current Price: {current_price}
            Technical Indicators: {technical_indicators}
            Chart Patterns: {chart_patterns}
            
            Provide a technical analysis with buy/sell/hold recommendation.
            """,
            
            AgentRole.SENTIMENT: """
            You are a sentiment analyst. Analyze the following sentiment data:
            
            Social Media Sentiment: {social_sentiment}
            News Sentiment: {news_sentiment}
            Market Fear/Greed Index: {fear_greed_index}
            
            Provide a sentiment analysis with buy/sell/hold recommendation.
            """
        }
        
        # Use custom prompt if available, otherwise use base prompt
        prompt_template = self.custom_prompts.get(
            agent_role.value, 
            base_prompts.get(agent_role, "Analyze the given data and provide a recommendation.")
        )
        
        return prompt_template.format(**context)
    
    def customize_technical_agent(self, 
                                rsi_weight: float = 1.0,
                                macd_weight: float = 1.0,
                                bollinger_weight: float = 0.8,
                                volume_weight: float = 0.6):
        """Customize technical analysis agent weights."""
        self.set_analysis_weights(AgentRole.TECHNICAL, {
            'rsi': rsi_weight,
            'macd': macd_weight,
            'bollinger_bands': bollinger_weight,
            'volume': volume_weight
        })
    
    def customize_fundamental_agent(self,
                                  pe_weight: float = 1.0,
                                  roe_weight: float = 1.0,
                                  debt_weight: float = 0.8,
                                  growth_weight: float = 1.2):
        """Customize fundamental analysis agent weights."""
        self.set_analysis_weights(AgentRole.FUNDAMENTAL, {
            'pe_ratio': pe_weight,
            'roe': roe_weight,
            'debt_to_equity': debt_weight,
            'revenue_growth': growth_weight
        })

class StrategyBacktester:
    """Backtest trading strategies."""
    
    def __init__(self):
        self.historical_data = {}
        self.backtest_results = {}
    
    def load_historical_data(self, symbol: str, data: List[Dict[str, Any]]):
        """Load historical price data for backtesting."""
        self.historical_data[symbol] = data
    
    def backtest_strategy(self, strategy: CustomStrategy, symbol: str, 
                         start_date: datetime, end_date: datetime,
                         initial_capital: float = 10000) -> Dict[str, Any]:
        """Backtest a strategy against historical data."""
        if symbol not in self.historical_data:
            return {'error': 'No historical data available for symbol'}
        
        # Filter data by date range
        data = [
            d for d in self.historical_data[symbol]
            if start_date <= datetime.fromisoformat(d['date']) <= end_date
        ]
        
        if not data:
            return {'error': 'No data in specified date range'}
        
        # Simulate trading
        capital = initial_capital
        position = 0
        trades = []
        portfolio_values = []
        
        for i, day_data in enumerate(data):
            current_price = day_data['close']
            
            # Simulate agent signals (simplified)
            # In real implementation, this would use historical analysis
            mock_signal = TradingSignal(
                agent_role=AgentRole.TECHNICAL,
                signal_type=SignalType.BUY if i % 10 == 0 else SignalType.HOLD,
                confidence=0.7,
                reasoning="Backtest simulation",
                timestamp=datetime.fromisoformat(day_data['date'])
            )
            
            strategy.add_signal(mock_signal)
            consensus = strategy.calculate_consensus(day_data)
            
            # Execute trades based on consensus
            if consensus['action'] == SignalType.BUY and position == 0:
                shares_to_buy = int(capital * 0.1 / current_price)  # 10% position
                if shares_to_buy > 0:
                    position = shares_to_buy
                    capital -= shares_to_buy * current_price
                    trades.append({
                        'date': day_data['date'],
                        'action': 'buy',
                        'shares': shares_to_buy,
                        'price': current_price,
                        'value': shares_to_buy * current_price
                    })
            
            elif consensus['action'] == SignalType.SELL and position > 0:
                capital += position * current_price
                trades.append({
                    'date': day_data['date'],
                    'action': 'sell',
                    'shares': position,
                    'price': current_price,
                    'value': position * current_price
                })
                position = 0
            
            # Calculate portfolio value
            portfolio_value = capital + (position * current_price)
            portfolio_values.append({
                'date': day_data['date'],
                'value': portfolio_value,
                'cash': capital,
                'position_value': position * current_price
            })
        
        # Calculate performance metrics
        final_value = portfolio_values[-1]['value'] if portfolio_values else initial_capital
        total_return = (final_value - initial_capital) / initial_capital
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_trades': len(trades),
            'trades': trades,
            'portfolio_values': portfolio_values,
            'max_drawdown': self._calculate_max_drawdown(portfolio_values),
            'sharpe_ratio': self._calculate_sharpe_ratio(portfolio_values)
        }
    
    def _calculate_max_drawdown(self, portfolio_values: List[Dict]) -> float:
        """Calculate maximum drawdown."""
        if not portfolio_values:
            return 0.0
        
        values = [pv['value'] for pv in portfolio_values]
        peak = values[0]
        max_drawdown = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_sharpe_ratio(self, portfolio_values: List[Dict], 
                               risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if len(portfolio_values) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(portfolio_values)):
            prev_value = portfolio_values[i-1]['value']
            curr_value = portfolio_values[i]['value']
            daily_return = (curr_value - prev_value) / prev_value
            returns.append(daily_return)
        
        if not returns:
            return 0.0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe ratio
        daily_risk_free = risk_free_rate / 252  # 252 trading days per year
        sharpe = (avg_return - daily_risk_free) / std_return * np.sqrt(252)
        
        return sharpe

# Predefined strategy templates
CONSERVATIVE_STRATEGY = StrategyParameters(
    max_position_size=0.05,
    stop_loss_percentage=0.03,
    take_profit_percentage=0.08,
    min_confidence_threshold=0.8,
    consensus_threshold=0.8
)

AGGRESSIVE_STRATEGY = StrategyParameters(
    max_position_size=0.2,
    stop_loss_percentage=0.08,
    take_profit_percentage=0.25,
    min_confidence_threshold=0.6,
    consensus_threshold=0.6
)

BALANCED_STRATEGY = StrategyParameters(
    max_position_size=0.1,
    stop_loss_percentage=0.05,
    take_profit_percentage=0.15,
    min_confidence_threshold=0.7,
    consensus_threshold=0.7
)

class RiskManager:
    """Risk management system for trading strategies."""
    
    def __init__(self):
        self.max_position_size = 0.1  # 10% of portfolio
        self.stop_loss_percentage = 0.05  # 5%
        self.max_daily_loss = 0.02  # 2%
        self.current_positions = {}
        self.daily_pnl = 0.0
        self.portfolio_value = 100000.0  # Default portfolio value
    
    def validate_trade(self, symbol: str, signal: TradingSignal, position_size: float) -> Dict[str, Any]:
        """Validate if a trade meets risk management criteria."""
        validation_result = {
            'approved': True,
            'reasons': [],
            'adjusted_size': position_size
        }
        
        # Check position size limit
        if position_size > self.max_position_size:
            validation_result['adjusted_size'] = self.max_position_size
            validation_result['reasons'].append(f"Position size reduced to {self.max_position_size*100}% limit")
        
        # Check daily loss limit
        if self.daily_pnl < -self.max_daily_loss * self.portfolio_value:
            validation_result['approved'] = False
            validation_result['reasons'].append("Daily loss limit exceeded")
        
        # Check signal confidence
        if signal.confidence < 0.5:
            validation_result['approved'] = False
            validation_result['reasons'].append("Signal confidence too low")
        
        return validation_result
    
    def calculate_stop_loss(self, entry_price: float, signal_type: SignalType) -> float:
        """Calculate stop loss price based on entry price and signal type."""
        if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            return entry_price * (1 - self.stop_loss_percentage)
        elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            return entry_price * (1 + self.stop_loss_percentage)
        return entry_price
    
    def update_position(self, symbol: str, quantity: float, price: float):
        """Update position tracking."""
        if symbol not in self.current_positions:
            self.current_positions[symbol] = {'quantity': 0, 'avg_price': 0}
        
        current_pos = self.current_positions[symbol]
        total_value = current_pos['quantity'] * current_pos['avg_price'] + quantity * price
        total_quantity = current_pos['quantity'] + quantity
        
        if total_quantity != 0:
            self.current_positions[symbol] = {
                'quantity': total_quantity,
                'avg_price': total_value / total_quantity
            }
        else:
            del self.current_positions[symbol]
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics."""
        total_exposure = sum(abs(pos['quantity'] * pos['avg_price']) 
                           for pos in self.current_positions.values())
        
        return {
            'total_exposure': total_exposure,
            'exposure_ratio': total_exposure / self.portfolio_value,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_ratio': self.daily_pnl / self.portfolio_value,
            'active_positions': len(self.current_positions),
            'max_position_size': self.max_position_size,
            'stop_loss_percentage': self.stop_loss_percentage
        }

class StrategyManager:
    """Main strategy management class for the TradingAgents GUI."""
    
    def __init__(self):
        self.strategies = {}
        self.active_strategy = None
        self.agent_customizer = AgentCustomizer()
        self.risk_manager = RiskManager()
        self.backtester = StrategyBacktester()
        
        # Load default strategies
        self._load_default_strategies()
    
    def _load_default_strategies(self):
        """Load predefined strategy templates."""
        self.strategies['conservative'] = CustomStrategy('Conservative', CONSERVATIVE_STRATEGY)
        self.strategies['aggressive'] = CustomStrategy('Aggressive', AGGRESSIVE_STRATEGY)
        self.strategies['balanced'] = CustomStrategy('Balanced', BALANCED_STRATEGY)
        
        # Set balanced as default
        self.active_strategy = self.strategies['balanced']
    
    def create_strategy(self, name: str, parameters: StrategyParameters) -> CustomStrategy:
        """Create a new custom strategy."""
        strategy = CustomStrategy(name, parameters)
        self.strategies[name.lower()] = strategy
        return strategy
    
    def set_active_strategy(self, strategy_name: str) -> bool:
        """Set the active trading strategy."""
        if strategy_name.lower() in self.strategies:
            self.active_strategy = self.strategies[strategy_name.lower()]
            return True
        return False
    
    def get_active_strategy(self) -> Optional[CustomStrategy]:
        """Get the currently active strategy."""
        return self.active_strategy
    
    def list_strategies(self) -> List[str]:
        """List all available strategies."""
        return list(self.strategies.keys())
    
    def validate_signals(self, signals: List[TradingSignal], 
                        market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate trading signals using the active strategy."""
        if not self.active_strategy:
            return {'valid': False, 'reason': 'No active strategy set'}
        
        # Combine signals using the active strategy
        combined_signal = self.active_strategy.combine_signals(signals)
        
        # Validate with risk management
        risk_validation = self.risk_manager.validate_trade(
            combined_signal['action'],
            market_data.get('current_price', 0),
            market_data.get('portfolio_value', 100000)
        )
        
        return {
            'valid': risk_validation['valid'],
            'combined_signal': combined_signal,
            'risk_validation': risk_validation,
            'strategy_name': self.active_strategy.name
        }
    
    def backtest_strategy(self, strategy_name: str, 
                         historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Backtest a strategy against historical data."""
        if strategy_name.lower() not in self.strategies:
            return {'error': f'Strategy {strategy_name} not found'}
        
        strategy = self.strategies[strategy_name.lower()]
        return self.backtester.run_backtest(strategy, historical_data)
    
    def get_strategy_performance(self, strategy_name: str) -> Dict[str, Any]:
        """Get performance metrics for a strategy."""
        if strategy_name.lower() not in self.strategies:
            return {'error': f'Strategy {strategy_name} not found'}
        
        strategy = self.strategies[strategy_name.lower()]
        return strategy.get_performance_summary()
    
    def customize_agent(self, agent_role: AgentRole, config: Dict[str, Any]):
        """Customize an agent's behavior."""
        self.agent_customizer.set_agent_config(agent_role, config)
    
    def get_agent_prompt(self, agent_role: AgentRole, context: Dict[str, Any]) -> str:
        """Get customized prompt for an agent."""
        return self.agent_customizer.get_agent_prompt(agent_role, context)
    
    def save_strategy(self, strategy_name: str, filepath: str) -> bool:
        """Save a strategy to file."""
        try:
            if strategy_name.lower() in self.strategies:
                self.strategies[strategy_name.lower()].save_to_file(filepath)
                return True
            return False
        except Exception as e:
            print(f"Error saving strategy: {e}")
            return False
    
    def load_strategy(self, filepath: str) -> bool:
        """Load a strategy from file."""
        try:
            strategy = CustomStrategy.load_from_file(filepath)
            self.strategies[strategy.name.lower()] = strategy
            return True
        except Exception as e:
            print(f"Error loading strategy: {e}")
            return False
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk management metrics."""
        return self.risk_manager.get_risk_metrics()
    
    def update_risk_parameters(self, parameters: Dict[str, Any]):
        """Update risk management parameters."""
        self.risk_manager.update_parameters(parameters)