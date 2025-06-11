from abc import ABC, abstractmethod

class ExitLogicMixin(ABC):
    @abstractmethod
    def init_exit(self, strategy, params): pass

    @abstractmethod
    def should_exit(self) -> bool: pass