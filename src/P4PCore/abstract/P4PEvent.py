from abc import ABC

class P4PEvent(ABC):
    """
    Protocol for a P4PEvent.
    """
    @staticmethod
    def isAsync() -> bool:
        """
        Check whether the event should be processed asynchronously.
        :return: True if the event is asynchronous, otherwise False.
        """
        ...