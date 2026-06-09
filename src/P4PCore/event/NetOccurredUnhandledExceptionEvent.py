from P4PCore.abstract.P4PEvent import P4PEvent

class NetOccurredUnhandledExceptionEvent(P4PEvent):
    def __init__(self, exception:Exception, data:bytes, addr:tuple[str, int], recvedTime:float):
        self._exception = exception
        self._data = data
        self._addr = addr
        self._recvedTime = recvedTime
    @property
    def exception(self) -> Exception:
        return self._exception
    @property
    def data(self) -> bytes:
        return self._data
    @property
    def addr(self) -> tuple[str, int]:
        return self._addr
    @property
    def recvedTime(self) -> float:
        return self._recvedTime