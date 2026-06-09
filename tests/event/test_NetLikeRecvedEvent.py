import asyncio
import pytest

from P4PCore.P4PRunner import P4PRunner
from P4PCore.model.NodeIdentify import NodeIdentify
from P4PCore.event.NetLikeRecvedEvent import NetLikeRecvedEvent
from P4PCore.manager.Events import EventListener

class TestNetLikeRecvedEvent:
    @pytest.mark.asyncio
    async def testNetRecved(self):
        runner = await P4PRunner.create()

        data = b"test"
        l = []

        class OnNetRecvedListener:
            @EventListener
            async def onNetRecved(self, event:NetLikeRecvedEvent) -> None:
                if not event.netLikeInst is runner.secureNet.rawNet:
                    return
                elif event.data != data:
                    return
                l.append(1)
        await runner.eventsManager.registerListener(OnNetRecvedListener())
        await runner.begin()

        runner2 = await P4PRunner.create()
        await runner2.begin()

        runner2.secureNet.rawNet.sendTo(data, runner.secureNet.rawNet._protocolV4.transport.get_extra_info("sockname"))
        await asyncio.sleep(0.1)
        
        assert l == [1]

    @pytest.mark.asyncio
    async def testNetRecvedCancelled(self):
        runner = await P4PRunner.create()

        class OnNetRecvedListener:
            @EventListener
            async def onNetRecved(self, event:NetLikeRecvedEvent) -> None:
                if not event.netLikeInst is runner.secureNet.rawNet:
                    return
                event.cancel()
        await runner.eventsManager.registerListener(OnNetRecvedListener())
        await runner.begin()

        runner2 = await P4PRunner.create()
        await runner2.begin()
        
        addr = runner.secureNet.rawNet._protocolV4.transport.get_extra_info("sockname")

        assert await runner2.secureNet.hello(
            NodeIdentify(
                ip=addr[0],
                port=addr[1],
                hashableEd25519PublicKey=runner.ed25519Signer.publicKey,
            ),
            timeoutSec=1,
            firstHelloAttempts=1
        ) == runner2.secureNet.HelloResult.FAILED_FIRST_HELLO

    @pytest.mark.asyncio
    async def testSecureNetRecved(self):
        runner = await P4PRunner.create()

        l = []
        
        class OnNetRecvedListener:
            @EventListener
            async def onNetRecved(self, event:NetLikeRecvedEvent) -> None:
                l.append(1)
        await runner.eventsManager.registerListener(OnNetRecvedListener())
        await runner.begin()

        runner2 = await P4PRunner.create()
        await runner2.begin()

        addr = runner.secureNet.rawNet._protocolV4.transport.get_extra_info("sockname")

        assert await runner2.secureNet.hello(
            NodeIdentify(
                ip=addr[0],
                port=addr[1],
                hashableEd25519PublicKey=runner.ed25519Signer.publicKey,
            ),
            timeoutSec=1,
            firstHelloAttempts=1
        ) == runner2.secureNet.HelloResult.SUCCESS
        await asyncio.sleep(0.1)
        assert l

    @pytest.mark.asyncio
    async def testSecureNetRecvedCancelled(self):
        runner = await P4PRunner.create()

        class OnNetRecvedListener:
            @EventListener
            async def onNetRecved(self, event:NetLikeRecvedEvent) -> None:
                if not event.netLikeInst is runner.secureNet:
                    return
                event.cancel()
        await runner.eventsManager.registerListener(OnNetRecvedListener())
        await runner.begin()

        runner2 = await P4PRunner.create()
        await runner2.begin()
        
        addr = runner.secureNet.rawNet._protocolV4.transport.get_extra_info("sockname")

        assert await runner2.secureNet.hello(
            NodeIdentify(
                ip=addr[0],
                port=addr[1],
                hashableEd25519PublicKey=runner.ed25519Signer.publicKey,
            ),
            timeoutSec=1,
            firstHelloAttempts=1
        ) == runner2.secureNet.HelloResult.FAILED_FIRST_HELLO