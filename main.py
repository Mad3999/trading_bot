"""
Main entry point that runs the options trading dashboard application.
"""

import logging
import threading
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), 
              logging.FileHandler("trading_log.txt")]
)
logger = logging.getLogger(__name__)

from services.api_service import initialize_smart_api, verify_session, session_monitor
from services.websocket_service import initialize_websocket
from trading.strategy import refresh_atm_options
from ui.dashboard import initialize_dashboard
from ui.callbacks import register_callbacks

def main():
    """Main function to start the trading system."""
    logger.info("Starting options trading dashboard")
    
    # Initialize Smart API
    if not initialize_smart_api():
        logger.error("Failed to initialize Smart API. Continuing with mock data.")
    
    # Find ATM options for all indices
    refresh_atm_options()
    
    # Initialize WebSocket
    initialize_websocket()
    
    # Start session monitor thread
    session_thread = threading.Thread(target=session_monitor, daemon=True)
    session_thread.start()
    
    # Initialize Dash app
    app = initialize_dashboard()
    
    # Register callbacks
    register_callbacks(app)
    
    # Start Dash app
    logger.info("Starting dashboard on http://localhost:8050")
    app.run_server(debug=True, host='0.0.0.0', port=8050)

if __name__ == "__main__":
    main()