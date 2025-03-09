def calculate_position_size(index_name, option_type, current_price, is_scalping=False):
    """Calculate position size and stop loss distance based on risk parameters."""
    from config import Config
    config = Config()
    
    # Check if we have enough capital
    if trading_state.capital <= 0:
        return 0, 0
    
    # Calculate risk amount in rupees
    risk_amount = trading_state.capital * (trading_state.RISK_PER_TRADE / 100)
    
    # For scalping, calculate stop loss based on ATR to be more dynamic with market volatility
    if is_scalping:
        from analysis.indicators import calculate_atr
        from services.price_service import price_history
        
        # Use ATR for more dynamic stop loss on scalping trades
        atr = calculate_atr(price_history[index_name][option_type]['price'])
        stop_loss_distance = max(atr * 0.5, current_price * (config.scalping_stop_loss_pct / 100))
    else:
        # Regular trading - stop loss is 1% of current price
        stop_loss_distance = current_price * 0.01
    
    # Calculate position size
    quantity = int(risk_amount / stop_loss_distance)
    
    # Ensure quantity is at least 1
    if quantity < 1:
        quantity = 1
    
    return quantity, stop_loss_distance