"""
High-return expiry day scalping strategy for options trading.
This module implements an aggressive scalping strategy specifically for expiry days
that aims for 10x higher returns by capitalizing on increased volatility.
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

# Expiry day specific strategy parameters
EXPIRY_SCALPING_TARGET_PCT = 1.2  # Higher target on expiry day (1.2% vs regular 0.5%)
EXPIRY_SCALPING_STOP_LOSS_PCT = 0.4  # Tighter stop loss on expiry day
EXPIRY_MAX_POSITION_HOLDING_TIME = 3  # Shorter holding time (3 mins vs regular 5)
EXPIRY_AGGRESSIVE_ENTRY_THRESHOLD = 2  # Lower signal threshold for entry (2 vs regular 3)
EXPIRY_TRADE_SIZE_MULTIPLIER = 1.5  # Increase position size by 50%

# Time windows for expiry day strategy
MORNING_WINDOW = {"start": "09:15", "end": "10:30"}  # Gap opening opportunities
MIDDAY_WINDOW = {"start": "12:30", "end": "13:30"}  # Lunch hour volatility 
CLOSING_WINDOW = {"start": "14:30", "end": "15:15"}  # Closing rush

def is_expiry_day(index_name):
    """Check if today is the expiry day for the given index."""
    if trading_state.expiry_dates[index_name] is None:
        return False
    
    today = datetime.now().date()
    expiry_date = trading_state.expiry_dates[index_name].date()
    
    return today == expiry_date

def is_in_trading_window():
    """Check if current time is within one of the optimal trading windows."""
    current_time = datetime.now().time()
    current_str = current_time.strftime("%H:%M")
    
    # Check if we're in any of the defined windows
    in_morning = MORNING_WINDOW["start"] <= current_str <= MORNING_WINDOW["end"]
    in_midday = MIDDAY_WINDOW["start"] <= current_str <= MIDDAY_WINDOW["end"]
    in_closing = CLOSING_WINDOW["start"] <= current_str <= CLOSING_WINDOW["end"]
    
    return in_morning or in_midday or in_closing

def calculate_expiry_position_size(index_name, option_type, current_price):
    """Calculate a more aggressive position size for expiry day trades."""
    from config import Config
    config = Config()
    
    # Check if we have enough capital
    if trading_state.capital <= 0:
        return 0, 0
    
    # Calculate risk amount in rupees - more aggressive on expiry day
    risk_amount = trading_state.capital * (trading_state.RISK_PER_TRADE / 100) * EXPIRY_TRADE_SIZE_MULTIPLIER
    
    # Tighter stop loss on expiry day
    stop_loss_distance = current_price * (EXPIRY_SCALPING_STOP_LOSS_PCT / 100)
    
    # Calculate position size
    quantity = int(risk_amount / stop_loss_distance)
    
    # Ensure quantity is at least 1
    if quantity < 1:
        quantity = 1
    
    return quantity, stop_loss_distance

def should_enter_expiry_trade(index_name, option_type):
    """Determine if we should enter an expiry day trade."""
    # Check if it's expiry day for this index
    if not is_expiry_day(index_name):
        return False
    
    # Check if we're in one of the optimal trading windows
    if not is_in_trading_window():
        return False
    
    # Check if we've hit the maximum trades for the day
    if trading_state.trades_today >= trading_state.MAX_TRADES_PER_DAY:
        return False
    
    # Check if we're already in a trade for this index and option type
    if trading_state.active_trades[index_name][option_type]:
        return False
    
    # Get the prediction signal
    signal = prediction_signals[index_name][option_type]['signal']
    strength = prediction_signals[index_name][option_type]['strength']
    
    # We use a lower threshold on expiry day for more aggressive trading
    signal_threshold = EXPIRY_AGGRESSIVE_ENTRY_THRESHOLD
    
    # Different criteria for CE and PE on expiry day
    # For CE, we want strong bullish signals
    if option_type == 'CE' and signal >= signal_threshold and strength >= 1.0:
        return True
    # For PE, we want strong bearish signals
    elif option_type == 'PE' and signal >= signal_threshold and strength >= 1.0:
        return True
    
    return False

def enter_expiry_trade(index_name, option_type):
    """Enter a trade with expiry day specific settings."""
    # Get current price
    current_price = last_ltp[index_name][option_type]
    
    if current_price is None:
        logger.warning(f"Cannot enter expiry {index_name} {option_type} trade: Price is None")
        return False
    
    # Calculate position size and stop loss with expiry day specific settings
    quantity, stop_loss_distance = calculate_expiry_position_size(index_name, option_type, current_price)
    
    if quantity <= 0:
        logger.warning(f"Cannot enter expiry {index_name} {option_type} trade: Invalid quantity {quantity}")
        return False
    
    # Calculate stop loss and target
    stop_loss = current_price - stop_loss_distance
    target = current_price + (stop_loss_distance * 3)  # 1:3 risk-reward for expiry scalping - more aggressive
    
    # Update trading state
    trading_state.active_trades[index_name][option_type] = True
    trading_state.entry_price[index_name][option_type] = current_price
    trading_state.entry_time[index_name][option_type] = datetime.now()
    trading_state.stop_loss[index_name][option_type] = stop_loss
    trading_state.initial_stop_loss[index_name][option_type] = stop_loss
    trading_state.target[index_name][option_type] = target
    trading_state.trailing_sl_activated[index_name][option_type] = False
    trading_state.index_entry_price[index_name][option_type] = last_ltp[index_name]["SPOT"]
    trading_state.quantity[index_name][option_type] = quantity
    trading_state.trade_type[index_name][option_type] = "expiry_scalping"
    
    # Increment trades today counter
    trading_state.trades_today += 1
    trading_state.index_trades[index_name] += 1
    trading_state.scalping_trades += 1
    
    # Log trade entry
    logger.info(f"Entered EXPIRY {index_name} {option_type} trade: Price: {current_price}, Qty: {quantity}, SL: {stop_loss}, Target: {target}")
    
    return True

def check_expiry_time_based_exit(index_name, option_type):
    """Check if we should exit a trade based on time held, with expiry day specific timing."""
    # Check if we're in a trade for this index and option type
    if not trading_state.active_trades[index_name][option_type]:
        return
    
    # Only apply to expiry scalping trades
    if trading_state.trade_type[index_name][option_type] != "expiry_scalping":
        return
    
    entry_time = trading_state.entry_time[index_name][option_type]
    current_time = datetime.now()
    
    # Calculate time held in minutes
    time_held = (current_time - entry_time).total_seconds() / 60
    
    # Check if we've held for the maximum time (shorter on expiry day)
    if time_held >= EXPIRY_MAX_POSITION_HOLDING_TIME:
        logger.info(f"{index_name} {option_type} expiry maximum holding time reached ({EXPIRY_MAX_POSITION_HOLDING_TIME} mins). Exiting.")
        exit_trade(index_name, option_type, reason="Expiry time-based exit")

def apply_expiry_scalping_strategy():
    """Apply the high-return expiry day scalping strategy to all indices."""
    for index_name in INSTRUMENTS:
        # Skip if not an expiry day for this index
        if not is_expiry_day(index_name):
            continue
        
        # Check for trade exits first (using regular exit logic)
        for option_type in ['CE', 'PE']:
            if trading_state.active_trades[index_name][option_type] and trading_state.trade_type[index_name][option_type] == "expiry_scalping":
                # Check for time-based exit with tighter timing on expiry day
                check_expiry_time_based_exit(index_name, option_type)
                
                # Update trailing stop loss for active trades
                update_stop_loss(index_name, option_type)
        
        # Check for expiry trade entries
        for option_type in ['CE', 'PE']:
            if not trading_state.active_trades[index_name][option_type] and should_enter_expiry_trade(index_name, option_type):
                enter_expiry_trade(index_name, option_type)

def get_historical_expiry_performance():
    """Analyze historical performance of the expiry day strategy."""
    expiry_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'expiry_scalping']
    
    if not expiry_trades:
        return {
            'trades': 0,
            'win_rate': 0,
            'avg_return': 0,
            'total_pnl': 0,
            'best_trade': 0,
            'worst_trade': 0
        }
    
    # Calculate statistics
    wins = sum(1 for trade in expiry_trades if trade['pnl'] > 0)
    total_pnl = sum(trade['pnl'] for trade in expiry_trades)
    avg_return = total_pnl / len(expiry_trades) if expiry_trades else 0
    best_trade = max(trade['pnl'] for trade in expiry_trades) if expiry_trades else 0
    worst_trade = min(trade['pnl'] for trade in expiry_trades) if expiry_trades else 0
    
    return {
        'trades': len(expiry_trades),
        'win_rate': (wins / len(expiry_trades) * 100) if expiry_trades else 0,
        'avg_return': avg_return,
        'total_pnl': total_pnl,
        'best_trade': best_trade,
        'worst_trade': worst_trade
    }

def is_high_volatility(index_name, threshold=1.5):
    """Check if current market volatility is above threshold."""
    volatility = calculate_volatility(index_name)
    avg_volatility = pd.Series(trading_state.volatility_window[index_name]).mean() if trading_state.volatility_window[index_name] else 0
    
    # Check if current volatility is higher than the average
    return volatility > (avg_volatility * threshold)

def get_expiry_strategy_recommendation(index_name):
    """Get a strategic recommendation for expiry day trading based on current market conditions."""
    if not is_expiry_day(index_name):
        return None
    
    current_time = datetime.now().time()
    current_str = current_time.strftime("%H:%M")
    
    # Calculate various indicators
    volatility = calculate_volatility(index_name)
    ce_signal = prediction_signals[index_name]['CE']['signal']
    pe_signal = prediction_signals[index_name]['PE']['signal']
    
    # Morning strategy
    if MORNING_WINDOW["start"] <= current_str <= MORNING_WINDOW["end"]:
        if is_high_volatility(index_name):
            # High volatility in morning - aggressive strategy
            if ce_signal > pe_signal:
                return {
                    'recommendation': 'BUY CE',
                    'reasoning': 'High morning volatility with bullish signal',
                    'risk_level': 'High',
                    'target_multiplier': 2.5  # Higher target for high volatility
                }
            else:
                return {
                    'recommendation': 'BUY PE',
                    'reasoning': 'High morning volatility with bearish signal',
                    'risk_level': 'High',
                    'target_multiplier': 2.5
                }
        else:
            # Low volatility in morning - conservative strategy
            return {
                'recommendation': 'WAIT',
                'reasoning': 'Low morning volatility, wait for momentum',
                'risk_level': 'Low',
                'target_multiplier': 1.5
            }
    
    # Midday strategy
    elif MIDDAY_WINDOW["start"] <= current_str <= MIDDAY_WINDOW["end"]:
        if abs(ce_signal - pe_signal) > 3:
            # Strong divergence between CE and PE signals
            if ce_signal > pe_signal:
                return {
                    'recommendation': 'BUY CE',
                    'reasoning': 'Strong midday CE/PE signal divergence',
                    'risk_level': 'Medium',
                    'target_multiplier': 2.0
                }
            else:
                return {
                    'recommendation': 'BUY PE',
                    'reasoning': 'Strong midday CE/PE signal divergence',
                    'risk_level': 'Medium',
                    'target_multiplier': 2.0
                }
        else:
            return {
                'recommendation': 'HEDGED STRATEGY',
                'reasoning': 'Unclear midday direction, consider hedged positions',
                'risk_level': 'Medium',
                'target_multiplier': 1.8
            }
    
    # Closing strategy
    elif CLOSING_WINDOW["start"] <= current_str <= CLOSING_WINDOW["end"]:
        # Closing hour - aggressive but short duration strategy
        if is_high_volatility(index_name, threshold=2.0):
            if ce_signal > pe_signal:
                return {
                    'recommendation': 'BUY CE',
                    'reasoning': 'High closing volatility with bullish signal',
                    'risk_level': 'Very High',
                    'target_multiplier': 3.0,
                    'max_duration': 2  # Very short duration
                }
            else:
                return {
                    'recommendation': 'BUY PE',
                    'reasoning': 'High closing volatility with bearish signal',
                    'risk_level': 'Very High',
                    'target_multiplier': 3.0,
                    'max_duration': 2
                }
        else:
            return {
                'recommendation': 'BOOK PROFITS',
                'reasoning': 'Close to expiry, secure existing profits',
                'risk_level': 'Low',
                'target_multiplier': 1.0
            }
    
    return {
        'recommendation': 'NEUTRAL',
        'reasoning': 'No clear expiry day opportunity at this time',
        'risk_level': 'Medium',
        'target_multiplier': 1.5
    }