"""
Enhanced trading strategy implementation that respects symbol-specific settings.
This module extends the existing trading strategy with support for per-symbol controls.
"""

import logging
from datetime import datetime

from models.trading_state import trading_state
from models.instruments import INSTRUMENTS
from trading.strategy import check_day_rollover, find_atm_options, refresh_atm_options
from analysis.signals import prediction_signals, generate_prediction_signals
from utils.data_utils import cleanup_historical_data
from trading.execution import enter_trade, exit_trade, should_exit_trade, update_stop_loss, check_time_based_exit

logger = logging.getLogger(__name__)

def apply_enhanced_trading_strategy(index_name, symbol_settings=None):
    """Apply trading strategy with respect to symbol-specific settings."""
    from config import Config
    config = Config()
    
    # If no settings provided, use defaults (enabled)
    if not symbol_settings:
        symbol_settings = {
            'NIFTY': {'trading_enabled': True, 'scalping_enabled': True, 'lot_size': 1},
            'BANKNIFTY': {'trading_enabled': True, 'scalping_enabled': True, 'lot_size': 1},
            'SENSEX': {'trading_enabled': True, 'scalping_enabled': True, 'lot_size': 1}
        }
    
    # Check if trading is enabled for this index
    index_settings = symbol_settings.get(index_name, {})
    trading_enabled = index_settings.get('trading_enabled', True)
    scalping_enabled = index_settings.get('scalping_enabled', True)
    lot_size = index_settings.get('lot_size', 1)
    
    if not trading_enabled:
        logger.info(f"Trading is disabled for {index_name}, skipping strategy")
        return
    
    # Check for trade exits first (exit regardless of settings to manage risk on existing trades)
    for option_type in ['CE', 'PE']:
        if trading_state.active_trades[index_name][option_type] and should_exit_trade(index_name, option_type):
            exit_trade(index_name, option_type, reason="Strategy")
    
    # Check for regular trade entries
    for option_type in ['CE', 'PE']:
        if not trading_state.active_trades[index_name][option_type] and should_enter_trade(index_name, option_type, "regular", lot_size):
            enter_trade(index_name, option_type, "regular", lot_size)
    
    # Check for scalping trade entries if enabled for both global and this index
    if config.scalping_enabled and scalping_enabled:
        for option_type in ['CE', 'PE']:
            if not trading_state.active_trades[index_name][option_type] and should_enter_trade(index_name, option_type, "scalping", lot_size):
                enter_trade(index_name, option_type, "scalping", lot_size)

def should_enter_trade(index_name, option_type, trade_type="regular", lot_size=1):
    """Determine if we should enter a trade for the given index and option type."""
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
    
    # Different entry criteria based on trade type
    if trade_type == "scalping":
        # For scalping, we need stronger signals
        if option_type == 'CE' and signal >= 3 and strength >= 1.5:
            return True
        elif option_type == 'PE' and signal >= 3 and strength >= 1.5:
            return True
    else:
        # Regular trading entry criteria
        if option_type == 'CE' and signal >= 2 and strength >= 1:
            return True
        elif option_type == 'PE' and signal >= 2 and strength >= 1:
            return True
    
    return False

def update_enhanced_analysis(index_name, symbol_settings=None):
    """Update analysis and trading strategy based on symbol settings."""
    # Clean up old data
    cleanup_historical_data(price_history, index_name)
    
    # Check for day rollover
    check_day_rollover()
    
    # Generate prediction signals
    generate_prediction_signals(index_name)
    
    # Apply trading strategy with symbol settings
    apply_enhanced_trading_strategy(index_name, symbol_settings)
    
    # Update stop loss if in active trade
    for option_type in ['CE', 'PE']:
        if trading_state.active_trades[index_name][option_type]:
            update_stop_loss(index_name, option_type)
            check_time_based_exit(index_name, option_type)

# Import at the bottom to avoid circular imports
from services.price_service import price_history