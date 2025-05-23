"""
Bot Manager Module
------------------

This module provides a unified interface for managing trading bot instances in memory. It supports starting, stopping, and tracking bots dynamically by strategy name and configuration. The bot manager is used by both the REST API and the web GUI to ensure consistent bot lifecycle management.

Main Features:
- Dynamically load and start bot classes by strategy name
- Assign unique bot IDs and track running bots and their threads
- Stop bots and clean up resources
- Query status and trade history for all running bots
- Used as a singleton registry for all bot management operations

Functions:
- start_bot(strategy_name, config, bot_id=None): Start a new bot instance
- stop_bot(bot_id): Stop a running bot by ID
- get_status(): Get status of all running bots
- get_trades(bot_id): Get trade history for a bot
- get_running_bots(): List all running bot IDs
"""
import importlib
import threading

# In-memory registry of running bots and their threads
running_bots = {}
bot_threads = {}

def start_bot(strategy_name, config, bot_id=None):
    """
    Start a trading bot for the given strategy. Returns bot_id.
    """
    if not bot_id:
        bot_id = strategy_name if strategy_name not in running_bots else f"{strategy_name}_{len(running_bots)+1}"
    if bot_id in running_bots:
        raise Exception(f"Bot with id {bot_id} is already running.")
    bot_module = importlib.import_module(f"src.trading.{strategy_name}_bot")
    bot_class = getattr(bot_module, ''.join([w.capitalize() for w in strategy_name.split('_')]) + 'Bot')
    bot_instance = bot_class(config)
    running_bots[bot_id] = bot_instance
    t = threading.Thread(target=bot_instance.run, daemon=True)
    bot_threads[bot_id] = t
    t.start()
    return bot_id

def stop_bot(bot_id):
    """
    Stop a running bot by id.
    """
    if bot_id not in running_bots:
        raise Exception(f"No running bot with id {bot_id}.")
    bot = running_bots[bot_id]
    bot.stop()
    del running_bots[bot_id]
    del bot_threads[bot_id]

def get_status():
    """
    Get status of all running bots.
    """
    return {bot_id: 'running' for bot_id in running_bots.keys()}

def get_trades(bot_id):
    """
    Get trade history for a running bot.
    """
    if bot_id in running_bots:
        return getattr(running_bots[bot_id], 'trade_history', [])
    return []

def get_running_bots():
    """
    Get a list of all running bot ids.
    """
    return list(running_bots.keys()) 