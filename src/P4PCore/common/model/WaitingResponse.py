import asyncio
from asyncio import AbstractEventLoop, Future, InvalidStateError
from asyncio.exceptions import CancelledError, TimeoutError
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from P4PCore.common.model.Response import Response
from P4PCore.common.model.WaitingResponseInfo import WaitingResponseInfo

A = ParamSpec("A")

OI = TypeVar("OI")
RV = TypeVar("RV")

class WaitingResponse[OI, RV]:
    """
    Represent a pending response whose value will be resolved later.
    """
    def __init__(self, waitingResponseInfo:WaitingResponseInfo, otherInfo:OI=None, loop:AbstractEventLoop | None=None):
        """
        Initialize the pending response with metadata and a future for the eventual result.
        You must call this function in main loop or make explicit by loop param. 
        :param waitingResponseInfo: The metadata used to identify the waiting response.
        :param otherInfo: Optional extra information associated with the response.
        :param loop: Main loop. If you call this function out main loop, you can make explicit by this param.
        """
        self._waitingResponseInfo:WaitingResponseInfo = waitingResponseInfo
        self._otherInfo:OI = otherInfo
        self._loop:AbstractEventLoop = loop or asyncio.get_running_loop()
        self._responseFuture:Future[Response[RV] | None] = self._loop.create_future()
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
    def newFuture(self) -> None:
        """
        Remake a waiting future.
        """
        self._responseFuture = self._loop.create_future()
    async def waitAndGet(self, timeoutSeconds:float | None = None) -> Response[RV] | None:
        """
        Wait for the response to arrive until the timeout expires.
        :param timeoutSeconds: The maximum time to wait in seconds, or None for no timeout.
        :return: The response value if it arrives in time, otherwise None.
        """
        try:
            return await asyncio.wait_for(self._responseFuture, timeout=timeoutSeconds)
        except (TimeoutError, CancelledError):
            return None
    def setCallback(self, callback:Callable[A, Any], *args:A.args) -> None:
        def cb(_):
            callback(*args)
        self._responseFuture.add_done_callback(cb)
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
    