import asyncio
from asyncio import BaseEventLoop, Event, Task
from collections.abc import Callable
from typing import Any, ParamSpec

from cachetools import TTLCache

from P4PCore.core.Net import Net
from P4PCore.core.UserNet import UserNet
from P4PCore.common.manager.WaitingResponses import WaitingResponses
from P4PCore.common.model.Response import Response
from P4PCore.common.model.WaitingResponse import WaitingResponse
from P4PCore.common.model.WaitingResponseInfo import WaitingResponseInfo
from P4PCore.core.protocol.Protocol import *
from P4PCore.common.util import BytesSplitter
from P4PCore.common.util.BytesCoverter import *
from P4PCore.core.abstract.NetHandler import NetHandler

A = ParamSpec("A")

class PingPongNet(NetHandler):
    """
    Provide a simple ping-pong request/response protocol over the main network.
    """
    def __init__(
        self,
        net:Net,
        userNet:UserNet,
        pingAliveTimeSeconds:float=5.0,
        pingResponsesStorageMaxSize:int=1000,
        reuseAliveTimeSeconds:float=30.0,
        aliveStorageNodesCount:int=1000
    ):
        """
        Create a ping-pong network handler and register it with the user network.
        :param net: The underlying network instance through which ping and pong packets are sent.
        :param userNet: The user network registry used to register this handler.
        :param pingAliveTimeSeconds: The time in seconds to wait for ping responses (> 0).
        :param pingResponsesStorageMaxSize: The maximum size of the waiting responses cache (> 0).
        :param reuseAliveTimeSeconds: The TTL in seconds for reusing alive node results (> 0).
        :param aliveStorageNodesCount: The maximum number of stored alive nodes (> 0).
        """
        if pingAliveTimeSeconds <= 0:
            raise ValueError("pingAliveTimeSeconds > 0")
        elif pingResponsesStorageMaxSize <= 0:
            raise ValueError("pingResponsesStorageMaxSize > 0")
        elif reuseAliveTimeSeconds <= 0:
            raise ValueError("reuseAliveTimeSeconds > 0")
        elif aliveStorageNodesCount <= 0:
            raise ValueError("aliveStorageNodesCount > 0")
        
        self._net:Net = net
        
        self._waitingResponses:WaitingResponses = WaitingResponses(
            mapping=TTLCache(
                pingResponsesStorageMaxSize,
                pingAliveTimeSeconds
            )
        )
        self._aliveNodesAndFoundTimes:TTLCache[tuple[str, int], None] = TTLCache(
            aliveStorageNodesCount,
            reuseAliveTimeSeconds
        )
        self._pingQueue:set[tuple[tuple[str, int], Callable[A, None], bool, tuple[Any, ...]]] = set()
        self._endEvent:Event = Event()
        self._pingDataReadyEvent:Event = Event()
        self._pingLoopTask:Task | None = None

        self._pingAliveTimeSeconds = pingAliveTimeSeconds

        if not userNet.registerHandler(itob(PacketFlag.PINGPONG, PacketElementSize.PACKET_FLAG), self):
            raise Exception("Cannot register for NetHandler. May be another handler registered for the same flag.")

    def pingWithCallback(self, addr:tuple[str, int], reusePreviousResult:bool, callback:Callable[A, None], *args:A.args) -> None:
        """
        Send a ping with a callback to the specified address.
        :param addr: The target address to ping.
        :param reusePreviousResult: Whether to reuse previous alive result if available.
        :param callback: The callback function to execute.
        :param *args: Arguments for the callback function (You must set hashable values).
        :return: None
        """
        self._pingQueue.add((addr, callback, reusePreviousResult, args))
        self._pingDataReadyEvent.set()
    
    async def ping(self, addr:tuple[str, int], timeoutSeconds:float | None = None, loop:BaseEventLoop | None = None) -> float | None:
        """
        Send a ping to the specified address and wait for a pong response.
        You can't wait for response longer than pingAliveTimeSeconds by this function.
        :param addr: The target address to ping.
        :param timeoutSeconds: The maximum time allowed to wait for a pong response. (<= pingAliveTimeSeconds in __init__ args)
        :param loop: The event loop to use.
        :return: The round-trip time in seconds, or None if no response is received.
        """
        loop = loop or asyncio.get_running_loop()
        future = loop.create_future()
        now = loop.time()
        self.pingWithCallback(addr, False, future.set_result, None)
        timeoutSeconds = (
            self._pingAliveTimeSeconds if timeoutSeconds is None
            else min(timeoutSeconds, self._pingAliveTimeSeconds)
        )
        try:
            await asyncio.wait_for(future, timeoutSeconds)
            return loop.time() - now
        except TimeoutError:
            return None

    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        now = asyncio.get_running_loop().time()
        if len(data) < (
            PacketElementSize.MODE_FLAG
            +PacketElementSize.RESPONSE_IDENTIFY
        ):
            return
        modeFlag, responseId = BytesSplitter.split(
            data,
            PacketElementSize.MODE_FLAG,
            PacketElementSize.RESPONSE_IDENTIFY
        )
        modeFlag = btoi(modeFlag)
        if modeFlag == ModeFlag.PING.value:
            self._net.sendTo(
                itob(PacketFlag.PINGPONG, PacketElementSize.PACKET_FLAG)
                +itob(ModeFlag.PONG, PacketElementSize.MODE_FLAG)
                +responseId,
                addr
            )
        elif modeFlag == ModeFlag.PONG.value:
            if waitingResponse := self._waitingResponses.get((addr, responseId)):
                waitingResponse.setResponse(Response(now))
                self._aliveNodesAndFoundTimes[addr] = None

    async def _pingLoop(self) -> None:
        while not self._endEvent.is_set():
            if not self._pingQueue:
                await self._pingDataReadyEvent.wait()
                self._pingDataReadyEvent.clear()
                if self._endEvent.is_set():
                    break
                continue
            addr, callback, reusePreviousResult, args = self._pingQueue.pop()
            if addr in self._aliveNodesAndFoundTimes and reusePreviousResult:
                callback(*args)
                continue
            waitingResponse = WaitingResponse(WaitingResponseInfo(addr))
            if not self._net.sendTo(
                itob(PacketFlag.PINGPONG, PacketElementSize.PACKET_FLAG)
                +itob(ModeFlag.PING, PacketElementSize.MODE_FLAG)
                +waitingResponse.waitingResponseInfo.identify,
                addr
            ):
                continue
            self._waitingResponses.add(waitingResponse)
            waitingResponse.setCallback(callback, *args)

    async def begin(self) -> None:
        """
        Begin the loop for ping.
        """
        self._pingLoopTask = asyncio.create_task(self._pingLoop())

    async def end(self) -> None:
        """
        End the loop for ping.
        """
        if not self._pingLoopTask:
            return
        self._endEvent.set()
        self._pingDataReadyEvent.set()
        await self._pingLoopTask