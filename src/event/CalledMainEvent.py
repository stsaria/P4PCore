from src.abstract.P4PEvent import P4PEvent


class CalledMainEvent(P4PEvent):
    def isAsync(self) -> bool:
        return False