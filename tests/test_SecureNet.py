from uuid import uuid4

from P4PCore.P4PRunner import P4PRunner
from P4PCore.abstract.NetHandler import NetHandler

from P4PCore.model.NodeIdentify import NodeIdentify
import pytest
import asyncio

class TestSecureNet:
    def testSecureNetRegisterHandler(self):
        runner = P4PRunner()
        
        class DummyHandler(NetHandler):
            async def handle(self, data: bytes, addr: tuple[str, int]) -> None:
                pass
        
        handler = DummyHandler()
        flag = uuid4()
        assert runner.secureUserNet.registerHandler(flag, handler)

class TestSecureNetCommunication:
    @pytest.mark.asyncio
    async def testSecureNetHello(self):
        runner = P4PRunner()
        secureNet = runner.secureNet
        await runner.begin()
        await asyncio.sleep(0.1)

        runner2 = P4PRunner()
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
        assert secureNet.confirmedAddrsToEd25519PublicKeys
        assert secureNet2.confirmedAddrsToEd25519PublicKeys
    @pytest.mark.asyncio
    async def testSecureUserNetCommunication(self):
        runner = P4PRunner()
        class TestNetHandler(NetHandler):
            def __init__(self):
                self.receivedData = []
                self.receivedAddr = []

            async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
                self.receivedData.append(data)
                self.receivedAddr.append(addr)
        handler = TestNetHandler()
        assert runner.secureNet.registerHandler(handler)
        await runner.begin()

        runner2 = P4PRunner()
        secureNet2 = runner2.secureNet
        await runner2.begin()

        netNI = NodeIdentify(
            ip="127.0.0.1",
            port=runner.net._protocolV4.transport.get_extra_info("sockname")[1],
            hashableEd25519PublicKey=runner.ed25519Signer.publicKey
        )
        assert await secureNet2.hello(netNI) == secureNet2.HelloResult.SUCCESS

        await asyncio.sleep(0.1)

        assert runner.secureNet.confirmedAddrsToEd25519PublicKeys
        assert secureNet2.confirmedAddrsToEd25519PublicKeys
        
        data = b"Hello, SecureNet!"
        assert secureNet2.sendToSecure(data, netNI) == secureNet2.SendToSecureResult.SUCCESS

        await asyncio.sleep(0.1)

        assert handler.receivedData
        assert handler.receivedAddr
