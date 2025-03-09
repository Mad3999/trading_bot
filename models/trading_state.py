"""
Trading state class and global variables for the options trading dashboard.
"""

from datetime import datetime
import pandas as pd

# ============ Trading Parameters ============
RISK_PER_TRADE = 1  # Risk per trade in percentage of capital
MAX_TRADES_PER_DAY = 40  # Maximum number of trades per day
MAX_LOSS_PERCENTAGE = 5.0  # Maximum loss percentage per day
TRAILING_SL_ACTIVATION = 1.0  # Percentage of profit at which to activate trailing stop loss
TRAILING_SL_PERCENTAGE = 0.4  # Trailing stop loss percentage
MAX_POSITION_HOLDING_TIME = 10  # Maximum position holding time in minutes
SCALPING_MAX_HOLDING_TIME = 5  # Maximum position holding time for scalping trades (minutes)

# ============ Technical Indicators Parameters ============
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2
ATR_PERIOD = 14
EMA_SHORT = 5
EMA_MEDIUM = 10
EMA_LONG = 20

# Moving average windows
SHORT_WINDOW = 5
MEDIUM_WINDOW = 10
LONG_WINDOW = 20

# Volatility tracking
VOLATILITY_PERIOD = 30

class TradingState:
    """Class to track the current state of all trading activities."""
    
    def __init__(self):
        # Trading parameters from global constants
        self.RISK_PER_TRADE = RISK_PER_TRADE
        self.MAX_TRADES_PER_DAY = MAX_TRADES_PER_DAY
        self.MAX_LOSS_PERCENTAGE = MAX_LOSS_PERCENTAGE
        self.TRAILING_SL_ACTIVATION = TRAILING_SL_ACTIVATION
        self.TRAILING_SL_PERCENTAGE = TRAILING_SL_PERCENTAGE
        self.VOLATILITY_PERIOD = VOLATILITY_PERIOD
        
        self.active_trades = {
            "NIFTY": {'CE': False, 'PE': False},
            "BANKNIFTY": {'CE': False, 'PE': False},
            "SENSEX": {'CE': False, 'PE': False}
        }
        self.entry_price = {
            "NIFTY": {'CE': None, 'PE': None},
            "BANKNIFTY": {'CE': None, 'PE': None},
            "SENSEX": {'CE': None, 'PE': None}
        }
        self.entry_time = {
            "NIFTY": {'CE': None, 'PE': None},
            "BANKNIFTY": {'CE': None, 'PE': None},
            "SENSEX": {'CE': None, 'PE': None}
        }
        self.stop_loss = {
            "NIFTY": {'CE': None, 'PE': None},
            "BANKNIFTY": {'CE': None, 'PE': None},
            "SENSEX": {'CE': None, 'PE': None}
        }
        self.initial_stop_loss = {
            "NIFTY": {'CE': None, 'PE': None},
            "BANKNIFTY": {'CE': None, 'PE': None},
            "SENSEX": {'CE': None, 'PE': None}
        }
        self.target = {
            "NIFTY": {'CE': None, 'PE': None},
            "BANKNIFTY": {'CE': None, 'PE': None},
            "SENSEX": {'CE': None, 'PE': None}
        }
        self.trailing_sl_activated = {
            "NIFTY": {'CE': False, 'PE': False},
            "BANKNIFTY": {'CE': False, 'PE': False},
            "SENSEX": {'CE': False, 'PE': False}
        }
        self.pnl = {
            "NIFTY": {'CE': 0, 'PE': 0},
            "BANKNIFTY": {'CE': 0, 'PE': 0},
            "SENSEX": {'CE': 0, 'PE': 0}
        }
        self.quantity = {
            "NIFTY": {'CE': 0, 'PE': 0},
            "BANKNIFTY": {'CE': 0, 'PE': 0},
            "SENSEX": {'CE': 0, 'PE': 0}
        }
        self.trade_type = {
            "NIFTY": {'CE': None, 'PE': None},
            "BANKNIFTY": {'CE': None, 'PE': None},
            "SENSEX": {'CE': None, 'PE': None}
        }
        self.index_entry_price = {
            "NIFTY": {'CE': None, 'PE': None},
            "BANKNIFTY": {'CE': None, 'PE': None},
            "SENSEX": {'CE': None, 'PE': None}
        }
        self.total_pnl = 0
        self.daily_pnl = 0
        self.trades_history = []
        self.trades_today = 0
        self.trading_day = datetime.now().date()
        self.capital = 100000  # Initial capital
        self.wins = 0
        self.losses = 0
        
        # Index-specific stats
        self.index_pnl = {
            "NIFTY": 0,
            "BANKNIFTY": 0,
            "SENSEX": 0
        }
        self.index_trades = {
            "NIFTY": 0,
            "BANKNIFTY": 0,
            "SENSEX": 0
        }
        
        # Trade types tracking
        self.scalping_trades = 0
        self.scalping_pnl = 0
        self.scalping_wins = 0
        self.scalping_losses = 0
        self.regular_trades = 0
        self.regular_pnl = 0
        self.regular_wins = 0
        self.regular_losses = 0
        
        # Enhanced scalping strategies tracking
        self.momentum_scalp_trades = 0
        self.momentum_scalp_pnl = 0
        self.momentum_scalp_wins = 0
        self.momentum_scalp_losses = 0
        
        self.pattern_scalp_trades = 0
        self.pattern_scalp_pnl = 0
        self.pattern_scalp_wins = 0
        self.pattern_scalp_losses = 0
        
        self.expiry_scalping_trades = 0
        self.expiry_scalping_pnl = 0
        self.expiry_scalping_wins = 0
        self.expiry_scalping_losses = 0
        
        # Volatility tracking
        self.volatility_window = {
            "NIFTY": [],
            "BANKNIFTY": [],
            "SENSEX": []
        }
        
        # Expiry information
        self.expiry_dates = {
            "NIFTY": None,
            "BANKNIFTY": None,
            "SENSEX": None
        }
        
        # Scalping performance tracking by day
        self.scalping_performance_by_day = {}
        
        # Pattern recognition tracking
        self.recognized_patterns = {
            "NIFTY": {'CE': [], 'PE': []},
            "BANKNIFTY": {'CE': [], 'PE': []},
            "SENSEX": {'CE': [], 'PE': []}
        }
        
        # Strategy comparison tracking
        self.strategy_comparison = {
            'regular': {'trades': 0, 'wins': 0, 'pnl': 0},
            'scalping': {'trades': 0, 'wins': 0, 'pnl': 0},
            'momentum_scalp': {'trades': 0, 'wins': 0, 'pnl': 0},
            'pattern_scalp': {'trades': 0, 'wins': 0, 'pnl': 0},
            'expiry_scalping': {'trades': 0, 'wins': 0, 'pnl': 0}
        }
        
        # Time of day performance tracking
        self.time_of_day_performance = {
            'morning': {'trades': 0, 'wins': 0, 'pnl': 0},  # 9:15 AM - 11:30 AM
            'midday': {'trades': 0, 'wins': 0, 'pnl': 0},   # 11:30 AM - 1:30 PM
            'afternoon': {'trades': 0, 'wins': 0, 'pnl': 0}, # 1:30 PM - 3:30 PM
        }

# Create the global trading state instance
trading_state = TradingState()