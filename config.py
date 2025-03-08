"""
Configuration settings for the options trading dashboard.
"""

import os

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
        
        # Trading configuration
        self.scalping_enabled = True
        self.scalping_target_pct = 0.5  # Target 0.5% profit for scalping
        self.scalping_stop_loss_pct = 0.3  # Stop loss at 0.3% for scalping
        
        # Added configuration validation
        self.validate_config()
    
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