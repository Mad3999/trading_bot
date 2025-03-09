"""
Adaptive scalping strategy that dynamically adjusts parameters based on market conditions.
This module implements an advanced self-adjusting scalping strategy that optimizes its parameters
based on real-time market conditions and historical performance.
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

# Base parameters that will be adjusted dynamically
BASE_PARAMS = {
    'target_multiplier': 2.0,     # Base target = stop_loss * this value
    'max_holding_time': 4,        # Base maximum holding time in minutes
    'min_signal_strength': 2.0,   # Base minimum signal strength
    'trailing_sl_activation': 0.5, # Base profit % to activate trailing stop loss
    'entry_threshold': 3          # Base signal threshold for entry
}

# Performance tracking window - store the last 20 trades for adaptive adjustments
MAX_PERFORMANCE_WINDOW = 20
performance_window = []

# Dictionary to track current adaptive parameters for each index/option type
adaptive_params = {
    "NIFTY": {
        'CE': BASE_PARAMS.copy(),
        'PE': BASE_PARAMS.copy()
    },
    "BANKNIFTY": {
        'CE': BASE_PARAMS.copy(),
        'PE': BASE_PARAMS.copy()
    },
    "SENSEX": {
        'CE': BASE_PARAMS.copy(),
        'PE': BASE_PARAMS.copy()
    }
}

# Market state classification
MARKET_STATES = {
    'low_volatility': {'volatility_threshold': 0.05, 'weight': 0.7},
    'medium_volatility': {'volatility_threshold': 0.15, 'weight': 1.0},
    'high_volatility': {'volatility_threshold': float('inf'), 'weight': 1.3}
}

def update_performance_window(trade_record):
    """Add a trade to the performance window and remove oldest if needed."""
    global performance_window
    
    # Add new trade to window
    performance_window.append(trade_record)
    
    # Keep only the last MAX_PERFORMANCE_WINDOW trades
    if len(performance_window) > MAX_PERFORMANCE_WINDOW:
        performance_window.pop(0)

def calculate_win_rate():
    """Calculate win rate from the performance window."""
    if not performance_window:
        return 0.5  # Default to 50% if no data
    
    wins = sum(1 for trade in performance_window if trade['pnl'] > 0)
    return wins / len(performance_window)

def classify_market_state(index_name):
    """Classify the current market state based on volatility and trend."""
    # Calculate volatility
    volatility = calculate_volatility(index_name)
    
    # Determine market state based on volatility
    if volatility < MARKET_STATES['low_volatility']['volatility_threshold']:
        volatility_state = 'low_volatility'
    elif volatility < MARKET_STATES['medium_volatility']['volatility_threshold']:
        volatility_state = 'medium_volatility'
    else:
        volatility_state = 'high_volatility'
    
    # Get recent movement trend
    if len(price_history[index_name]["SPOT"]) < 10:
        return volatility_state, 'neutral', volatility
    
    recent_prices = price_history[index_name]["SPOT"]['price'].tail(10)
    price_change = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0] * 100
    
    # Classify trend
    if price_change > 0.3:
        trend = 'bullish'
    elif price_change < -0.3:
        trend = 'bearish'
    else:
        trend = 'neutral'
    
    return volatility_state, trend, volatility

def adjust_params_for_market_state(base_params, market_state, win_rate):
    """
    Adjust parameters based on current market state and recent performance.
    
    Args:
        base_params: Base parameters to adjust
        market_state: Current market state classification
        win_rate: Recent win rate
        
    Returns:
        Adjusted parameters
    """
    adjusted_params = base_params.copy()
    
    # Get volatility weight
    volatility_weight = MARKET_STATES[market_state]['weight']
    
    # Adjust based on win rate
    win_rate_factor = (win_rate - 0.5) * 2  # Range from -1 to 1
    
    # Adjust target multiplier - more aggressive if winning, more conservative if losing
    adjusted_params['target_multiplier'] = max(1.5, 
                                             base_params['target_multiplier'] * (1 + win_rate_factor * 0.2))
    
    # Adjust max holding time - shorter in high volatility, longer in low volatility
    if market_state == 'high_volatility':
        adjusted_params['max_holding_time'] = int(max(2, base_params['max_holding_time'] * 0.7))
    elif market_state == 'low_volatility':
        adjusted_params['max_holding_time'] = int(min(8, base_params['max_holding_time'] * 1.3))
    
    # Adjust signal strength requirement - higher in high volatility
    adjusted_params['min_signal_strength'] = base_params['min_signal_strength'] * volatility_weight
    
    # Adjust trailing stop loss activation - earlier in high volatility
    adjusted_params['trailing_sl_activation'] = base_params['trailing_sl_activation'] / volatility_weight
    
    # Adjust entry threshold - higher if losing, lower if winning
    win_rate_adjustment = 1 - win_rate_factor * 0.3
    adjusted_params['entry_threshold'] = max(2, base_params['entry_threshold'] * win_rate_adjustment)
    
    return adjusted_params

def update_adaptive_params():
    """Update adaptive parameters for all indices based on market conditions."""
    win_rate = calculate_win_rate()
    
    for index_name in INSTRUMENTS:
        volatility_state, trend, _ = classify_market_state(index_name)
        
        for option_type in ['CE', 'PE']:
            # Get base parameters
            base_params = adaptive_params[index_name][option_type]
            
            # Adjust parameters based on market state
            adjusted_params = adjust_params_for_market_state(base_params, volatility_state, win_rate)
            
            # Further adjust based on trend
            if (option_type == 'CE' and trend == 'bullish') or (option_type == 'PE' and trend == 'bearish'):
                # More aggressive for favorable trend
                adjusted_params['target_multiplier'] *= 1.1
                adjusted_params['entry_threshold'] *= 0.9
            elif (option_type == 'CE' and trend == 'bearish') or (option_type == 'PE' and trend == 'bullish'):
                # More conservative for unfavorable trend
                adjusted_params['target_multiplier'] *= 0.9
                adjusted_params['entry_threshold'] *= 1.1
            
            # Update adaptive parameters
            adaptive_params[index_name][option_type] = adjusted_params

def should_enter_adaptive_scalp(index_name, option_type):
    """Determine if we should enter an adaptive scalping trade."""
    # Check if we've hit the maximum trades for the day
    if trading_state.trades_today >= trading_state.MAX_TRADES_PER_DAY:
        return False
    
    # Check if we've hit the maximum loss percentage for the day
    if trading_state.daily_pnl <= -trading_state.MAX_LOSS_PERCENTAGE * trading_state.capital / 100:
        logger.warning(f"Maximum daily loss reached. No more trades today.")
        return False
    
    # Check if we're already in a trade for this index and option type
    if trading_state.active_trades[index_name][option_type]:
        return False
    
    # Get the prediction signal
    signal = prediction_signals[index_name][option_type]['signal']
    strength = prediction_signals[index_name][option_type]['strength']
    
    # Get current adaptive parameters
    params = adaptive_params[index_name][option_type]
    
    # Check if signal meets adaptive threshold
    if signal < params['entry_threshold'] or strength < params['min_signal_strength']:
        return False
    
    # Check time of day - avoid scalping in the first 15 minutes of market open
    current_time = datetime.now().time()
    if current_time.hour == 9 and current_time.minute < 15:
        return False
    
    # Avoid scalping in the last 15 minutes of market close
    if current_time.hour == 15 and current_time.minute > 15:
        return False
    
    # Verify market volatility is sufficient
    volatility = calculate_volatility(index_name)
    if volatility < 0.03:  # Extremely low volatility
        return False
    
    return True

def enter_adaptive_scalp(index_name, option_type):
    """Enter an adaptive scalping trade with parameters adjusted to market conditions."""
    # Use the regular enter_trade function with the "adaptive_scalp" trade type
    success = enter_trade(index_name, option_type, "adaptive_scalp")
    
    if success:
        # Get current adaptive parameters
        params = adaptive_params[index_name][option_type]
        
        # Set the target and stop loss based on adaptive parameters
        current_price = trading_state.entry_price[index_name][option_type]
        stop_loss = trading_state.stop_loss[index_name][option_type]
        
        # Calculate stop loss distance
        stop_loss_distance = current_price - stop_loss
        
        # Set target based on adaptive target multiplier
        target = current_price + (stop_loss_distance * params['target_multiplier'])
        trading_state.target[index_name][option_type] = target
        
        # Set custom trailing stop loss activation threshold
        # This requires adding a custom field to the trading state
        if not hasattr(trading_state, 'custom_trailing_sl_activation'):
            trading_state.custom_trailing_sl_activation = {
                "NIFTY": {'CE': None, 'PE': None},
                "BANKNIFTY": {'CE': None, 'PE': None},
                "SENSEX": {'CE': None, 'PE': None}
            }
        
        trading_state.custom_trailing_sl_activation[index_name][option_type] = params['trailing_sl_activation']
        
        volatility_state, trend, volatility = classify_market_state(index_name)
        
        logger.info(f"Adaptive scalp entry for {index_name} {option_type}: Price: {current_price}, "
                   f"SL: {stop_loss}, Target: {target}, "
                   f"Market: {volatility_state}/{trend}, Volatility: {volatility:.4f}, "
                   f"Params: {params}")
    
    return success

def check_adaptive_exit_conditions(index_name, option_type):
    """Check if an adaptive scalp should be exited based on adaptive parameters."""
    if not trading_state.active_trades[index_name][option_type]:
        return False
    
    # Only check for adaptive scalps
    if trading_state.trade_type[index_name][option_type] != "adaptive_scalp":
        return False
    
    # Get current adaptive parameters
    params = adaptive_params[index_name][option_type]
    
    # Check if we've held for the adaptive maximum time
    entry_time = trading_state.entry_time[index_name][option_type]
    current_time = datetime.now()
    time_held = (current_time - entry_time).total_seconds() / 60
    
    if time_held >= params['max_holding_time']:
        logger.info(f"{index_name} {option_type} adaptive scalp maximum holding time reached ({params['max_holding_time']} mins)")
        return True
    
    # Check for signal deterioration
    signal = prediction_signals[index_name][option_type]['signal']
    if signal < 0:  # Signal has reversed
        logger.info(f"{index_name} {option_type} adaptive scalp exit: Signal reversed to {signal}")
        return True
    
    # Get current price
    current_price = last_ltp[index_name][option_type]
    entry_price = trading_state.entry_price[index_name][option_type]
    
    # If we're in profit but signal is weakening, exit
    if current_price > entry_price and signal < params['entry_threshold'] / 2:
        logger.info(f"{index_name} {option_type} adaptive scalp exit: In profit but signal weakening to {signal}")
        return True
    
    return False

def apply_adaptive_scalping_strategy():
    """Apply the adaptive scalping strategy to all indices."""
    # First, update adaptive parameters based on market conditions
    update_adaptive_params()
    
    # Check for exit conditions for active adaptive scalp trades
    for index_name in INSTRUMENTS:
        for option_type in ['CE', 'PE']:
            if trading_state.active_trades[index_name][option_type] and \
               trading_state.trade_type[index_name][option_type] == "adaptive_scalp":
                
                if check_adaptive_exit_conditions(index_name, option_type):
                    exit_trade(index_name, option_type, reason="Adaptive strategy")
                else:
                    # Update trailing stop loss for active trades with custom activation
                    update_adaptive_stop_loss(index_name, option_type)
    
    # Check for new trade entries
    for index_name in INSTRUMENTS:
        for option_type in ['CE', 'PE']:
            if not trading_state.active_trades[index_name][option_type] and \
               should_enter_adaptive_scalp(index_name, option_type):
                
                enter_adaptive_scalp(index_name, option_type)

def update_adaptive_stop_loss(index_name, option_type):
    """Update trailing stop loss with adaptive activation threshold."""
    # Check if we're in a trade for this index and option type
    if not trading_state.active_trades[index_name][option_type]:
        return
    
    # Check if this is an adaptive scalp
    if trading_state.trade_type[index_name][option_type] != "adaptive_scalp":
        return
    
    # Get current price and parameters
    current_price = last_ltp[index_name][option_type]
    entry_price = trading_state.entry_price[index_name][option_type]
    current_stop_loss = trading_state.stop_loss[index_name][option_type]
    
    # Get custom trailing stop loss activation if set
    if hasattr(trading_state, 'custom_trailing_sl_activation') and \
       trading_state.custom_trailing_sl_activation[index_name][option_type] is not None:
        activation_threshold = trading_state.custom_trailing_sl_activation[index_name][option_type]
    else:
        activation_threshold = trading_state.TRAILING_SL_ACTIVATION
    
    # Calculate current profit percentage
    current_profit_pct = (current_price - entry_price) / entry_price * 100
    
    # Check if trailing stop loss should be activated
    if not trading_state.trailing_sl_activated[index_name][option_type] and current_profit_pct >= activation_threshold:
        trading_state.trailing_sl_activated[index_name][option_type] = True
        logger.info(f"{index_name} {option_type} adaptive trailing stop loss activated at {current_profit_pct:.2f}% profit")
    
    # Update trailing stop loss if activated
    if trading_state.trailing_sl_activated[index_name][option_type]:
        # Calculate the adaptive trailing percentage based on volatility
        volatility_state, _, volatility = classify_market_state(index_name)
        
        if volatility_state == 'high_volatility':
            # Tighter trailing stop in high volatility
            trail_percentage = trading_state.TRAILING_SL_PERCENTAGE * 0.7
        elif volatility_state == 'low_volatility':
            # Wider trailing stop in low volatility
            trail_percentage = trading_state.TRAILING_SL_PERCENTAGE * 1.3
        else:
            trail_percentage = trading_state.TRAILING_SL_PERCENTAGE
        
        # Calculate new stop loss (moves up with price)
        new_stop_loss = current_price * (1 - trail_percentage / 100)
        
        # Only update if new stop loss is higher than current stop loss
        if new_stop_loss > current_stop_loss:
            trading_state.stop_loss[index_name][option_type] = new_stop_loss
            logger.info(f"{index_name} {option_type} adaptive trailing stop loss updated to {new_stop_loss:.2f} ({trail_percentage:.2f}%)")

def get_adaptive_scalping_stats():
    """Get statistics about adaptive scalping performance."""
    adaptive_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'adaptive_scalp']
    
    if not adaptive_trades:
        return {
            'trades': 0,
            'win_rate': 0,
            'avg_return': 0,
            'total_pnl': 0,
            'avg_duration': 0,
            'best_market_state': 'Unknown',
            'current_params': adaptive_params
        }
    
    # Calculate statistics
    wins = sum(1 for trade in adaptive_trades if trade['pnl'] > 0)
    total_pnl = sum(trade['pnl'] for trade in adaptive_trades)
    avg_return = total_pnl / len(adaptive_trades)
    
    # Calculate average duration in minutes
    durations = [(trade['exit_time'] - trade['entry_time']).total_seconds() / 60 for trade in adaptive_trades]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Determine best performing market state
    # This would require storing market state with each trade
    best_market_state = 'Unknown'
    
    return {
        'trades': len(adaptive_trades),
        'win_rate': (wins / len(adaptive_trades) * 100) if adaptive_trades else 0,
        'avg_return': avg_return,
        'total_pnl': total_pnl,
        'avg_duration': avg_duration,
        'best_market_state': best_market_state,
        'current_params': adaptive_params
    }