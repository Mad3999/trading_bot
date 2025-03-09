"""
Price update and fetching functions for the options trading dashboard.
"""

import logging
import threading
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime

from models.trading_state import trading_state
from models.instruments import INSTRUMENTS, DEFAULT_INDEX_PRICE
from utils.data_utils import cleanup_historical_data

logger = logging.getLogger(__name__)

# Thread lock for synchronizing access to price data
lock = threading.Lock()

# Price tracking dictionaries
last_ltp = {
    "NIFTY": {"SPOT": None, "CE": None, "PE": None},
    "BANKNIFTY": {"SPOT": None, "CE": None, "PE": None},
    "SENSEX": {"SPOT": None, "CE": None, "PE": None}
}

movement_pct = {
    "NIFTY": 0,
    "BANKNIFTY": 0,
    "SENSEX": 0
}

previous_price = {
    "NIFTY": None,
    "BANKNIFTY": None,
    "SENSEX": None
}

# Price history for analysis
price_history = {
    "NIFTY": {
        "SPOT": pd.DataFrame(columns=['timestamp', 'price']),
        "CE": pd.DataFrame(columns=['timestamp', 'price', 'volume']),
        "PE": pd.DataFrame(columns=['timestamp', 'price', 'volume'])
    },
    "BANKNIFTY": {
        "SPOT": pd.DataFrame(columns=['timestamp', 'price']),
        "CE": pd.DataFrame(columns=['timestamp', 'price', 'volume']),
        "PE": pd.DataFrame(columns=['timestamp', 'price', 'volume'])
    },
    "SENSEX": {
        "SPOT": pd.DataFrame(columns=['timestamp', 'price']),
        "CE": pd.DataFrame(columns=['timestamp', 'price', 'volume']),
        "PE": pd.DataFrame(columns=['timestamp', 'price', 'volume'])
    }
}

def update_index_price(index_name, ltp):
    """Update index price from WebSocket data."""
    global last_ltp, price_history, previous_price, movement_pct
    
    # Check if value is realistic (SENSEX should be in thousands, NIFTY and BANKNIFTY should be in high hundreds)
    if (index_name == "SENSEX" and ltp < 1000) or \
       ((index_name == "NIFTY" or index_name == "BANKNIFTY") and ltp < 100):
        logger.warning(f"{index_name} value suspiciously low ({ltp}), using default value")
        ltp = DEFAULT_INDEX_PRICE[index_name]
    
    with lock:
        # Calculate movement percentage if we have a previous value
        if previous_price[index_name] is not None:
            movement_pct[index_name] = ((ltp - previous_price[index_name]) / previous_price[index_name]) * 100
        
        # Update values
        previous_price[index_name] = last_ltp[index_name]["SPOT"]
        last_ltp[index_name]["SPOT"] = ltp
        
        # Add to price history for analysis
        timestamp = pd.Timestamp.now()
        new_row = pd.DataFrame({'timestamp': [timestamp], 'price': [ltp]})
        price_history[index_name]["SPOT"] = pd.concat([price_history[index_name]["SPOT"], new_row], ignore_index=True)
        
        # Update volatility window
        if len(price_history[index_name]["SPOT"]) >= 2:
            latest_prices = price_history[index_name]["SPOT"]['price'].tail(2).values
            latest_pct_change = (latest_prices[1] - latest_prices[0]) / latest_prices[0] * 100
            update_volatility(index_name, latest_pct_change)
    
    logger.info(f"{index_name} LTP (WebSocket): {last_ltp[index_name]['SPOT']}, Movement: {movement_pct[index_name]:.2f}%")
    
    # Update analysis after price change
    from trading.strategy import update_analysis
    update_analysis(index_name)

def update_option_price(index_name, option_type, ltp):
    """Update option price from WebSocket data."""
    global last_ltp, price_history
    
    with lock:
        last_ltp[index_name][option_type] = ltp
        # Add to price history for analysis
        timestamp = pd.Timestamp.now()
        volume = 5000  # Default volume for calculation
        new_row = pd.DataFrame({'timestamp': [timestamp], 'price': [ltp], 'volume': [volume]})
        price_history[index_name][option_type] = pd.concat([price_history[index_name][option_type], new_row], ignore_index=True)
    
    logger.info(f"{index_name} {option_type} LTP (WebSocket): {last_ltp[index_name][option_type]} ({INSTRUMENTS[index_name][option_type]['symbol']})")
    
    # Update analysis after price change
    from trading.strategy import update_analysis
    update_analysis(index_name)

def update_volatility(index_name, latest_pct_change):
    """Update the volatility window with the latest percentage change."""
    # Add the latest percentage change to the window
    trading_state.volatility_window[index_name].append(latest_pct_change)
    
    # Keep only the latest VOLATILITY_PERIOD points
    if len(trading_state.volatility_window[index_name]) > trading_state.VOLATILITY_PERIOD:
        trading_state.volatility_window[index_name].pop(0)

def fetch_ltp(exchange, symbol, token):
    """Fetch LTP using REST API as fallback if WebSocket fails."""
    try:
        from services.api_service import smart_api, broker_connected
        
        if smart_api and broker_connected:
            # Direct call using the known working formats
            ltp_data = smart_api.ltpData(exchange, symbol, token)
            if ltp_data.get("status") and "data" in ltp_data:
                logger.info(f"Successfully fetched LTP for {symbol} on {exchange}")
                return float(ltp_data["data"]["ltp"])
            else:
                logger.warning(f"Failed to fetch LTP for {symbol} on {exchange}: {ltp_data}")
                return None
        return None
    except Exception as e:
        logger.error(f"Error fetching LTP for {symbol}: {e}")
        return None

def fetch_index_ltp(index_name):
    """Fetch index LTP from REST API as fallback."""
    global last_ltp
    
    ltp = fetch_ltp(INSTRUMENTS[index_name]["SPOT"]["exchange"], 
                   INSTRUMENTS[index_name]["SPOT"]["symbol"], 
                   INSTRUMENTS[index_name]["SPOT"]["token"])
    
    # Handle suspiciously low values or API failure
    if ltp is not None:
        # Check if value is realistic
        if (index_name == "SENSEX" and ltp < 1000) or \
           ((index_name == "NIFTY" or index_name == "BANKNIFTY") and ltp < 100):
            logger.warning(f"{index_name} value suspiciously low ({ltp}), using default value")
            ltp = DEFAULT_INDEX_PRICE[index_name]
    else:
        # Use last known value or default
        if last_ltp[index_name]["SPOT"] is not None:
            ltp = last_ltp[index_name]["SPOT"]
            logger.warning(f"Using last known {index_name} value: {ltp}")
        else:
            ltp = DEFAULT_INDEX_PRICE[index_name]
            logger.warning(f"Using default {index_name} value: {ltp}")
    
    # Update the price using the common handler
    update_index_price(index_name, ltp)

def fetch_option_ltp(index_name, option_type):
    """Fetch option LTP from REST API as fallback."""
    global last_ltp
    
    ltp = fetch_ltp(INSTRUMENTS[index_name][option_type]["exchange"], 
                   INSTRUMENTS[index_name][option_type]["symbol"], 
                   INSTRUMENTS[index_name][option_type]["token"])
    
    # Handle API failure
    if ltp is None:
        if last_ltp[index_name][option_type] is not None:
            ltp = last_ltp[index_name][option_type]
            logger.warning(f"Using last known {index_name} {option_type} value: {ltp}")
        else:
            # Use a default that makes sense for the index
            if index_name == "SENSEX":
                ltp = 250.0 if option_type == "CE" else 200.0
            elif index_name == "NIFTY":
                ltp = 150.0 if option_type == "CE" else 120.0
            else:  # BANKNIFTY
                ltp = 180.0 if option_type == "CE" else 150.0
            logger.warning(f"Using default {index_name} {option_type} value: {ltp}")
    else:
        logger.info(f"Got real {index_name} {option_type} price: {ltp}")
    
    # Update the price using the common handler
    update_option_price(index_name, option_type, ltp)

def fetch_prices_periodically():
    """Fetch prices periodically as fallback if WebSocket fails."""
    from services.websocket_service import websocket_connected
    
    while True:
        # Only use REST API if WebSocket is not connected
        if not websocket_connected:
            try:
                logger.info("Using REST API fallback since WebSocket is not connected")
                
                # Fetch all indices and options
                for index_name in INSTRUMENTS:
                    fetch_index_ltp(index_name)
                    time.sleep(1)
                    
                    fetch_option_ltp(index_name, "CE")
                    time.sleep(1)
                    
                    fetch_option_ltp(index_name, "PE")
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Error in fallback price fetching cycle: {e}")
        
        # Sleep for a longer time since WebSocket should be the primary source
        time.sleep(10)  # 10 seconds between fallback cycles