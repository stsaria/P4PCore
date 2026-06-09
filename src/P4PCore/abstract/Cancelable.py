from abc import ABC, abstractmethod

class Cancelable(ABC):
    @abstractmethod
    def cancel(self): ...
    @abstractmethod
    @property
    def isCanceled(self): ...