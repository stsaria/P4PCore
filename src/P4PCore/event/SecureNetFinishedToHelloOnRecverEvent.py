from enum import Enum, auto

from P4PCore.abstract.P4PEvent import P4PEvent

class SecureNetFinishedToHelloOnRecverEventResult(Enum):
    """
    Result codes for the secure connection hello process on the receiver side.
    """
    SUCCESS = auto()
    FAILED_CHALLENGE = auto()
    ALREADY_EXISTS_BUT_DIFFRENT_PUBLIC_KEY = auto()

class SecureNetFinishedToHelloOnRecverEvent(P4PEvent):
    """
    Event fired when the receiver finishes the hello handshake for a secure connection.
    """
    @staticmethod
    def isAsync() -> bool:
        return True

    def __init__(self, addr:tuple[str, int], result:SecureNetFinishedToHelloOnRecverEventResult):
        """
        Initialize the event with the node address and hello result.
        :param addr: The node address involved in the hello handshake.
        :param result: The result of the handshake attempt.
        """
        self._addr:tuple[str, int] = addr
        self._result:SecureNetFinishedToHelloOnRecverEventResult = result

    @property
    def addr(self) -> tuple[str, int]:
        """
        The address of the node involved in the hello exchange.
        """
        return self._addr

    @property
    def result(self) -> SecureNetFinishedToHelloOnRecverEventResult:
        """
        The outcome of the hello handshake attempt.
        """
        return self._result