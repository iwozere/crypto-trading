from abc import ABC, abstractmethod

class EntryLogicMixin(ABC):
    @abstractmethod
    def init_entry(self, strategy, params): pass
    
    @abstractmethod
    def should_enter(self) -> bool: pass