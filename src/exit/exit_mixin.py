from abc import ABC, abstractmethod

class ExitLogicMixin(ABC):
    @abstractmethod
    def init_exit(self, params=None): pass

    @abstractmethod
    def should_exit(self) -> bool: pass