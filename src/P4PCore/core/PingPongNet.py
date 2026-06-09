import asyncio

from P4PCore.core.Net import Net
from P4PCore.event.NetLikeRecvedEvent import NetLikeRecvedEvent
from P4PCore.manager.Events import EventListener, Events
from P4PCore.manager.WaitingResponses import WaitingResponses
from P4PCore.model.Response import Response
from P4PCore.model.WaitingResponse import WaitingResponse
from P4PCore.model.WaitingResponseInfo import WaitingResponseInfo
from P4PCore.protocol.Protocol import *
from P4PCore.util import BytesSplitter
from P4PCore.util.BytesCoverter import *

class PingPongNet:
    _net:Net
    _events:Events
    _waitingResponses:WaitingResponses
    @classmethod
    async def create(cls, net:Net, events:Events) -> "PingPongNet":
        inst = cls()

        inst._net = net
        inst._events = events
        inst._waitingResponses = WaitingResponses()

        await events.registerListener(inst)

        return inst
    
    async def ping(self, addr:tuple[str, int], timeoutSecs:int | None = None) -> float | None:
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
    @EventListener
    async def recvedNet(self, event:NetLikeRecvedEvent) -> None:
        if not event.netLikeInst is self._net:
            return
        
        data, addr = event.data, event.addr
        if len(data) < (
            PacketElementSize.PACKET_FLAG
            +PacketElementSize.MODE_FLAG
            +PacketElementSize.RESPONSE_IDENTIFY
        ):
            return
        packetFlag, modeFlag, responseId = BytesSplitter.split(
            data,
            PacketElementSize.PACKET_FLAG,
            PacketElementSize.MODE_FLAG,
            PacketElementSize.RESPONSE_IDENTIFY
        )
        if btoi(packetFlag) != PacketFlag.PINGPONG.value:
            return
        
        modeFlag = btoi(modeFlag)

        if modeFlag == ModeFlag.PING.value:
            self._net.sendTo(
                packetFlag
                +itob(ModeFlag.PONG, PacketElementSize.MODE_FLAG)
                +responseId,
                addr
            )
        elif modeFlag == ModeFlag.PONG.value:
            if wR := await self._waitingResponses.get((addr, responseId)):
                wR.setResponse(Response(event.recvedTime))

        event.cancel()


