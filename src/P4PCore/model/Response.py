from typing import Generic, TypeVar

RV = TypeVar("RV")

class Response(Generic[RV]):
    """
    Hold a response payload and an optional identifier for a subsequent response.
    """
    def __init__(self, value:RV, nextResponseIdentify:bytes | None = None):
        """
        Initialize the response value and the next response identifier.
        :param value: The response payload to store.
        :param nextResponseIdentify: An optional identifier for a chained response, or None when there is no next response.
        """
        self._value:RV = value
        
        self._nextResponseId:bytes | None = nextResponseIdentify
    @property
    def value(self) -> RV:
        """
        The response payload.
        """
        return self._value

    @property
    def nextResponseId(self) -> bytes:
        """
        The next response identifier, or None if unavailable.
        """
        return self._nextResponseId