"""
Pattern recognition scalping strategy for options trading dashboard.
This module identifies common chart patterns for short-term scalping opportunities.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from models.trading_state import trading_state
from models.instruments import INSTRUMENTS
from services.price_service import last_ltp, price_history
from analysis.signals import prediction_signals
from analysis.volatility import calculate_volatility
from trading.execution import enter_trade, exit_trade, update_stop_loss

logger = logging.getLogger(__name__)

# Pattern scalping parameters
PATTERN_LOOKBACK = 20       # Number of candles to analyze for patterns
MIN_PATTERN_QUALITY = 0.75  # Minimum quality score for pattern detection (0-1)
PATTERN_TARGET_MULTIPLIER = 1.8  # Target = stop_loss * this value
PATTERN_MAX_DURATION = 4    # Maximum holding time in minutes for pattern trades

# Dictionary to track pattern scores
pattern_scores = {
    "NIFTY": {'CE': {'score': 0, 'pattern': None}, 'PE': {'score': 0, 'pattern': None}},
    "BANKNIFTY": {'CE': {'score': 0, 'pattern': None}, 'PE': {'score': 0, 'pattern': None}},
    "SENSEX": {'CE': {'score': 0, 'pattern': None}, 'PE': {'score': 0, 'pattern': None}}
}

def detect_double_bottom(price_series):
    """
    Detect a double bottom pattern.
    Returns (success, quality score, pattern data)
    """
    if len(price_series) < PATTERN_LOOKBACK:
        return False, 0, None
    
    # Get the lookback window
    window = price_series.tail(PATTERN_LOOKBACK)
    
    # Find local minima
    minima_indices = []
    for i in range(1, len(window) - 1):
        if window.iloc[i] < window.iloc[i-1] and window.iloc[i] < window.iloc[i+1]:
            minima_indices.append(i)
    
    # Need at least 2 minima to form a double bottom
    if len(minima_indices) < 2:
        return False, 0, None
    
    # Check the last two minima
    min1_idx, min2_idx = minima_indices[-2], minima_indices[-1]
    min1, min2 = window.iloc[min1_idx], window.iloc[min2_idx]
    
    # Double bottom criteria:
    # 1. Two minima should be at similar levels
    # 2. There should be a peak between them
    # 3. The second minimum should be followed by an uptrend
    
    # Check if minima are at similar levels (within 0.5%)
    if abs(min1 - min2) / min1 > 0.005:
        return False, 0, None
    
    # Check if there's a peak between the minima
    between_slice = window.iloc[min1_idx:min2_idx+1]
    max_between = between_slice.max()
    
    if max_between <= min1 or max_between <= min2:
        return False, 0, None
    
    # Calculate the recovery percentage after the second minimum
    if len(window) > min2_idx + 1:
        recovery = (window.iloc[-1] - min2) / min2
        # Recovery should be positive for a valid double bottom
        if recovery <= 0:
            return False, 0, None
    else:
        return False, 0, None
    
    # Calculate quality score (0-1)
    peak_height = (max_between - min1) / min1
    quality = min(0.5 + peak_height + recovery, 1.0)
    
    return True, quality, {
        'pattern': 'double_bottom',
        'min1_idx': min1_idx,
        'min2_idx': min2_idx,
        'min1': min1,
        'min2': min2,
        'peak': max_between,
        'recovery': recovery
    }

def detect_double_top(price_series):
    """
    Detect a double top pattern.
    Returns (success, quality score, pattern data)
    """
    if len(price_series) < PATTERN_LOOKBACK:
        return False, 0, None
    
    # Get the lookback window
    window = price_series.tail(PATTERN_LOOKBACK)
    
    # Find local maxima
    maxima_indices = []
    for i in range(1, len(window) - 1):
        if window.iloc[i] > window.iloc[i-1] and window.iloc[i] > window.iloc[i+1]:
            maxima_indices.append(i)
    
    # Need at least 2 maxima to form a double top
    if len(maxima_indices) < 2:
        return False, 0, None
    
    # Check the last two maxima
    max1_idx, max2_idx = maxima_indices[-2], maxima_indices[-1]
    max1, max2 = window.iloc[max1_idx], window.iloc[max2_idx]
    
    # Double top criteria:
    # 1. Two maxima should be at similar levels
    # 2. There should be a trough between them
    # 3. The second maximum should be followed by a downtrend
    
    # Check if maxima are at similar levels (within 0.5%)
    if abs(max1 - max2) / max1 > 0.005:
        return False, 0, None
    
    # Check if there's a trough between the maxima
    between_slice = window.iloc[max1_idx:max2_idx+1]
    min_between = between_slice.min()
    
    if min_between >= max1 or min_between >= max2:
        return False, 0, None
    
    # Calculate the decline percentage after the second maximum
    if len(window) > max2_idx + 1:
        decline = (max2 - window.iloc[-1]) / max2
        # Decline should be positive for a valid double top
        if decline <= 0:
            return False, 0, None
    else:
        return False, 0, None
    
    # Calculate quality score (0-1)
    trough_depth = (max1 - min_between) / max1
    quality = min(0.5 + trough_depth + decline, 1.0)
    
    return True, quality, {
        'pattern': 'double_top',
        'max1_idx': max1_idx,
        'max2_idx': max2_idx,
        'max1': max1,
        'max2': max2,
        'trough': min_between,
        'decline': decline
    }

def detect_bullish_engulfing(price_series, volume_series=None):
    """
    Detect a bullish engulfing pattern.
    Returns (success, quality score, pattern data)
    """
    if len(price_series) < 2:
        return False, 0, None
    
    # Get the last two prices
    prev_price = price_series.iloc[-2]
    curr_price = price_series.iloc[-1]
    
    # Check if current price completely engulfs previous price (bullish)
    if curr_price <= prev_price:
        return False, 0, None
    
    # Calculate size of the engulfing
    engulf_size = (curr_price - prev_price) / prev_price
    
    # Calculate quality based on size of engulfing
    quality = min(0.5 + engulf_size * 50, 1.0)  # Scaled to make reasonable values
    
    # If volume data is available, factor it into quality
    if volume_series is not None and len(volume_series) >= 2:
        curr_volume = volume_series.iloc[-1]
        prev_volume = volume_series.iloc[-2]
        
        # Higher volume on engulfing candle is better
        if curr_volume > prev_volume:
            volume_ratio = curr_volume / prev_volume
            quality = min(quality * (1 + (volume_ratio - 1) * 0.2), 1.0)
    
    return True, quality, {
        'pattern': 'bullish_engulfing',
        'prev_price': prev_price,
        'curr_price': curr_price,
        'engulf_size': engulf_size
    }

def detect_bearish_engulfing(price_series, volume_series=None):
    """
    Detect a bearish engulfing pattern.
    Returns (success, quality score, pattern data)
    """
    if len(price_series) < 2:
        return False, 0, None
    
    # Get the last two prices
    prev_price = price_series.iloc[-2]
    curr_price = price_series.iloc[-1]
    
    # Check if current price completely engulfs previous price (bearish)
    if curr_price >= prev_price:
        return False, 0, None
    
    # Calculate size of the engulfing
    engulf_size = (prev_price - curr_price) / prev_price
    
    # Calculate quality based on size of engulfing
    quality = min(0.5 + engulf_size * 50, 1.0)  # Scaled to make reasonable values
    
    # If volume data is available, factor it into quality
    if volume_series is not None and len(volume_series) >= 2:
        curr_volume = volume_series.iloc[-1]
        prev_volume = volume_series.iloc[-2]
        
        # Higher volume on engulfing candle is better
        if curr_volume > prev_volume:
            volume_ratio = curr_volume / prev_volume
            quality = min(quality * (1 + (volume_ratio - 1) * 0.2), 1.0)
    
    return True, quality, {
        'pattern': 'bearish_engulfing',
        'prev_price': prev_price,
        'curr_price': curr_price,
        'engulf_size': engulf_size
    }

def update_pattern_scores(index_name, option_type):
    """
    Update pattern detection scores for the specified instrument.
    """
    if len(price_history[index_name][option_type]) < PATTERN_LOOKBACK:
        return
    
    price_series = price_history[index_name][option_type]['price']
    volume_series = price_history[index_name][option_type]['volume'] if 'volume' in price_history[index_name][option_type].columns else None
    
    # Check for each pattern and store the one with highest quality
    patterns = []
    
    # For CE options, bullish patterns are good
    if option_type == 'CE':
        success, quality, data = detect_double_bottom(price_series)
        if success and quality >= MIN_PATTERN_QUALITY:
            patterns.append((quality, data))
        
        success, quality, data = detect_bullish_engulfing(price_series, volume_series)
        if success and quality >= MIN_PATTERN_QUALITY:
            patterns.append((quality, data))
    
    # For PE options, bearish patterns are good
    if option_type == 'PE':
        success, quality, data = detect_double_top(price_series)
        if success and quality >= MIN_PATTERN_QUALITY:
            patterns.append((quality, data))
        
        success, quality, data = detect_bearish_engulfing(price_series, volume_series)
        if success and quality >= MIN_PATTERN_QUALITY:
            patterns.append((quality, data))
    
    # Update with the highest quality pattern if any were found
    if patterns:
        best_pattern = max(patterns, key=lambda x: x[0])
        pattern_scores[index_name][option_type] = {
            'score': best_pattern[0],
            'pattern': best_pattern[1]
        }
    else:
        pattern_scores[index_name][option_type] = {
            'score': 0,
            'pattern': None
        }

def should_enter_pattern_scalp(index_name, option_type):
    """Determine if we should enter a pattern-based scalping trade."""
    # Check if we've hit the maximum trades for the day
    if trading_state.trades_today >= trading_state.MAX_TRADES_PER_DAY:
        return False
    
    # Check if we're already in a trade for this index and option type
    if trading_state.active_trades[index_name][option_type]:
        return False
    
    # Get current pattern score
    pattern_data = pattern_scores[index_name][option_type]
    
    # Only enter if we have a high-quality pattern
    if pattern_data['score'] < MIN_PATTERN_QUALITY or pattern_data['pattern'] is None:
        return False
    
    # Check market volatility - we want some volatility but not extreme
    volatility = calculate_volatility(index_name)
    if volatility < 0.05 or volatility > 0.5:  # Avoid extremely low or high volatility
        return False
    
    # Check trading hours - focus on the most active market hours
    current_time = datetime.now().time()
    current_hour = current_time.hour
    
    # Avoid trading in the first 15 minutes (market opening) and last 15 minutes (market closing)
    if (current_hour == 9 and current_time.minute < 30) or \
       (current_hour == 15 and current_time.minute > 15):
        return False
    
    return True

def enter_pattern_scalp(index_name, option_type):
    """Enter a pattern-based scalping trade."""
    pattern_data = pattern_scores[index_name][option_type]
    
    # Use the regular enter_trade function with the "pattern_scalp" trade type
    success = enter_trade(index_name, option_type, "pattern_scalp")
    
    if success:
        # Set a tighter target and stop loss for pattern scalps
        current_price = trading_state.entry_price[index_name][option_type]
        stop_loss = trading_state.stop_loss[index_name][option_type]
        
        # Calculate stop loss distance
        stop_loss_distance = current_price - stop_loss
        
        # Set target based on pattern quality
        target_multiplier = PATTERN_TARGET_MULTIPLIER * pattern_data['score']
        target = current_price + (stop_loss_distance * target_multiplier)
        trading_state.target[index_name][option_type] = target
        
        logger.info(f"Pattern scalp entry for {index_name} {option_type}: Price: {current_price}, "
                   f"SL: {stop_loss}, Target: {target}, Pattern: {pattern_data['pattern']['pattern']}, "
                   f"Quality: {pattern_data['score']:.2f}")
    
    return success

def check_pattern_exit_conditions(index_name, option_type):
    """Check if a pattern scalp should be exited based on pattern invalidation."""
    if not trading_state.active_trades[index_name][option_type]:
        return False
    
    # Only check for pattern-based exit for pattern scalps
    if trading_state.trade_type[index_name][option_type] != "pattern_scalp":
        return False
    
    # For CE options, check if a bearish pattern has formed
    if option_type == 'CE':
        price_series = price_history[index_name][option_type]['price']
        volume_series = price_history[index_name][option_type]['volume'] if 'volume' in price_history[index_name][option_type].columns else None
        
        success, quality, _ = detect_bearish_engulfing(price_series, volume_series)
        if success and quality >= MIN_PATTERN_QUALITY:
            logger.info(f"{index_name} {option_type} pattern scalp exit: Bearish pattern formed")
            return True
    
    # For PE options, check if a bullish pattern has formed
    if option_type == 'PE':
        price_series = price_history[index_name][option_type]['price']
        volume_series = price_history[index_name][option_type]['volume'] if 'volume' in price_history[index_name][option_type].columns else None
        
        success, quality, _ = detect_bullish_engulfing(price_series, volume_series)
        if success and quality >= MIN_PATTERN_QUALITY:
            logger.info(f"{index_name} {option_type} pattern scalp exit: Bullish pattern formed")
            return True
    
    # Check if we've held for the maximum time
    entry_time = trading_state.entry_time[index_name][option_type]
    current_time = datetime.now()
    time_held = (current_time - entry_time).total_seconds() / 60
    
    if time_held >= PATTERN_MAX_DURATION:
        logger.info(f"{index_name} {option_type} pattern scalp maximum holding time reached ({PATTERN_MAX_DURATION} mins)")
        return True
    
    return False

def apply_pattern_scalping_strategy():
    """Apply the pattern-based scalping strategy to all indices."""
    # First, update pattern scores for all instruments
    for index_name in INSTRUMENTS:
        for option_type in ['CE', 'PE']:
            update_pattern_scores(index_name, option_type)
    
    # Check for exit conditions for active pattern scalp trades
    for index_name in INSTRUMENTS:
        for option_type in ['CE', 'PE']:
            if trading_state.active_trades[index_name][option_type] and \
               trading_state.trade_type[index_name][option_type] == "pattern_scalp":
                
                if check_pattern_exit_conditions(index_name, option_type):
                    exit_trade(index_name, option_type, reason="Pattern invalidation")
                else:
                    # Update trailing stop loss for active trades
                    update_stop_loss(index_name, option_type)
    
    # Check for new trade entries
    for index_name in INSTRUMENTS:
        for option_type in ['CE', 'PE']:
            if not trading_state.active_trades[index_name][option_type] and \
               should_enter_pattern_scalp(index_name, option_type):
                
                enter_pattern_scalp(index_name, option_type)

def get_pattern_stats():
    """Get statistics about pattern scalping performance."""
    pattern_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'pattern_scalp']
    
    if not pattern_trades:
        return {
            'trades': 0,
            'win_rate': 0,
            'avg_return': 0,
            'total_pnl': 0,
            'avg_duration': 0,
            'pattern_breakdown': {}
        }
    
    # Calculate statistics
    wins = sum(1 for trade in pattern_trades if trade['pnl'] > 0)
    total_pnl = sum(trade['pnl'] for trade in pattern_trades)
    avg_return = total_pnl / len(pattern_trades)
    
    # Calculate average duration in minutes
    durations = [(trade['exit_time'] - trade['entry_time']).total_seconds() / 60 for trade in pattern_trades]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Get breakdown by pattern type if available
    pattern_breakdown = {}
    
    return {
        'trades': len(pattern_trades),
        'win_rate': (wins / len(pattern_trades) * 100) if pattern_trades else 0,
        'avg_return': avg_return,
        'total_pnl': total_pnl,
        'avg_duration': avg_duration,
        'pattern_breakdown': pattern_breakdown
    }