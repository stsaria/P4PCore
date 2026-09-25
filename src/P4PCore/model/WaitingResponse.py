import asyncio
from asyncio import Future, InvalidStateError
from asyncio.exceptions import CancelledError, TimeoutError
from typing import Generic, TypeVar

from P4PCore.model.Response import Response
from P4PCore.model.WaitingResponseInfo import WaitingResponseInfo

OI = TypeVar("OI")
RV = TypeVar("RV")

class WaitingResponse(Generic[OI, RV]):
    """
    Represent a pending response whose value will be resolved later.
    """
    def __init__(self, waitingResponseInfo:WaitingResponseInfo, otherInfo:OI=None):
        """
        Initialize the pending response with metadata and a future for the eventual result.
        :param waitingResponseInfo: The metadata used to identify the waiting response.
        :param otherInfo: Optional extra information associated with the response.
        """
        self._waitingResponseInfo:WaitingResponseInfo = waitingResponseInfo
        self._otherInfo:OI = otherInfo
        self._responseFuture:Future[Response[RV] | None] = Future()
    def setResponse(self, response:Response[RV] | None) -> bool:
        """
        Set the eventual response for this waiting call.
        :param response: The response to resolve with, or None if no response is available.
        :return: True if the value was set successfully, otherwise False if it was already resolved.
        """
        try:
            self._responseFuture.set_result(response)
            return True
        except InvalidStateError:
            return False
    async def waitAndGet(self, timeoutSec:float | None=None) -> Response[RV] | None:
        """
        Wait for the response to arrive until the timeout expires.
        :param timeoutSec: The maximum time to wait in seconds, or None for no timeout.
        :return: The response value if it arrives in time, otherwise None.
        """
        try:
            return await asyncio.wait_for(self._responseFuture, timeout=timeoutSec)
        except (TimeoutError, CancelledError):
            return None
    @property
    def waitingResponseInfo(self) -> WaitingResponseInfo:
        """
        The metadata object used to identify this waiting response.
        """
        return self._waitingResponseInfo
    @property
    def otherInfo(self) -> OI:
        """
        The extra information associated with this waiting response.
        """
        return self._otherInfo
    def __bool__(self) -> bool:
        return not self._responseFuture.done()
    