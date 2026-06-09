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
        runner = await P4PRunner.create()

        l = []

        class OnSecureNetFinishedToHelloOnRecverListener:
            @EventListener
            async def onSecureNetFinishedToHelloOnRecver(self, event:SecureNetFinishedToHelloOnRecverEvent) -> None:
                if event.result != SecureNetFinishedToHelloOnRecverEventResult.SUCCESS:
                    return
                l.append(1)
        
        await runner.eventsManager.registerListener(OnSecureNetFinishedToHelloOnRecverListener())
        
        await runner.begin()

        runner2 = await P4PRunner.create()
        await runner2.begin()

        addr = runner.secureNet.rawNet._protocolV4.transport.get_extra_info("sockname")

        assert await runner2.secureNet.hello(
            NodeIdentify(
                ip=addr[0],
                port=addr[1],
                hashableEd25519PublicKey=runner.ed25519Signer.publicKey
            )
        ) == runner.secureNet.HelloResult.SUCCESS

        await asyncio.sleep(0.1)

        assert l == [1]
    
    @pytest.mark.asyncio
    async def testFailedChallengeSecureNetHello(self):
        runner = await P4PRunner.create()

        l = []

        class OnSecureNetFinishedToHelloOnRecverListener:
            @EventListener
            async def onSecureNetStartedToHelloOnRecver(self, event:SecureNetStartedToHelloOnRecver) -> None:
                event.timeoutSecOnHello = 0.5
            @EventListener
            async def onSecureNetFinishedToHelloOnRecver(self, event:SecureNetFinishedToHelloOnRecverEvent) -> None:
                if event.result != SecureNetFinishedToHelloOnRecverEventResult.FAILED_CHALLENGE:
                    return
                l.append(1)
        
        await runner.eventsManager.registerListener(OnSecureNetFinishedToHelloOnRecverListener())
        await runner.begin()

        runner2 = await P4PRunner.create()
        await runner2.begin()

        runner2.secureNet.rawNet.sendTo(
            itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
            +itob(ModeFlag.HELLO, SecurePacketElementSize.MODE_FLAG)
            +b"\x00" * (
                SecurePacketElementSize.RESPONSE_IDENTIFY
                +ANY_UNIQUE_RANDOM_BYTES_SIZE
            )
            +runner2.ed25519Signer.publicKey.publicKeyBytes,
            runner.secureNet.rawNet._protocolV4.transport.get_extra_info("sockname")
        )

        await asyncio.sleep(1)

        assert l == [1]