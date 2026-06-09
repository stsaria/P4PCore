from P4PCore.abstract.P4PEvent import P4PEvent

class NetLikeRecvedEvent(P4PEvent):
    @staticmethod
    def isAsync() -> bool:
        return True

    def __init__(self, netLikeInst:object, data:bytes, addr:tuple[str, int], recvedTime:float):
        self._netLikeInst:object = netLikeInst
        self._data:bytes = data
        self._addr:tuple[str, int] = addr
        self._recvedTime:float = recvedTime

        self._cancel:bool = False

    @property
    def recvedTime(self) -> float:
        """
        Receive timestamp
        """
        return self._recvedTime

    @property
    def netLikeInst(self) -> object:
        """
        Recver instance
        """
        return self._netLikeInst

    @property
    def data(self) -> bytes:
        """
        Received data
        """
        return self._data

    @property
    def addr(self) -> tuple[str, int]:
        """
        Sender's address
        """
        return self._addr

    def cancel(self) -> None:
        self._cancel = True

    @property
    def isCancelled(self) -> bool:
        """
        Whether processing has been cancelled
        """
        return self._cancel