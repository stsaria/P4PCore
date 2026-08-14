import pytest
import asyncio

from P4PCore.P4PRunner import P4PRunner
from P4PCore.abstract.NetHandler import NetHandler
from P4PCore.core.Net import Net
from P4PCore.manager.Events import Events
from P4PCore.protocol.Protocol import PacketElementSize, PacketFlag
from P4PCore.util.BytesCoverter import itob

class TestNet:
    @pytest.mark.asyncio
    async def testNetCreate(self):
        net = Net(Events())
        assert net.isRunning() is False

    @pytest.mark.asyncio
    async def testNetBeginAndEnd(self):
        net = Net(Events())
        
        await net.begin()
        assert net.isRunning() is True
        
        await net.end()
        await asyncio.sleep(0.1)
        assert net.isRunning() is False

    @pytest.mark.asyncio
    async def testNetSendToWithoutStart(self):
        net = Net(Events())
        net.v4ListeningAddr = ("127.0.0.1", 0)
        net.v6ListeningAddr = ("::1", 0)
        
        assert not (net.sendTo(b"test", ("127.0.0.1", 8080)) and net.sendTo(b"test", ("::1", 8080)))

    @pytest.mark.asyncio
    async def testNetSendToAfterStart(self):
        net = Net(Events())
        net.v4ListeningAddr = ("127.0.0.1", 0)
        net.v6ListeningAddr = ("::1", 0)
        
        await net.begin()
        
        assert net.sendTo(b"test", ("127.0.0.1", 8080)) and net.sendTo(b"test", ("::1", 8080))
        
        await net.end()
        await asyncio.sleep(0.1)

class TestNetHandlerCommunication:
    @pytest.mark.asyncio
    async def testFullCommunication(self):
        net = Net(Events())

        class TestNetHandler(NetHandler):
            def __init__(self):
                self.receivedData = []

            async def handle(self, data: bytes, _: tuple[str, int]) -> None:
                self.receivedData.append(data)
        handler = TestNetHandler()
        assert await net.registerHandler(handler)

        await net.begin()
        await asyncio.sleep(0.1)
        assert net.isRunning()

        net2 = Net(Events())
        await net2.begin()
        await asyncio.sleep(0.1)
        assert net2.isRunning()

        testData = b"Hello, Net!"

        assert net2.sendTo(testData, net._protocolV4.transport.get_extra_info("sockname"))
        await asyncio.sleep(0.1)
        assert len(handler.receivedData) == 1
        assert handler.receivedData[0] == testData
