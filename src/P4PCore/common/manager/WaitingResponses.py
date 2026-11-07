from collections.abc import MutableMapping
from typing import TypeVar

from P4PCore.common.model.WaitingResponseInfo import WAITING_RESPONSE_INFO_KEY, WaitingResponseInfo
from P4PCore.common.model.WaitingResponse import WaitingResponse

OI = TypeVar("OI")
RT = TypeVar("RT")

class WaitingResponses:
    """
    Track in-flight waiting responses by their response key.
    """

    def __init__(
        self,
        mapping:MutableMapping[WAITING_RESPONSE_INFO_KEY, WaitingResponse] | None = None
    ):
        """
        Initialize the manager that stores waiting responses by key.
        :param mapping: A unique mapping object; it can be used in cases where you wish to utilize objects such as TTLCache.
        """
        self._mapping:MutableMapping[WAITING_RESPONSE_INFO_KEY, WaitingResponse] = mapping if mapping is not None else {}
    
    class _ResponseContext[OI, RT]:
        """
        Context manager for registering a waiting response while it is in use.
        """

        def __init__(self, mapping:MutableMapping[WAITING_RESPONSE_INFO_KEY, WaitingResponse], waitingResponse:WaitingResponse[OI, RT]):
            self._mapping:MutableMapping[WAITING_RESPONSE_INFO_KEY, WaitingResponse] = mapping
            self._waitingResponseInfo:WaitingResponseInfo = waitingResponse.waitingResponseInfo
            self._waitingResponse:WaitingResponse = waitingResponse

        @property
        def waitingResponse(self) -> WaitingResponse[OI, RT]:
            """
            Return the wrapped waiting response instance.
            """
            return self._waitingResponse

        def __enter__(self):
            self._mapping.setdefault(self._waitingResponseInfo.key, self._waitingResponse)
            return self

        def __exit__(self, _, __, ___):
            self._mapping.pop(self._waitingResponseInfo.key, None)

    def open(self, waitingResponse:WaitingResponse[OI, RT]) -> _ResponseContext[OI, RT]:
        """
        Open a context that registers a waiting response for the duration of the scope.
        :param waitingResponse: A WaitingResponse object for catching a response.
        :return: A context object for safe response capture.
        """
        return self._ResponseContext(self._mapping, waitingResponse)

    def add(self, waitingResponse:WaitingResponse[OI, RT]) -> None:
        """
        Add a WaitingResponse object for catching a response without a context
        :param waitingResponse: A WaitingResponse object for catching a response.
        """
        self._mapping.setdefault(waitingResponse.waitingResponseInfo.key, waitingResponse)

    def get(self, waitingResponseInfoKey:WAITING_RESPONSE_INFO_KEY) -> WaitingResponse | None:
        """
        Return the waiting response registered under the specified key, if any.
        :param waitingResponseInfoKey: A identify object for finding WaitingResponse.
        """
        return self._mapping.get(waitingResponseInfoKey)