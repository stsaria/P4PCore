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
        return self._seqWhenOverflowed

    @property
    def originalData(self) -> bytes:
        return self._originalData

    @property
    def addr(self) -> tuple[str, int]:
        return self._addr