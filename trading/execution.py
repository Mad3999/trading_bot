"""
Trade execution logic for the options trading dashboard.
Handles entering, exiting, and managing trades.
"""

import logging
from datetime import datetime
import threading

from models.trading_state import trading_state, SCALPING_MAX_HOLDING_TIME, MAX_POSITION_HOLDING_TIME
from models.instruments import INSTRUMENTS
from services.price_service import last_ltp
from analysis.signals import prediction_signals
from analysis.volatility import calculate_volatility
from analysis.indicators import calculate_atr

logger = logging.getLogger(__name__)

# Thread lock for synchronizing access to shared data
lock = threading.Lock()

def enter_trade(index_name, option_type, trade_type="regular"):
    """Enter a trade for the given index and option type."""
    with lock:
        # Get current price
        current_price = last_ltp[index_name][option_type]
        
        if current_price is None:
            logger.warning(f"Cannot enter {index_name} {option_type} trade: Price is None")
            return False
        
        # Calculate position size and stop loss
        is_scalping = trade_type in ["scalping", "momentum_scalp", "pattern_scalp", "expiry_scalping"]
        quantity, stop_loss_distance = calculate_position_size(index_name, option_type, current_price, is_scalping, trade_type)
        
        if quantity <= 0:
            logger.warning(f"Cannot enter {index_name} {option_type} trade: Invalid quantity {quantity}")
            return False
        
        # Calculate stop loss and target
        stop_loss = current_price - stop_loss_distance
        
        # Different risk-reward based on trade type
        if trade_type == "momentum_scalp":
            target = current_price + (stop_loss_distance * 2.0)  # Higher RR for momentum due to strong signals
        elif trade_type == "pattern_scalp":
            target = current_price + (stop_loss_distance * 1.8)  # Slightly lower RR for pattern recognition
        elif trade_type == "expiry_scalping":
            target = current_price + (stop_loss_distance * 2.5)  # Highest RR for expiry day due to volatility
        elif trade_type == "scalping":
            target = current_price + (stop_loss_distance * 1.5)  # 1:1.5 risk-reward for standard scalping
        else:
            target = current_price + (stop_loss_distance * 2)  # 1:2 risk-reward for regular trading
        
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
        trading_state.trade_type[index_name][option_type] = trade_type
        
        # Increment trades today counter
        trading_state.trades_today += 1
        trading_state.index_trades[index_name] += 1
        
        # Update trade type specific counters
        if trade_type == "scalping":
            trading_state.scalping_trades += 1
        elif trade_type == "momentum_scalp":
            trading_state.momentum_scalp_trades += 1
        elif trade_type == "pattern_scalp":
            trading_state.pattern_scalp_trades += 1
        elif trade_type == "expiry_scalping":
            trading_state.expiry_scalping_trades += 1
        else:
            trading_state.regular_trades += 1
        
        # Log trade entry
        logger.info(f"Entered {index_name} {option_type} {trade_type} trade: Price: {current_price}, Qty: {quantity}, SL: {stop_loss}, Target: {target}")
        
        return True

def exit_trade(index_name, option_type, reason="Manual"):
    """Exit a trade for the given index and option type."""
    with lock:
        # Check if we're in a trade for this index and option type
        if not trading_state.active_trades[index_name][option_type]:
            return False
        
        # Get current price
        current_price = last_ltp[index_name][option_type]
        
        if current_price is None:
            logger.warning(f"Cannot exit {index_name} {option_type} trade: Price is None")
            return False
        
        # Calculate P&L
        entry_price = trading_state.entry_price[index_name][option_type]
        quantity = trading_state.quantity[index_name][option_type]
        trade_type = trading_state.trade_type[index_name][option_type]
        pnl = (current_price - entry_price) * quantity
        pnl_pct = (current_price - entry_price) / entry_price * 100
        
        # Update trading state
        trading_state.active_trades[index_name][option_type] = False
        trading_state.pnl[index_name][option_type] = pnl
        trading_state.total_pnl += pnl
        trading_state.daily_pnl += pnl
        trading_state.index_pnl[index_name] += pnl
        
        # Update trade type specific stats
        if trade_type == "scalping":
            trading_state.scalping_pnl += pnl
            if pnl > 0:
                trading_state.scalping_wins += 1
            else:
                trading_state.scalping_losses += 1
        elif trade_type == "momentum_scalp":
            trading_state.momentum_scalp_pnl += pnl
            if pnl > 0:
                trading_state.momentum_scalp_wins += 1
            else:
                trading_state.momentum_scalp_losses += 1
        elif trade_type == "pattern_scalp":
            trading_state.pattern_scalp_pnl += pnl
            if pnl > 0:
                trading_state.pattern_scalp_wins += 1
            else:
                trading_state.pattern_scalp_losses += 1
        elif trade_type == "expiry_scalping":
            trading_state.expiry_scalping_pnl += pnl
            if pnl > 0:
                trading_state.expiry_scalping_wins += 1
            else:
                trading_state.expiry_scalping_losses += 1
        else:
            trading_state.regular_pnl += pnl
            if pnl > 0:
                trading_state.regular_wins += 1
            else:
                trading_state.regular_losses += 1
                
        # Update daily scalping performance for all scalping types
        if trade_type in ["scalping", "momentum_scalp", "pattern_scalp", "expiry_scalping"]:
            day_str = datetime.now().date().strftime("%Y-%m-%d")
            if day_str not in trading_state.scalping_performance_by_day:
                trading_state.scalping_performance_by_day[day_str] = {
                    'date': datetime.now().date(),
                    'pnl': 0,
                    'trades': 0,
                    'wins': 0,
                    'win_rate': 0
                }
            
            trading_state.scalping_performance_by_day[day_str]['pnl'] += pnl
            trading_state.scalping_performance_by_day[day_str]['trades'] += 1
            if pnl > 0:
                trading_state.scalping_performance_by_day[day_str]['wins'] += 1
            trading_state.scalping_performance_by_day[day_str]['win_rate'] = (
                trading_state.scalping_performance_by_day[day_str]['wins'] / 
                trading_state.scalping_performance_by_day[day_str]['trades'] * 100
            )
        
        # Update win/loss counter
        if pnl > 0:
            trading_state.wins += 1
        else:
            trading_state.losses += 1
        
        # Add to trade history
        trade_record = {
            'index': index_name,
            'option_type': option_type,
            'trade_type': trade_type,
            'entry_time': trading_state.entry_time[index_name][option_type],
            'exit_time': datetime.now(),
            'entry_price': entry_price,
            'exit_price': current_price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'expiry': trading_state.expiry_dates[index_name]
        }
        trading_state.trades_history.append(trade_record)
        
        # Reset entry and stop loss values
        trading_state.entry_price[index_name][option_type] = None
        trading_state.entry_time[index_name][option_type] = None
        trading_state.stop_loss[index_name][option_type] = None
        trading_state.initial_stop_loss[index_name][option_type] = None
        trading_state.target[index_name][option_type] = None
        trading_state.trailing_sl_activated[index_name][option_type] = False
        trading_state.index_entry_price[index_name][option_type] = None
        trading_state.quantity[index_name][option_type] = 0
        trading_state.trade_type[index_name][option_type] = None
        
        # Log trade exit
        logger.info(f"Exited {index_name} {option_type} {trade_type} trade: Price: {current_price}, P&L: {pnl}, P&L%: {pnl_pct:.2f}%, Reason: {reason}")
        
        return True

def should_exit_trade(index_name, option_type):
    """Determine if we should exit a trade for the given index and option type."""
    # Check if we're in a trade for this index and option type
    if not trading_state.active_trades[index_name][option_type]:
        return False
    
    # Get current price
    current_price = last_ltp[index_name][option_type]
    
    if current_price is None:
        return False
    
    entry_price = trading_state.entry_price[index_name][option_type]
    stop_loss = trading_state.stop_loss[index_name][option_type]
    target = trading_state.target[index_name][option_type]
    trade_type = trading_state.trade_type[index_name][option_type]
    
    # Check for stop loss hit
    if current_price <= stop_loss:
        logger.info(f"{index_name} {option_type} stop loss hit: {stop_loss}")
        return True
    
    # Check for target hit
    if current_price >= target:
        logger.info(f"{index_name} {option_type} target hit: {target}")
        return True
    
    # For scalping trades, we have additional exit criteria
    if trade_type in ["scalping", "momentum_scalp", "pattern_scalp", "expiry_scalping"]:
        # Calculate current profit percentage
        current_profit_pct = (current_price - entry_price) / entry_price * 100
        
        # Exit if we have a small profit but the signal is weakening
        if current_profit_pct > 0.2 and prediction_signals[index_name][option_type]['signal'] < 1:
            logger.info(f"{index_name} {option_type} {trade_type} exit: Small profit with weakening signal")
            return True
    else:
        # Check for reversal in prediction signals for regular trades
        signal = prediction_signals[index_name][option_type]['signal']
        if option_type == 'CE' and signal <= -2:
            logger.info(f"{index_name} {option_type} exit based on signal reversal")
            return True
        elif option_type == 'PE' and signal <= -2:
            logger.info(f"{index_name} {option_type} exit based on signal reversal")
            return True
    
    return False

def update_stop_loss(index_name, option_type):
    """Update trailing stop loss if conditions are met."""
    # Check if we're in a trade for this index and option type
    if not trading_state.active_trades[index_name][option_type]:
        return
    
    # Get current price
    current_price = last_ltp[index_name][option_type]
    
    if current_price is None:
        return
    
    entry_price = trading_state.entry_price[index_name][option_type]
    current_stop_loss = trading_state.stop_loss[index_name][option_type]
    trade_type = trading_state.trade_type[index_name][option_type]
    
    # Calculate current profit percentage
    current_profit_pct = (current_price - entry_price) / entry_price * 100
    
    # Check if trailing stop loss should be activated
    # Different activation thresholds based on trade type
    if trade_type == "momentum_scalp":
        activation_threshold = trading_state.TRAILING_SL_ACTIVATION * 0.4  # Activate earlier for momentum scalps
    elif trade_type == "pattern_scalp":
        activation_threshold = trading_state.TRAILING_SL_ACTIVATION * 0.5  # Activate earlier for pattern scalps
    elif trade_type == "expiry_scalping":
        activation_threshold = trading_state.TRAILING_SL_ACTIVATION * 0.6  # Activate earlier for expiry scalps
    elif trade_type == "scalping":
        activation_threshold = trading_state.TRAILING_SL_ACTIVATION * 0.5  # Activate earlier for standard scalps
    else:
        activation_threshold = trading_state.TRAILING_SL_ACTIVATION  # Regular activation for swing trades
    
    if not trading_state.trailing_sl_activated[index_name][option_type] and current_profit_pct >= activation_threshold:
        trading_state.trailing_sl_activated[index_name][option_type] = True
        logger.info(f"{index_name} {option_type} trailing stop loss activated at {current_profit_pct:.2f}% profit")
    
    # Update trailing stop loss if activated
    if trading_state.trailing_sl_activated[index_name][option_type]:
        # Calculate new stop loss (moves up with price)
        # Different trailing percentages based on trade type
        if trade_type == "momentum_scalp":
            trail_percentage = trading_state.TRAILING_SL_PERCENTAGE * 0.4  # Tighter trailing for momentum
        elif trade_type == "pattern_scalp":
            trail_percentage = trading_state.TRAILING_SL_PERCENTAGE * 0.5  # Tighter trailing for pattern
        elif trade_type == "expiry_scalping":
            trail_percentage = trading_state.TRAILING_SL_PERCENTAGE * 0.6  # Tighter trailing for expiry
        elif trade_type == "scalping":
            trail_percentage = trading_state.TRAILING_SL_PERCENTAGE * 0.5  # Tighter trailing for standard scalps
        else:
            trail_percentage = trading_state.TRAILING_SL_PERCENTAGE  # Regular trailing for swing trades
        
        new_stop_loss = current_price * (1 - trail_percentage / 100)
        
        # Only update if new stop loss is higher than current stop loss
        if new_stop_loss > current_stop_loss:
            trading_state.stop_loss[index_name][option_type] = new_stop_loss
            logger.info(f"{index_name} {option_type} trailing stop loss updated to {new_stop_loss}")

def check_time_based_exit(index_name, option_type):
    """Check if we should exit a trade based on time held."""
    # Check if we're in a trade for this index and option type
    if not trading_state.active_trades[index_name][option_type]:
        return
    
    entry_time = trading_state.entry_time[index_name][option_type]
    current_time = datetime.now()
    trade_type = trading_state.trade_type[index_name][option_type]
    
    # Calculate time held in minutes
    time_held = (current_time - entry_time).total_seconds() / 60
    
    # Check if we've held for the maximum time based on trade type
    if trade_type == "momentum_scalp":
        max_time = 3  # Shorter time for momentum scalps
    elif trade_type == "pattern_scalp":
        max_time = 4  # Short time for pattern scalps
    elif trade_type == "expiry_scalping":
        max_time = 3  # Shorter time for expiry day scalps
    elif trade_type == "scalping":
        max_time = SCALPING_MAX_HOLDING_TIME
    else:
        max_time = MAX_POSITION_HOLDING_TIME
    
    if time_held >= max_time:
        logger.info(f"{index_name} {option_type} maximum holding time reached ({max_time} mins). Exiting.")
        exit_trade(index_name, option_type, reason="Time-based exit")

def calculate_position_size(index_name, option_type, current_price, is_scalping=False, trade_type="regular"):
    """Calculate position size and stop loss distance based on risk parameters."""
    from config import Config
    config = Config()
    
    # Check if we have enough capital
    if trading_state.capital <= 0:
        return 0, 0
    
    # Calculate risk amount in rupees - adjust risk based on trade type
    risk_multiplier = 1.0  # Default risk multiplier
    
    if trade_type == "momentum_scalp":
        risk_multiplier = 1.2  # Slightly higher risk for momentum scalps due to stronger signals
    elif trade_type == "pattern_scalp":
        risk_multiplier = 1.1  # Slightly higher risk for pattern scalps
    elif trade_type == "expiry_scalping":
        risk_multiplier = 1.5  # Higher risk for expiry scalping due to higher volatility
    elif trade_type == "scalping":
        risk_multiplier = 1.0  # Standard risk for regular scalping
    
    risk_amount = trading_state.capital * (trading_state.RISK_PER_TRADE / 100) * risk_multiplier
    
    # For scalping trades, use ATR for dynamic stop loss distance
    if is_scalping:
        from services.price_service import price_history
        
        if len(price_history[index_name][option_type]) > ATR_PERIOD:
            # Calculate ATR-based stop loss
            atr = calculate_atr(price_history[index_name][option_type]['price'])
            
            # Different ATR multipliers based on trade type
            if trade_type == "momentum_scalp":
                atr_multiplier = 0.5  # Tighter stop for momentum trades
            elif trade_type == "pattern_scalp":
                atr_multiplier = 0.6  # Slightly wider stop for pattern trades
            elif trade_type == "expiry_scalping":
                atr_multiplier = 0.4  # Tightest stop for expiry day trades
            else:
                atr_multiplier = 0.7  # Standard for regular scalping
                
            stop_loss_distance = atr * atr_multiplier
            
            # Ensure minimum stop loss distance
            min_stop_loss_distance = current_price * (config.scalping_stop_loss_pct / 100)
            stop_loss_distance = max(stop_loss_distance, min_stop_loss_distance)
        else:
            # Not enough data for ATR, use percentage-based stop loss
            if trade_type == "expiry_scalping":
                stop_loss_distance = current_price * 0.4 / 100  # 0.4% for expiry
            elif trade_type == "momentum_scalp":
                stop_loss_distance = current_price * 0.5 / 100  # 0.5% for momentum
            elif trade_type == "pattern_scalp":
                stop_loss_distance = current_price * 0.6 / 100  # 0.6% for pattern
            else:
                stop_loss_distance = current_price * (config.scalping_stop_loss_pct / 100)
    else:
        # Regular trading - stop loss is 1% of current price
        stop_loss_distance = current_price * 0.01
    
    # Calculate position size
    quantity = int(risk_amount / stop_loss_distance)
    
    # Ensure quantity is at least 1
    if quantity < 1:
        quantity = 1
    
    # For high-frequency scalping strategies, keep position size reasonable
    if trade_type in ["momentum_scalp", "pattern_scalp", "expiry_scalping"]:
        max_quantity = int(trading_state.capital * 0.05 / current_price)  # Max 5% of capital in high-frequency trades
        quantity = min(quantity, max_quantity)
    
    return quantity, stop_loss_distance