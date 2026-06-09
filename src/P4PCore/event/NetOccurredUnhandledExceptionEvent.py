from P4PCore.abstract.P4PEvent import P4PEvent

class NetOccurredUnhandledExceptionEvent(P4PEvent):
    def __init__(self, exception:Exception, data:bytes, addr:tuple[str, int], recvedTime:float):
        self._exception = exception
        self._data = data
        self._addr = addr
        self._recvedTime = recvedTime

    @property
    def exception(self) -> Exception:
        """
        Unhandled exception that occurred during packet processing
        """
        return self._exception

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

    @property
    def recvedTime(self) -> float:
        """
        Receive timestamp
        """
        return self._recvedTime