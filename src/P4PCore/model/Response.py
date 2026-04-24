class Response[RV]:
    def __init__(self, value:RV, nextResponseId:bytes | None = None):
        self._nextResponseId:bytes | None = nextResponseId
        self._value:RV = value
    @property
    def nextResponseId(self) -> bytes:
        return self._nextResponseId
    @property
    def value(self) -> RV:
        return self._value