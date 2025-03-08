import logging
from models.trading_state import trading_state
from config import RISK_PER_TRADE

logger = logging.getLogger(__name__)

# ============ Position Sizing ============
def calculate_position_size(index_name, option_type, current_price, is_scalping=False):
    """Calculate position size and stop loss distance based on risk parameters."""
    global trading_state
    from config import config
    
    # Check if we have enough capital
    if trading_state.capital <= 0:
        return 0, 0
    
    # Calculate risk amount in rupees
    risk_amount = trading_state.capital * (RISK_PER_TRADE / 100)
    
    # For scalping, we use tighter stop loss
    if is_scalping:
        stop_loss_distance = current_price * (config.scalping_stop_loss_pct / 100)
    else:
        # Regular trading - stop loss is 1% of current price
        stop_loss_distance = current_price * 0.01
    
    # Calculate position size
    quantity = int(risk_amount / stop_loss_distance)
    
    # Ensure quantity is at least 1
    if quantity < 1:
        quantity = 1
    
    return quantity, stop_loss_distance