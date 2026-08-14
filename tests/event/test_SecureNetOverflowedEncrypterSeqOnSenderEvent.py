import asyncio

import pytest

from P4PCore.P4PRunner import P4PRunner
from P4PCore.event.SecureNetOverflowedEncrypterSeqOnSenderEvent import SecureNetOverflowedEncrypterSeqOnSenderEvent
from P4PCore.manager.Events import EventListener
from P4PCore.model.NodeIdentify import NodeIdentify
from P4PCore.protocol.Protocol import MAX_SEQ_OF_SECURE_NET

class TestSecureNetOverflowedEncrypterSeqOnSenderEvent:
    @pytest.mark.asyncio
    async def testOverflow(self):
        runner = await P4PRunner.create()
        await runner.begin()

        addr = runner.net._protocolV4.transport.get_extra_info("sockname")

        runner2 = await P4PRunner.create()

        l = []

        class OnSecureNetOverflowedEncrypterSeqOnSenderListener:
            @EventListener
            async def onSecureNetOverflowedEncrypterSeqOnSender(self, event:SecureNetOverflowedEncrypterSeqOnSenderEvent) -> None:
                if event.seqWhenOverflowed != MAX_SEQ_OF_SECURE_NET+1:
                    return
                elif event.originalData != b"test":
                    return
                elif event.addr != addr:
                    return
                l.append(1)
        await runner2.eventsManager.registerListener(OnSecureNetOverflowedEncrypterSeqOnSenderListener())

        await runner2.begin()

        addr = runner.net._protocolV4.transport.get_extra_info("sockname")
        await runner2.secureNet.hello(
            NodeIdentify(
                ip=addr[0],
                port=addr[1],
                hashableEd25519PublicKey=runner.ed25519Signer.publicKey
            )
        )

        runner2.secureNet._encrypters._dict[addr]._seq = MAX_SEQ_OF_SECURE_NET
        await runner2.secureNet.sendToSecure(b"test", addr)

        assert l == [1]

