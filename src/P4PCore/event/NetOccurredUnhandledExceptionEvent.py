from P4PCore.abstract.P4PEvent import P4PEvent

class NetOccurredUnhandledExceptionEvent(P4PEvent):
    """
    Event fired when an unhandled exception occurs while processing network data.
    """
    def __init__(self, exception:Exception, data:bytes, addr:tuple[str, int], recvedTime:float):
        """
        Initialize the event with the exception and received packet details.
        :param exception: The unhandled exception that was raised.
        :param data: The raw packet bytes that caused the exception.
        :param addr: The sender address associated with the packet.
        :param recvedTime: The time at which the packet was received.
        :return: None.
        """
        self._exception = exception
        self._data = data
        self._addr = addr
        self._recvedTime = recvedTime

    @property
    def exception(self) -> Exception:
        """
        The exception that occurred.
        """
        return self._exception

    @property
    def data(self) -> bytes:
        """
        The packet data that caused the exception.
        """
        return self._data

    @property
    def addr(self) -> tuple[str, int]:
        """
        The sender's address.
        """
        return self._addr

    @property
    def recvedTime(self) -> float:
        """
        The receive time.
        """
        return self._recvedTime