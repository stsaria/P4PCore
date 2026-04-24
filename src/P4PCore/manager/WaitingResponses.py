from typing import Any, Generic, Hashable, Type, TypeVar

from P4PCore.manager.SimpleImpls import SimpleCannotOverwriteKVManager
from P4PCore.abstract.IncludeGC import IncludeGC
from P4PCore.model.WaitingResponseInfo import WAITING_RESPONSE_INFO_KEY, WaitingResponseInfo
from P4PCore.model.WaitingResponse import WaitingResponse

OI = TypeVar("OI")
RT = TypeVar("RT")

class WaitingResponses:
    def __init__(self):
        self._manager:SimpleCannotOverwriteKVManager[WAITING_RESPONSE_INFO_KEY, WaitingResponse] = SimpleCannotOverwriteKVManager()
    class _ResponseContext(Generic[OI, RT]):
        def __init__(self, manager:SimpleCannotOverwriteKVManager[WAITING_RESPONSE_INFO_KEY, WaitingResponse], waitingResponse:WaitingResponse[OI, RT]):
            self._manager:SimpleCannotOverwriteKVManager[WAITING_RESPONSE_INFO_KEY, WaitingResponse] = manager
            self._waitingResponseInfo:WaitingResponseInfo = waitingResponse.waitingResponseInfo
            self._waitingResponse = waitingResponse

            self._exited:bool = False
        @property
        def waitingResponse(self) -> WaitingResponse[OI, RT]:
            return self._waitingResponse
        async def __aenter__(self):
            await self._manager.add(self._waitingResponseInfo.key, self._waitingResponse)
            return self
        async def __aexit__(self, _, __, ___):
            self._exited = True
            await self._manager.delete(self._waitingResponseInfo.key)
    def open(self, waitingResponse:WaitingResponse[OI, RT]) -> _ResponseContext[OI, RT]:
        return self._ResponseContext(self._manager, waitingResponse)
    async def get(self, waitingResponseInfoKey:WAITING_RESPONSE_INFO_KEY) -> WaitingResponse | None:
        return await self._manager.get(waitingResponseInfoKey)
    
    

