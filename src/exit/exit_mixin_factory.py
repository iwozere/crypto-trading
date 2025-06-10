from src.exit.fixed_ratio_mixin import FixedRatioExitMixin
from src.exit.trailing_stop_mixin import TrailingStopExitMixin
from src.exit.atr_exit_mixin import ATRExitMixin
from src.exit.ma_crossover_exit_mixin import MACrossoverExitMixin
from src.exit.time_based_exit_mixin import TimeBasedExitMixin


class ExitMixinFactory:
    
    EXIT_PARAM_MAP = {
        "ATRExitMixin": {
            "atr_period": "int",
            "tp_multiplier": "float",
            "sl_multiplier": "float",
            "use_talib": "bool"
        },
        "FixedRatioExitMixin": {
            "sl_pct": "float",
            "rr": "float"
        },
        "MACrossoverExitMixin": {
            "ma_period": "int"
        },
        "TimeBasedExitMixin": {
            "time_period": "int"
        },
        "TrailingStopExitMixin": {
            "trail_pct": "float"
        }
    }

    # Registry of available exit logic classes
    EXIT_LOGIC_REGISTRY = {
        "FixedRatioExitMixin": FixedRatioExitMixin,
        "TrailingStopExitMixin": TrailingStopExitMixin,
        "ATRExitMixin": ATRExitMixin,
        "MACrossoverExitMixin": MACrossoverExitMixin,
        "TimeBasedExitMixin": TimeBasedExitMixin
    }
    
    @staticmethod
    def get_exit_mixin(exit_type: str):
        if exit_type not in ExitMixinFactory.EXIT_LOGIC_REGISTRY:
            raise ValueError(f"Unknown exit logic: {exit_type}")
        return ExitMixinFactory.EXIT_LOGIC_REGISTRY[exit_type]

    @staticmethod
    def get_exit_mixin_params(exit_type: str):
        if exit_type not in ExitMixinFactory.EXIT_PARAM_MAP:
            raise ValueError(f"Unknown exit logic: {exit_type}")
        return ExitMixinFactory.EXIT_PARAM_MAP[exit_type]
