import asyncio
import os

from manager.SimpleImpls import SimpleKVManager
from manager.WaitingResponses import WaitingResponses
from model.WaitingResponse import WaitingResponse
from model.WaitingResponseInfo import WaitingResponseInfo
from protocol.ProgramProtocol import *
from model.NodeIdentify import NodeIdentify
from core.Net import Net
from model.NetConfig import NetConfig
from protocol.Protocol import *
from util import RedundancyCalc
from util.BytesCoverter import itob, btoi
from abstract.NetHandler import NetHandler

class ExNet(Net, NetHandler):
    def __init__(self, netConfig:NetConfig):
        super().__init__(netConfig)

        self._redundancies:SimpleKVManager[str, int] = SimpleKVManager()
        self.__waitingResponses:WaitingResponses = WaitingResponses()

        asyncio.run(super().registerHandler(PacketFlag.EX, self))
    def _getAddr(self, node:NodeIdentify | tuple[str, int]) -> tuple[str, int]:
        return node.addr if isinstance(node, NodeIdentify) else node
    def sendTo(self, data:bytes, node:NodeIdentify | tuple[str, int]) -> bool:
        return super().sendTo(data, self._getAddr(node) if isinstance(node, NodeIdentify) else node)
    async def sendToIncludeRedundancy(self, data:bytes, node:NodeIdentify | tuple[str, int]) -> None:
        addr = node.addr if isinstance(node, NodeIdentify) else node
        for _ in range(
            r if (r := await self._redundancies.get(addr[0])) else PING_MILLI_SECS_REDUNDANCIES[0][1]
        ): 
            super().sendTo(data, addr)
    async def ping(self, node:NodeIdentify | tuple[str, int]) -> float | None:
        addr = self._getAddr(node)
        s = asyncio.get_running_loop().time()
        async with self.__waitingResponses.open(
            WaitingResponse(
                WaitingResponseInfo(addr),
                sid := os.urandom(ANY_UNIQUE_RANDOM_BYTES_SIZE)
            )
        ) as c:
            self.sendTo(
                (
                    itob(PacketFlag.EX, SecurePacketElementSize.PACKET_FLAG)
                    +itob(PacketModeFlag.PING, SecurePacketElementSize.MODE_FLAG)
                    +sid
                ),
                addr
            )
            if not await c.waitingResponse.waitAndGet(TIME_OUT_MILLI_SEC):
                return None
        return asyncio.get_running_loop().time() - s
    def _setRedudancyForAtomic(self, d:dict[str, int], ip:str, r:int, dUIC:bool) -> bool:
        if dUIC and ip in d:
            return False
        d[ip] = r
        return True
    async def pingAndSetRedundancy(self, node:NodeIdentify | tuple[str, int], dontUpdateIfContains:bool=True) -> bool:
        addr = self._getAddr(node)
        ip = addr[0]
        if await self._redundancies.get(ip) is not None and dontUpdateIfContains: return True
        pings = []
        for _ in range(PING_WINDOW):
            if l := self.ping(addr):
                pings.append(l)
        r:list = [r async for r in asyncio.gather(*(self.ping(addr) for _ in range(PING_WINDOW))) if not r is None]
        if len(pings) <= 0:
            return False
        redundancy = RedundancyCalc.calcRedundancyByPing(
            PING_MILLI_SECS_REDUNDANCIES,
            pings,
            PING_CALC_TRIM_RATIO
        )
        if dontUpdateIfContains and not await self._redundancies.get(addr[0]) is None:
            return False
        await self._redundancies.put(addr[0], redundancy)
        return await self._redundancies.atomic(self._setRedudancyForAtomic, addr[0], )
    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        m = btoi(data[:PacketElementSize.MODE_FLAG], ENDIAN)
        if m == PacketModeFlag.PING.value:
            self.sendTo(
                PacketFlag.EX
                +PacketModeFlag.PONG
                +data[
                    PacketElementSize.PACKET_FLAG
                    +PacketElementSize.MODE_FLAG:
                ],
                addr
            )
        elif m == PacketModeFlag.PONG.value:
            if not await self.__waitingResponses.get(
                (k := 
                    (addr[0],
                        addr[1],
                        self,
                        PacketModeFlag.RESP_HELLO,
                        data[
                            PacketElementSize.PACKET_FLAG
                        +PacketElementSize.MODE_FLAG:
                        ]
                    )
                )
            ) is None:
                await self.__waitingResponses.setValue(k, 1)