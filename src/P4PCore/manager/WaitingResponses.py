from typing import Generic, TypeVar

from P4PCore.manager.SimpleImpls import SimpleCannotOverwriteKVManager
from P4PCore.model.WaitingResponseInfo import WAITING_RESPONSE_INFO_KEY, WaitingResponseInfo
from P4PCore.model.WaitingResponse import WaitingResponse

OI = TypeVar("OI")
RT = TypeVar("RT")

class WaitingResponses:
    """Track in-flight waiting responses by their response key."""
    def __init__(self):
        """Initialize the manager that stores waiting responses by key."""
        self._manager:SimpleCannotOverwriteKVManager[WAITING_RESPONSE_INFO_KEY, WaitingResponse] = SimpleCannotOverwriteKVManager()
    class _ResponseContext(Generic[OI, RT]):
        """Context manager for registering a waiting response while it is in use."""
        def __init__(self, manager:SimpleCannotOverwriteKVManager[WAITING_RESPONSE_INFO_KEY, WaitingResponse], waitingResponse:WaitingResponse[OI, RT]):
            """Create a response context bound to a specific waiting-response instance."""
            self._manager:SimpleCannotOverwriteKVManager[WAITING_RESPONSE_INFO_KEY, WaitingResponse] = manager
            self._waitingResponseInfo:WaitingResponseInfo = waitingResponse.waitingResponseInfo
            self._waitingResponse = waitingResponse

            self._exited:bool = False
        @property
        def waitingResponse(self) -> WaitingResponse[OI, RT]:
            """Return the wrapped waiting response instance."""
            return self._waitingResponse
        async def __aenter__(self):
            """Register the waiting response when entering the context."""
            await self._manager.add(self._waitingResponseInfo.key, self._waitingResponse)
            return self
        async def __aexit__(self, _, __, ___):
            """Unregister the waiting response when leaving the context."""
            self._exited = True
            await self._manager.delete(self._waitingResponseInfo.key)
    def open(self, waitingResponse:WaitingResponse[OI, RT]) -> _ResponseContext[OI, RT]:
        """Open a context that registers a waiting response for the duration of the scope."""
        return self._ResponseContext(self._manager, waitingResponse)
    async def get(self, waitingResponseInfoKey:WAITING_RESPONSE_INFO_KEY) -> WaitingResponse | None:
        """Return the waiting response registered under the specified key, if any."""
        return await self._manager.get(waitingResponseInfoKey)
    
    

