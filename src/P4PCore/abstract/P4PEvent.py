from abc import ABC

class P4PEvent(ABC):
    """
    Protocol for a P4PEvent.
    """
    @staticmethod
    def isAsync() -> bool: ...