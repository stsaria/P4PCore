import asyncio

import pytest


from P4PCore.P4PRunner import P4PRunner
from P4PCore.event.SecureNetStartedToHelloOnRecver import SecureNetStartedToHelloOnRecver
from P4PCore.manager.Events import EventListener
from P4PCore.model.NodeIdentify import NodeIdentify
from P4PCore.event.SecureNetFinishedToHelloOnRecverEvent import SecureNetFinishedToHelloOnRecverEvent, SecureNetFinishedToHelloOnRecverEventResult
from P4PCore.protocol.Protocol import ModeFlag, PacketFlag, SecurePacketElementSize, ANY_UNIQUE_RANDOM_BYTES_SIZE
from P4PCore.util.BytesCoverter import itob

class TestSecureNetFinishedToHelloOnRecverEvent:
    @pytest.mark.asyncio
    async def testSuccessSecureNetHello(self):
        runner = P4PRunner()

        l = []

        class OnSecureNetFinishedToHelloOnRecverListener:
            @EventListener
            async def onSecureNetFinishedToHelloOnRecver(self, event:SecureNetFinishedToHelloOnRecverEvent) -> None:
                if event.result != SecureNetFinishedToHelloOnRecverEventResult.SUCCESS:
                    return
                l.append(1)
        
        runner.eventsManager.registerListener(OnSecureNetFinishedToHelloOnRecverListener())
        
        await runner.begin()

        runner2 = P4PRunner()
        await runner2.begin()

        addr = runner.net._protocolV4.transport.get_extra_info("sockname")

        assert await runner2.secureNet.hello(
            NodeIdentify(
                ip=addr[0],
                port=addr[1],
                hashableEd25519PublicKey=runner.ed25519Signer.publicKey
            )
        ) == runner.secureNet.HelloResult.SUCCESS

        await asyncio.sleep(0.1)

        assert l == [1]