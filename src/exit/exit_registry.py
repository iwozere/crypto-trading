"""
Registry for all exit logic classes. Allows dynamic lookup and instantiation by name.
"""
from src.exit.atr_exit import ATRExit
from src.exit.fixed_sl_tp_exit import FixedTP_SL_Exit
from src.exit.ma_crossover_exit import MACrossoverExit
from src.exit.time_based_exit import TimeBasedExit
from src.exit.trailing_stop_exit import TrailingStopExit

EXIT_REGISTRY = {
    'atr_exit': ATRExit,
    'fixed_sl_tp_exit': FixedTP_SL_Exit,
    'ma_crossover_exit': MACrossoverExit,
    'time_based_exit': TimeBasedExit,
    'trailing_stop_exit': TrailingStopExit,
}

EXIT_PARAM_MAP = {
    'atr_exit': {
        'sl_mult': {'type': 'Real', 'low': 1.0, 'high': 3.0},
        'tp_mult': {'type': 'Real', 'low': 1.0, 'high': 5.0}
    },
    'fixed_sl_tp_exit': {
        'rr': {'type': 'Real', 'low': 1.0, 'high': 4.0},
        'sl_pct': {'type': 'Real', 'low': 0.005, 'high': 0.05}
    },
    'ma_crossover_exit': {
        'ma_period': {'type': 'Integer', 'low': 10, 'high': 50}
    },
    'time_based_exit': {
        'time_period': {'type': 'Integer', 'low': 3, 'high': 30}
    },
    'trailing_stop_exit': {
        'trail_pct': {'type': 'Real', 'low': 0.01, 'high': 0.05}
    },
}

def register_exit(name, exit_class):
    """Register a new exit logic class under a given name."""
    EXIT_REGISTRY[name] = exit_class

def get_exit_class(name):
    """Retrieve an exit logic class by name. Raises KeyError if not found."""
    return EXIT_REGISTRY[name]
