from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseExitMixin(ABC):
    """Base class for all exit mixins"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.strategy = None
        self.params = params or {}
        self.indicators = {}

        self._validate_params()
        self._set_defaults()

    def _validate_params(self):
        required_params = self.get_required_params()
        for param in required_params:
            if param not in self.params:
                raise ValueError(
                    f"Required parameter '{param}' not provided for {self.__class__.__name__}"
                )

    def _set_defaults(self):
        defaults = self.get_default_params()
        for key, value in defaults.items():
            if key not in self.params:
                self.params[key] = value

    @abstractmethod
    def get_required_params(self) -> list:
        return []

    @abstractmethod
    def get_default_params(self) -> Dict[str, Any]:
        return {}

    def init_exit(self, strategy, additional_params: Optional[Dict[str, Any]] = None):
        self.strategy = strategy

        if additional_params:
            self.params.update(additional_params)
            self._validate_params()

        self._init_indicators()

    @abstractmethod
    def _init_indicators(self):
        pass

    @abstractmethod
    def should_exit(self) -> bool:
        pass

    @abstractmethod
    def get_exit_reason(self) -> str:
        """Get the reason for exiting the position"""
        pass

    def get_param(self, key: str, default=None):
        return self.params.get(key, default)
