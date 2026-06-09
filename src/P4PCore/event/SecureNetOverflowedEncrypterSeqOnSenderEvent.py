from P4PCore.abstract.P4PEvent import P4PEvent

class SecureNetOverflowedEncrypterSeqOnSenderEvent(P4PEvent):
    @staticmethod
    def isAsync() -> bool:
        return True

    def __init__(self, seqWhenOverflowed:int, originalData:bytes, addr:tuple[str, int]):
        self._seqWhenOverflowed = seqWhenOverflowed
        self._originalData = originalData
        self._addr = addr

    @property
    def seqWhenOverflowed(self) -> int:
        """
        Sequence number when the overflow occurred
        """
        return self._seqWhenOverflowed

    @property
    def originalData(self) -> bytes:
        """
        Original data that caused the overflow
        """
        return self._originalData

    @property
    def addr(self) -> tuple[str, int]:
        """
        Receiver's address
        """
        return self._addr