#!/usr/bin/env python3
"""
Advanced Technical Indicators Module for TradingAgents GUI

This module provides comprehensive technical analysis indicators:
- Trend indicators (MACD, ADX, Parabolic SAR)
- Momentum indicators (Stochastic, Williams %R, CCI)
- Volume indicators (OBV, Volume Profile, VWAP)
- Volatility indicators (ATR, Keltner Channels)
- Support/Resistance levels
- Pattern recognition
- Custom indicator framework

Author: TradingAgents GUI Team
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import math
from collections import deque

class IndicatorType(Enum):
    """Types of technical indicators."""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLUME = "volume"
    VOLATILITY = "volatility"
    SUPPORT_RESISTANCE = "support_resistance"
    PATTERN = "pattern"

@dataclass
class OHLCV:
    """Open, High, Low, Close, Volume data structure."""
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime

@dataclass
class IndicatorResult:
    """Result of technical indicator calculation."""
    name: str
    type: IndicatorType
    values: Dict[str, float]
    signals: List[str]
    confidence: float
    timestamp: datetime

class TrendIndicators:
    """Trend-following technical indicators."""
    
    @staticmethod
    def macd(prices: List[float], fast_period: int = 12, 
             slow_period: int = 26, signal_period: int = 9) -> Dict[str, float]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(prices) < slow_period:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        # Calculate EMAs
        ema_fast = TrendIndicators._ema(prices, fast_period)
        ema_slow = TrendIndicators._ema(prices, slow_period)
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD)
        macd_values = [macd_line] * len(prices)  # Simplified for demo
        signal_line = TrendIndicators._ema(macd_values[-signal_period:], signal_period)
        
        # Histogram
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def adx(highs: List[float], lows: List[float], closes: List[float], 
            period: int = 14) -> Dict[str, float]:
        """Calculate ADX (Average Directional Index)."""
        if len(closes) < period + 1:
            return {'adx': 0, 'di_plus': 0, 'di_minus': 0}
        
        # Calculate True Range and Directional Movement
        tr_values = []
        dm_plus = []
        dm_minus = []
        
        for i in range(1, len(closes)):
            # True Range
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr = max(tr1, tr2, tr3)
            tr_values.append(tr)
            
            # Directional Movement
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            
            dm_plus.append(up_move if up_move > down_move and up_move > 0 else 0)
            dm_minus.append(down_move if down_move > up_move and down_move > 0 else 0)
        
        if len(tr_values) < period:
            return {'adx': 0, 'di_plus': 0, 'di_minus': 0}
        
        # Calculate smoothed averages
        atr = sum(tr_values[-period:]) / period
        dm_plus_smooth = sum(dm_plus[-period:]) / period
        dm_minus_smooth = sum(dm_minus[-period:]) / period
        
        # Calculate DI+ and DI-
        di_plus = (dm_plus_smooth / atr) * 100 if atr > 0 else 0
        di_minus = (dm_minus_smooth / atr) * 100 if atr > 0 else 0
        
        # Calculate ADX
        dx = abs(di_plus - di_minus) / (di_plus + di_minus) * 100 if (di_plus + di_minus) > 0 else 0
        adx = dx  # Simplified - should be smoothed average of DX
        
        return {
            'adx': adx,
            'di_plus': di_plus,
            'di_minus': di_minus
        }
    
    @staticmethod
    def parabolic_sar(highs: List[float], lows: List[float], 
                      acceleration: float = 0.02, maximum: float = 0.2) -> List[float]:
        """Calculate Parabolic SAR."""
        if len(highs) < 2:
            return [highs[0] if highs else 0]
        
        sar_values = [lows[0]]  # Start with first low
        af = acceleration
        ep = highs[0]  # Extreme point
        is_uptrend = True
        
        for i in range(1, len(highs)):
            # Calculate SAR
            sar = sar_values[-1] + af * (ep - sar_values[-1])
            
            if is_uptrend:
                # Uptrend
                if lows[i] <= sar:
                    # Trend reversal
                    is_uptrend = False
                    sar = ep
                    ep = lows[i]
                    af = acceleration
                else:
                    # Continue uptrend
                    if highs[i] > ep:
                        ep = highs[i]
                        af = min(af + acceleration, maximum)
                    
                    # Adjust SAR
                    sar = min(sar, lows[i-1], lows[i] if i > 0 else lows[i-1])
            else:
                # Downtrend
                if highs[i] >= sar:
                    # Trend reversal
                    is_uptrend = True
                    sar = ep
                    ep = highs[i]
                    af = acceleration
                else:
                    # Continue downtrend
                    if lows[i] < ep:
                        ep = lows[i]
                        af = min(af + acceleration, maximum)
                    
                    # Adjust SAR
                    sar = max(sar, highs[i-1], highs[i] if i > 0 else highs[i-1])
            
            sar_values.append(sar)
        
        return sar_values
    
    @staticmethod
    def _ema(prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return sum(prices) / len(prices) if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # Start with SMA
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema

class MomentumIndicators:
    """Momentum-based technical indicators."""
    
    @staticmethod
    def stochastic(highs: List[float], lows: List[float], closes: List[float],
                   k_period: int = 14, d_period: int = 3) -> Dict[str, float]:
        """Calculate Stochastic Oscillator."""
        if len(closes) < k_period:
            return {'%K': 50, '%D': 50}
        
        # Calculate %K
        recent_highs = highs[-k_period:]
        recent_lows = lows[-k_period:]
        current_close = closes[-1]
        
        highest_high = max(recent_highs)
        lowest_low = min(recent_lows)
        
        if highest_high == lowest_low:
            k_percent = 50
        else:
            k_percent = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
        
        # Calculate %D (SMA of %K)
        # For simplicity, using current %K as %D
        d_percent = k_percent
        
        return {
            '%K': k_percent,
            '%D': d_percent
        }
    
    @staticmethod
    def williams_r(highs: List[float], lows: List[float], closes: List[float],
                   period: int = 14) -> float:
        """Calculate Williams %R."""
        if len(closes) < period:
            return -50
        
        recent_highs = highs[-period:]
        recent_lows = lows[-period:]
        current_close = closes[-1]
        
        highest_high = max(recent_highs)
        lowest_low = min(recent_lows)
        
        if highest_high == lowest_low:
            return -50
        
        williams_r = ((highest_high - current_close) / (highest_high - lowest_low)) * -100
        return williams_r
    
    @staticmethod
    def cci(highs: List[float], lows: List[float], closes: List[float],
            period: int = 20) -> float:
        """Calculate Commodity Channel Index."""
        if len(closes) < period:
            return 0
        
        # Calculate Typical Price
        typical_prices = []
        for i in range(len(closes)):
            tp = (highs[i] + lows[i] + closes[i]) / 3
            typical_prices.append(tp)
        
        # Calculate SMA of Typical Price
        recent_tp = typical_prices[-period:]
        sma_tp = sum(recent_tp) / period
        
        # Calculate Mean Deviation
        mean_deviation = sum(abs(tp - sma_tp) for tp in recent_tp) / period
        
        # Calculate CCI
        if mean_deviation == 0:
            return 0
        
        current_tp = typical_prices[-1]
        cci = (current_tp - sma_tp) / (0.015 * mean_deviation)
        
        return cci
    
    @staticmethod
    def roc(prices: List[float], period: int = 12) -> float:
        """Calculate Rate of Change."""
        if len(prices) < period + 1:
            return 0
        
        current_price = prices[-1]
        past_price = prices[-(period + 1)]
        
        if past_price == 0:
            return 0
        
        roc = ((current_price - past_price) / past_price) * 100
        return roc

class VolumeIndicators:
    """Volume-based technical indicators."""
    
    @staticmethod
    def obv(closes: List[float], volumes: List[float]) -> float:
        """Calculate On-Balance Volume."""
        if len(closes) < 2 or len(volumes) != len(closes):
            return 0
        
        obv = 0
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv += volumes[i]
            elif closes[i] < closes[i-1]:
                obv -= volumes[i]
            # If closes[i] == closes[i-1], OBV remains unchanged
        
        return obv
    
    @staticmethod
    def vwap(highs: List[float], lows: List[float], closes: List[float],
             volumes: List[float]) -> float:
        """Calculate Volume Weighted Average Price."""
        if not all(len(lst) == len(closes) for lst in [highs, lows, volumes]):
            return 0
        
        total_volume = 0
        total_price_volume = 0
        
        for i in range(len(closes)):
            typical_price = (highs[i] + lows[i] + closes[i]) / 3
            volume = volumes[i]
            
            total_price_volume += typical_price * volume
            total_volume += volume
        
        if total_volume == 0:
            return 0
        
        return total_price_volume / total_volume
    
    @staticmethod
    def volume_profile(prices: List[float], volumes: List[float],
                      num_levels: int = 20) -> Dict[str, Any]:
        """Calculate Volume Profile."""
        if len(prices) != len(volumes) or len(prices) < 2:
            return {'levels': [], 'poc': 0, 'value_area': (0, 0)}
        
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        
        if price_range == 0:
            return {'levels': [], 'poc': prices[0], 'value_area': (prices[0], prices[0])}
        
        level_size = price_range / num_levels
        volume_levels = [0] * num_levels
        
        # Distribute volume across price levels
        for price, volume in zip(prices, volumes):
            level_index = min(int((price - min_price) / level_size), num_levels - 1)
            volume_levels[level_index] += volume
        
        # Find Point of Control (highest volume level)
        poc_index = volume_levels.index(max(volume_levels))
        poc_price = min_price + (poc_index + 0.5) * level_size
        
        # Calculate Value Area (70% of volume)
        total_volume = sum(volume_levels)
        target_volume = total_volume * 0.7
        
        # Find value area around POC
        value_area_volume = volume_levels[poc_index]
        lower_bound = upper_bound = poc_index
        
        while value_area_volume < target_volume and (lower_bound > 0 or upper_bound < num_levels - 1):
            lower_vol = volume_levels[lower_bound - 1] if lower_bound > 0 else 0
            upper_vol = volume_levels[upper_bound + 1] if upper_bound < num_levels - 1 else 0
            
            if lower_vol >= upper_vol and lower_bound > 0:
                lower_bound -= 1
                value_area_volume += lower_vol
            elif upper_bound < num_levels - 1:
                upper_bound += 1
                value_area_volume += upper_vol
            else:
                break
        
        value_area_low = min_price + lower_bound * level_size
        value_area_high = min_price + (upper_bound + 1) * level_size
        
        return {
            'levels': volume_levels,
            'poc': poc_price,
            'value_area': (value_area_low, value_area_high)
        }

class VolatilityIndicators:
    """Volatility-based technical indicators."""
    
    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float],
            period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(closes) < 2:
            return 0
        
        true_ranges = []
        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0
        
        return sum(true_ranges[-period:]) / period
    
    @staticmethod
    def keltner_channels(highs: List[float], lows: List[float], closes: List[float],
                        period: int = 20, multiplier: float = 2.0) -> Dict[str, float]:
        """Calculate Keltner Channels."""
        if len(closes) < period:
            current_price = closes[-1] if closes else 0
            return {
                'upper': current_price * 1.02,
                'middle': current_price,
                'lower': current_price * 0.98
            }
        
        # Calculate EMA of typical price
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        ema_tp = TrendIndicators._ema(typical_prices, period)
        
        # Calculate ATR
        atr = VolatilityIndicators.atr(highs, lows, closes, period)
        
        return {
            'upper': ema_tp + (multiplier * atr),
            'middle': ema_tp,
            'lower': ema_tp - (multiplier * atr)
        }
    
    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20,
                       std_multiplier: float = 2.0) -> Dict[str, float]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            current_price = prices[-1] if prices else 0
            return {
                'upper': current_price * 1.02,
                'middle': current_price,
                'lower': current_price * 0.98,
                'bandwidth': 0.04,
                '%b': 0.5
            }
        
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period
        
        # Calculate standard deviation
        variance = sum((price - sma) ** 2 for price in recent_prices) / period
        std_dev = math.sqrt(variance)
        
        upper_band = sma + (std_multiplier * std_dev)
        lower_band = sma - (std_multiplier * std_dev)
        
        # Calculate %B and Bandwidth
        current_price = prices[-1]
        bandwidth = (upper_band - lower_band) / sma if sma != 0 else 0
        
        if upper_band != lower_band:
            percent_b = (current_price - lower_band) / (upper_band - lower_band)
        else:
            percent_b = 0.5
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band,
            'bandwidth': bandwidth,
            '%b': percent_b
        }

class SupportResistanceAnalyzer:
    """Support and resistance level analysis."""
    
    @staticmethod
    def find_pivot_points(highs: List[float], lows: List[float], closes: List[float],
                         lookback: int = 5) -> Dict[str, List[float]]:
        """Find pivot highs and lows."""
        pivot_highs = []
        pivot_lows = []
        
        for i in range(lookback, len(highs) - lookback):
            # Check for pivot high
            is_pivot_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and highs[j] >= highs[i]:
                    is_pivot_high = False
                    break
            
            if is_pivot_high:
                pivot_highs.append(highs[i])
            
            # Check for pivot low
            is_pivot_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and lows[j] <= lows[i]:
                    is_pivot_low = False
                    break
            
            if is_pivot_low:
                pivot_lows.append(lows[i])
        
        return {
            'resistance_levels': pivot_highs,
            'support_levels': pivot_lows
        }
    
    @staticmethod
    def fibonacci_retracement(high: float, low: float) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels."""
        diff = high - low
        
        return {
            '0%': high,
            '23.6%': high - (diff * 0.236),
            '38.2%': high - (diff * 0.382),
            '50%': high - (diff * 0.5),
            '61.8%': high - (diff * 0.618),
            '78.6%': high - (diff * 0.786),
            '100%': low
        }
    
    @staticmethod
    def identify_key_levels(prices: List[float], volume: List[float],
                           min_touches: int = 2) -> List[Dict[str, Any]]:
        """Identify key support/resistance levels."""
        if len(prices) < 10:
            return []
        
        # Group prices into levels
        price_range = max(prices) - min(prices)
        level_tolerance = price_range * 0.01  # 1% tolerance
        
        levels = []
        for price in prices:
            # Find existing level within tolerance
            found_level = None
            for level in levels:
                if abs(price - level['price']) <= level_tolerance:
                    found_level = level
                    break
            
            if found_level:
                found_level['touches'] += 1
                found_level['total_volume'] += volume[prices.index(price)] if volume else 0
            else:
                levels.append({
                    'price': price,
                    'touches': 1,
                    'total_volume': volume[prices.index(price)] if volume else 0,
                    'strength': 0
                })
        
        # Filter levels with minimum touches and calculate strength
        key_levels = []
        for level in levels:
            if level['touches'] >= min_touches:
                # Calculate strength based on touches and volume
                level['strength'] = level['touches'] * (1 + level['total_volume'] / max(volume) if volume else 1)
                key_levels.append(level)
        
        # Sort by strength
        key_levels.sort(key=lambda x: x['strength'], reverse=True)
        
        return key_levels[:10]  # Return top 10 levels

class PatternRecognition:
    """Chart pattern recognition."""
    
    @staticmethod
    def detect_double_top(highs: List[float], tolerance: float = 0.02) -> bool:
        """Detect double top pattern."""
        if len(highs) < 10:
            return False
        
        # Find the two highest peaks
        sorted_highs = sorted(enumerate(highs), key=lambda x: x[1], reverse=True)
        
        if len(sorted_highs) < 2:
            return False
        
        peak1_idx, peak1_val = sorted_highs[0]
        peak2_idx, peak2_val = sorted_highs[1]
        
        # Check if peaks are similar in height
        if abs(peak1_val - peak2_val) / max(peak1_val, peak2_val) > tolerance:
            return False
        
        # Check if peaks are separated by at least 5 periods
        if abs(peak1_idx - peak2_idx) < 5:
            return False
        
        # Check if there's a valley between peaks
        start_idx = min(peak1_idx, peak2_idx)
        end_idx = max(peak1_idx, peak2_idx)
        valley_min = min(highs[start_idx:end_idx+1])
        
        # Valley should be significantly lower than peaks
        if (min(peak1_val, peak2_val) - valley_min) / min(peak1_val, peak2_val) < 0.05:
            return False
        
        return True
    
    @staticmethod
    def detect_double_bottom(lows: List[float], tolerance: float = 0.02) -> bool:
        """Detect double bottom pattern."""
        if len(lows) < 10:
            return False
        
        # Find the two lowest troughs
        sorted_lows = sorted(enumerate(lows), key=lambda x: x[1])
        
        if len(sorted_lows) < 2:
            return False
        
        trough1_idx, trough1_val = sorted_lows[0]
        trough2_idx, trough2_val = sorted_lows[1]
        
        # Check if troughs are similar in depth
        if abs(trough1_val - trough2_val) / max(trough1_val, trough2_val) > tolerance:
            return False
        
        # Check if troughs are separated by at least 5 periods
        if abs(trough1_idx - trough2_idx) < 5:
            return False
        
        # Check if there's a peak between troughs
        start_idx = min(trough1_idx, trough2_idx)
        end_idx = max(trough1_idx, trough2_idx)
        peak_max = max(lows[start_idx:end_idx+1])
        
        # Peak should be significantly higher than troughs
        if (peak_max - max(trough1_val, trough2_val)) / max(trough1_val, trough2_val) < 0.05:
            return False
        
        return True
    
    @staticmethod
    def detect_head_and_shoulders(highs: List[float], tolerance: float = 0.03) -> Dict[str, Any]:
        """Detect head and shoulders pattern."""
        if len(highs) < 15:
            return {'detected': False}
        
        # Find three highest peaks
        sorted_highs = sorted(enumerate(highs), key=lambda x: x[1], reverse=True)
        
        if len(sorted_highs) < 3:
            return {'detected': False}
        
        # Get top 3 peaks
        peaks = sorted_highs[:3]
        peaks.sort(key=lambda x: x[0])  # Sort by index (time)
        
        left_shoulder = peaks[0]
        head = peaks[1]
        right_shoulder = peaks[2]
        
        # Check if head is higher than shoulders
        if head[1] <= max(left_shoulder[1], right_shoulder[1]):
            return {'detected': False}
        
        # Check if shoulders are roughly equal
        shoulder_diff = abs(left_shoulder[1] - right_shoulder[1]) / max(left_shoulder[1], right_shoulder[1])
        if shoulder_diff > tolerance:
            return {'detected': False}
        
        # Check spacing between peaks
        if (head[0] - left_shoulder[0] < 3 or 
            right_shoulder[0] - head[0] < 3):
            return {'detected': False}
        
        # Calculate neckline (support level)
        neckline = (left_shoulder[1] + right_shoulder[1]) / 2
        
        return {
            'detected': True,
            'left_shoulder': left_shoulder,
            'head': head,
            'right_shoulder': right_shoulder,
            'neckline': neckline
        }

class TechnicalAnalyzer:
    """Main technical analysis coordinator."""
    
    def __init__(self):
        self.trend_indicators = TrendIndicators()
        self.momentum_indicators = MomentumIndicators()
        self.volume_indicators = VolumeIndicators()
        self.volatility_indicators = VolatilityIndicators()
        self.support_resistance = SupportResistanceAnalyzer()
        self.pattern_recognition = PatternRecognition()
        
        self.indicator_cache = {}
        self.analysis_history = deque(maxlen=100)
    
    def analyze_ohlcv_data(self, ohlcv_data: List[OHLCV]) -> Dict[str, IndicatorResult]:
        """Comprehensive analysis of OHLCV data."""
        if not ohlcv_data:
            return {}
        
        # Extract data arrays
        opens = [d.open for d in ohlcv_data]
        highs = [d.high for d in ohlcv_data]
        lows = [d.low for d in ohlcv_data]
        closes = [d.close for d in ohlcv_data]
        volumes = [d.volume for d in ohlcv_data]
        
        results = {}
        current_time = datetime.now()
        
        # Trend Analysis
        macd_data = self.trend_indicators.macd(closes)
        results['MACD'] = IndicatorResult(
            name='MACD',
            type=IndicatorType.TREND,
            values=macd_data,
            signals=self._generate_macd_signals(macd_data),
            confidence=self._calculate_macd_confidence(macd_data),
            timestamp=current_time
        )
        
        adx_data = self.trend_indicators.adx(highs, lows, closes)
        results['ADX'] = IndicatorResult(
            name='ADX',
            type=IndicatorType.TREND,
            values=adx_data,
            signals=self._generate_adx_signals(adx_data),
            confidence=self._calculate_adx_confidence(adx_data),
            timestamp=current_time
        )
        
        # Momentum Analysis
        stoch_data = self.momentum_indicators.stochastic(highs, lows, closes)
        results['Stochastic'] = IndicatorResult(
            name='Stochastic',
            type=IndicatorType.MOMENTUM,
            values=stoch_data,
            signals=self._generate_stochastic_signals(stoch_data),
            confidence=self._calculate_stochastic_confidence(stoch_data),
            timestamp=current_time
        )
        
        rsi_value = self._calculate_rsi(closes)
        results['RSI'] = IndicatorResult(
            name='RSI',
            type=IndicatorType.MOMENTUM,
            values={'rsi': rsi_value},
            signals=self._generate_rsi_signals(rsi_value),
            confidence=self._calculate_rsi_confidence(rsi_value),
            timestamp=current_time
        )
        
        # Volume Analysis
        obv_value = self.volume_indicators.obv(closes, volumes)
        vwap_value = self.volume_indicators.vwap(highs, lows, closes, volumes)
        results['Volume'] = IndicatorResult(
            name='Volume Analysis',
            type=IndicatorType.VOLUME,
            values={'obv': obv_value, 'vwap': vwap_value},
            signals=self._generate_volume_signals(obv_value, vwap_value, closes[-1]),
            confidence=0.7,
            timestamp=current_time
        )
        
        # Volatility Analysis
        bb_data = self.volatility_indicators.bollinger_bands(closes)
        atr_value = self.volatility_indicators.atr(highs, lows, closes)
        results['Volatility'] = IndicatorResult(
            name='Volatility Analysis',
            type=IndicatorType.VOLATILITY,
            values={**bb_data, 'atr': atr_value},
            signals=self._generate_volatility_signals(bb_data, atr_value),
            confidence=self._calculate_volatility_confidence(bb_data),
            timestamp=current_time
        )
        
        # Support/Resistance Analysis
        sr_levels = self.support_resistance.find_pivot_points(highs, lows, closes)
        key_levels = self.support_resistance.identify_key_levels(closes, volumes)
        results['Support_Resistance'] = IndicatorResult(
            name='Support/Resistance',
            type=IndicatorType.SUPPORT_RESISTANCE,
            values={'pivot_points': sr_levels, 'key_levels': key_levels},
            signals=self._generate_sr_signals(key_levels, closes[-1]),
            confidence=0.8,
            timestamp=current_time
        )
        
        # Pattern Recognition
        patterns = self._detect_patterns(highs, lows, closes)
        results['Patterns'] = IndicatorResult(
            name='Chart Patterns',
            type=IndicatorType.PATTERN,
            values=patterns,
            signals=self._generate_pattern_signals(patterns),
            confidence=self._calculate_pattern_confidence(patterns),
            timestamp=current_time
        )
        
        # Store analysis in history
        self.analysis_history.append({
            'timestamp': current_time,
            'results': results,
            'data_points': len(ohlcv_data)
        })
        
        return results
    
    def get_trading_signals(self, analysis_results: Dict[str, IndicatorResult]) -> Dict[str, Any]:
        """Generate consolidated trading signals."""
        signals = {
            'overall_signal': 'NEUTRAL',
            'confidence': 0.0,
            'signals_breakdown': {},
            'risk_level': 'MEDIUM'
        }
        
        bullish_signals = 0
        bearish_signals = 0
        total_confidence = 0
        signal_count = 0
        
        for indicator_name, result in analysis_results.items():
            indicator_signals = result.signals
            confidence = result.confidence
            
            signals['signals_breakdown'][indicator_name] = {
                'signals': indicator_signals,
                'confidence': confidence
            }
            
            # Count bullish/bearish signals
            for signal in indicator_signals:
                if 'BUY' in signal or 'BULLISH' in signal:
                    bullish_signals += 1
                elif 'SELL' in signal or 'BEARISH' in signal:
                    bearish_signals += 1
            
            total_confidence += confidence
            signal_count += 1
        
        # Determine overall signal
        if bullish_signals > bearish_signals * 1.5:
            signals['overall_signal'] = 'BUY'
        elif bearish_signals > bullish_signals * 1.5:
            signals['overall_signal'] = 'SELL'
        else:
            signals['overall_signal'] = 'NEUTRAL'
        
        # Calculate overall confidence
        signals['confidence'] = total_confidence / max(signal_count, 1)
        
        # Determine risk level
        volatility_result = analysis_results.get('Volatility')
        if volatility_result:
            atr = volatility_result.values.get('atr', 0)
            bandwidth = volatility_result.values.get('bandwidth', 0)
            
            if atr > 2.0 or bandwidth > 0.1:
                signals['risk_level'] = 'HIGH'
            elif atr < 0.5 and bandwidth < 0.03:
                signals['risk_level'] = 'LOW'
        
        return signals
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _detect_patterns(self, highs: List[float], lows: List[float], 
                        closes: List[float]) -> Dict[str, Any]:
        """Detect chart patterns."""
        patterns = {
            'double_top': self.pattern_recognition.detect_double_top(highs),
            'double_bottom': self.pattern_recognition.detect_double_bottom(lows),
            'head_and_shoulders': self.pattern_recognition.detect_head_and_shoulders(highs)
        }
        
        return patterns
    
    # Signal generation methods
    def _generate_macd_signals(self, macd_data: Dict[str, float]) -> List[str]:
        signals = []
        macd = macd_data.get('macd', 0)
        signal = macd_data.get('signal', 0)
        histogram = macd_data.get('histogram', 0)
        
        if macd > signal and histogram > 0:
            signals.append('MACD BULLISH CROSSOVER')
        elif macd < signal and histogram < 0:
            signals.append('MACD BEARISH CROSSOVER')
        
        return signals
    
    def _generate_adx_signals(self, adx_data: Dict[str, float]) -> List[str]:
        signals = []
        adx = adx_data.get('adx', 0)
        di_plus = adx_data.get('di_plus', 0)
        di_minus = adx_data.get('di_minus', 0)
        
        if adx > 25:
            if di_plus > di_minus:
                signals.append('STRONG UPTREND')
            else:
                signals.append('STRONG DOWNTREND')
        elif adx < 20:
            signals.append('WEAK TREND - SIDEWAYS')
        
        return signals
    
    def _generate_stochastic_signals(self, stoch_data: Dict[str, float]) -> List[str]:
        signals = []
        k_percent = stoch_data.get('%K', 50)
        
        if k_percent > 80:
            signals.append('OVERBOUGHT')
        elif k_percent < 20:
            signals.append('OVERSOLD')
        
        return signals
    
    def _generate_rsi_signals(self, rsi: float) -> List[str]:
        signals = []
        
        if rsi > 70:
            signals.append('RSI OVERBOUGHT')
        elif rsi < 30:
            signals.append('RSI OVERSOLD')
        elif rsi > 50:
            signals.append('RSI BULLISH')
        else:
            signals.append('RSI BEARISH')
        
        return signals
    
    def _generate_volume_signals(self, obv: float, vwap: float, current_price: float) -> List[str]:
        signals = []
        
        if current_price > vwap:
            signals.append('PRICE ABOVE VWAP')
        else:
            signals.append('PRICE BELOW VWAP')
        
        if obv > 0:
            signals.append('POSITIVE VOLUME FLOW')
        else:
            signals.append('NEGATIVE VOLUME FLOW')
        
        return signals
    
    def _generate_volatility_signals(self, bb_data: Dict[str, float], atr: float) -> List[str]:
        signals = []
        percent_b = bb_data.get('%b', 0.5)
        bandwidth = bb_data.get('bandwidth', 0)
        
        if percent_b > 1:
            signals.append('PRICE ABOVE UPPER BOLLINGER BAND')
        elif percent_b < 0:
            signals.append('PRICE BELOW LOWER BOLLINGER BAND')
        
        if bandwidth < 0.02:
            signals.append('LOW VOLATILITY - SQUEEZE')
        elif bandwidth > 0.1:
            signals.append('HIGH VOLATILITY')
        
        return signals
    
    def _generate_sr_signals(self, key_levels: List[Dict[str, Any]], current_price: float) -> List[str]:
        signals = []
        
        for level in key_levels[:3]:  # Check top 3 levels
            price_level = level['price']
            tolerance = abs(current_price - price_level) / current_price
            
            if tolerance < 0.01:  # Within 1%
                if current_price > price_level:
                    signals.append(f'NEAR RESISTANCE AT {price_level:.2f}')
                else:
                    signals.append(f'NEAR SUPPORT AT {price_level:.2f}')
        
        return signals
    
    def _generate_pattern_signals(self, patterns: Dict[str, Any]) -> List[str]:
        signals = []
        
        if patterns.get('double_top'):
            signals.append('DOUBLE TOP PATTERN DETECTED')
        
        if patterns.get('double_bottom'):
            signals.append('DOUBLE BOTTOM PATTERN DETECTED')
        
        hs_pattern = patterns.get('head_and_shoulders', {})
        if hs_pattern.get('detected'):
            signals.append('HEAD AND SHOULDERS PATTERN DETECTED')
        
        return signals
    
    # Confidence calculation methods
    def _calculate_macd_confidence(self, macd_data: Dict[str, float]) -> float:
        histogram = abs(macd_data.get('histogram', 0))
        return min(histogram * 10, 1.0)  # Scale to 0-1
    
    def _calculate_adx_confidence(self, adx_data: Dict[str, float]) -> float:
        adx = adx_data.get('adx', 0)
        return min(adx / 50, 1.0)  # Scale to 0-1
    
    def _calculate_stochastic_confidence(self, stoch_data: Dict[str, float]) -> float:
        k_percent = stoch_data.get('%K', 50)
        # Higher confidence at extremes
        if k_percent > 80 or k_percent < 20:
            return 0.8
        else:
            return 0.4
    
    def _calculate_rsi_confidence(self, rsi: float) -> float:
        # Higher confidence at extremes
        if rsi > 70 or rsi < 30:
            return 0.9
        elif rsi > 60 or rsi < 40:
            return 0.6
        else:
            return 0.3
    
    def _calculate_volatility_confidence(self, bb_data: Dict[str, float]) -> float:
        percent_b = bb_data.get('%b', 0.5)
        # Higher confidence at band extremes
        if percent_b > 1 or percent_b < 0:
            return 0.8
        else:
            return 0.5
    
    def _calculate_pattern_confidence(self, patterns: Dict[str, Any]) -> float:
        detected_patterns = sum(1 for pattern in patterns.values() 
                              if (isinstance(pattern, bool) and pattern) or 
                                 (isinstance(pattern, dict) and pattern.get('detected')))
        return min(detected_patterns * 0.3, 1.0)
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of recent analysis."""
        if not self.analysis_history:
            return {}
        
        recent_analysis = list(self.analysis_history)[-5:]  # Last 5 analyses
        
        return {
            'total_analyses': len(self.analysis_history),
            'recent_analyses': len(recent_analysis),
            'last_analysis_time': recent_analysis[-1]['timestamp'] if recent_analysis else None,
            'average_data_points': sum(a['data_points'] for a in recent_analysis) / len(recent_analysis)
        }