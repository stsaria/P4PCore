from enum import Enum, auto

from P4PCore.abstract.P4PEvent import P4PEvent

class SecureNetFinishedToHelloOnRecverEventResult(Enum):
    SUCCESS = auto()
    FAILED_CHALLENGE = auto()
    ALREADY_EXISTS_BUT_DIFFRENT_PUBLIC_KEY = auto()

class SecureNetFinishedToHelloOnRecverEvent(P4PEvent):
    @staticmethod
    def isAsync() -> bool:
        return True

    def __init__(self, addr:tuple[str, int], result:SecureNetFinishedToHelloOnRecverEventResult):
        self._addr:tuple[str, int] = addr
        self._result:SecureNetFinishedToHelloOnRecverEventResult = result

    @property
    def addr(self) -> tuple[str, int]:
        """
        Sender's address
        """
        return self._addr

    @property
    def result(self) -> SecureNetFinishedToHelloOnRecverEventResult:
        """
        Result of hello
        """
        return self._result