from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseEntryMixin(ABC):
    """Base class for all entry mixins"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialization of the mixin

        Args:
            params: Dictionary with configuration parameters
        """
        self.strategy = None
        self.params = params or {}
        self.indicators = {}

        # Validation of parameters when creating
        self._validate_params()

        # Setting default values
        self._set_defaults()

    def _validate_params(self):
        """Validation of mixin parameters"""
        required_params = self.get_required_params()
        for param in required_params:
            if param not in self.params:
                raise ValueError(
                    f"Required parameter '{param}' not provided for {self.__class__.__name__}"
                )

    def _set_defaults(self):
        """Setting default values for parameters"""
        defaults = self.get_default_params()
        for key, value in defaults.items():
            if key not in self.params:
                self.params[key] = value

    @abstractmethod
    def get_required_params(self) -> list:
        """Returns a list of required parameters"""
        return []

    @abstractmethod
    def get_default_params(self) -> Dict[str, Any]:
        """Returns a dictionary of default parameters"""
        return {}

    def init_entry(self, strategy, additional_params: Optional[Dict[str, Any]] = None):
        """
        Initialization of the mixin with a strategy

        Args:
            strategy: Backtrader strategy instance
            additional_params: Additional parameters for updating
        """
        self.strategy = strategy

        # Update parameters if additional parameters are provided
        if additional_params:
            self.params.update(additional_params)

        # Initialize indicators
        self._init_indicators()

    @abstractmethod
    def _init_indicators(self):
        """Initialization of technical indicators"""
        pass

    @abstractmethod
    def should_enter(self, strategy) -> bool:
        """
        Determines if the mixin should enter a position

        Args:
            strategy: Backtrader strategy instance

        Returns:
            bool: True if the mixin should enter a position
        """
        pass

    def get_param(self, key: str, default=None):
        """Safe parameter retrieval"""
        return self.params.get(key, default)

    @classmethod
    def from_config(cls, config: Dict[str, Any]):
        """
        Creating an instance from configuration

        Args:
            config: Dictionary with configuration parameters

        Returns:
            RSIBBMixin: Instance of the class
        """
        return cls(params=config)
