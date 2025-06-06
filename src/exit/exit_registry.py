"""
Exit logic registry for trading strategies. Provides a centralized way to register and retrieve exit logic classes.
"""
from src.exit.atr_exit import ATRExit
from src.exit.fixed_sl_tp_exit import FixedSLTPExit
from src.exit.ma_crossover_exit import MACrossoverExit
from src.exit.time_based_exit import TimeBasedExit
from src.exit.trailing_stop_exit import TrailingStopExit

# Registry of exit logic classes
EXIT_REGISTRY = {
    'atr_exit': ATRExit,
    'fixed_sl_tp_exit': FixedSLTPExit,
    'ma_crossover_exit': MACrossoverExit,
    'time_based_exit': TimeBasedExit,
    'trailing_stop_exit': TrailingStopExit
}

# Map of exit logic names to their required parameters
EXIT_PARAM_MAP = {
    'atr_exit': {
        'sl_mult': {'type': 'real', 'min': 0.5, 'max': 3.0},
        'tp_mult': {'type': 'real', 'min': 1.0, 'max': 5.0}
    },
    'fixed_sl_tp_exit': {
        'sl_pct': {'type': 'real', 'min': 0.01, 'max': 0.05},
        'rr': {'type': 'real', 'min': 1.0, 'max': 5.0}
    },
    'ma_crossover_exit': {
        'ma_period': {'type': 'integer', 'min': 10, 'max': 50}
    },
    'time_based_exit': {
        'time_period': {'type': 'integer', 'min': 3, 'max': 30}
    },
    'trailing_stop_exit': {
        'trail_pct': {'type': 'real', 'min': 0.01, 'max': 0.05}
    }
}

def get_exit_class(exit_logic_name: str):
    """
    Get the exit logic class for the given name.
    
    Args:
        exit_logic_name (str): Name of the exit logic
        
    Returns:
        class: The exit logic class
        
    Raises:
        ValueError: If the exit logic name is not found
    """
    if exit_logic_name not in EXIT_REGISTRY:
        raise ValueError(f"Exit logic '{exit_logic_name}' not found in registry")
    return EXIT_REGISTRY[exit_logic_name]

def get_exit_params(exit_logic_name: str):
    """
    Get the required parameters for the given exit logic.
    
    Args:
        exit_logic_name (str): Name of the exit logic
        
    Returns:
        dict: Dictionary of required parameters and their constraints
        
    Raises:
        ValueError: If the exit logic name is not found
    """
    if exit_logic_name not in EXIT_PARAM_MAP:
        raise ValueError(f"Exit logic '{exit_logic_name}' not found in parameter map")
    return EXIT_PARAM_MAP[exit_logic_name]
