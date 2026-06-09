from P4PCore.abstract.P4PEvent import P4PEvent

class SecureNetOverflowedEncrypterSeqOnRecverEvent(P4PEvent):
    @staticmethod
    def isAsync() -> bool:
        return True

    def __init__(self, seqWhenOverflowed:int, decryptedData:bytes, addr:tuple[str, int]):
        self._seqWhenOverflowed = seqWhenOverflowed
        self._decryptedData = decryptedData
        self._addr = addr

    @property
    def seqWhenOverflowed(self) -> int:
        """
        Sequence number when the overflow occurred
        """
        return self._seqWhenOverflowed

    @property
    def decryptedData(self) -> bytes:
        """
        Decrypted data that caused the overflow
        """
        return self._decryptedData

    @property
    def addr(self) -> tuple[str, int]:
        """
        Sender's address
        """
        return self._addr