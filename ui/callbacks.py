"""
Dashboard callbacks for the options trading dashboard.
Updated with support for symbol-specific settings and enhanced scalping strategies.
"""

import dash
from dash import Output, Input, State, html
import pandas as pd
import dash_bootstrap_components as dbc

from models.trading_state import trading_state
from models.instruments import INSTRUMENTS
from services.price_service import last_ltp, movement_pct
from services.websocket_service import websocket_connected
from analysis.signals import prediction_signals
from analysis.volatility import calculate_volatility
from trading.strategy import refresh_atm_options, calculate_pcr, calculate_index_range
from config import Config, config

# Try to import enhanced_strategy and symbol_callbacks, but don't fail if they don't exist
try:
    from trading.enhanced_strategy import update_enhanced_analysis
except ImportError:
    # Create a placeholder function if the import fails
    def update_enhanced_analysis(index_name, symbol_settings):
        pass

try:
    from ui.symbol_callbacks import register_symbol_callbacks
except ImportError:
    # Create a placeholder function if the import fails
    def register_symbol_callbacks(app):
        pass

def register_enhanced_scalping_callbacks(app):
    """Register callbacks for the enhanced scalping analytics tab."""
    
    @app.callback(
        [
            # Momentum scalping stats
            Output("momentum-scalp-trades", "children"),
            Output("momentum-scalp-win-rate", "children"),
            Output("momentum-scalp-pnl", "children"),
            Output("momentum-scalp-duration", "children"),
            
            # Pattern scalping stats
            Output("pattern-scalp-trades", "children"),
            Output("pattern-scalp-win-rate", "children"),
            Output("pattern-scalp-pnl", "children"),
            Output("pattern-scalp-duration", "children"),
            
            # Expiry scalping stats
            Output("expiry-scalp-trades", "children"),
            Output("expiry-scalp-win-rate", "children"),
            Output("expiry-scalp-pnl", "children"),
            Output("expiry-scalp-duration", "children"),
            
            # Standard scalping stats
            Output("standard-scalp-trades", "children"),
            Output("standard-scalp-win-rate", "children"),
            Output("standard-scalp-pnl", "children"),
            Output("standard-scalp-duration", "children"),
            
            # Best strategy
            Output("best-scalping-strategy", "children")
        ],
        [Input("interval-component", "n_intervals")]
    )
    def update_scalping_strategy_stats(n_intervals):
        # Get data for each strategy type
        momentum_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'momentum_scalp']
        pattern_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'pattern_scalp']
        expiry_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'expiry_scalping']
        standard_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'scalping']
        
        # Calculate metrics for each strategy
        outputs = []
        
        # Helper function to calculate strategy metrics
        def calculate_strategy_metrics(trades):
            if not trades:
                return "0", "0.00%", "₹0.00", "0.0 mins"
                
            num_trades = len(trades)
            wins = sum(1 for trade in trades if trade['pnl'] > 0)
            win_rate = (wins / num_trades * 100) if num_trades > 0 else 0
            total_pnl = sum(trade['pnl'] for trade in trades)
            
            # Calculate average duration
            durations = [(trade['exit_time'] - trade['entry_time']).total_seconds() / 60 for trade in trades]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return (
                str(num_trades),
                f"{win_rate:.2f}%",
                html.Span(f"₹{total_pnl:.2f}", style={"color": "green" if total_pnl >= 0 else "red"}),
                f"{avg_duration:.1f} mins"
            )
        
        # Calculate and add momentum stats
        momentum_metrics = calculate_strategy_metrics(momentum_trades)
        outputs.extend(momentum_metrics)
        
        # Calculate and add pattern stats
        pattern_metrics = calculate_strategy_metrics(pattern_trades)
        outputs.extend(pattern_metrics)
        
        # Calculate and add expiry stats
        expiry_metrics = calculate_strategy_metrics(expiry_trades)
        outputs.extend(expiry_metrics)
        
        # Calculate and add standard scalping stats
        standard_metrics = calculate_strategy_metrics(standard_trades)
        outputs.extend(standard_metrics)
        
        # Determine best strategy
        strategy_pnls = {
            'Momentum Scalping': sum(trade['pnl'] for trade in momentum_trades),
            'Pattern Scalping': sum(trade['pnl'] for trade in pattern_trades),
            'Expiry Scalping': sum(trade['pnl'] for trade in expiry_trades),
            'Standard Scalping': sum(trade['pnl'] for trade in standard_trades)
        }
        
        # Filter out strategies with no trades
        valid_strategies = {k: v for k, v in strategy_pnls.items() if v != 0}
        
        if valid_strategies:
            best_strategy = max(valid_strategies.items(), key=lambda x: x[1])
            best_strategy_text = f"{best_strategy[0]} (₹{best_strategy[1]:.2f})"
        else:
            best_strategy_text = "No data available yet"
        
        outputs.append(best_strategy_text)
        
        return tuple(outputs)
    
    @app.callback(
        Output("pattern-recognition-analysis", "children"),
        [Input("interval-component", "n_intervals")]
    )
    def update_pattern_analysis(n_intervals):
        # Get all pattern trades
        pattern_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'pattern_scalp']
        
        if not pattern_trades:
            return html.P("No pattern-based trades have been executed yet.")
        
        # Create a summary of pattern results
        return html.Div([
            html.P(f"Total pattern-based trades: {len(pattern_trades)}"),
            html.P(f"Success rate: {sum(1 for t in pattern_trades if t['pnl'] > 0) / len(pattern_trades) * 100:.2f}%"),
            html.P(f"Average P&L: ₹{sum(t['pnl'] for t in pattern_trades) / len(pattern_trades):.2f}")
        ])
    
    @app.callback(
        Output("momentum-analysis", "children"),
        [Input("interval-component", "n_intervals")]
    )
    def update_momentum_analysis(n_intervals):
        # Get all momentum trades
        momentum_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'momentum_scalp']
        
        if not momentum_trades:
            return html.P("No momentum-based trades have been executed yet.")
        
        # Calculate time-based performance (morning vs afternoon)
        morning_trades = [t for t in momentum_trades if t['entry_time'].hour < 12]
        afternoon_trades = [t for t in momentum_trades if t['entry_time'].hour >= 12]
        
        morning_pnl = sum(t['pnl'] for t in morning_trades) if morning_trades else 0
        afternoon_pnl = sum(t['pnl'] for t in afternoon_trades) if afternoon_trades else 0
        
        morning_win_rate = sum(1 for t in morning_trades if t['pnl'] > 0) / len(morning_trades) * 100 if morning_trades else 0
        afternoon_win_rate = sum(1 for t in afternoon_trades if t['pnl'] > 0) / len(afternoon_trades) * 100 if afternoon_trades else 0
        
        # Create a table for time-based performance
        header = html.Thead(html.Tr([
            html.Th("Time of Day"),
            html.Th("Trades"),
            html.Th("Win Rate"),
            html.Th("P&L")
        ]))
        
        rows = [
            html.Tr([
                html.Td("Morning (9:00-12:00)"),
                html.Td(len(morning_trades)),
                html.Td(f"{morning_win_rate:.2f}%"),
                html.Td(html.Span(f"₹{morning_pnl:.2f}", style={"color": "green" if morning_pnl >= 0 else "red"}))
            ]),
            html.Tr([
                html.Td("Afternoon (12:00-15:30)"),
                html.Td(len(afternoon_trades)),
                html.Td(f"{afternoon_win_rate:.2f}%"),
                html.Td(html.Span(f"₹{afternoon_pnl:.2f}", style={"color": "green" if afternoon_pnl >= 0 else "red"}))
            ])
        ]
        
        body = html.Tbody(rows)
        time_table = dbc.Table([header, body], bordered=True, striped=True, hover=True, responsive=True)
        
        return html.Div([
            html.P(f"Total momentum-based trades: {len(momentum_trades)}"),
            html.P(f"Success rate: {sum(1 for t in momentum_trades if t['pnl'] > 0) / len(momentum_trades) * 100:.2f}%"),
            html.P(f"Average P&L: ₹{sum(t['pnl'] for t in momentum_trades) / len(momentum_trades):.2f}"),
            html.H5("Performance by Time of Day", className="mt-3"),
            time_table
        ])

def register_callbacks(app):
    """Register all callbacks for the dashboard."""
    register_enhanced_scalping_callbacks(app)
    
    # Register symbol-specific callbacks
    register_symbol_callbacks(app)
    
    # Main interval update callback
    @app.callback(
        [
            # NIFTY tab outputs
            Output("nifty-price", "children"),
            Output("nifty-movement", "children"),
            Output("nifty-trend", "children"),
            Output("nifty-volatility", "children"),
            Output("nifty-range", "children"),
            Output("nifty-pcr", "children"),
            Output("nifty-expiry", "children"),
            Output("nifty-pnl", "children"),
            Output("nifty-trades", "children"),
            Output("websocket-status-nifty", "children"),
            Output("nifty-ce-symbol", "children"),
            Output("nifty-ce-price", "children"),
            Output("nifty-ce-signal", "children"),
            Output("nifty-ce-signal-value", "children"),
            Output("nifty-ce-strength-value", "children"),
            Output("nifty-pe-symbol", "children"),
            Output("nifty-pe-price", "children"),
            Output("nifty-pe-signal", "children"),
            Output("nifty-pe-signal-value", "children"),
            Output("nifty-pe-strength-value", "children"),
            Output("nifty-active-trades-container", "children"),
            Output("nifty-recent-trades-container", "children"),
            
            # BANKNIFTY tab outputs
            Output("banknifty-price", "children"),
            Output("banknifty-movement", "children"),
            Output("banknifty-trend", "children"),
            Output("banknifty-volatility", "children"),
            Output("banknifty-range", "children"),
            Output("banknifty-pcr", "children"),
            Output("banknifty-expiry", "children"),
            Output("banknifty-pnl", "children"),
            Output("banknifty-trades", "children"),
            Output("websocket-status-banknifty", "children"),
            Output("banknifty-ce-symbol", "children"),
            Output("banknifty-ce-price", "children"),
            Output("banknifty-ce-signal", "children"),
            Output("banknifty-ce-signal-value", "children"),
            Output("banknifty-ce-strength-value", "children"),
            Output("banknifty-pe-symbol", "children"),
            Output("banknifty-pe-price", "children"),
            Output("banknifty-pe-signal", "children"),
            Output("banknifty-pe-signal-value", "children"),
            Output("banknifty-pe-strength-value", "children"),
            Output("banknifty-active-trades-container", "children"),
            Output("banknifty-recent-trades-container", "children"),
            
            # SENSEX tab outputs
            Output("sensex-price", "children"),
            Output("sensex-movement", "children"),
            Output("sensex-trend", "children"),
            Output("sensex-volatility", "children"),
            Output("sensex-range", "children"),
            Output("sensex-pcr", "children"),
            Output("sensex-expiry", "children"),
            Output("sensex-pnl", "children"),
            Output("sensex-trades", "children"),
            Output("websocket-status-sensex", "children"),
            Output("sensex-ce-symbol", "children"),
            Output("sensex-ce-price", "children"),
            Output("sensex-ce-signal", "children"),
            Output("sensex-ce-signal-value", "children"),
            Output("sensex-ce-strength-value", "children"),
            Output("sensex-pe-symbol", "children"),
            Output("sensex-pe-price", "children"),
            Output("sensex-pe-signal", "children"),
            Output("sensex-pe-signal-value", "children"),
            Output("sensex-pe-strength-value", "children"),
            Output("sensex-active-trades-container", "children"),
            Output("sensex-recent-trades-container", "children"),
            
            # Overall performance tab outputs
            Output("total-pnl", "children"),
            Output("daily-pnl", "children"),
            Output("win-rate", "children"),
            Output("trades-today", "children"),
            Output("websocket-status", "children"),
            Output("overall-nifty-pnl", "children"),
            Output("overall-banknifty-pnl", "children"),
            Output("overall-sensex-pnl", "children"),
            Output("best-index", "children"),
            Output("total-trades", "children"),
            Output("overall-nifty-trades", "children"),
            Output("overall-banknifty-trades", "children"),
            Output("overall-sensex-trades", "children"),
            Output("regular-trades", "children"),
            Output("regular-trades-pnl", "children"),
            Output("regular-win-rate", "children"),
            Output("scalping-mode", "children"),
            Output("scalping-pnl", "children"),
            Output("scalping-win-rate", "children"),
            Output("scalping-avg-duration", "children"),
            Output("best-scalping-day", "children"),
            Output("best-expiry-performance", "children"),
            Output("all-recent-trades-container", "children"),
            
            # Scalping analytics tab outputs
            Output("daily-scalping-performance", "children"),
            Output("expiry-day-performance", "children"),
            Output("scalping-trade-analysis", "children")
        ],
        [Input("interval-component", "n_intervals"),
         Input("symbol-settings", "data")]
    )
    def update_dashboard(n_intervals, symbol_settings):
        # Default symbol_settings if None
        if symbol_settings is None:
            symbol_settings = {}
        
        # Apply enhanced strategy for each index, respecting symbol settings
        try:
            update_enhanced_analysis('NIFTY', symbol_settings)
            update_enhanced_analysis('BANKNIFTY', symbol_settings)
            update_enhanced_analysis('SENSEX', symbol_settings)
        except Exception as e:
            print(f"Error in enhanced analysis: {e}")
        
        # Helper function to generate HTML based on movement
        def get_movement_html(value):
            if value is not None:
                if value > 0:
                    return html.Span(f"▲ {value:.2f}%", style={"color": "green"})
                elif value < 0:
                    return html.Span(f"▼ {value:.2f}%", style={"color": "red"})
                else:
                    return html.Span(f"- {value:.2f}%", style={"color": "gray"})
            return "0.00%"
        
        # Helper function to generate market trend HTML
        def get_trend_html(index_name):
            if movement_pct[index_name] > 0.2:
                return html.Span("BULLISH", style={"color": "green", "font-weight": "bold"})
            elif movement_pct[index_name] < -0.2:
                return html.Span("BEARISH", style={"color": "red", "font-weight": "bold"})
            else:
                return html.Span("NEUTRAL", style={"color": "gray", "font-weight": "bold"})
        
        # Helper function to generate signal HTML
        def get_signal_html(index_name, option_type):
            trend = prediction_signals[index_name][option_type]["trend"]
            signal = prediction_signals[index_name][option_type]["signal"]
            
            style = {"color": "green" if trend == "BULLISH" else "red" if trend == "BEARISH" else "gray",
                    "font-weight": "bold"}
            
            return html.Span(f"{trend} ({signal})", style=style)
        
        # Helper function to generate active trades HTML
        def get_active_trades_html(index_name):
            active_trades_elements = []
            
            # Add trading status indicator at the top
            is_trading_enabled = symbol_settings.get(index_name, {}).get('trading_enabled', True)
            is_scalping_enabled = symbol_settings.get(index_name, {}).get('scalping_enabled', True)
            lot_size = symbol_settings.get(index_name, {}).get('lot_size', 1)
            
            status_indicators = []
            if not is_trading_enabled:
                status_indicators.append(
                    html.Div("Trading is DISABLED for this symbol", 
                             className="alert alert-warning py-1 mb-2")
                )
            
            status_indicators.append(
                html.P([
                    f"Lot Size: ",
                    html.Span(f"{lot_size}", style={"font-weight": "bold"}),
                    f" | Scalping: ",
                    html.Span("Enabled", style={"color": "green", "font-weight": "bold"}) if is_scalping_enabled 
                    else html.Span("Disabled", style={"color": "red", "font-weight": "bold"})
                ], className="mb-2")
            )
            
            if status_indicators:
                active_trades_elements.extend(status_indicators)
            
            for option_type in ['CE', 'PE']:
                if trading_state.active_trades[index_name][option_type]:
                    entry_price = trading_state.entry_price[index_name][option_type]
                    current_price = last_ltp[index_name][option_type]
                    current_pnl = (current_price - entry_price) * trading_state.quantity[index_name][option_type] if current_price is not None else 0
                    current_pnl_pct = (current_price - entry_price) / entry_price * 100 if current_price is not None else 0
                    
                    pnl_style = {"color": "green" if current_pnl >= 0 else "red"}
                    
                    entry_time = trading_state.entry_time[index_name][option_type]
                    time_held = (pd.Timestamp.now() - entry_time).total_seconds() / 60 if entry_time else 0
                    
                    trade_type = trading_state.trade_type[index_name][option_type]
                    
                    trade_info = dbc.Card([
                        dbc.CardHeader(f"{option_type} {trade_type.upper()} Trade: {INSTRUMENTS[index_name][option_type]['symbol']}"),
                        dbc.CardBody([
                            html.P(f"Entry Price: ₹{entry_price:.2f} | Current: ₹{current_price:.2f}"),
                            html.P(f"Quantity: {trading_state.quantity[index_name][option_type]} (Lot Size: {lot_size})"),
                            html.P([
                                "Current P&L: ",
                                html.Span(f"₹{current_pnl:.2f} ({current_pnl_pct:.2f}%)", style=pnl_style)
                            ]),
                            html.P(f"Stop Loss: ₹{trading_state.stop_loss[index_name][option_type]:.2f}"),
                            html.P(f"Target: ₹{trading_state.target[index_name][option_type]:.2f}"),
                            html.P(f"Time Held: {time_held:.1f} mins"),
                        ])
                    ], className="mb-3")
                    
                    active_trades_elements.append(trade_info)
            
            if not active_trades_elements or (len(active_trades_elements) <= len(status_indicators)):
                active_trades_elements.append(html.P("No active trades", className="text-muted"))
            
            return active_trades_elements
        
        # Helper function to generate recent trades HTML
        def get_recent_trades_html(index_name):
            is_trading_enabled = symbol_settings.get(index_name, {}).get('trading_enabled', True)
            
            if not is_trading_enabled:
                return html.Div("Trading is DISABLED for this symbol", 
                               className="alert alert-warning py-1 mb-2")
                
            recent_trades = [trade for trade in trading_state.trades_history if trade['index'] == index_name]
            recent_trades_elements = []
            
            for trade in reversed(recent_trades[-5:]):
                pnl_style = {"color": "green" if trade['pnl'] >= 0 else "red"}
                
                trade_duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 60
                
                trade_card = dbc.Card([
                    dbc.CardHeader(f"{trade['option_type']} {trade['trade_type'].upper()} Trade: {trade['exit_time'].strftime('%H:%M:%S')}"),
                    dbc.CardBody([
                        html.P(f"Entry: ₹{trade['entry_price']:.2f} | Exit: ₹{trade['exit_price']:.2f}"),
                        html.P([
                            "P&L: ",
                            html.Span(f"₹{trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)", style=pnl_style)
                        ]),
                        html.P(f"Duration: {trade_duration:.1f} mins"),
                        html.P(f"Reason: {trade['reason']}", className="text-muted"),
                    ])
                ], className="mb-2")
                
                recent_trades_elements.append(trade_card)
            
            if not recent_trades_elements:
                recent_trades_elements = html.P("No recent trades", className="text-muted")
            
            return recent_trades_elements
        
        # Helper function to get all recent trades HTML
        def get_all_recent_trades_html():
            recent_trades_elements = []
            
            for trade in reversed(trading_state.trades_history[-10:]):
                # Check if trading is enabled for this index
                if not symbol_settings.get(trade['index'], {}).get('trading_enabled', True):
                    continue
                    
                pnl_style = {"color": "green" if trade['pnl'] >= 0 else "red"}
                
                trade_duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 60
                
                trade_card = dbc.Card([
                    dbc.CardHeader(f"{trade['index']} {trade['option_type']} {trade['trade_type'].upper()} Trade: {trade['exit_time'].strftime('%H:%M:%S')}"),
                    dbc.CardBody([
                        html.P(f"Entry: ₹{trade['entry_price']:.2f} | Exit: ₹{trade['exit_price']:.2f}"),
                        html.P([
                            "P&L: ",
                            html.Span(f"₹{trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)", style=pnl_style)
                        ]),
                        html.P(f"Duration: {trade_duration:.1f} mins"),
                        html.P(f"Reason: {trade['reason']}", className="text-muted"),
                    ])
                ], className="mb-2")
                
                recent_trades_elements.append(trade_card)
            
            if not recent_trades_elements:
                recent_trades_elements = html.P("No recent trades", className="text-muted")
            
            return recent_trades_elements
        
        # Helper function to generate daily scalping performance HTML
        def get_daily_scalping_performance():
            if not trading_state.scalping_performance_by_day:
                return html.P("No scalping performance data available yet", className="text-muted")
                
            tables = []
            
            # Sort by date descending
            sorted_days = sorted(trading_state.scalping_performance_by_day.keys(), reverse=True)
            
            # Create a table
            header = html.Thead(html.Tr([
                html.Th("Date"),
                html.Th("P&L"),
                html.Th("Trades"),
                html.Th("Wins"),
                html.Th("Win Rate")
            ]))
            
            rows = []
            for day in sorted_days:
                data = trading_state.scalping_performance_by_day[day]
                pnl_style = {"color": "green" if data['pnl'] >= 0 else "red"}
                
                row = html.Tr([
                    html.Td(day),
                    html.Td(html.Span(f"₹{data['pnl']:.2f}", style=pnl_style)),
                    html.Td(data['trades']),
                    html.Td(data['wins']),
                    html.Td(f"{data['win_rate']:.2f}%")
                ])
                rows.append(row)
            
            body = html.Tbody(rows)
            table = dbc.Table([header, body], bordered=True, striped=True, hover=True, responsive=True)
            tables.append(table)
            
            return tables
        
        # Helper function to get expiry day performance
        def get_expiry_day_performance():
            if not trading_state.trades_history:
                return html.P("No expiry day performance data available yet", className="text-muted")
            
            # Group trades by expiry date
            expiry_trades = {}
            for trade in trading_state.trades_history:
                if trade['expiry'] is None:
                    continue
                    
                expiry_key = trade['expiry'].strftime("%Y-%m-%d")
                if expiry_key not in expiry_trades:
                    expiry_trades[expiry_key] = []
                expiry_trades[expiry_key].append(trade)
            
            if not expiry_trades:
                return html.P("No expiry day performance data available yet", className="text-muted")
            
            # Calculate stats for each expiry
            expiry_stats = {}
            for expiry, trades in expiry_trades.items():
                pnl = sum(trade['pnl'] for trade in trades)
                wins = sum(1 for trade in trades if trade['pnl'] > 0)
                win_rate = wins / len(trades) * 100 if trades else 0
                
                expiry_stats[expiry] = {
                    'expiry': expiry,
                    'pnl': pnl,
                    'trades': len(trades),
                    'wins': wins,
                    'win_rate': win_rate
                }
            
            # Sort by date descending
            sorted_expiries = sorted(expiry_stats.keys(), reverse=True)
            
            # Create a table
            header = html.Thead(html.Tr([
                html.Th("Expiry Date"),
                html.Th("P&L"),
                html.Th("Trades"),
                html.Th("Wins"),
                html.Th("Win Rate")
            ]))
            
            rows = []
            for expiry in sorted_expiries:
                data = expiry_stats[expiry]
                pnl_style = {"color": "green" if data['pnl'] >= 0 else "red"}
                
                row = html.Tr([
                    html.Td(expiry),
                    html.Td(html.Span(f"₹{data['pnl']:.2f}", style=pnl_style)),
                    html.Td(data['trades']),
                    html.Td(data['wins']),
                    html.Td(f"{data['win_rate']:.2f}%")
                ])
                rows.append(row)
            
            body = html.Tbody(rows)
            table = dbc.Table([header, body], bordered=True, striped=True, hover=True, responsive=True)
            
            return table
        
        # Helper function to get scalping trade analysis
        def get_scalping_trade_analysis():
            scalping_trades = [trade for trade in trading_state.trades_history 
                              if trade['trade_type'] in ['scalping', 'momentum_scalp', 'pattern_scalp', 'expiry_scalping']]
            
            if not scalping_trades:
                return html.P("No scalping trades data available yet", className="text-muted")
            
            # Analyze time of day performance
            morning_trades = [t for t in scalping_trades if t['entry_time'].hour < 12]
            afternoon_trades = [t for t in scalping_trades if 12 <= t['entry_time'].hour < 15]
            closing_trades = [t for t in scalping_trades if t['entry_time'].hour >= 15]
            
            morning_pnl = sum(t['pnl'] for t in morning_trades) if morning_trades else 0
            afternoon_pnl = sum(t['pnl'] for t in afternoon_trades) if afternoon_trades else 0
            closing_pnl = sum(t['pnl'] for t in closing_trades) if closing_trades else 0
            
            morning_win_rate = sum(1 for t in morning_trades if t['pnl'] > 0) / len(morning_trades) * 100 if morning_trades else 0
            afternoon_win_rate = sum(1 for t in afternoon_trades if t['pnl'] > 0) / len(afternoon_trades) * 100 if afternoon_trades else 0
            closing_win_rate = sum(1 for t in closing_trades if t['pnl'] > 0) / len(closing_trades) * 100 if closing_trades else 0
            
            # Create time of day table
            tod_header = html.Thead(html.Tr([
                html.Th("Time of Day"),
                html.Th("Trades"),
                html.Th("Win Rate"),
                html.Th("P&L")
            ]))
            
            tod_rows = [
                html.Tr([
                    html.Td("Morning (9:00-12:00)"),
                    html.Td(len(morning_trades)),
                    html.Td(f"{morning_win_rate:.2f}%"),
                    html.Td(html.Span(f"₹{morning_pnl:.2f}", style={"color": "green" if morning_pnl >= 0 else "red"}))
                ]),
                html.Tr([
                    html.Td("Afternoon (12:00-15:00)"),
                    html.Td(len(afternoon_trades)),
                    html.Td(f"{afternoon_win_rate:.2f}%"),
                    html.Td(html.Span(f"₹{afternoon_pnl:.2f}", style={"color": "green" if afternoon_pnl >= 0 else "red"}))
                ]),
                html.Tr([
                    html.Td("Closing (15:00-15:30)"),
                    html.Td(len(closing_trades)),
                    html.Td(f"{closing_win_rate:.2f}%"),
                    html.Td(html.Span(f"₹{closing_pnl:.2f}", style={"color": "green" if closing_pnl >= 0 else "red"}))
                ])
            ]
            
            tod_body = html.Tbody(tod_rows)
            tod_table = dbc.Table([tod_header, tod_body], bordered=True, striped=True, hover=True, responsive=True)
            
            # Analyze duration performance
            short_trades = [t for t in scalping_trades if (t['exit_time'] - t['entry_time']).total_seconds() / 60 < 2]
            medium_trades = [t for t in scalping_trades if 2 <= (t['exit_time'] - t['entry_time']).total_seconds() / 60 < 5]
            long_trades = [t for t in scalping_trades if (t['exit_time'] - t['entry_time']).total_seconds() / 60 >= 5]
            
            short_pnl = sum(t['pnl'] for t in short_trades) if short_trades else 0
            medium_pnl = sum(t['pnl'] for t in medium_trades) if medium_trades else 0
            long_pnl = sum(t['pnl'] for t in long_trades) if long_trades else 0
            
            short_win_rate = sum(1 for t in short_trades if t['pnl'] > 0) / len(short_trades) * 100 if short_trades else 0
            medium_win_rate = sum(1 for t in medium_trades if t['pnl'] > 0) / len(medium_trades) * 100 if medium_trades else 0
            long_win_rate = sum(1 for t in long_trades if t['pnl'] > 0) / len(long_trades) * 100 if long_trades else 0
            
            # Create duration table
            dur_header = html.Thead(html.Tr([
                html.Th("Duration"),
                html.Th("Trades"),
                html.Th("Win Rate"),
                html.Th("P&L")
            ]))
            
            dur_rows = [
                html.Tr([
                    html.Td("Short (<2 mins)"),
                    html.Td(len(short_trades)),
                    html.Td(f"{short_win_rate:.2f}%"),
                    html.Td(html.Span(f"₹{short_pnl:.2f}", style={"color": "green" if short_pnl >= 0 else "red"}))
                ]),
                html.Tr([
                    html.Td("Medium (2-5 mins)"),
                    html.Td(len(medium_trades)),
                    html.Td(f"{medium_win_rate:.2f}%"),
                    html.Td(html.Span(f"₹{medium_pnl:.2f}", style={"color": "green" if medium_pnl >= 0 else "red"}))
                ]),
                html.Tr([
                    html.Td("Long (>5 mins)"),
                    html.Td(len(long_trades)),
                    html.Td(f"{long_win_rate:.2f}%"),
                    html.Td(html.Span(f"₹{long_pnl:.2f}", style={"color": "green" if long_pnl >= 0 else "red"}))
                ])
            ]
            
            dur_body = html.Tbody(dur_rows)
            dur_table = dbc.Table([dur_header, dur_body], bordered=True, striped=True, hover=True, responsive=True)
            
            return html.Div([
                html.H5("Scalping Performance by Time of Day"),
                tod_table,
                html.H5("Scalping Performance by Trade Duration", className="mt-4"),
                dur_table
            ])
            
        # Process NIFTY data
        # NIFTY price
        nifty_price = f"₹{last_ltp['NIFTY']['SPOT']:.2f}" if last_ltp['NIFTY']['SPOT'] is not None else "Loading..."
        outputs = [nifty_price]
        
        # NIFTY movement
        outputs.append(get_movement_html(movement_pct['NIFTY']))
        
        # NIFTY trend
        outputs.append(get_trend_html('NIFTY'))
        
        # NIFTY volatility
        outputs.append(f"{calculate_volatility('NIFTY'):.4f}%")
        
        # NIFTY range
        range_low, range_high = calculate_index_range('NIFTY')
        if range_low is not None and range_high is not None:
            nifty_range = f"₹{range_low:.2f} - ₹{range_high:.2f}"
        else:
            nifty_range = "Calculating..."
        outputs.append(nifty_range)
        
        # NIFTY PCR
        outputs.append(f"{calculate_pcr('NIFTY'):.2f}")
        
        # NIFTY expiry
        nifty_expiry = trading_state.expiry_dates['NIFTY'].strftime("%d-%b-%Y") if trading_state.expiry_dates['NIFTY'] else "Not set"
        outputs.append(nifty_expiry)
        
        # NIFTY P&L
        nifty_pnl = html.Span(f"₹{trading_state.index_pnl['NIFTY']:.2f}", 
                            style={"color": "green" if trading_state.index_pnl['NIFTY'] >= 0 else "red"})
        outputs.append(nifty_pnl)
        
        # NIFTY trades
        outputs.append(str(trading_state.index_trades['NIFTY']))
        
        # WebSocket status for NIFTY
        websocket_status = html.Span("CONNECTED", style={"color": "green", "font-weight": "bold"}) if websocket_connected else html.Span("DISCONNECTED", style={"color": "red", "font-weight": "bold"})
        outputs.append(websocket_status)
        
        # NIFTY CE info
        outputs.append(INSTRUMENTS["NIFTY"]["CE"]["symbol"])
        outputs.append(f"₹{last_ltp['NIFTY']['CE']:.2f}" if last_ltp['NIFTY']['CE'] is not None else "Loading...")
        outputs.append(get_signal_html('NIFTY', 'CE'))
        outputs.append(f"{prediction_signals['NIFTY']['CE']['signal']}")
        outputs.append(f"{prediction_signals['NIFTY']['CE']['strength']:.2f}")
        
        # NIFTY PE info
        outputs.append(INSTRUMENTS["NIFTY"]["PE"]["symbol"])
        outputs.append(f"₹{last_ltp['NIFTY']['PE']:.2f}" if last_ltp['NIFTY']['PE'] is not None else "Loading...")
        outputs.append(get_signal_html('NIFTY', 'PE'))
        outputs.append(f"{prediction_signals['NIFTY']['PE']['signal']}")
        outputs.append(f"{prediction_signals['NIFTY']['PE']['strength']:.2f}")
        
        # NIFTY active trades
        outputs.append(get_active_trades_html('NIFTY'))
        
        # NIFTY recent trades
        outputs.append(get_recent_trades_html('NIFTY'))
        
        # Process BANKNIFTY data
        # BANKNIFTY price
        banknifty_price = f"₹{last_ltp['BANKNIFTY']['SPOT']:.2f}" if last_ltp['BANKNIFTY']['SPOT'] is not None else "Loading..."
        outputs.append(banknifty_price)
        
        # BANKNIFTY movement and other outputs
        outputs.append(get_movement_html(movement_pct['BANKNIFTY']))
        outputs.append(get_trend_html('BANKNIFTY'))
        outputs.append(f"{calculate_volatility('BANKNIFTY'):.4f}%")
        
        # BANKNIFTY range
        range_low, range_high = calculate_index_range('BANKNIFTY')
        if range_low is not None and range_high is not None:
            banknifty_range = f"₹{range_low:.2f} - ₹{range_high:.2f}"
        else:
            banknifty_range = "Calculating..."
        outputs.append(banknifty_range)
        
        # Remaining BANKNIFTY outputs
        outputs.append(f"{calculate_pcr('BANKNIFTY'):.2f}")
        banknifty_expiry = trading_state.expiry_dates['BANKNIFTY'].strftime("%d-%b-%Y") if trading_state.expiry_dates['BANKNIFTY'] else "Not set"
        outputs.append(banknifty_expiry)
        outputs.append(html.Span(f"₹{trading_state.index_pnl['BANKNIFTY']:.2f}", style={"color": "green" if trading_state.index_pnl['BANKNIFTY'] >= 0 else "red"}))
        outputs.append(str(trading_state.index_trades['BANKNIFTY']))
        outputs.append(websocket_status)
        outputs.append(INSTRUMENTS["BANKNIFTY"]["CE"]["symbol"])
        outputs.append(f"₹{last_ltp['BANKNIFTY']['CE']:.2f}" if last_ltp['BANKNIFTY']['CE'] is not None else "Loading...")
        outputs.append(get_signal_html('BANKNIFTY', 'CE'))
        outputs.append(f"{prediction_signals['BANKNIFTY']['CE']['signal']}")
        outputs.append(f"{prediction_signals['BANKNIFTY']['CE']['strength']:.2f}")
        outputs.append(INSTRUMENTS["BANKNIFTY"]["PE"]["symbol"])
        outputs.append(f"₹{last_ltp['BANKNIFTY']['PE']:.2f}" if last_ltp['BANKNIFTY']['PE'] is not None else "Loading...")
        outputs.append(get_signal_html('BANKNIFTY', 'PE'))
        outputs.append(f"{prediction_signals['BANKNIFTY']['PE']['signal']}")
        outputs.append(f"{prediction_signals['BANKNIFTY']['PE']['strength']:.2f}")
        outputs.append(get_active_trades_html('BANKNIFTY'))
        outputs.append(get_recent_trades_html('BANKNIFTY'))
        
        # Process SENSEX data
        # SENSEX price and other outputs
        sensex_price = f"₹{last_ltp['SENSEX']['SPOT']:.2f}" if last_ltp['SENSEX']['SPOT'] is not None else "Loading..."
        outputs.append(sensex_price)
        outputs.append(get_movement_html(movement_pct['SENSEX']))
        outputs.append(get_trend_html('SENSEX'))
        outputs.append(f"{calculate_volatility('SENSEX'):.4f}%")
        
        # SENSEX range
        range_low, range_high = calculate_index_range('SENSEX')
        if range_low is not None and range_high is not None:
            sensex_range = f"₹{range_low:.2f} - ₹{range_high:.2f}"
        else:
            sensex_range = "Calculating..."
        outputs.append(sensex_range)
        
        # Remaining SENSEX outputs
        outputs.append(f"{calculate_pcr('SENSEX'):.2f}")
        sensex_expiry = trading_state.expiry_dates['SENSEX'].strftime("%d-%b-%Y") if trading_state.expiry_dates['SENSEX'] else "Not set"
        outputs.append(sensex_expiry)
        outputs.append(html.Span(f"₹{trading_state.index_pnl['SENSEX']:.2f}", style={"color": "green" if trading_state.index_pnl['SENSEX'] >= 0 else "red"}))
        outputs.append(str(trading_state.index_trades['SENSEX']))
        outputs.append(websocket_status)
        outputs.append(INSTRUMENTS["SENSEX"]["CE"]["symbol"])
        outputs.append(f"₹{last_ltp['SENSEX']['CE']:.2f}" if last_ltp['SENSEX']['CE'] is not None else "Loading...")
        outputs.append(get_signal_html('SENSEX', 'CE'))
        outputs.append(f"{prediction_signals['SENSEX']['CE']['signal']}")
        outputs.append(f"{prediction_signals['SENSEX']['CE']['strength']:.2f}")
        outputs.append(INSTRUMENTS["SENSEX"]["PE"]["symbol"])
        outputs.append(f"₹{last_ltp['SENSEX']['PE']:.2f}" if last_ltp['SENSEX']['PE'] is not None else "Loading...")
        outputs.append(get_signal_html('SENSEX', 'PE'))
        outputs.append(f"{prediction_signals['SENSEX']['PE']['signal']}")
        outputs.append(f"{prediction_signals['SENSEX']['PE']['strength']:.2f}")
        outputs.append(get_active_trades_html('SENSEX'))
        outputs.append(get_recent_trades_html('SENSEX'))
        
        # Overall performance data
        # Total P&L
        total_pnl = html.Span(f"₹{trading_state.total_pnl:.2f}", 
                            style={"color": "green" if trading_state.total_pnl >= 0 else "red"})
        outputs.append(total_pnl)
        
        # Daily P&L
        daily_pnl = html.Span(f"₹{trading_state.daily_pnl:.2f}", 
                            style={"color": "green" if trading_state.daily_pnl >= 0 else "red"})
        outputs.append(daily_pnl)
        
        # Win rate
        total_trades = trading_state.wins + trading_state.losses
        win_rate = f"{(trading_state.wins / total_trades * 100):.2f}%" if total_trades > 0 else "0.00%"
        outputs.append(win_rate)
        
        # Trades today
        outputs.append(f"{trading_state.trades_today} / {trading_state.MAX_TRADES_PER_DAY}")
        
        # Overall WebSocket status
        outputs.append(websocket_status)
        
        # Index-specific P&L
        outputs.append(html.Span(f"₹{trading_state.index_pnl['NIFTY']:.2f}", 
                            style={"color": "green" if trading_state.index_pnl['NIFTY'] >= 0 else "red"}))
        outputs.append(html.Span(f"₹{trading_state.index_pnl['BANKNIFTY']:.2f}", 
                            style={"color": "green" if trading_state.index_pnl['BANKNIFTY'] >= 0 else "red"}))
        outputs.append(html.Span(f"₹{trading_state.index_pnl['SENSEX']:.2f}", 
                            style={"color": "green" if trading_state.index_pnl['SENSEX'] >= 0 else "red"}))
        
        # Best performing index
        index_pnls = {
            'NIFTY': trading_state.index_pnl['NIFTY'],
            'BANKNIFTY': trading_state.index_pnl['BANKNIFTY'],
            'SENSEX': trading_state.index_pnl['SENSEX']
        }
        
        best_index = max(index_pnls, key=index_pnls.get) if any(index_pnls.values()) else "None"
        outputs.append(best_index)
        
        # Trade statistics
        outputs.append(str(total_trades))
        outputs.append(str(trading_state.index_trades['NIFTY']))
        outputs.append(str(trading_state.index_trades['BANKNIFTY']))
        outputs.append(str(trading_state.index_trades['SENSEX']))
        outputs.append(str(trading_state.regular_trades))
        
        # Regular trades P&L
        regular_pnl = html.Span(f"₹{trading_state.regular_pnl:.2f}", 
                            style={"color": "green" if trading_state.regular_pnl >= 0 else "red"})
        outputs.append(regular_pnl)
        
        # Regular win rate
        regular_total_trades = trading_state.regular_wins + trading_state.regular_losses
        regular_win_rate = f"{(trading_state.regular_wins / regular_total_trades * 100):.2f}%" if regular_total_trades > 0 else "0.00%"
        outputs.append(regular_win_rate)
        
        # Scalping mode - now shows which indices have it enabled
        enabled_indices = [idx for idx, settings in symbol_settings.items() if settings.get('scalping_enabled', True)]
        if enabled_indices:
            scalping_mode = html.Span(f"ENABLED for {', '.join(enabled_indices)}", style={"color": "green", "font-weight": "bold"})
        else:
            scalping_mode = html.Span("DISABLED for all indices", style={"color": "red", "font-weight": "bold"})
        outputs.append(scalping_mode)
        
        # Scalping P&L
        outputs.append(html.Span(f"₹{trading_state.scalping_pnl:.2f}", 
                            style={"color": "green" if trading_state.scalping_pnl >= 0 else "red"}))
        
        # Scalping win rate
        scalping_total_trades = trading_state.scalping_wins + trading_state.scalping_losses
        scalping_win_rate = f"{(trading_state.scalping_wins / scalping_total_trades * 100):.2f}%" if scalping_total_trades > 0 else "0.00%"
        outputs.append(scalping_win_rate)
        
        # Calculate average scalping trade duration
        scalping_trades = [trade for trade in trading_state.trades_history if trade['trade_type'] == 'scalping']
        if scalping_trades:
            avg_duration = sum((trade['exit_time'] - trade['entry_time']).total_seconds() / 60 for trade in scalping_trades) / len(scalping_trades)
            outputs.append(f"{avg_duration:.1f} mins")
        else:
            outputs.append("N/A")
        
        # Best scalping day
        if trading_state.scalping_performance_by_day:
            best_day = max(trading_state.scalping_performance_by_day.keys(), key=lambda k: trading_state.scalping_performance_by_day[k]['pnl'])
            best_day_data = trading_state.scalping_performance_by_day[best_day]
            outputs.append(f"{best_day} (₹{best_day_data['pnl']:.2f}, {best_day_data['win_rate']:.2f}% win rate)")
        else:
            outputs.append("No data yet")
        
        # Best expiry performance
        expiry_trades = {}
        for trade in trading_state.trades_history:
            if trade['expiry'] is None:
                continue
                
            expiry_key = trade['expiry'].strftime("%Y-%m-%d")
            if expiry_key not in expiry_trades:
                expiry_trades[expiry_key] = []
            expiry_trades[expiry_key].append(trade)
        
        if expiry_trades:
            expiry_pnls = {expiry: sum(trade['pnl'] for trade in trades) for expiry, trades in expiry_trades.items()}
            best_expiry = max(expiry_pnls.keys(), key=lambda k: expiry_pnls[k])
            best_expiry_pnl = expiry_pnls[best_expiry]
            outputs.append(f"{best_expiry} (₹{best_expiry_pnl:.2f})")
        else:
            outputs.append("No data yet")
        
        # All recent trades
        outputs.append(get_all_recent_trades_html())
        
        # Scalping analytics tab outputs
        outputs.append(get_daily_scalping_performance())
        outputs.append(get_expiry_day_performance())
        outputs.append(get_scalping_trade_analysis())
        
        return tuple(outputs)
    
    # Symbol update callback for refreshing ATM options
    @app.callback(
        [Output("atm-refresh-status", "children"),
         Output("current-atm-options", "children")],
        [Input("refresh-atm-button", "n_clicks"),
         Input("option-display-interval", "n_intervals")]
    )
    def update_atm_options(n_clicks, n_intervals):
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        # Only refresh ATM options when the button is clicked
        if triggered_id == "refresh-atm-button" and n_clicks:
            try:
                success = refresh_atm_options()
                if success:
                    status = html.Div("ATM options refreshed successfully", style={"color": "green"})
                else:
                    status = html.Div("Failed to refresh some ATM options", style={"color": "orange"})
            except Exception as e:
                status = html.Div(f"Error refreshing ATM options: {str(e)}", style={"color": "red"})
        else:
            # Just display current status without refreshing
            status = html.Div("")
        
        # Always show the current options
        options_display = []
        for index_name in INSTRUMENTS:
            index_card = dbc.Card([
                dbc.CardHeader(html.H5(f"{index_name} Options")),
                dbc.CardBody([
                    html.P(f"Spot Price: ₹{last_ltp[index_name]['SPOT']:.2f}" if last_ltp[index_name]['SPOT'] is not None else "Loading..."),
                    html.P([
                        "CE: ", 
                        html.Span(f"{INSTRUMENTS[index_name]['CE']['symbol']} (Strike: {INSTRUMENTS[index_name]['CE'].get('strike', 'N/A')})", 
                                style={"fontWeight": "bold"})
                    ]),
                    html.P([
                        "PE: ", 
                        html.Span(f"{INSTRUMENTS[index_name]['PE']['symbol']} (Strike: {INSTRUMENTS[index_name]['PE'].get('strike', 'N/A')})",
                                style={"fontWeight": "bold"})
                    ]),
                    html.P([
                        "Expiry: ", 
                        html.Span(f"{trading_state.expiry_dates[index_name].strftime('%d-%b-%Y')}" if trading_state.expiry_dates[index_name] else "Not set",
                                style={"fontWeight": "bold"})
                    ])
                ])
            ], className="mb-3")
            
            options_display.append(index_card)
        
        return status, options_display
    
    # Combined callback for scalping settings
    @app.callback(
        Output("scalping-settings-status", "children"),
        [
            Input("update-scalping-settings", "n_clicks")
        ],
        [
            State("scalping-target-slider", "value"),
            State("scalping-sl-slider", "value"),
            State("scalping-max-time-slider", "value"),
            State("momentum-weight-slider", "value"),
            State("pattern-weight-slider", "value"),
            State("expiry-weight-slider", "value"),
            State("standard-weight-slider", "value")
        ]
    )
    def update_all_scalping_settings(
        n_clicks, 
        target_pct, 
        sl_pct, 
        max_time,
        momentum_weight=25,
        pattern_weight=25,
        expiry_weight=25,
        standard_weight=25
    ):
        """Combined callback for updating all scalping settings."""
        if not n_clicks:
            return ""
            
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        # Update config settings
        config.scalping_target_pct = target_pct
        config.scalping_stop_loss_pct = sl_pct
        
        # Update the global SCALPING_MAX_HOLDING_TIME constant
        import trading.execution
        trading.execution.SCALPING_MAX_HOLDING_TIME = max_time
        
        # Store strategy weights if they were provided
        if all(weight is not None for weight in [momentum_weight, pattern_weight, expiry_weight, standard_weight]):
            config.momentum_strategy_weight = momentum_weight
            config.pattern_strategy_weight = pattern_weight
            config.expiry_strategy_weight = expiry_weight
            config.standard_strategy_weight = standard_weight
        
        # Save updated config to file
        config.save_to_file()
        
        # Build response message
        response_elements = [
            "Scalping settings updated successfully",
            html.Br(),
            f"Target: {target_pct:.1f}%, Stop Loss: {sl_pct:.1f}%, Max Time: {max_time} mins"
        ]
        
        # Add strategy weights info if they were provided
        if all(weight is not None for weight in [momentum_weight, pattern_weight, expiry_weight, standard_weight]):
            response_elements.extend([
                html.Br(),
                f"Strategy Weights: Momentum ({momentum_weight}%), Pattern ({pattern_weight}%), ",
                f"Expiry ({expiry_weight}%), Standard ({standard_weight}%)"
            ])
        
        return html.Div(response_elements, style={"color": "green"})