import asyncio

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
    """
    Provide a simple ping-pong request/response protocol over the main network.
    """
    def __init__(self, net:Net, userNet:UserNet):
        """
        Create a ping-pong network handler and register it with the user network.
        :param net: The underlying network instance through which ping and pong packets are sent.
        :param userNet: The user network registry used to register this handler.
        :return: The initialized PingPongNet instance.
        """
        self._net:Net = net
        self._waitingResponses:WaitingResponses = WaitingResponses()

        if not userNet.registerHandler(itob(PacketFlag.PINGPONG, PacketElementSize.PACKET_FLAG), self):
            raise Exception("Cannot register for NetHandler. May be another handler registered for the same flag.")
    
    async def ping(self, addr:tuple[str, int], timeoutSeconds:int | None = None) -> float | None:
        """
        Send a ping to the specified address and wait for a pong response.
        :param addr: The target address to ping.
        :param timeoutSecs: The maximum time allowed to wait for a pong response.
        :return: The round-trip time in seconds, or None if no response is received.
        """
        with self._waitingResponses.open(
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
            if not (r := await c.waitingResponse.waitAndGet(timeoutSeconds)):
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
            if waitingResponse := self._waitingResponses.get((addr, responseId)):
                waitingResponse.setResponse(Response(now))

