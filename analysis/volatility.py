"""
Volatility calculations for the options trading dashboard.
"""

import numpy as np
import logging
from models.trading_state import trading_state

logger = logging.getLogger(__name__)

def calculate_volatility(index_name):
    """Calculate the current market volatility for the specified index."""
    if len(trading_state.volatility_window[index_name]) < 5:  # Need at least 5 data points
        return 1.0  # Default volatility
    
    # Calculate standard deviation of the percentage changes
    return np.std(trading_state.volatility_window[index_name])