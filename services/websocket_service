"""
WebSocket connection and handlers for the options trading dashboard.
"""

import logging
import threading
import time
import json

from config import Config
from models.instruments import INSTRUMENTS
from services.price_service import update_index_price, update_option_price

logger = logging.getLogger(__name__)

# Global WebSocket variables
websocket = None
websocket_connected = False

def initialize_websocket():
    """Initialize the WebSocket connection to Angel Broking."""
    global websocket, websocket_connected
    config = Config()
    
    try:
        # In a real implementation, this would connect to the actual WebSocket
        # For this demo, we'll use a mock WebSocket
        class MockWebSocket:
            def __init__(self):
                self.on_open = None
                self.on_data = None
                self.on_error = None
                self.on_close = None
                self.connected = False
            
            def connect(self):
                logger.info("Mock WebSocket connected")
                self.connected = True
                if self.on_open:
                    self.on_open()
                return True
            
            def close_connection(self):
                logger.info("Mock WebSocket disconnected")
                self.connected = False
                if self.on_close:
                    self.on_close()
                return True
                
            def heartbeat(self):
                logger.debug("Mock WebSocket heartbeat sent")
                return True
                
            def subscribe(self, mode, subscription_payload):
                logger.info(f"Mock WebSocket subscribed with mode {mode} to {len(subscription_payload)} channels")
                return True
                
            def simulate_data(self, data):
                """Simulate receiving data from WebSocket"""
                if self.on_data:
                    self.on_data(data)
        
        # Close existing WebSocket if any
        if websocket:
            try:
                websocket.close_connection()
            except:
                pass
        
        # Create a new WebSocket instance
        websocket = MockWebSocket()
        
        # Set callbacks
        websocket.on_open = on_websocket_open
        websocket.on_data = on_websocket_data
        websocket.on_error = on_websocket_error
        websocket.on_close = on_websocket_close
        
        # Attempt to connect
        websocket.connect()
        
        # Start heartbeat thread and data simulation thread for demo
        threading.Thread(target=websocket_heartbeat, daemon=True).start()
        threading.Thread(target=simulate_market_data, daemon=True).start()
        
        return True
    except Exception as e:
        logger.error(f"Error initializing WebSocket: {e}")
        websocket_connected = False
        return False

def on_websocket_open():
    """Callback when WebSocket connection is established."""
    global websocket_connected
    
    logger.info("WebSocket connection established")
    websocket_connected = True
    
    # Subscribe to market data
    subscribe_to_market_data()

def on_websocket_data(data):
    """Callback when data is received from WebSocket."""
    try:
        # Parse the data
        if isinstance(data, str):
            data = json.loads(data)
        
        # Process LTP data
        if data.get('type') == 'sf' and 'tk' in data:
            token = data.get('tk')
            ltp = float(data.get('lp', 0))  # LTP (Last Traded Price)
            
            # Update based on token for NIFTY
            if token == INSTRUMENTS["NIFTY"]["SPOT"]["token"]:
                update_index_price("NIFTY", ltp)
            elif token == INSTRUMENTS["NIFTY"]["CE"]["token"]:
                update_option_price("NIFTY", "CE", ltp)
            elif token == INSTRUMENTS["NIFTY"]["PE"]["token"]:
                update_option_price("NIFTY", "PE", ltp)
            
            # Update based on token for BANKNIFTY
            elif token == INSTRUMENTS["BANKNIFTY"]["SPOT"]["token"]:
                update_index_price("BANKNIFTY", ltp)
            elif token == INSTRUMENTS["BANKNIFTY"]["CE"]["token"]:
                update_option_price("BANKNIFTY", "CE", ltp)
            elif token == INSTRUMENTS["BANKNIFTY"]["PE"]["token"]:
                update_option_price("BANKNIFTY", "PE", ltp)
            
            # Update based on token for SENSEX
            elif token == INSTRUMENTS["SENSEX"]["SPOT"]["token"]:
                update_index_price("SENSEX", ltp)
            elif token == INSTRUMENTS["SENSEX"]["CE"]["token"]:
                update_option_price("SENSEX", "CE", ltp)
            elif token == INSTRUMENTS["SENSEX"]["PE"]["token"]:
                update_option_price("SENSEX", "PE", ltp)
    except Exception as e:
        logger.error(f"Error processing WebSocket data: {e}")

def on_websocket_error(error):
    """Callback when WebSocket error occurs."""
    global websocket_connected
    
    logger.error(f"WebSocket error: {error}")
    websocket_connected = False
    
    # Schedule reconnection
    config = Config()
    threading.Timer(config.ws_reconnect_interval, initialize_websocket).start()

def on_websocket_close():
    """Callback when WebSocket connection is closed."""
    global websocket_connected
    
    logger.info("WebSocket connection closed")
    websocket_connected = False
    
    # Schedule reconnection
    config = Config()
    threading.Timer(config.ws_reconnect_interval, initialize_websocket).start()

def websocket_heartbeat():
    """Send heartbeat messages to keep the WebSocket connection alive."""
    global websocket, websocket_connected
    config = Config()
    
    while True:
        time.sleep(config.ws_heartbeat_interval)
        
        if websocket and websocket_connected:
            try:
                websocket.heartbeat()
                logger.debug("WebSocket heartbeat sent")
            except Exception as e:
                logger.error(f"Error sending WebSocket heartbeat: {e}")
                websocket_connected = False
                # Try to reconnect
                initialize_websocket()
        elif websocket:
            # Try to reconnect if broker is connected but WebSocket is not
            from services.api_service import broker_connected
            if broker_connected:
                initialize_websocket()

def subscribe_to_market_data():
    """Subscribe to market data for all indices and options."""
    global websocket, websocket_connected
    
    if not websocket or not websocket_connected:
        logger.error("Cannot subscribe to market data: WebSocket not connected")
        return False
    
    try:
        # Create subscription payload for all tokens
        subscription_payload = []
        
        # Add all indices and their options
        for index_name in INSTRUMENTS:
            # Add spot
            subscription_payload.append({
                "exchangeType": INSTRUMENTS[index_name]["SPOT"]["exchange"],
                "tokens": [INSTRUMENTS[index_name]["SPOT"]["token"]]
            })
            
            # Add CE option
            subscription_payload.append({
                "exchangeType": INSTRUMENTS[index_name]["CE"]["exchange"],
                "tokens": [INSTRUMENTS[index_name]["CE"]["token"]]
            })
            
            # Add PE option
            subscription_payload.append({
                "exchangeType": INSTRUMENTS[index_name]["PE"]["exchange"],
                "tokens": [INSTRUMENTS[index_name]["PE"]["token"]]
            })
        
        # Subscribe to LTP data (mode 1 = LTP)
        websocket.subscribe(1, subscription_payload)
        
        logger.info("Subscribed to market data successfully")
        return True
    except Exception as e:
        logger.error(f"Error subscribing to market data: {e}")
        return False

def simulate_market_data():
    """
    Simulate market data for demo purposes.
    In a real implementation, this would not be needed as data would come from the WebSocket.
    """
    global websocket, websocket_connected
    import random
    import time
    
    if not websocket:
        return
    
    # Initial prices
    prices = {
        "NIFTY": 22354.5,
        "BANKNIFTY": 47103.75,
        "SENSEX": 74512.3,
        "NIFTY_CE": 152.35,
        "NIFTY_PE": 128.65,
        "BANKNIFTY_CE": 185.75,
        "BANKNIFTY_PE": 162.25,
        "SENSEX_CE": 247.85,
        "SENSEX_PE": 213.45
    }
    
    while True:
        if websocket_connected:
            try:
                # Simulate price fluctuations
                for key in prices:
                    # Random price change within ±0.1%
                    price_change_pct = (random.random() - 0.5) * 0.002  # -0.1% to +0.1%
                    prices[key] *= (1 + price_change_pct)
                
                # Simulate NIFTY SPOT data
                websocket.simulate_data({
                    'type': 'sf',
                    'tk': INSTRUMENTS["NIFTY"]["SPOT"]["token"],
                    'lp': prices["NIFTY"]
                })
                
                # Simulate NIFTY CE data
                websocket.simulate_data({
                    'type': 'sf',
                    'tk': INSTRUMENTS["NIFTY"]["CE"]["token"],
                    'lp': prices["NIFTY_CE"]
                })
                
                # Simulate NIFTY PE data
                websocket.simulate_data({
                    'type': 'sf',
                    'tk': INSTRUMENTS["NIFTY"]["PE"]["token"],
                    'lp': prices["NIFTY_PE"]
                })
                
                # Simulate BANKNIFTY SPOT data
                websocket.simulate_data({
                    'type': 'sf',
                    'tk': INSTRUMENTS["BANKNIFTY"]["SPOT"]["token"],
                    'lp': prices["BANKNIFTY"]
                })
                
                # Simulate SENSEX SPOT data
                websocket.simulate_data({
                    'type': 'sf',
                    'tk': INSTRUMENTS["SENSEX"]["SPOT"]["token"],
                    'lp': prices["SENSEX"]
                })
            except Exception as e:
                logger.error(f"Error simulating market data: {e}")
        
        # Sleep for a short time before next update
        time.sleep(2)