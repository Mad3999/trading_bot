"""
Momentum-based scalping strategy for options trading dashboard.
This module implements high-frequency scalping techniques based on short-term momentum indicators.
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

# Momentum scalping parameters
MOMENTUM_TRIGGER_THRESHOLD = 0.15  # Minimum price movement in % to trigger entry
MIN_MOMENTUM_STRENGTH = 2.0        # Minimum strength of price momentum
QUICK_SCALP_TARGET_MULTIPLIER = 2.0  # Target = stop_loss * this value
QUICK_SCALP_MAX_DURATION = 3      # Maximum holding time in minutes for quick scalps
MOMENTUM_WINDOW = 5               # Number of price points to calculate momentum

# Dictionary to track momentum for each instrument
momentum_tracker = {
    "NIFTY": {'CE': [], 'PE': []},
    "BANKNIFTY": {'CE': [], 'PE': []},
    "SENSEX": {'CE': [], 'PE': []}
}

def calculate_price_momentum(price_series, window=MOMENTUM_WINDOW):
    """Calculate price momentum (rate of change) over specified window."""
    if len(price_series) < window + 1:
        return 0
    
    # Calculate percentage change over the window
    current_price = price_series.iloc[-1]
    past_price = price_series.iloc[-window]
    
    if past_price == 0:
        return 0
        
    momentum = ((current_price - past_price) / past_price) * 100
    return momentum

def update_momentum_tracker(index_name, option_type):
    """Update momentum tracking for the specified instrument."""
    if len(price_history[index_name][option_type]) < MOMENTUM_WINDOW + 1:
        return
    
    price_series = price_history[index_name][option_type]['price']
    
    # Calculate current momentum
    current_momentum = calculate_price_momentum(price_series)
    
    # Add to tracker with timestamp
    momentum_tracker[index_name][option_type].append({
        'timestamp': datetime.now(),
        'momentum': current_momentum
    })
    
    # Keep only the last 20 momentum points to avoid memory bloat
    if len(momentum_tracker[index_name][option_type]) > 20:
        momentum_tracker[index_name][option_type].pop(0)

def get_current_momentum(index_name, option_type):
    """Get the current momentum value for an instrument."""
    if not momentum_tracker[index_name][option_type]:
        return 0
    
    return momentum_tracker[index_name][option_type][-1]['momentum']

def detect_momentum_surge(index_name, option_type):
    """Detect if there's a recent surge in momentum indicating a potential scalping opportunity."""
    if len(momentum_tracker[index_name][option_type]) < 3:
        return False, 0
    
    # Get the last 3 momentum values
    recent_momentum = [entry['momentum'] for entry in momentum_tracker[index_name][option_type][-3:]]
    
    # Check for increasing momentum exceeding threshold
    if all(recent_momentum[i] < recent_momentum[i+1] for i in range(len(recent_momentum)-1)) and \
       recent_momentum[-1] > MOMENTUM_TRIGGER_THRESHOLD:
        return True, recent_momentum[-1]
    
    return False, 0

def should_enter_momentum_scalp(index_name, option_type):
    """Determine if we should enter a momentum-based scalping trade."""
    # Check if we've hit the maximum trades for the day
    if trading_state.trades_today >= trading_state.MAX_TRADES_PER_DAY:
        return False
    
    # Check if we're already in a trade for this index and option type
    if trading_state.active_trades[index_name][option_type]:
        return False
    
    # Detect momentum surge
    momentum_surge, momentum_value = detect_momentum_surge(index_name, option_type)
    
    if not momentum_surge:
        return False
    
    # For a momentum scalp, we want the price to be moving in the expected direction
    # For CE options, we want positive momentum (price rising)
    # For PE options, we want negative momentum (price rising, which is good for PE buyers)
    if option_type == 'CE' and momentum_value < 0:
        return False
    
    if option_type == 'PE' and momentum_value < 0:
        return False
    
    # Check if the momentum is strong enough
    if abs(momentum_value) < MIN_MOMENTUM_STRENGTH:
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

def enter_momentum_scalp(index_name, option_type):
    """Enter a momentum-based scalping trade with appropriate parameters."""
    # Use the regular enter_trade function with the "momentum_scalp" trade type
    success = enter_trade(index_name, option_type, "momentum_scalp")
    
    if success:
        # Set a tighter target and stop loss for momentum scalps
        current_price = trading_state.entry_price[index_name][option_type]
        stop_loss = trading_state.stop_loss[index_name][option_type]
        
        # Calculate stop loss distance
        stop_loss_distance = current_price - stop_loss
        
        # Set a more aggressive target for momentum scalping
        target = current_price + (stop_loss_distance * QUICK_SCALP_TARGET_MULTIPLIER)
        trading_state.target[index_name][option_type] = target
        
        logger.info(f"Momentum scalp entry for {index_name} {option_type}: Price: {current_price}, "
                   f"SL: {stop_loss}, Target: {target}, Momentum: {get_current_momentum(index_name, option_type):.2f}%")
    
    return success

def check_momentum_exit_conditions(index_name, option_type):
    """Check if a momentum scalp should be exited based on momentum reversal."""
    if not trading_state.active_trades[index_name][option_type]:
        return False
    
    # Only check for momentum-based exit for momentum scalps
    if trading_state.trade_type[index_name][option_type] != "momentum_scalp":
        return False
    
    # Get current momentum
    current_momentum = get_current_momentum(index_name, option_type)
    
    # Exit if momentum has reversed significantly
    if option_type == 'CE' and current_momentum < -MIN_MOMENTUM_STRENGTH/2:
        logger.info(f"{index_name} {option_type} momentum scalp exit: Momentum reversed to {current_momentum:.2f}%")
        return True
    
    if option_type == 'PE' and current_momentum < -MIN_MOMENTUM_STRENGTH/2:
        logger.info(f"{index_name} {option_type} momentum scalp exit: Momentum reversed to {current_momentum:.2f}%")
        return True
    
    # Check if we've held for the maximum time
    entry_time = trading_state.entry_time[index_name][option_type]
    current_time = datetime.now()
    time_held = (current_time - entry_time).total_seconds() / 60
    
    if time_held >= QUICK_SCALP_MAX_DURATION:
        logger.info(f"{index_name} {option_type} momentum scalp maximum holding time reached ({QUICK_SCALP_MAX_DURATION} mins)")
        return True
    
    return False

def apply_momentum_scalping_strategy():
    """Apply the momentum-based scalping strategy to all indices."""
    # First, update momentum trackers for all instruments
    for index_name in INSTRUMENTS:
        for option_type in ['CE', 'PE']:
            update_momentum_tracker(index_name, option_type)
    
    # Check for exit conditions for active momentum scalp trades
    for index_name in INSTRUMENTS:
        for option_type in ['CE', 'PE']:
            if trading_state.active_trades[index_name][option_type] and \
               trading_state.trade_type[index_name][option_type] == "momentum_scalp":
                
                if check_momentum_exit_conditions(index_name, option_type):
                    exit_trade(index_name, option_type, reason="Momentum reversal")
                else:
                    # Update trailing stop loss for active trades
                    update_stop_loss(index_name, option_type)
    
    # Check for new trade entries
    for index_name in INSTRUMENTS:
        for option_type in ['CE', 'PE']:
            if not trading_state.active_trades[index_name][option_type] and \
               should_enter_momentum_scalp(index_name, option_type):
                
                enter_momentum_scalp(index_name, option_type)

def get_momentum_stats():
    """Get statistics about momentum scalping performance."""
    momentum_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'momentum_scalp']
    
    if not momentum_trades:
        return {
            'trades': 0,
            'win_rate': 0,
            'avg_return': 0,
            'total_pnl': 0,
            'avg_duration': 0,
            'best_trade': 0,
            'worst_trade': 0
        }
    
    # Calculate statistics
    wins = sum(1 for trade in momentum_trades if trade['pnl'] > 0)
    total_pnl = sum(trade['pnl'] for trade in momentum_trades)
    avg_return = total_pnl / len(momentum_trades)
    best_trade = max(trade['pnl'] for trade in momentum_trades)
    worst_trade = min(trade['pnl'] for trade in momentum_trades)
    
    # Calculate average duration in minutes
    durations = [(trade['exit_time'] - trade['entry_time']).total_seconds() / 60 for trade in momentum_trades]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    return {
        'trades': len(momentum_trades),
        'win_rate': (wins / len(momentum_trades) * 100) if momentum_trades else 0,
        'avg_return': avg_return,
        'total_pnl': total_pnl,
        'avg_duration': avg_duration,
        'best_trade': best_trade,
        'worst_trade': worst_trade
    }