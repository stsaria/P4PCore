from P4PCore.abstract.P4PEvent import P4PEvent

class SecureNetOverflowedEncrypterSeqOnSenderEvent(P4PEvent):
    """
    Event fired when the sender detects an encryption sequence overflow.
    This class is required at overflowed sequence, but sequence length is uint64, so it won't happen in most cases.
    """
    @staticmethod
    def isAsync() -> bool:
        return True

    def __init__(self, seqWhenOverflowed:int, originalData:bytes, addr:tuple[str, int]):
        """
        Initialize the event with the overflow information.
        :param seqWhenOverflowed: The sequence number when overflow was detected.
        :param originalData: The original payload that overflowed on the sender side.
        :param addr: The node address involved in the overflow.
        """
        self._seqWhenOverflowed = seqWhenOverflowed
        self._originalData = originalData
        self._addr = addr

    @property
    def seqWhenOverflowed(self) -> int:
        """
        The overflow sequence number.
        """
        return self._seqWhenOverflowed

    @property
    def originalData(self) -> bytes:
        """
        The original payload.
        """
        return self._originalData

    @property
    def addr(self) -> tuple[str, int]:
        """
        The node address.
        """
        return self._addr