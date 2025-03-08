"""
Utility functions for data management in the options trading dashboard.
"""

import logging

logger = logging.getLogger(__name__)

def cleanup_historical_data(price_history, index_name):
    """Clean up old data to prevent memory bloat."""
    # Keep only the latest 1000 data points for the index
    if len(price_history[index_name]["SPOT"]) > 1000:
        price_history[index_name]["SPOT"] = price_history[index_name]["SPOT"].tail(1000)
    
    # Keep only the latest 1000 data points for CE
    if len(price_history[index_name]["CE"]) > 1000:
        price_history[index_name]["CE"] = price_history[index_name]["CE"].tail(1000)
    
    # Keep only the latest 1000 data points for PE
    if len(price_history[index_name]["PE"]) > 1000:
        price_history[index_name]["PE"] = price_history[index_name]["PE"].tail(1000)