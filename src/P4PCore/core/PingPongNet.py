import asyncio
import logging
import sys

from P4PCore.core.Net import Net
from P4PCore.core.UserNet import UserNet
from P4PCore.manager.WaitingResponses import WaitingResponses
from P4PCore.model.Response import Response
from P4PCore.model.WaitingResponse import WaitingResponse
from P4PCore.model.WaitingResponseInfo import WaitingResponseInfo
from P4PCore.protocol.Protocol import *
from P4PCore.util import BytesSplitter
from P4PCore.util.BytesCoverter import *
from P4PCore.abstract.NetHandler import NetHandler

class PingPongNet(NetHandler):
    _net:Net
    _waitingResponses:WaitingResponses
    @classmethod
    async def create(cls, net:Net, userNet:UserNet) -> "PingPongNet":
        inst = cls()

        inst._net = net
        inst._waitingResponses = WaitingResponses()

        if not await userNet.registerHandler(itob(PacketFlag.PINGPONG, PacketElementSize.PACKET_FLAG), inst):
            raise Exception("Cannot register for NetHandler. May be another handler registered for the same flag.")

        return inst
    
    async def ping(self, addr:tuple[str, int], timeoutSecs:int | None = None) -> float | None:
        """
        Send a ping to the specified address and wait for a pong response. The method returns the round-trip time in seconds if the pong is received within the specified timeout. If the pong is not received within the timeout or if there is an error sending the ping, the method returns None.
        """
        async with self._waitingResponses.open(
            WaitingResponse(WaitingResponseInfo(addr))
        ) as c:
            startTime = asyncio.get_running_loop().time()
            if not self._net.sendTo(
                itob(PacketFlag.PINGPONG, PacketElementSize.PACKET_FLAG)
                +itob(ModeFlag.PING, PacketElementSize.MODE_FLAG)
                +c.waitingResponse.waitingResponseInfo.identify,
                addr
            ):
                return None
            if not (r := await c.waitingResponse.waitAndGet(timeoutSecs)):
                return None
            return r.value - startTime
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
            if waitingResponse := await self._waitingResponses.get((addr, responseId)):
                waitingResponse.setResponse(Response(now))

