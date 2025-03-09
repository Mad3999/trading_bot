"""
Symbol-specific trading controls for the options trading dashboard.
This module provides UI components for controlling trading settings per symbol.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc

def create_symbol_controls(symbol):
    """Create control panel for a specific symbol."""
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                # Symbol name with button group
                dbc.Col([
                    html.H5(f"{symbol} Controls", className="d-inline-block mr-3"),
                ], width=3),
                
                # Trading toggle
                dbc.Col([
                    html.Div([
                        dbc.Label("Trading:", className="mr-2"),
                        dbc.Checklist(
                            options=[{"label": "Enabled", "value": 1}],
                            value=[1],
                            id=f"{symbol.lower()}-trading-toggle",
                            switch=True,
                            inline=True
                        )
                    ], className="d-flex align-items-center mb-0")
                ], width=2),
                
                # Scalping toggle
                dbc.Col([
                    html.Div([
                        dbc.Label("Scalping:", className="mr-2"),
                        dbc.Checklist(
                            options=[{"label": "Enabled", "value": 1}],
                            value=[1],
                            id=f"{symbol.lower()}-scalping-toggle",
                            switch=True,
                            inline=True
                        )
                    ], className="d-flex align-items-center mb-0")
                ], width=2),
                
                # Lot size control
                dbc.Col([
                    html.Div([
                        dbc.Label("Lot Size:", className="mr-2"),
                        dbc.Input(
                            type="number",
                            id=f"{symbol.lower()}-lot-size",
                            value=1,
                            min=1,
                            max=10,
                            step=1,
                            className="w-50"
                        )
                    ], className="d-flex align-items-center mb-0")
                ], width=3),
                
                # Save button
                dbc.Col([
                    dbc.Button(
                        "Apply", 
                        id=f"{symbol.lower()}-settings-apply", 
                        color="primary", 
                        size="sm",
                        className="ml-2"
                    ),
                    html.Span(id=f"{symbol.lower()}-settings-status", className="ml-2")
                ], width=2)
            ])
        ])
    ], className="mb-3")

def create_broker_status_indicator():
    """Create broker connection status indicator."""
    return dbc.Alert(
        [
            html.Span("Broker Connection: "),
            html.Span(id="broker-status-indicator", className="ml-2")
        ],
        color="light",
        className="d-flex justify-content-between align-items-center mb-2"
    )