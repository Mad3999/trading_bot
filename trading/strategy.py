"""
Trading strategy implementation for the options trading dashboard.
"""

import logging
from datetime import datetime, timedelta
import threading
import pandas as pd
import numpy as np

from models.trading_state import trading_state
from models.instruments import INSTRUMENTS
from services.price_service import last_ltp, price_history
from utils.data_utils import cleanup_historical_data
from analysis.signals import generate_prediction_signals
from analysis.volatility import calculate_volatility

# Import scalping strategies
from trading.momentum_scalping import apply_momentum_scalping_strategy, get_momentum_stats
from trading.pattern_scalping import apply_pattern_scalping_strategy, get_pattern_stats
from trading.expiry_scalping import apply_expiry_scalping_strategy, get_historical_expiry_performance, is_expiry_day

logger = logging.getLogger(__name__)

def apply_trading_strategy(index_name):
    """Apply the trading strategy by checking for entry and exit conditions for the specified index."""
    from config import Config
    config = Config()
    
    # Check for trade exits first
    for option_type in ['CE', 'PE']:
        if trading_state.active_trades[index_name][option_type] and should_exit_trade(index_name, option_type):
            exit_trade(index_name, option_type, reason="Strategy")
    
    # Check for regular trade entries
    for option_type in ['CE', 'PE']:
        if not trading_state.active_trades[index_name][option_type] and should_enter_trade(index_name, option_type, "regular"):
            enter_trade(index_name, option_type, "regular")
    
    # Check for scalping trade entries if enabled
    if config.scalping_enabled:
        # Check if it's an expiry day - prioritize expiry day strategy if it is
        if is_expiry_day(index_name):
            # Expiry day scalping is handled separately
            pass  # This will be applied through its own function call
        else:
            # Apply regular scalping strategies
            for option_type in ['CE', 'PE']:
                if not trading_state.active_trades[index_name][option_type] and should_enter_trade(index_name, option_type, "scalping"):
                    enter_trade(index_name, option_type, "scalping")

def apply_all_scalping_strategies():
    """Apply all scalping strategies."""
    from config import Config
    config = Config()
    
    if not config.scalping_enabled:
        return
    
    # Apply momentum-based scalping
    apply_momentum_scalping_strategy()
    
    # Apply pattern-based scalping
    apply_pattern_scalping_strategy()
    
    # Apply expiry day scalping
    apply_expiry_scalping_strategy()

def should_enter_trade(index_name, option_type, trade_type="regular"):
    """Determine if we should enter a trade for the given index and option type."""
    from analysis.signals import prediction_signals
    
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
    
    # For expiry day trades, use different criteria
    if is_expiry_day(index_name) and trade_type == "scalping":
        # Expiry day scalping is handled separately
        return False
    
    # Different entry criteria based on trade type
    if trade_type == "scalping":
        # For scalping, we need stronger signals
        if option_type == 'CE' and signal >= 3 and strength >= 1.5:
            # Additionally check volatility for scalping trades
            volatility = calculate_volatility(index_name)
            if volatility < 0.05:  # Avoid extremely low volatility for scalping
                return False
                
            # Check time of day - avoid scalping in the first 15 minutes of market open
            current_time = datetime.now().time()
            if current_time.hour == 9 and current_time.minute < 15:
                return False
                
            return True
        elif option_type == 'PE' and signal >= 3 and strength >= 1.5:
            # Same checks for PE
            volatility = calculate_volatility(index_name)
            if volatility < 0.05:
                return False
                
            current_time = datetime.now().time()
            if current_time.hour == 9 and current_time.minute < 15:
                return False
                
            return True
    else:
        # Regular trading entry criteria
        if option_type == 'CE' and signal >= 2 and strength >= 1:
            return True
        elif option_type == 'PE' and signal >= 2 and strength >= 1:
            return True
    
    return False

def update_analysis(index_name):
    """Update analysis and trading strategy based on new price data for the specified index."""
    # Clean up old data
    cleanup_historical_data(price_history, index_name)
    
    # Check for day rollover
    check_day_rollover()
    
    # Generate prediction signals
    generate_prediction_signals(index_name)
    
    # Apply trading strategy
    apply_trading_strategy(index_name)
    
    # Update stop loss if in active trade
    for option_type in ['CE', 'PE']:
        if trading_state.active_trades[index_name][option_type]:
            update_stop_loss(index_name, option_type)
            check_time_based_exit(index_name, option_type)

def check_day_rollover():
    """Check if trading day has changed and reset daily stats."""
    current_date = datetime.now().date()
    if current_date != trading_state.trading_day:
        logger.info(f"New trading day detected. Resetting daily stats.")
        
        # Record daily scalping performance
        scalping_trades = [trade for trade in trading_state.trades_history 
                          if trade['trade_type'] in ['scalping', 'momentum_scalp', 'pattern_scalp', 'expiry_scalping'] and 
                          trade['exit_time'].date() == trading_state.trading_day]
        
        if scalping_trades:
            daily_pnl = sum(trade['pnl'] for trade in scalping_trades)
            daily_trades = len(scalping_trades)
            daily_wins = sum(1 for trade in scalping_trades if trade['pnl'] > 0)
            day_str = trading_state.trading_day.strftime("%Y-%m-%d")
            
            trading_state.scalping_performance_by_day[day_str] = {
                'date': trading_state.trading_day,
                'pnl': daily_pnl,
                'trades': daily_trades,
                'wins': daily_wins,
                'win_rate': daily_wins / daily_trades * 100 if daily_trades > 0 else 0
            }
        
        # Reset daily stats
        trading_state.trading_day = current_date
        trading_state.trades_today = 0
        trading_state.daily_pnl = 0

def find_atm_options(index_name):
    """Find At-The-Money (ATM) options for the given index."""
    try:
        # Get current spot price
        spot_price = last_ltp[index_name]["SPOT"]
        
        if spot_price is None:
            logger.warning(f"Cannot find ATM options for {index_name}: Spot price is None")
            return None
        
        # Round to the nearest strike price interval
        strike_interval = 100
        if index_name == "SENSEX":
            strike_interval = 500
        elif index_name == "NIFTY":
            strike_interval = 50
        elif index_name == "BANKNIFTY":
            strike_interval = 100
        
        atm_strike = round(spot_price / strike_interval) * strike_interval
        
        # Get the nearest weekly expiry (Thursday)
        today = datetime.now()
        days_to_thursday = (3 - today.weekday()) % 7
        if days_to_thursday == 0 and today.hour >= 15:  # If it's Thursday after market closes
            days_to_thursday = 7
        
        expiry_date = today + timedelta(days=days_to_thursday)
        
        # Update expiry dates
        trading_state.expiry_dates[index_name] = expiry_date
        
        # Format the date strings
        day_str = expiry_date.strftime('%d')
        month_str = expiry_date.strftime('%b').upper()
        year_str = expiry_date.strftime('%y')
        
        # Construct symbols
        ce_symbol = f"{index_name}{day_str}{month_str}{year_str}C{atm_strike}"
        pe_symbol = f"{index_name}{day_str}{month_str}{year_str}P{atm_strike}"
        
        # For demo purposes, we're generating the tokens since we can't fetch them
        # In a real system, you would query the exchange for token numbers
        ce_token = f"{index_name[0]}{atm_strike}C{day_str}{month_str[0]}"  # Example token generation
        pe_token = f"{index_name[0]}{atm_strike}P{day_str}{month_str[0]}"  # Example token generation
        
        logger.info(f"Found ATM options for {index_name} at strike {atm_strike}: CE={ce_symbol}, PE={pe_symbol}")
        
        return {
            "CE": {"symbol": ce_symbol, "token": ce_token, "exchange": "NFO", "strike": atm_strike},
            "PE": {"symbol": pe_symbol, "token": pe_token, "exchange": "NFO", "strike": atm_strike}
        }
    except Exception as e:
        logger.error(f"Error finding ATM options for {index_name}: {e}")
        return None

def refresh_atm_options():
    """Refresh ATM options for all indices."""
    success = True
    updated_options = {}
    
    for index_name in INSTRUMENTS:
        try:
            # Find ATM options
            atm_options = find_atm_options(index_name)
            
            if atm_options:
                # Store updates for later application
                updated_options[index_name] = atm_options
                logger.info(f"Found new {index_name} options: CE={atm_options['CE']['symbol']}, PE={atm_options['PE']['symbol']}")
            else:
                success = False
                logger.warning(f"Failed to find ATM options for {index_name}")
        except Exception as e:
            success = False
            logger.error(f"Error refreshing ATM options for {index_name}: {e}")
    
    # Apply updates only after all options have been successfully found
    if success:
        for index_name, options in updated_options.items():
            INSTRUMENTS[index_name]["CE"] = options["CE"]
            INSTRUMENTS[index_name]["PE"] = options["PE"]
            logger.info(f"Updated {index_name} options: CE={options['CE']['symbol']}, PE={options['PE']['symbol']}")
        
        # Resubscribe to updated symbols if WebSocket is connected
        from services.websocket_service import websocket_connected, subscribe_to_market_data
        if websocket_connected:
            subscribe_to_market_data()
    
    return success

def calculate_pcr(index_name):
    """Calculate Put-Call Ratio based on CE and PE volumes for the specified index."""
    if len(price_history[index_name]["CE"]) > 0 and len(price_history[index_name]["PE"]) > 0:
        # Calculate total volume for CE and PE
        ce_volume = price_history[index_name]["CE"]['volume'].sum() if 'volume' in price_history[index_name]["CE"].columns else 1
        pe_volume = price_history[index_name]["PE"]['volume'].sum() if 'volume' in price_history[index_name]["PE"].columns else 1
        
        # Avoid division by zero
        if ce_volume == 0:
            ce_volume = 1
        
        pcr = pe_volume / ce_volume
        return pcr
    else:
        return 1.0  # Default neutral PCR

def calculate_index_range(index_name):
    """Calculate the predicted range for the index based on historical volatility and ATR."""
    if len(price_history[index_name]["SPOT"]) < 30:
        return None, None  # Not enough data
    
    # Calculate daily returns
    returns = price_history[index_name]["SPOT"]['price'].pct_change().dropna()
    
    # Calculate historical volatility (standard deviation of returns)
    volatility = returns.std() * np.sqrt(252)  # Annualized volatility
    
    # Calculate ATR for intraday range
    from analysis.indicators import calculate_atr
    atr = calculate_atr(price_history[index_name]["SPOT"]['price'])
    
    # Predicted range = Current Price ± (Volatility * Current Price)
    current_price = price_history[index_name]["SPOT"]['price'].iloc[-1]
    predicted_range_high = current_price * (1 + volatility)
    predicted_range_low = current_price * (1 - volatility)
    
    return predicted_range_low, predicted_range_high

def get_scalping_performance_metrics():
    """Get combined performance metrics for all scalping strategies."""
    # Get individual strategy stats
    momentum_stats = get_momentum_stats()
    pattern_stats = get_pattern_stats()
    expiry_stats = get_historical_expiry_performance()
    
    # Combine stats
    total_scalping_trades = momentum_stats['trades'] + pattern_stats['trades'] + expiry_stats['trades']
    
    if total_scalping_trades == 0:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'avg_return': 0,
            'total_pnl': 0,
            'strategy_breakdown': {
                'momentum': {'trades': 0, 'win_rate': 0, 'pnl': 0},
                'pattern': {'trades': 0, 'win_rate': 0, 'pnl': 0},
                'expiry': {'trades': 0, 'win_rate': 0, 'pnl': 0}
            },
            'best_strategy': 'None'
        }
    
    # Calculate combined stats
    total_pnl = momentum_stats['total_pnl'] + pattern_stats['total_pnl'] + expiry_stats['total_pnl']
    
    # Calculate weighted win rate
    weighted_win_rate = 0
    if total_scalping_trades > 0:
        weighted_win_rate = (
            (momentum_stats['win_rate'] * momentum_stats['trades']) +
            (pattern_stats['win_rate'] * pattern_stats['trades']) +
            (expiry_stats['win_rate'] * expiry_stats['trades'])
        ) / total_scalping_trades
    
    # Determine best strategy
    strategy_pnls = {
        'momentum': momentum_stats['total_pnl'],
        'pattern': pattern_stats['total_pnl'],
        'expiry': expiry_stats['total_pnl']
    }
    
    best_strategy = max(strategy_pnls, key=strategy_pnls.get) if any(strategy_pnls.values()) else 'None'
    
    return {
        'total_trades': total_scalping_trades,
        'win_rate': weighted_win_rate,
        'avg_return': total_pnl / total_scalping_trades if total_scalping_trades > 0 else 0,
        'total_pnl': total_pnl,
        'strategy_breakdown': {
            'momentum': {
                'trades': momentum_stats['trades'],
                'win_rate': momentum_stats['win_rate'],
                'pnl': momentum_stats['total_pnl']
            },
            'pattern': {
                'trades': pattern_stats['trades'],
                'win_rate': pattern_stats['win_rate'],
                'pnl': pattern_stats['total_pnl']
            },
            'expiry': {
                'trades': expiry_stats['trades'],
                'win_rate': expiry_stats['win_rate'],
                'pnl': expiry_stats['total_pnl']
            }
        },
        'best_strategy': best_strategy
    }

# Import these at the bottom to avoid circular imports
from trading.execution import enter_trade, exit_trade, should_exit_trade, update_stop_loss, check_time_based_exit