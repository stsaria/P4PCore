from __future__ import annotations
import asyncio
from asyncio import DatagramTransport, DatagramProtocol, Semaphore

from P4PCore.abstract.HasLoop import HasLoop
from P4PCore.abstract.NetHandler import NetHandler
from P4PCore.abstract.NetHandlerRegistry import NetHandlerRegistry
from P4PCore.event.NetOccurredUnhandledExceptionEvent import NetOccurredUnhandledExceptionEvent
from P4PCore.manager.Events import Events
from P4PCore.manager.SimpleImpls import SimpleSetManager
from P4PCore.protocol.Protocol import MAGIC, SOCKET_BUFFER

class NetServerProtocol(DatagramProtocol):
    def __init__(self, net:Net):
        self._net:Net = net

        self.transport:DatagramTransport = None
    def connection_made(self, transport:DatagramTransport):
        self.transport = transport
    async def _arecved(self, data:bytes, addr:tuple[str, int], recvedTime:float) -> None:
        async with self._net._sem:
            try:
                for handler in await self._net._handlers.getAll():
                    await handler.handle(data, addr)
            except Exception as e:
                await self._net._events.triggerEvent(NetOccurredUnhandledExceptionEvent(e, data, addr, recvedTime))
    def datagram_received(self, data:bytes, addr:tuple[str, int]) -> None:
        recvedTime = asyncio.get_running_loop().time()
        if len(data) > SOCKET_BUFFER:
            return
        elif data[:len(MAGIC)] != MAGIC:
            return
        asyncio.create_task(self._arecved(data[len(MAGIC):], addr, recvedTime))

class Net(NetHandlerRegistry, HasLoop):
    def __init__(self, events:Events) -> None:
        self._events:Events = events

        self._handlers:SimpleSetManager[NetHandler] = SimpleSetManager()

        self._protocolV4:NetServerProtocol = None
        self._protocolV6:NetServerProtocol = None

        self._v4ListeningAddr:tuple[str, int] | None = ("127.0.0.1", 0)
        self._v6ListeningAddr:tuple[str, int] | None = None
        self._semaphoreLimits:int = 100
    @property
    def v4ListeningAddr(self) -> tuple[str, int] | None:
        return self._v4ListeningAddr
    @v4ListeningAddr.setter
    def v4ListeningAddr(self, addr:tuple[str, int] | None) -> None:
        self._v4ListeningAddr = addr
    @property
    def v6ListeningAddr(self) -> tuple[str, int] | None:
        return self._v6ListeningAddr
    @v6ListeningAddr.setter
    def v6ListeningAddr(self, addr:tuple[str, int] | None) -> None:
        self._v6ListeningAddr = addr
    @property
    def semaphoreLimits(self) -> int:
        return self._semaphoreLimits
    @semaphoreLimits.setter
    def semaphoreLimits(self, semaphoreLimits:int) -> int:
        self._semaphoreLimits = semaphoreLimits
    async def registerHandler(self, handler:NetHandler) -> bool:
        return await self._handlers.add(handler)
    def sendTo(self, data:bytes, addr:tuple[str, int]) -> bool:
        """
        Send data to the specified address. The address can be either IPv4 or IPv6. The data will be sent with a magic prefix to ensure that it is recognized by the receiving end.
        """
        if not (p := (self._protocolV6 if ':' in addr[0] else self._protocolV4)):
            return False
        elif not (t := p.transport):
            return False
        t.sendto(MAGIC+data, addr)
        return True

    def isRunning(self) -> bool:
        """
        Check if the Net server is running. It checks both IPv4 and IPv6 protocols to determine if either is active. If either protocol is running, the server is considered to be running.
        """
        v4Running = v4T.is_closing() is False if ((v4 := self._protocolV4) and (v4T := v4.transport)) else False
        v6Running = v6T.is_closing() is False if ((v6 := self._protocolV6) and (v6T := v6.transport)) else False
        return v4Running or v6Running # If v4Running is False and v4is_closing() is True, v6 may be not supported by system but net is still running, so use "or" instead of "and". The opposite is a very special enviroment at present but this line may be correct for the future.

    async def begin(self) -> None:
        loop = asyncio.get_running_loop()
        self._sem = Semaphore(self._semaphoreLimits)
        
        if self.v4ListeningAddr:
            _, self._protocolV4 = await loop.create_datagram_endpoint(
                lambda: NetServerProtocol(self),
                local_addr=self._v4ListeningAddr
            )
        if self.v6ListeningAddr:
            _, self._protocolV6 = await loop.create_datagram_endpoint(
                lambda: NetServerProtocol(self),
                local_addr=self._v6ListeningAddr
            )
    
    async def end(self) -> None:
        if (v4 := self._protocolV4) and (v4T := v4.transport):
            v4T.close()
        if (v6 := self._protocolV6) and (v6T := v6.transport):
            v6T.close()