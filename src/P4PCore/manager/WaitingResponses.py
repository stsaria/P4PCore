from typing import TypeVar

from P4PCore.model.WaitingResponseInfo import WAITING_RESPONSE_INFO_KEY, WaitingResponseInfo
from P4PCore.model.WaitingResponse import WaitingResponse

OI = TypeVar("OI")
RT = TypeVar("RT")


class WaitingResponses:
    """Track in-flight waiting responses by their response key."""

    def __init__(self):
        """Initialize the manager that stores waiting responses by key."""
        self._dict: dict[WAITING_RESPONSE_INFO_KEY, WaitingResponse] = {}

    class _ResponseContext[OI, RT]:
        """Context manager for registering a waiting response while it is in use."""

        def __init__(self, dictRef: dict[WAITING_RESPONSE_INFO_KEY, WaitingResponse], waitingResponse: WaitingResponse[OI, RT]):
            """Create a response context bound to a specific waiting-response instance."""
            self._dict: dict[WAITING_RESPONSE_INFO_KEY, WaitingResponse] = dictRef
            self._waitingResponseInfo: WaitingResponseInfo = waitingResponse.waitingResponseInfo
            self._waitingResponse = waitingResponse

        @property
        def waitingResponse(self) -> WaitingResponse[OI, RT]:
            """Return the wrapped waiting response instance."""
            return self._waitingResponse

        def __enter__(self):
            """Register the waiting response when entering the context."""
            self._dict[self._waitingResponseInfo.key] = self._waitingResponse
            return self

        def __exit__(self, _, __, ___):
            """Unregister the waiting response when leaving the context."""
            self._dict.pop(self._waitingResponseInfo.key, None)

    def open(self, waitingResponse: WaitingResponse[OI, RT]) -> _ResponseContext[OI, RT]:
        """Open a context that registers a waiting response for the duration of the scope."""
        return self._ResponseContext(self._dict, waitingResponse)

    def get(self, waitingResponseInfoKey: WAITING_RESPONSE_INFO_KEY) -> WaitingResponse | None:
        """Return the waiting response registered under the specified key, if any."""
        return self._dict.get(waitingResponseInfoKey)