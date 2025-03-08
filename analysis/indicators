"""
Technical indicators calculations for the options trading dashboard.
"""

import pandas as pd
import numpy as np
from models.trading_state import RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL, BOLLINGER_PERIOD, BOLLINGER_STD, ATR_PERIOD

def calculate_rsi(data, period=RSI_PERIOD):
    """Calculate RSI technical indicator."""
    if len(data) < period + 1:
        return 50  # Default neutral RSI when not enough data
    
    # Get price differences
    delta = data.diff()
    
    # Get gains and losses
    gain = delta.copy()
    loss = delta.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0
    loss = abs(loss)
    
    # Calculate average gain and loss
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    
    # Handle division by zero
    rs = rs.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1]

def calculate_macd(data, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL):
    """Calculate MACD technical indicator."""
    if len(data) < slow + signal:
        return 0, 0, 0  # Default neutral MACD when not enough data
    
    # Calculate EMAs
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    
    # Calculate MACD line and signal line
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    
    # Calculate histogram
    histogram = macd_line - signal_line
    
    return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]

def calculate_bollinger_bands(data, period=BOLLINGER_PERIOD, std_dev=BOLLINGER_STD):
    """Calculate Bollinger Bands technical indicator."""
    if len(data) < period:
        return data.iloc[-1], data.iloc[-1], data.iloc[-1]  # Default when not enough data
    
    # Calculate middle band (SMA)
    middle_band = data.rolling(window=period).mean()
    
    # Calculate standard deviation
    std = data.rolling(window=period).std()
    
    # Calculate upper and lower bands
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    
    return upper_band.iloc[-1], middle_band.iloc[-1], lower_band.iloc[-1]

def calculate_atr(data, period=ATR_PERIOD):
    """Calculate Average True Range (ATR) technical indicator."""
    if len(data) < period + 1:
        return 1.0  # Default ATR when not enough data
    
    # Create high, low, close series (in this case, they're all the same since we only have LTP)
    high = data
    low = data
    close = data
    
    # Calculate true range
    tr1 = high.diff().abs()
    tr2 = (high - low).abs()
    tr3 = (low - close.shift()).abs()
    
    # Find true range - this can be simplified in our case since high=low=close
    # But keeping the standard calculation for future enhancements
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate ATR
    atr = tr.rolling(window=period).mean()
    
    return atr.iloc[-1]

def calculate_ema(data, span):
    """Calculate Exponential Moving Average (EMA)."""
    if len(data) < span:
        return data.iloc[-1]  # Default when not enough data
    
    return data.ewm(span=span, adjust=False).mean().iloc[-1]