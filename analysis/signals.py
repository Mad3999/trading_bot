"""
Signal generation and prediction for the options trading dashboard.
"""

import logging
from models.trading_state import EMA_SHORT, EMA_MEDIUM, EMA_LONG, RSI_OVERSOLD, RSI_OVERBOUGHT
from services.price_service import price_history
from analysis.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands, calculate_ema

logger = logging.getLogger(__name__)

# Prediction models state
prediction_signals = {
    "NIFTY": {'CE': {'signal': 0, 'strength': 0, 'trend': 'NEUTRAL'}, 'PE': {'signal': 0, 'strength': 0, 'trend': 'NEUTRAL'}},
    "BANKNIFTY": {'CE': {'signal': 0, 'strength': 0, 'trend': 'NEUTRAL'}, 'PE': {'signal': 0, 'strength': 0, 'trend': 'NEUTRAL'}},
    "SENSEX": {'CE': {'signal': 0, 'strength': 0, 'trend': 'NEUTRAL'}, 'PE': {'signal': 0, 'strength': 0, 'trend': 'NEUTRAL'}}
}

def generate_prediction_signals(index_name):
    """Generate prediction signals based on technical indicators for the specified index."""
    global prediction_signals
    
    # Process CE option
    if len(price_history[index_name]["CE"]) > EMA_LONG:
        ce_price_series = price_history[index_name]["CE"]['price']
        
        # Calculate technical indicators for CE
        rsi_ce = calculate_rsi(ce_price_series)
        macd_line_ce, signal_line_ce, histogram_ce = calculate_macd(ce_price_series)
        upper_band_ce, middle_band_ce, lower_band_ce = calculate_bollinger_bands(ce_price_series)
        ema_short_ce = calculate_ema(ce_price_series, EMA_SHORT)
        ema_medium_ce = calculate_ema(ce_price_series, EMA_MEDIUM)
        ema_long_ce = calculate_ema(ce_price_series, EMA_LONG)
        
        # Generate CE signal based on indicators
        ce_signal = 0
        ce_strength = 0
        
        # RSI signal (Bullish for CE when RSI is low and rising)
        if rsi_ce < RSI_OVERSOLD:
            ce_signal += 1
            ce_strength += (RSI_OVERSOLD - rsi_ce) / 10
        elif rsi_ce > RSI_OVERBOUGHT:
            ce_signal -= 1
            ce_strength -= (rsi_ce - RSI_OVERBOUGHT) / 10
        
        # MACD signal
        if histogram_ce > 0:
            ce_signal += 1
            ce_strength += abs(histogram_ce) / 2
        elif histogram_ce < 0:
            ce_signal -= 1
            ce_strength -= abs(histogram_ce) / 2
        
        # Bollinger Bands signal
        last_price_ce = ce_price_series.iloc[-1]
        if last_price_ce < lower_band_ce:
            ce_signal += 1
            ce_strength += (lower_band_ce - last_price_ce) / last_price_ce * 10
        elif last_price_ce > upper_band_ce:
            ce_signal -= 1
            ce_strength -= (last_price_ce - upper_band_ce) / last_price_ce * 10
        
        # EMA signal
        if ema_short_ce > ema_medium_ce > ema_long_ce:
            ce_signal += 1
            ce_strength += 0.5
        elif ema_short_ce < ema_medium_ce < ema_long_ce:
            ce_signal -= 1
            ce_strength -= 0.5
        
        # Trend determination
        ce_trend = "NEUTRAL"
        if ce_signal > 1:
            ce_trend = "BULLISH"
        elif ce_signal < -1:
            ce_trend = "BEARISH"
        
        # Update prediction signals for CE
        prediction_signals[index_name]['CE'] = {
            'signal': ce_signal,
            'strength': ce_strength,
            'trend': ce_trend
        }
    
    # Process PE option
    if len(price_history[index_name]["PE"]) > EMA_LONG:
        pe_price_series = price_history[index_name]["PE"]['price']
        
        # Calculate technical indicators for PE
        rsi_pe = calculate_rsi(pe_price_series)
        macd_line_pe, signal_line_pe, histogram_pe = calculate_macd(pe_price_series)
        upper_band_pe, middle_band_pe, lower_band_pe = calculate_bollinger_bands(pe_price_series)
        ema_short_pe = calculate_ema(pe_price_series, EMA_SHORT)
        ema_medium_pe = calculate_ema(pe_price_series, EMA_MEDIUM)
        ema_long_pe = calculate_ema(pe_price_series, EMA_LONG)
        
        # Generate PE signal based on indicators
        pe_signal = 0
        pe_strength = 0
        
        # RSI signal (Bullish for PE when RSI is low and rising)
        if rsi_pe < RSI_OVERSOLD:
            pe_signal += 1
            pe_strength += (RSI_OVERSOLD - rsi_pe) / 10
        elif rsi_pe > RSI_OVERBOUGHT:
            pe_signal -= 1
            pe_strength -= (rsi_pe - RSI_OVERBOUGHT) / 10
        
        # MACD signal
        if histogram_pe > 0:
            pe_signal += 1
            pe_strength += abs(histogram_pe) / 2
        elif histogram_pe < 0:
            pe_signal -= 1
            pe_strength -= abs(histogram_pe) / 2
        
        # Bollinger Bands signal
        last_price_pe = pe_price_series.iloc[-1]
        if last_price_pe < lower_band_pe:
            pe_signal += 1
            pe_strength += (lower_band_pe - last_price_pe) / last_price_pe * 10
        elif last_price_pe > upper_band_pe:
            pe_signal -= 1
            pe_strength -= (last_price_pe - upper_band_pe) / last_price_pe * 10
        
        # EMA signal
        if ema_short_pe > ema_medium_pe > ema_long_pe:
            pe_signal += 1
            pe_strength += 0.5
        elif ema_short_pe < ema_medium_pe < ema_long_pe:
            pe_signal -= 1
            pe_strength -= 0.5
        
        # Trend determination
        pe_trend = "NEUTRAL"
        if pe_signal > 1:
            pe_trend = "BULLISH"
        elif pe_signal < -1:
            pe_trend = "BEARISH"
        
        # Update prediction signals for PE
        prediction_signals[index_name]['PE'] = {
            'signal': pe_signal,
            'strength': pe_strength,
            'trend': pe_trend
        }