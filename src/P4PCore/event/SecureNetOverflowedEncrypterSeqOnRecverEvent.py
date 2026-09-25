from P4PCore.abstract.P4PEvent import P4PEvent

class SecureNetOverflowedEncrypterSeqOnRecverEvent(P4PEvent):
    """
    Event fired when the receiver detects an encryption sequence overflow.
    This class is required at overflowed sequence, but sequence length is uint64, so it won't happen in most cases.
    """
    @staticmethod
    def isAsync() -> bool:
        return True

    def __init__(self, seqWhenOverflowed:int, decryptedData:bytes, addr:tuple[str, int]):
        """
        Initialize the event with the overflow information.
        :param seqWhenOverflowed: The sequence number when overflow was detected.
        :param decryptedData: The decrypted payload associated with the overflow.
        :param addr: The node address involved in the overflow.
        """
        self._seqWhenOverflowed = seqWhenOverflowed
        self._decryptedData = decryptedData
        self._addr = addr

    @property
    def seqWhenOverflowed(self) -> int:
        """
        The overflow sequence number.
        """
        return self._seqWhenOverflowed

    @property
    def decryptedData(self) -> bytes:
        """
        The decrypted payload.
        """
        return self._decryptedData

    @property
    def addr(self) -> tuple[str, int]:
        """
        The node address.
        """
        return self._addr