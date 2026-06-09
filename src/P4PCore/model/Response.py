from typing import Generic, TypeVar

RV = TypeVar("RV")

class Response(Generic[RV]):
    def __init__(self, value:RV, nextResponseIdentify:bytes | None = None):
        self._value:RV = value
        
        self._nextResponseId:bytes | None = nextResponseIdentify
    @property
    def value(self) -> RV:
        return self._value

    @property
    def nextResponseId(self) -> bytes:
        return self._nextResponseId