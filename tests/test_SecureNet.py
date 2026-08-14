from uuid import uuid4

from P4PCore.P4PRunner import P4PRunner
from P4PCore.abstract.NetHandler import NetHandler

from P4PCore.model.NodeIdentify import NodeIdentify
import pytest
import asyncio

class TestSecureNet:
    @pytest.mark.asyncio
    async def testSecureNetRegisterHandler(self):
        runner = await P4PRunner.create()
        
        class DummyHandler(NetHandler):
            async def handle(self, data: bytes, addr: tuple[str, int]) -> None:
                pass
        
        handler = DummyHandler()
        flag = uuid4()
        assert await runner.secureUserNet.registerHandler(flag, handler)

class TestSecureNetCommunication:
    @pytest.mark.asyncio
    async def testSecureNetHello(self):
        runner = await P4PRunner.create()
        secureNet = runner.secureNet
        await runner.begin()
        await asyncio.sleep(0.1)

        runner2 = await P4PRunner.create()
        secureNet2 = runner2.secureNet
        await runner2.begin()
        await asyncio.sleep(0.1)

        assert await secureNet2.hello(
            NodeIdentify(
                ip="127.0.0.1",
                port=runner.net._protocolV4.transport.get_extra_info("sockname")[1],
                hashableEd25519PublicKey=runner.ed25519Signer.publicKey
            )
        ) == runner2.secureNet.HelloResult.SUCCESS
        await asyncio.sleep(0.1)
        assert await secureNet.getAddrs()
        assert await secureNet2.getAddrs()
    @pytest.mark.asyncio
    async def testSecureUserNetCommunication(self):
        runner = await P4PRunner.create()
        class TestNetHandler(NetHandler):
            def __init__(self):
                self.receivedData = []
                self.receivedAddr = []

            async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
                self.receivedData.append(data)
                self.receivedAddr.append(addr)
        handler = TestNetHandler()
        handlerFlag = uuid4()
        assert await runner.secureUserNet.registerHandler(handlerFlag.bytes, handler)
        await runner.begin()
        await asyncio.sleep(0.1)

        runner2 = await P4PRunner.create()
        secureNet2 = runner2.secureNet
        await runner2.begin()
        await asyncio.sleep(0.1)

        netNI = NodeIdentify(
            ip="127.0.0.1",
            port=runner.net._protocolV4.transport.get_extra_info("sockname")[1],
            hashableEd25519PublicKey=runner.ed25519Signer.publicKey
        )
        await secureNet2.hello(netNI)
        await asyncio.sleep(0.1)
        
        data = b"Hello, SecureNet!"
        assert await secureNet2.sendToSecure(handlerFlag.bytes+data, netNI)
        await asyncio.sleep(0.1)
        assert handler.receivedData
        assert handler.receivedAddr
