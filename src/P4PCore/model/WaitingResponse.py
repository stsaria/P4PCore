import asyncio
from asyncio import Future, InvalidStateError
from asyncio.exceptions import CancelledError, TimeoutError
from typing import Generic, TypeVar

from P4PCore.model.Response import Response
from P4PCore.model.WaitingResponseInfo import WaitingResponseInfo

OI = TypeVar("OI")
RV = TypeVar("RV")

class WaitingResponse(Generic[OI, RV]):
    def __init__(self, waitingResponseInfo:WaitingResponseInfo, otherInfo:OI=None):
        self._waitingResponseInfo:WaitingResponseInfo = waitingResponseInfo
        self._otherInfo:OI = otherInfo
        self._responseFuture:Future[Response[RV] | None] = Future()
    def setResponse(self, response:Response[RV] | None) -> bool:
        try:
            self._responseFuture.set_result(response)
            return True
        except InvalidStateError:
            return False
    async def waitAndGet(self, timeoutSec:float | None=None) -> Response[RV] | None:
        try:
            return await asyncio.wait_for(self._responseFuture, timeout=timeoutSec)
        except (TimeoutError, CancelledError):
            return None
    @property
    def waitingResponseInfo(self) -> WaitingResponseInfo:
        return self._waitingResponseInfo
    @property
    def otherInfo(self) -> OI:
        return self._otherInfo
    def __bool__(self) -> bool:
        return not self._responseFuture.done()
    