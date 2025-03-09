"""
Main dashboard layout for the options trading dashboard.
With added symbol-specific controls, broker status indicator, and improved performance.
"""

import dash
from dash import dcc, html, callback
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
from dash.dependencies import Input, Output, State, ALL, MATCH
from dash.exceptions import PreventUpdate
import pandas as pd
from datetime import datetime

from config import Config

# Initialize Dash app
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP], 
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

# Helper functions for chart generation
def create_performance_chart(data):
    """
    Create a performance comparison chart.
    
    Parameters:
    -----------
    data : dict
        Dictionary containing symbol names as keys and performance values as values
    
    Returns:
    --------
    plotly.graph_objs._figure.Figure
        A plotly figure object
    """
    df = pd.DataFrame({
        'Symbol': list(data.keys()),
        'P&L': list(data.values())
    })
    
    # Sort by P&L
    df = df.sort_values('P&L', ascending=False)
    
    # Create colors based on positive/negative values
    df['Color'] = df['P&L'].apply(lambda x: 'green' if x >= 0 else 'red')
    
    fig = px.bar(
        df, 
        x='Symbol', 
        y='P&L',
        color='Color',
        color_discrete_map={'green': '#28a745', 'red': '#dc3545'},
        labels={'P&L': 'Profit/Loss'},
        title='Index Performance Comparison'
    )
    
    fig.update_layout(
        xaxis_title="",
        yaxis_title="P&L (₹)",
        showlegend=False,
        margin=dict(l=40, r=40, t=40, b=20),
        height=300
    )
    
    return fig

def create_scalping_performance_chart(data):
    """
    Create a chart showing daily scalping performance.
    
    Parameters:
    -----------
    data : pandas.DataFrame
        DataFrame containing date and P&L information
    
    Returns:
    --------
    plotly.graph_objs._figure.Figure
        A plotly figure object
    """
    fig = px.line(
        data,
        x='Date',
        y='P&L',
        markers=True,
        labels={'P&L': 'Profit/Loss'},
        title='Daily Scalping Performance'
    )
    
    # Add a horizontal line at y=0
    fig.add_shape(
        type='line',
        x0=data['Date'].min(),
        y0=0,
        x1=data['Date'].max(),
        y1=0,
        line=dict(color='gray', width=1, dash='dash')
    )
    
    # Customize appearance
    fig.update_layout(
        xaxis_title="",
        yaxis_title="P&L (₹)",
        margin=dict(l=40, r=40, t=40, b=20),
        height=300
    )
    
    # Color code points based on positive/negative values
    fig.update_traces(
        marker=dict(
            size=8,
            color=data['P&L'].apply(lambda x: '#28a745' if x >= 0 else '#dc3545').tolist(),
            line=dict(width=1, color='#000000')
        )
    )
    
    return fig

def create_symbol_controls(symbol):
    """
    Create control panel for a specific symbol.
    
    Parameters:
    -----------
    symbol : str
        The trading symbol name (e.g., 'NIFTY', 'BANKNIFTY')
    
    Returns:
    --------
    dbc.Card
        A Card component containing controls for the specified symbol
    """
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                # Symbol name with button group
                dbc.Col([
                    html.H5(f"{symbol} Controls", className="d-inline-block mr-3"),
                ], width={"size": 3, "order": 1}),
                
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
                ], width={"size": 2, "order": 2}),
                
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
                ], width={"size": 2, "order": 3}),
                
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
                ], width={"size": 3, "order": 4}),
                
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
                ], width={"size": 2, "order": 5})
            ])
        ])
    ], className="mb-3 shadow-sm")

def create_header_bar():
    """
    Create the header bar with broker status and dark mode toggle.
    
    Returns:
    --------
    dbc.Row
        A row component containing the header elements
    """
    return dbc.Row([
        dbc.Col([
            html.H1("Multi-Index Options Trading Dashboard", className="text-center mb-2")
        ], width={"size": 8, "offset": 2}),
        
        dbc.Col([
            html.Div([
                html.Span("Dark Mode: ", className="mr-2"),
                dbc.Checklist(
                    options=[{"label": "", "value": 1}],
                    value=[],
                    id="dark-mode-toggle",
                    switch=True,
                    inline=True
                )
            ], className="d-flex align-items-center justify-content-end")
        ], width=2),
        
        dbc.Col([
            dbc.Alert(
                [
                    html.Span("Broker Connection: "),
                    html.Span(id="broker-status-indicator", className="ml-2"),
                    html.Span(id="last-update-time", className="float-right text-muted small")
                ],
                color="light",
                className="d-flex justify-content-between align-items-center mt-2 shadow-sm"
            )
        ], width=12)
    ])

def create_index_info_card(symbol):
    """
    Create a card displaying index information.
    
    Parameters:
    -----------
    symbol : str
        The trading symbol name (e.g., 'NIFTY', 'BANKNIFTY')
    
    Returns:
    --------
    dbc.Card
        A Card component containing index information
    """
    symbol_lower = symbol.lower()
    
    return dbc.Card([
        dbc.CardHeader(html.H4(symbol)),
        dbc.CardBody([
            html.H2(id=f"{symbol_lower}-price", className="text-primary"),
            html.P(id=f"{symbol_lower}-movement"),
            html.P(id=f"{symbol_lower}-trend"),
            html.Div([
                html.P(["Volatility: ", html.Span(id=f"{symbol_lower}-volatility")]),
                html.P(["Predicted Range: ", html.Span(id=f"{symbol_lower}-range")]),
                html.P(["PCR: ", html.Span(id=f"{symbol_lower}-pcr")]),
                html.P(["Expiry: ", html.Span(id=f"{symbol_lower}-expiry")])
            ], className="mt-3")
        ])
    ], className="mb-4 h-100 shadow-sm")

def create_performance_card(symbol):
    """
    Create a card displaying performance information.
    
    Parameters:
    -----------
    symbol : str
        The trading symbol name (e.g., 'NIFTY', 'BANKNIFTY')
    
    Returns:
    --------
    dbc.Card
        A Card component containing performance information
    """
    symbol_lower = symbol.lower()
    
    return dbc.Card([
        dbc.CardHeader(html.H4(f"{symbol} Performance")),
        dbc.CardBody([
            html.H5("P&L"),
            html.P([f"{symbol} P&L: ", html.Span(id=f"{symbol_lower}-pnl")]),
            html.P([f"{symbol} Trades: ", html.Span(id=f"{symbol_lower}-trades")]),
            html.P(["WebSocket: ", html.Span(id=f"websocket-status-{symbol_lower}", className="text-muted")])
        ])
    ], className="mb-4 h-100 shadow-sm")

def create_option_card(symbol, option_type):
    """
    Create a card displaying option information.
    
    Parameters:
    -----------
    symbol : str
        The trading symbol name (e.g., 'NIFTY', 'BANKNIFTY')
    option_type : str
        The option type ('CE' or 'PE')
    
    Returns:
    --------
    dbc.Card
        A Card component containing option information
    """
    symbol_lower = symbol.lower()
    
    return dbc.Card([
        dbc.CardHeader(html.H4(f"{symbol} {option_type} Option")),
        dbc.CardBody([
            html.H5(id=f"{symbol_lower}-{option_type.lower()}-symbol"),
            html.P(id=f"{symbol_lower}-{option_type.lower()}-price"),
            html.P(id=f"{symbol_lower}-{option_type.lower()}-signal"),
            html.Div([
                html.P(["Signal Value: ", html.Span(id=f"{symbol_lower}-{option_type.lower()}-signal-value")]),
                html.P(["Strength Value: ", html.Span(id=f"{symbol_lower}-{option_type.lower()}-strength-value")])
            ])
        ])
    ], className="mb-4 h-100 shadow-sm")

def create_trades_card(symbol, trade_type):
    """
    Create a card displaying trade information.
    
    Parameters:
    -----------
    symbol : str
        The trading symbol name (e.g., 'NIFTY', 'BANKNIFTY')
    trade_type : str
        The trade type ('active' or 'recent')
    
    Returns:
    --------
    dbc.Card
        A Card component containing trade information
    """
    symbol_lower = symbol.lower()
    title = f"{symbol} {trade_type.capitalize()} Trades"
    
    return dbc.Card([
        dbc.CardHeader(html.H4(title)),
        dbc.CardBody([
            html.Div(id=f"{symbol_lower}-{trade_type}-trades-container", className="table-responsive")
        ])
    ], className="mb-4 h-100 shadow-sm")

def create_symbol_tab(symbol):
    """
    Create a complete tab for a symbol.
    
    Parameters:
    -----------
    symbol : str
        The trading symbol name (e.g., 'NIFTY', 'BANKNIFTY')
    
    Returns:
    --------
    dcc.Tab
        A Tab component containing all content for the symbol
    """
    return dcc.Tab(
        label=symbol, 
        children=[
            dbc.Row([
                dbc.Col([
                    create_symbol_controls(symbol),
                ], width=12, className="mb-2")
            ]),
            
            dbc.Row([
                dbc.Col([
                    create_index_info_card(symbol),
                ], width=6, className="mb-3"),
                
                dbc.Col([
                    create_performance_card(symbol),
                ], width=6, className="mb-3")
            ]),
            
            dbc.Row([
                dbc.Col([
                    create_option_card(symbol, "CE"),
                ], width=6, className="mb-3"),
                
                dbc.Col([
                    create_option_card(symbol, "PE"),
                ], width=6, className="mb-3")
            ]),
            
            dbc.Row([
                dbc.Col([
                    create_trades_card(symbol, "active"),
                ], width=6, className="mb-3"),
                
                dbc.Col([
                    create_trades_card(symbol, "recent"),
                ], width=6, className="mb-3")
            ]),
        ],
        className="p-3"
    )

def create_overall_performance_tab():
    """
    Create the overall performance tab.
    
    Returns:
    --------
    dcc.Tab
        A Tab component for overall performance
    """
    return dcc.Tab(
        label="Overall Performance", 
        children=[
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Overall Performance")),
                        dbc.CardBody([
                            html.H5("P&L", className="mb-3"),
                            html.Div([
                                html.P(["Total: ", html.Span(id="total-pnl", className="font-weight-bold")]),
                                html.P(["Today: ", html.Span(id="daily-pnl")]),
                                html.P(["Win Rate: ", html.Span(id="win-rate")]),
                                html.P(["Trades Today: ", html.Span(id="trades-today", className="text-muted")]),
                                html.P(["WebSocket: ", html.Span(id="websocket-status", className="text-muted")])
                            ])
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Index Performance Comparison")),
                        dbc.CardBody([
                            html.Div(id="performance-chart", className="mb-3"),
                            html.Div([
                                html.P(["NIFTY P&L: ", html.Span(id="overall-nifty-pnl")]),
                                html.P(["BANKNIFTY P&L: ", html.Span(id="overall-banknifty-pnl")]),
                                html.P(["SENSEX P&L: ", html.Span(id="overall-sensex-pnl")]),
                                html.P(["Best Performing Index: ", html.Span(id="best-index", className="font-weight-bold")])
                            ])
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=6)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Trade Statistics")),
                        dbc.CardBody([
                            html.Div([
                                html.P(["Total Trades: ", html.Span(id="total-trades")]),
                                html.P(["NIFTY Trades: ", html.Span(id="overall-nifty-trades")]),
                                html.P(["BANKNIFTY Trades: ", html.Span(id="overall-banknifty-trades")]),
                                html.P(["SENSEX Trades: ", html.Span(id="overall-sensex-trades")]),
                                html.P(["Regular Trades: ", html.Span(id="regular-trades")]),
                                html.P(["Regular Trades P&L: ", html.Span(id="regular-trades-pnl")]),
                                html.P(["Regular Win Rate: ", html.Span(id="regular-win-rate")])
                            ])
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Scalping Performance")),
                        dbc.CardBody([
                            html.Div([
                                html.P(["Global Scalping Mode: ", html.Span(id="scalping-mode")]),
                                html.P(["Scalping P&L: ", html.Span(id="scalping-pnl")]),
                                html.P(["Scalping Win Rate: ", html.Span(id="scalping-win-rate")]),
                                html.P(["Avg. Scalping Trade Duration: ", html.Span(id="scalping-avg-duration")]),
                                html.P(["Best Scalping Day: ", html.Span(id="best-scalping-day")]),
                                html.P(["Best Expiry Performance: ", html.Span(id="best-expiry-performance")])
                            ])
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=6)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Recent Trades Across All Indices")),
                        dbc.CardBody([
                            html.Div(id="all-recent-trades-container", className="table-responsive")
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=12)
            ])
        ],
        className="p-3"
    )

def create_scalping_analytics_tab(config=None):
    """
    Create the scalping analytics tab.
    
    Parameters:
    -----------
    config : Config, optional
        The application configuration object. If None, will use default values.
        
    Returns:
    --------
    dcc.Tab
        A Tab component for scalping analytics
    """
    return dcc.Tab(
        label="Scalping Analytics", 
        children=[
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Daily Scalping Performance")),
                        dbc.CardBody([
                            html.Div(id="daily-scalping-chart", className="mb-3"),
                            html.Div(id="daily-scalping-performance", className="table-responsive")
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=12)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Expiry Day Performance")),
                        dbc.CardBody([
                            html.Div(id="expiry-day-chart", className="mb-3"),
                            html.Div(id="expiry-day-performance", className="table-responsive")
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Scalping Strategy Settings")),
                        dbc.CardBody([
                            html.P("Target Percentage:"),
                            dcc.Slider(
                                id='scalping-target-slider',
                                min=0.1,
                                max=1.0,
                                step=0.1,
                                value=getattr(config, 'scalping_target_pct', None) if config else 0.5,
                                marks={i/10: f'{i/10:.1f}%' for i in range(1, 11)},
                            ),
                            html.P("Stop Loss Percentage:", className="mt-4"),
                            dcc.Slider(
                                id='scalping-sl-slider',
                                min=0.1,
                                max=1.0,
                                step=0.1,
                                value=getattr(config, 'scalping_stop_loss_pct', None) if config else 0.3,
                                marks={i/10: f'{i/10:.1f}%' for i in range(1, 11)},
                            ),
                            html.P("Maximum Holding Time (minutes):", className="mt-4"),
                            dcc.Slider(
                                id='scalping-max-time-slider',
                                min=1,
                                max=10,
                                step=1,
                                value=getattr(config, 'max_scalping_time_minutes', None) if config else 5,
                                marks={i: f'{i}' for i in range(1, 11)},
                            ),
                            html.Div([
                                dbc.Button("Update Settings", id="update-scalping-settings", color="primary", className="mt-4")
                            ]),
                            html.Div(id="scalping-settings-status", className="mt-2 text-success")
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=6)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Scalping Trade Analysis")),
                        dbc.CardBody([
                            html.Div(id="scalping-trade-analysis", className="table-responsive")
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=12)
            ])
        ],
        className="p-3"
    )

# Option Configuration Tab
def create_option_configuration_tab():
    """
    Create the option configuration tab.
    
    Returns:
    --------
    dcc.Tab
        A Tab component for option configuration
    """
    return dcc.Tab(
        label="Option Configuration", 
        children=[
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Option Configuration")),
                        dbc.CardBody([
                            html.P("Automatically fetch and update ATM options for all indices"),
                            dbc.Button("Refresh ATM Options", id="refresh-atm-button", color="primary", className="mr-2"),
                            html.Div(id="atm-refresh-status", className="mt-2"),
                            html.Div([
                                html.H5("Current ATM Options", className="mt-3"),
                                html.Div(id="current-atm-options", className="table-responsive")
                            ], className="mt-3")
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=12)
            ]),
            
            # Add strategy parameters
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Strategy Parameters")),
                        dbc.CardBody([
                            html.P("Momentum Weight:"),
                            dcc.Slider(
                                id='momentum-weight-slider',
                                min=0.1,
                                max=1.0,
                                step=0.1,
                                value=0.5,
                                marks={i/10: f'{i/10:.1f}' for i in range(1, 11)},
                            ),
                            html.P("Volatility Weight:", className="mt-4"),
                            dcc.Slider(
                                id='volatility-weight-slider',
                                min=0.1,
                                max=1.0,
                                step=0.1,
                                value=0.3,
                                marks={i/10: f'{i/10:.1f}' for i in range(1, 11)},
                            ),
                            html.P("Signal Threshold:", className="mt-4"),
                            dcc.Slider(
                                id='signal-threshold-slider',
                                min=0.1,
                                max=1.0,
                                step=0.1,
                                value=0.7,
                                marks={i/10: f'{i/10:.1f}' for i in range(1, 11)},
                            ),
                            html.P("Pattern Weight:", className="mt-4"),
                            dcc.Slider(
                                id='pattern-weight-slider',
                                min=0.1,
                                max=1.0,
                                step=0.1,
                                value=0.4,
                                marks={i/10: f'{i/10:.1f}' for i in range(1, 11)},
                            ),
                            html.P("Expiry Weight:", className="mt-4"),
                            dcc.Slider(
                                id='expiry-weight-slider',
                                min=0.1,
                                max=1.0,
                                step=0.1,
                                value=0.6,
                                marks={i/10: f'{i/10:.1f}' for i in range(1, 11)},
                            ),
                            html.P("Standard Weight:", className="mt-4"),
                            dcc.Slider(
                                id='standard-weight-slider',
                                min=0.1,
                                max=1.0,
                                step=0.1,
                                value=0.5,
                                marks={i/10: f'{i/10:.1f}' for i in range(1, 11)},
                            ),
                            html.Div([
                                dbc.Button("Update Strategy Parameters", id="update-strategy-params", color="primary", className="mt-4")
                            ]),
                            html.Div(id="strategy-params-status", className="mt-2 text-success")
                        ])
                    ], className="mb-4 shadow-sm")
                ], width=12)
            ])
        ],
        className="p-3"
    )

def initialize_dashboard(config=None):
    """
    Initialize the dashboard layout.
    
    Parameters:
    -----------
    config : Config, optional
        The application configuration object. If None, will use default values.
        
    Returns:
    --------
    dash.Dash
        The initialized Dash app with all components
    """
    # If config is not provided, use default values
    if config is None:
        from config import Config
        config = Config()
    # Set the app layout
    app.layout = dbc.Container([
        create_header_bar(),
        
        html.Hr(),
        
        dcc.Tabs([
            create_symbol_tab("NIFTY"),
            create_symbol_tab("BANKNIFTY"),
            create_symbol_tab("SENSEX"),
            create_overall_performance_tab(),
            create_scalping_analytics_tab(config),
            create_option_configuration_tab()
        ]),
        
        # Intervals - moved from inline to config-based values
        dcc.Interval(
            id='interval-component',
            interval=getattr(config, 'ui_refresh_interval_ms', None) if config else 5000,  # in milliseconds
            n_intervals=0
        ),
        
        dcc.Interval(
            id='option-display-interval',
            interval=getattr(config, 'option_refresh_interval_ms', None) if config else 10000,  # in milliseconds
            n_intervals=0
        ),

        # Store components to track per-symbol settings
        dcc.Store(id='symbol-settings', data={
            'NIFTY': {'trading_enabled': True, 'scalping_enabled': True, 'lot_size': 1},
            'BANKNIFTY': {'trading_enabled': True, 'scalping_enabled': True, 'lot_size': 1},
            'SENSEX': {'trading_enabled': True, 'scalping_enabled': True, 'lot_size': 1}
        }),
        
        # Store for theme preference
        dcc.Store(id='theme-store', data={'dark_mode': False})
    ],
    fluid=True,
    className="p-4 dashboard-light"
    )
    
    return app