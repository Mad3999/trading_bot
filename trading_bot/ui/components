"""
Reusable UI components for the options trading dashboard.
"""

import dash_bootstrap_components as dbc
from dash import html
import plotly.graph_objs as go
import pandas as pd

def create_info_card(title, value, color=None, additional_info=None):
    """
    Create a simple info card with a title and value.
    
    Args:
        title (str): Card title
        value (str or dash component): Main value to display
        color (str, optional): Color for the value text
        additional_info (str or dash component, optional): Additional information to display
        
    Returns:
        dbc.Card: A Bootstrap card component
    """
    card_body = [html.H5(title, className="card-title"), html.H3(value, style={"color": color} if color else {})]
    
    if additional_info:
        card_body.append(html.P(additional_info, className="text-muted mt-2"))
    
    return dbc.Card(dbc.CardBody(card_body), className="mb-4")

def create_trade_card(trade, show_index=False):
    """
    Create a card displaying trade information.
    
    Args:
        trade (dict): Trade information
        show_index (bool): Whether to show the index name in the header
        
    Returns:
        dbc.Card: A Bootstrap card component
    """
    pnl_style = {"color": "green" if trade['pnl'] >= 0 else "red"}
    
    trade_duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 60
    
    if show_index:
        header_text = f"{trade['index']} {trade['option_type']} {trade['trade_type'].upper()} Trade: {trade['exit_time'].strftime('%H:%M:%S')}"
    else:
        header_text = f"{trade['option_type']} {trade['trade_type'].upper()} Trade: {trade['exit_time'].strftime('%H:%M:%S')}"
    
    return dbc.Card([
        dbc.CardHeader(header_text),
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

def create_active_trade_card(trade_info):
    """
    Create a card displaying active trade information.
    
    Args:
        trade_info (dict): Active trade information
        
    Returns:
        dbc.Card: A Bootstrap card component
    """
    return dbc.Card([
        dbc.CardHeader(f"{trade_info['option_type']} {trade_info['trade_type'].upper()} Trade: {trade_info['symbol']}"),
        dbc.CardBody([
            html.P(f"Entry Price: ₹{trade_info['entry_price']:.2f} | Current: ₹{trade_info['current_price']:.2f}"),
            html.P(f"Quantity: {trade_info['quantity']}"),
            html.P([
                "Current P&L: ",
                html.Span(f"₹{trade_info['current_pnl']:.2f} ({trade_info['current_pnl_pct']:.2f}%)", 
                         style={"color": "green" if trade_info['current_pnl'] >= 0 else "red"})
            ]),
            html.P(f"Stop Loss: ₹{trade_info['stop_loss']:.2f}"),
            html.P(f"Target: ₹{trade_info['target']:.2f}"),
            html.P(f"Time Held: {trade_info['time_held']:.1f} mins"),
        ])
    ], className="mb-3")