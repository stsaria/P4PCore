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
        return self._seqWhenOverflowed
    @property
    def decryptedData(self) -> bytes:
        return self._decryptedData
    @property
    def addr(self) -> tuple[str, int]:
        return self._addr