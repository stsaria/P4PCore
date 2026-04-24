import asyncio
from asyncio import Future

from src.P4PCore.model.Response import Response
from src.P4PCore.model.WaitingResponseInfo import WaitingResponseInfo

class WaitingResponse[OI, RV]:
    def __init__(self, waitingResponseInfo:WaitingResponseInfo, otherInfo:OI=None):
        self._waitingResponseInfo:WaitingResponseInfo = waitingResponseInfo
        self._otherInfo:OI = otherInfo
        self._responseF:Future[Response[RV]] = Future()
    def setResponse(self, response:Response[RV]) -> bool:
        try:
            self._responseF.set_result(response)
            return True
        except Exception:
            return False
    async def waitAndGet(self, timeoutSec:float | None=None) -> Response[RV]:
        return await asyncio.wait_for(self._responseF, timeout=timeoutSec)
    @property
    def waitingResponseInfo(self) -> WaitingResponseInfo:
        return self._waitingResponseInfo
    @property
    def otherInfo(self) -> OI:
        return self._otherInfo
    def __bool__(self) -> bool:
        return not self._responseF.done()
    