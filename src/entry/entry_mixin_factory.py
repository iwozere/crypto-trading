from src.entry.rsi_bb_mixin import RSIBBMixin
from src.entry.rsi_ichimoku_mixin import RSIIchimokuMixin
from src.entry.rsi_bb_volume_mixin import RSIBBVolumeMixin
from src.entry.rsi_volume_supertrend_mixin import RSIVolumeSuperTrendMixin
from src.entry.bb_volume_supertrend_mixin import BBVolumeSuperTrendMixin

# Parameter map for each entry logic
ENTRY_PARAM_MAP = {
    "RSIBBMixin": {
        "rsi_period": "int",
        "bb_period": "int",
        "bb_dev": "float",
        "rsi_oversold": "int"
    },
    "RSIIchimokuMixin": {
        "rsi_period": "int",
        "tenkan_period": "int",
        "kijun_period": "int",
        "rsi_oversold": "int"
    },
    "RSIBBVolumeMixin": {
        "rsi_period": "int",
        "bb_period": "int",
        "bb_dev": "float",
        "vol_ma_period": "int",
        "rsi_oversold": "int"
    },
    "RSIVolumeSuperTrendMixin": {
        "rsi_period": "int",
        "vol_ma_period": "int",
        "st_period": "int",
        "st_multiplier": "float",
        "rsi_oversold": "int",
        "use_talib": "bool"
    },
    "BBVolumeSuperTrendMixin": {
        "bb_period": "int",
        "bb_dev": "float",
        "vol_ma_period": "int",
        "st_period": "int",
        "st_multiplier": "float",
        "use_talib": "bool"
    }
}

# Registry of available entry logic classes
ENTRY_LOGIC_REGISTRY = {
    "RSIBBMixin": RSIBBMixin,
    "RSIIchimokuMixin": RSIIchimokuMixin,
    "RSIBBVolumeMixin": RSIBBVolumeMixin,
    "RSIVolumeSuperTrendMixin": RSIVolumeSuperTrendMixin,
    "BBVolumeSuperTrendMixin": BBVolumeSuperTrendMixin
}

class EntryMixinFactory:
    @staticmethod
    def get_entry_mixin(entry_type: str):
        if entry_type not in ENTRY_LOGIC_REGISTRY:
            raise ValueError(f"Unknown entry logic: {entry_type}")
        return ENTRY_LOGIC_REGISTRY[entry_type]

    @staticmethod
    def get_entry_mixin_params(entry_type: str):
        if entry_type not in ENTRY_PARAM_MAP:
            raise ValueError(f"Unknown entry logic: {entry_type}")
        return ENTRY_PARAM_MAP[entry_type] 