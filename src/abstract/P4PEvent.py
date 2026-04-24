from abc import ABC

class P4PEvent(ABC):
    @staticmethod
    def isAsync() -> bool: ...