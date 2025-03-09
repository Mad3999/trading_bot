"""
Enhanced Scalping Analytics Tab for the dashboard.
"""

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

def create_enhanced_scalping_tab():
    """Create an enhanced scalping analytics tab with detailed strategy breakdowns."""
    
    tab_content = [
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Daily Scalping Performance")),
                    dbc.CardBody(id="daily-scalping-performance")
                ], className="mb-4")
            ], width=12)
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Scalping Strategies Comparison")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("Momentum Scalping"),
                                    dbc.CardBody([
                                        html.P(["Trades: ", html.Span(id="momentum-scalp-trades")]),
                                        html.P(["Win Rate: ", html.Span(id="momentum-scalp-win-rate")]),
                                        html.P(["P&L: ", html.Span(id="momentum-scalp-pnl")]),
                                        html.P(["Avg Duration: ", html.Span(id="momentum-scalp-duration")])
                                    ])
                                ], className="h-100")
                            ], width=3),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("Pattern Scalping"),
                                    dbc.CardBody([
                                        html.P(["Trades: ", html.Span(id="pattern-scalp-trades")]),
                                        html.P(["Win Rate: ", html.Span(id="pattern-scalp-win-rate")]),
                                        html.P(["P&L: ", html.Span(id="pattern-scalp-pnl")]),
                                        html.P(["Avg Duration: ", html.Span(id="pattern-scalp-duration")])
                                    ])
                                ], className="h-100")
                            ], width=3),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("Expiry Scalping"),
                                    dbc.CardBody([
                                        html.P(["Trades: ", html.Span(id="expiry-scalp-trades")]),
                                        html.P(["Win Rate: ", html.Span(id="expiry-scalp-win-rate")]),
                                        html.P(["P&L: ", html.Span(id="expiry-scalp-pnl")]),
                                        html.P(["Avg Duration: ", html.Span(id="expiry-scalp-duration")])
                                    ])
                                ], className="h-100")
                            ], width=3),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("Standard Scalping"),
                                    dbc.CardBody([
                                        html.P(["Trades: ", html.Span(id="standard-scalp-trades")]),
                                        html.P(["Win Rate: ", html.Span(id="standard-scalp-win-rate")]),
                                        html.P(["P&L: ", html.Span(id="standard-scalp-pnl")]),
                                        html.P(["Avg Duration: ", html.Span(id="standard-scalp-duration")])
                                    ])
                                ], className="h-100")
                            ], width=3)
                        ]),
                        html.Div([
                            html.H5("Best Performing Strategy:", className="mt-3"),
                            html.P(id="best-scalping-strategy", className="font-weight-bold")
                        ], className="mt-3")
                    ])
                ], className="mb-4")
            ], width=12)
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Expiry Day Performance")),
                    dbc.CardBody(id="expiry-day-performance")
                ], className="mb-4")
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
                            value=0.5,  # Default value from config
                            marks={i/10: f'{i/10:.1f}%' for i in range(1, 11)},
                        ),
                        html.P("Stop Loss Percentage:"),
                        dcc.Slider(
                            id='scalping-sl-slider',
                            min=0.1,
                            max=1.0,
                            step=0.1,
                            value=0.3,  # Default value from config
                            marks={i/10: f'{i/10:.1f}%' for i in range(1, 11)},
                        ),
                        html.P("Maximum Holding Time (minutes):"),
                        dcc.Slider(
                            id='scalping-max-time-slider',
                            min=1,
                            max=10,
                            step=1,
                            value=5,  # Default value
                            marks={i: f'{i}' for i in range(1, 11)},
                        ),
                        
                        html.P("Strategy Weights:"),
                        html.Div([
                            html.P("Momentum Scalping:"),
                            dcc.Slider(
                                id='momentum-weight-slider',
                                min=0,
                                max=100,
                                step=10,
                                value=25,  # Default value
                                marks={i: f'{i}%' for i in range(0, 101, 10)},
                            ),
                        ]),
                        html.Div([
                            html.P("Pattern Scalping:"),
                            dcc.Slider(
                                id='pattern-weight-slider',
                                min=0,
                                max=100,
                                step=10,
                                value=25,  # Default value
                                marks={i: f'{i}%' for i in range(0, 101, 10)},
                            ),
                        ]),
                        html.Div([
                            html.P("Expiry Scalping:"),
                            dcc.Slider(
                                id='expiry-weight-slider',
                                min=0,
                                max=100,
                                step=10,
                                value=25,  # Default value
                                marks={i: f'{i}%' for i in range(0, 101, 10)},
                            ),
                        ]),
                        html.Div([
                            html.P("Standard Scalping:"),
                            dcc.Slider(
                                id='standard-weight-slider',
                                min=0,
                                max=100,
                                step=10,
                                value=25,  # Default value
                                marks={i: f'{i}%' for i in range(0, 101, 10)},
                            ),
                        ]),
                        
                        html.Div([
                            dbc.Button("Update Settings", id="update-scalping-settings", color="primary", className="mt-3")
                        ]),
                        html.Div(id="scalping-settings-status", className="mt-2")
                    ])
                ], className="mb-4")
            ], width=6)
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Scalping Trade Analysis")),
                    dbc.CardBody(id="scalping-trade-analysis")
                ], className="mb-4")
            ], width=12)
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Pattern Recognition Analysis")),
                    dbc.CardBody(id="pattern-recognition-analysis")
                ], className="mb-4")
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("Momentum Analysis")),
                    dbc.CardBody(id="momentum-analysis")
                ], className="mb-4")
            ], width=6)
        ])
    ]
    
    return tab_content