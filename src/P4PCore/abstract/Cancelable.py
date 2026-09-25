from abc import ABC, abstractmethod

class Cancelable(ABC):
    @abstractmethod
    def cancel(self): ...
    @property
    @abstractmethod
    def isCanceled(self): ...