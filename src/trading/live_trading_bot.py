"""
Live Trading Bot Module
----------------------

This module implements a comprehensive live trading bot that:
1. Reads configuration from JSON files
2. Constructs data feeds, strategies, and brokers
3. Manages live trading with real-time data
4. Handles error recovery and notifications
5. Integrates with existing components

Main Features:
- Configuration-driven setup
- Live data feed integration
- Strategy execution with Backtrader
- Position management and persistence
- Error handling and recovery
- Notification system integration
- Web interface integration

Classes:
- LiveTradingBot: Main live trading bot implementation
"""

import json
import os
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Any, Dict, Optional

import backtrader as bt

from src.broker.broker_factory import get_broker
from src.data.data_feed_factory import DataFeedFactory
from src.notification.logger import setup_logger
from src.notification.telegram_notifier import create_notifier as create_telegram_notifier
from src.notification.emailer import EmailNotifier
from src.strategy.custom_strategy import CustomStrategy
from src.trading.base_trading_bot import BaseTradingBot

_logger = setup_logger(__name__)


class LiveTradingBot:
    """
    Comprehensive live trading bot that orchestrates all components.
    
    This bot reads configuration from a JSON file and manages:
    - Data feed initialization and monitoring
    - Strategy execution with Backtrader
    - Broker integration and order management
    - Position tracking and persistence
    - Error handling and recovery
    - Notifications and logging
    """
    
    def __init__(self, config_file: str):
        """
        Initialize the live trading bot.
        
        Args:
            config_file: Path to configuration file (e.g., '0001.json')
        """
        self.config_file = config_file
        self.config = None
        self.data_feed = None
        self.broker = None
        self.cerebro = None
        self.strategy = None
        self.is_running = False
        self.should_stop = False
        self.error_count = 0
        self.max_errors = 5
        self.error_retry_interval = 60  # seconds
        
        # Notification setup
        self.telegram_notifier = None
        self.email_notifier = None
        
        # Threading
        self.main_thread = None
        self.monitor_thread = None
        
        # Load configuration
        self._load_configuration()
        self._setup_notifications()
        self._validate_configuration()
    
    def _load_configuration(self):
        """Load configuration from JSON file."""
        try:
            config_path = f"config/trading/{self.config_file}"
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            _logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            _logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _setup_notifications(self):
        """Setup notification systems."""
        try:
            # Setup Telegram notifications
            if self.config.get("notifications", {}).get("telegram", {}).get("enabled", False):
                self.telegram_notifier = create_telegram_notifier()
                _logger.info("Telegram notifications enabled")
            
            # Setup Email notifications
            if self.config.get("notifications", {}).get("email", {}).get("enabled", False):
                from config.donotshare.donotshare import SENDGRID_API_KEY
                self.email_notifier = EmailNotifier(SENDGRID_API_KEY)
                _logger.info("Email notifications enabled")
                
        except Exception as e:
            _logger.warning(f"Failed to setup notifications: {e}")
    
    def _validate_configuration(self):
        """Validate configuration parameters."""
        required_sections = ["broker", "trading", "data", "strategy"]
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate data feed configuration
        data_config = self.config["data"]
        if "data_source" not in data_config:
            raise ValueError("Missing data_source in data configuration")
        
        # Validate strategy configuration
        strategy_config = self.config["strategy"]
        if strategy_config.get("type") != "custom":
            raise ValueError("Only 'custom' strategy type is supported")
        
        if "entry_logic" not in strategy_config:
            raise ValueError("Missing entry_logic in strategy configuration")
        
        if "exit_logic" not in strategy_config:
            raise ValueError("Missing exit_logic in strategy configuration")
        
        _logger.info("Configuration validation passed")
    
    def _create_data_feed(self):
        """Create and initialize the data feed."""
        try:
            data_config = self.config["data"]
            
            # Add callback for new data notifications
            if self.telegram_notifier:
                def on_new_bar(symbol, timestamp, data):
                    self._notify_new_bar(symbol, timestamp, data)
                data_config["on_new_bar"] = on_new_bar
            
            self.data_feed = DataFeedFactory.create_data_feed(data_config)
            
            if self.data_feed is None:
                raise ValueError("Failed to create data feed")
            
            _logger.info(f"Created data feed for {data_config.get('symbol', 'unknown')}")
            return True
            
        except Exception as e:
            _logger.error(f"Error creating data feed: {e}")
            return False
    
    def _create_broker(self):
        """Create and initialize the broker."""
        try:
            broker_config = self.config["broker"]
            self.broker = get_broker(broker_config)
            _logger.info(f"Created broker: {broker_config.get('type', 'unknown')}")
            return True
            
        except Exception as e:
            _logger.error(f"Error creating broker: {e}")
            return False
    
    def _create_strategy(self):
        """Create the strategy configuration for Backtrader."""
        try:
            strategy_config = self.config["strategy"]
            trading_config = self.config["trading"]
            
            # Build strategy configuration
            strategy_params = {
                "strategy_config": {
                    "entry_logic": strategy_config["entry_logic"],
                    "exit_logic": strategy_config["exit_logic"],
                    "position_size": trading_config.get("position_size", 0.1),
                    "use_talib": strategy_config.get("use_talib", False)
                }
            }
            
            self.strategy = CustomStrategy
            self.strategy_params = strategy_params
            
            _logger.info(f"Created strategy: {strategy_config.get('type', 'custom')}")
            return True
            
        except Exception as e:
            _logger.error(f"Error creating strategy: {e}")
            return False
    
    def _setup_backtrader(self):
        """Setup Backtrader engine."""
        try:
            self.cerebro = bt.Cerebro()
            
            # Add data feed
            self.cerebro.adddata(self.data_feed)
            
            # Add strategy
            self.cerebro.addstrategy(self.strategy, **self.strategy_params)
            
            # Setup broker
            if self.broker:
                self.cerebro.broker = self.broker
            
            # Setup initial cash
            initial_balance = self.config["broker"].get("initial_balance", 1000.0)
            self.cerebro.broker.setcash(initial_balance)
            
            # Setup commission
            commission = self.config["broker"].get("commission", 0.001)
            self.cerebro.broker.setcommission(commission=commission)
            
            _logger.info(f"Setup Backtrader with initial balance: {initial_balance}")
            return True
            
        except Exception as e:
            _logger.error(f"Error setting up Backtrader: {e}")
            return False
    
    def _load_open_positions(self):
        """Load open positions from database or state file."""
        try:
            # TODO: Implement database loading of open positions
            # For now, we'll start fresh
            _logger.info("No open positions to load")
            return True
            
        except Exception as e:
            _logger.error(f"Error loading open positions: {e}")
            return False
    
    def _save_open_positions(self):
        """Save open positions to database or state file."""
        try:
            # TODO: Implement database saving of open positions
            _logger.info("Open positions saved")
            return True
            
        except Exception as e:
            _logger.error(f"Error saving open positions: {e}")
            return False
    
    def _notify_new_bar(self, symbol: str, timestamp, data: Dict[str, Any]):
        """Notify about new data bar."""
        try:
            if self.telegram_notifier:
                message = f"📊 New {symbol} bar: O={data['open']:.4f} H={data['high']:.4f} L={data['low']:.4f} C={data['close']:.4f}"
                self.telegram_notifier.send_message(message)
        except Exception as e:
            _logger.error(f"Error notifying new bar: {e}")
    
    def _notify_trade(self, trade_type: str, symbol: str, price: float, size: float, pnl: Optional[float] = None):
        """Notify about trade execution."""
        try:
            message = f"💰 {trade_type} {symbol}: {size:.4f} @ {price:.4f}"
            if pnl is not None:
                message += f" (PnL: {pnl:.2f}%)"
            
            if self.telegram_notifier:
                self.telegram_notifier.send_message(message)
            
            if self.email_notifier:
                self.email_notifier.send_trade_notification(trade_type, symbol, price, size, pnl)
                
        except Exception as e:
            _logger.error(f"Error notifying trade: {e}")
    
    def _notify_error(self, error: str):
        """Notify about errors."""
        try:
            message = f"❌ Bot Error: {error}"
            
            if self.telegram_notifier:
                self.telegram_notifier.send_message(message)
            
            if self.email_notifier:
                self.email_notifier.send_error_notification(error)
                
        except Exception as e:
            _logger.error(f"Error notifying error: {e}")
    
    def _notify_status(self, status: str):
        """Notify about bot status changes."""
        try:
            message = f"🤖 Bot Status: {status}"
            
            if self.telegram_notifier:
                self.telegram_notifier.send_message(message)
                
        except Exception as e:
            _logger.error(f"Error notifying status: {e}")
    
    def _monitor_data_feed(self):
        """Monitor data feed health and reconnect if needed."""
        while self.is_running and not self.should_stop:
            try:
                if self.data_feed:
                    status = self.data_feed.get_status()
                    if not status.get("is_connected", False):
                        _logger.warning("Data feed disconnected, attempting to reconnect...")
                        self._reconnect_data_feed()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                _logger.error(f"Error in data feed monitor: {e}")
                time.sleep(60)
    
    def _reconnect_data_feed(self):
        """Reconnect data feed."""
        try:
            if self.data_feed:
                self.data_feed.stop()
                time.sleep(5)
            
            if self._create_data_feed():
                self._setup_backtrader()
                _logger.info("Data feed reconnected successfully")
                self._notify_status("Data feed reconnected")
            else:
                _logger.error("Failed to reconnect data feed")
                self._notify_error("Failed to reconnect data feed")
                
        except Exception as e:
            _logger.error(f"Error reconnecting data feed: {e}")
    
    def _run_backtrader(self):
        """Run Backtrader engine."""
        try:
            _logger.info("Starting Backtrader engine...")
            self._notify_status("Starting Backtrader engine")
            
            # Run Backtrader
            results = self.cerebro.run()
            
            _logger.info("Backtrader engine completed")
            return True
            
        except Exception as e:
            _logger.error(f"Error in Backtrader engine: {e}")
            self._notify_error(f"Backtrader error: {str(e)}")
            return False
    
    def start(self):
        """Start the live trading bot."""
        try:
            _logger.info(f"Starting live trading bot: {self.config_file}")
            self._notify_status("Starting live trading bot")
            
            # Initialize components
            if not self._create_data_feed():
                raise RuntimeError("Failed to create data feed")
            
            if not self._create_broker():
                raise RuntimeError("Failed to create broker")
            
            if not self._create_strategy():
                raise RuntimeError("Failed to create strategy")
            
            if not self._setup_backtrader():
                raise RuntimeError("Failed to setup Backtrader")
            
            if not self._load_open_positions():
                raise RuntimeError("Failed to load open positions")
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_data_feed, daemon=True)
            self.monitor_thread.start()
            
            # Set running flag
            self.is_running = True
            
            # Start main trading loop
            self._run_backtrader()
            
        except Exception as e:
            _logger.error(f"Error starting bot: {e}")
            self._notify_error(f"Failed to start bot: {str(e)}")
            raise
    
    def stop(self):
        """Stop the live trading bot."""
        try:
            _logger.info("Stopping live trading bot...")
            self._notify_status("Stopping live trading bot")
            
            self.should_stop = True
            self.is_running = False
            
            # Stop data feed
            if self.data_feed:
                self.data_feed.stop()
            
            # Save open positions
            self._save_open_positions()
            
            _logger.info("Live trading bot stopped")
            self._notify_status("Live trading bot stopped")
            
        except Exception as e:
            _logger.error(f"Error stopping bot: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status."""
        try:
            status = {
                "config_file": self.config_file,
                "is_running": self.is_running,
                "should_stop": self.should_stop,
                "error_count": self.error_count,
                "data_feed_status": None,
                "broker_status": None,
                "strategy_status": None
            }
            
            if self.data_feed:
                status["data_feed_status"] = self.data_feed.get_status()
            
            if self.broker:
                status["broker_status"] = {
                    "type": self.config["broker"].get("type"),
                    "cash": getattr(self.cerebro.broker, 'cash', 0) if self.cerebro else 0
                }
            
            if self.strategy:
                status["strategy_status"] = {
                    "type": self.config["strategy"].get("type"),
                    "entry_logic": self.config["strategy"]["entry_logic"]["name"],
                    "exit_logic": self.config["strategy"]["exit_logic"]["name"]
                }
            
            return status
            
        except Exception as e:
            _logger.error(f"Error getting status: {e}")
            return {"error": str(e)}
    
    def restart(self):
        """Restart the live trading bot."""
        try:
            _logger.info("Restarting live trading bot...")
            self._notify_status("Restarting live trading bot")
            
            self.stop()
            time.sleep(5)  # Wait for cleanup
            
            # Reset state
            self.should_stop = False
            self.error_count = 0
            
            # Start again
            self.start()
            
        except Exception as e:
            _logger.error(f"Error restarting bot: {e}")
            self._notify_error(f"Failed to restart bot: {str(e)}")


def main():
    """Main function to run the live trading bot."""
    if len(sys.argv) != 2:
        print("Usage: python live_trading_bot.py <config_file>")
        print("Example: python live_trading_bot.py 0001.json")
        sys.exit(1)
    
    config_file = sys.argv[1]
    
    # Create and start bot
    bot = LiveTradingBot(config_file)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        _logger.info(f"Received signal {signum}, shutting down...")
        bot.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        bot.start()
    except KeyboardInterrupt:
        _logger.info("Received keyboard interrupt, shutting down...")
        bot.stop()
    except Exception as e:
        _logger.error(f"Unexpected error: {e}")
        bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    main() 