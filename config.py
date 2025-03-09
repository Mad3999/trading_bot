"""
Configuration settings for the options trading dashboard.
"""

import os
import json
from datetime import datetime

class Config:
    """Configuration class for the application."""
    
    def __init__(self):
        # Using environment variables with more secure defaults
        self.api_key = os.getenv("SMARTAPI_KEY", "B8GFtq9f")
        self.username = os.getenv("SMARTAPI_USERNAME", "M243904")
        self.password = os.getenv("SMARTAPI_PASSWORD", "1209")
        self.totp_secret = os.getenv("SMARTAPI_TOTP", "KSFDSR2QQ5D2VNZF2QKO2HRD5A")
        
        # Using exchange/symbols that are confirmed working
        self.nse_exchange = "NSE"
        self.options_exchange = "NFO"
        
        # WebSocket configuration
        self.feed_token = None  # Will be set after login
        self.client_code = self.username  # Client code is usually the username
        self.ws_reconnect_interval = 5  # Reconnect every 5 seconds if disconnected
        self.ws_heartbeat_interval = 30  # Send heartbeat every 30 seconds
        
        # Basic trading configuration
        self.risk_per_trade = float(os.getenv("RISK_PER_TRADE", "1.0"))  # Risk per trade in percentage of capital
        self.max_trades_per_day = int(os.getenv("MAX_TRADES_PER_DAY", "40"))  # Maximum trades per day
        self.max_loss_percentage = float(os.getenv("MAX_LOSS_PERCENTAGE", "5.0"))  # Max daily loss percentage
        
        # Basic scalping configuration
        self.scalping_enabled = True
        self.scalping_target_pct = 0.5  # Target 0.5% profit for scalping
        self.scalping_stop_loss_pct = 0.3  # Stop loss at 0.3% for scalping
        
        # Enhanced scalping strategy configuration
        # Momentum scalping parameters
        self.momentum_scalping_enabled = True
        self.momentum_trigger_threshold = 0.15  # Minimum price movement in % to trigger entry
        self.min_momentum_strength = 2.0  # Minimum strength of price momentum
        self.momentum_target_multiplier = 2.0  # Target = stop_loss * this value
        self.momentum_max_duration = 3  # Maximum holding time in minutes for momentum scalps
        self.momentum_window = 5  # Number of price points to calculate momentum
        
        # Pattern scalping parameters
        self.pattern_scalping_enabled = True
        self.pattern_lookback = 20  # Number of candles to analyze for patterns
        self.min_pattern_quality = 0.75  # Minimum quality score for pattern detection (0-1)
        self.pattern_target_multiplier = 1.8  # Target = stop_loss * this value
        self.pattern_max_duration = 4  # Maximum holding time in minutes for pattern trades
        
        # Expiry day scalping parameters
        self.expiry_scalping_enabled = True
        self.expiry_scalping_target_pct = 1.2  # Higher target on expiry day (1.2% vs regular 0.5%)
        self.expiry_scalping_stop_loss_pct = 0.4  # Tighter stop loss on expiry day
        self.expiry_max_position_holding_time = 3  # Shorter holding time (3 mins vs regular 5)
        self.expiry_aggressive_entry_threshold = 2  # Lower signal threshold for entry (2 vs regular 3)
        self.expiry_trade_size_multiplier = 1.5  # Increase position size by 50%
        
        # Strategy weights configuration
        self.momentum_strategy_weight = 25  # Default weight for momentum strategy (%)
        self.pattern_strategy_weight = 25   # Default weight for pattern strategy (%)
        self.expiry_strategy_weight = 25    # Default weight for expiry strategy (%)
        self.standard_strategy_weight = 25  # Default weight for standard scalping (%)
        
        # Time window settings for trading
        self.trading_windows = {
            "morning": {"start": "09:15", "end": "11:30"},  # Morning window
            "midday": {"start": "11:30", "end": "13:30"},  # Midday window
            "afternoon": {"start": "13:30", "end": "15:15"}  # Afternoon window
        }
        
        # Added configuration validation
        self.validate_config()
        
        # Try to load saved config if it exists
        self.load_from_file()
    
    def validate_config(self):
        """Validate that required configuration is present"""
        missing = []
        if not self.api_key:
            missing.append("SMARTAPI_KEY")
        if not self.username:
            missing.append("SMARTAPI_USERNAME")
        if not self.password:
            missing.append("SMARTAPI_PASSWORD")
        if not self.totp_secret:
            missing.append("SMARTAPI_TOTP")
        
        if missing:
            print(f"Missing required environment variables: {', '.join(missing)}")
            print("Please set these environment variables before running the application")
            print("Using default values for development purposes")
    
    def save_to_file(self):
        """Save configuration to file."""
        config_dict = {
            # Don't save credentials
            "scalping_enabled": self.scalping_enabled,
            "scalping_target_pct": self.scalping_target_pct,
            "scalping_stop_loss_pct": self.scalping_stop_loss_pct,
            "momentum_scalping_enabled": self.momentum_scalping_enabled,
            "momentum_trigger_threshold": self.momentum_trigger_threshold,
            "min_momentum_strength": self.min_momentum_strength,
            "momentum_target_multiplier": self.momentum_target_multiplier,
            "momentum_max_duration": self.momentum_max_duration,
            "momentum_window": self.momentum_window,
            "pattern_scalping_enabled": self.pattern_scalping_enabled,
            "pattern_lookback": self.pattern_lookback,
            "min_pattern_quality": self.min_pattern_quality,
            "pattern_target_multiplier": self.pattern_target_multiplier,
            "pattern_max_duration": self.pattern_max_duration,
            "expiry_scalping_enabled": self.expiry_scalping_enabled,
            "expiry_scalping_target_pct": self.expiry_scalping_target_pct,
            "expiry_scalping_stop_loss_pct": self.expiry_scalping_stop_loss_pct,
            "expiry_max_position_holding_time": self.expiry_max_position_holding_time,
            "expiry_aggressive_entry_threshold": self.expiry_aggressive_entry_threshold,
            "expiry_trade_size_multiplier": self.expiry_trade_size_multiplier,
            "risk_per_trade": self.risk_per_trade,
            "max_trades_per_day": self.max_trades_per_day,
            "max_loss_percentage": self.max_loss_percentage,
            "trading_windows": self.trading_windows,
            "momentum_strategy_weight": self.momentum_strategy_weight,
            "pattern_strategy_weight": self.pattern_strategy_weight,
            "expiry_strategy_weight": self.expiry_strategy_weight,
            "standard_strategy_weight": self.standard_strategy_weight
        }
        
        try:
            with open("trading_config.json", "w") as f:
                json.dump(config_dict, f, indent=4)
            print(f"Configuration saved to trading_config.json at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def load_from_file(self):
        """Load configuration from file."""
        try:
            if os.path.exists("trading_config.json"):
                with open("trading_config.json", "r") as f:
                    config_dict = json.load(f)
                
                # Update configuration from file
                for key, value in config_dict.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                
                print(f"Configuration loaded from trading_config.json at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration")

# Create a global config instance
config = Config()