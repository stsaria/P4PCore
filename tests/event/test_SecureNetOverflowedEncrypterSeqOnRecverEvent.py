import asyncio

import pytest

from P4PCore.P4PRunner import P4PRunner
from P4PCore.event.SecureNetOverflowedEncrypterSeqOnRecverEvent import SecureNetOverflowedEncrypterSeqOnRecverEvent
from P4PCore.manager.Events import EventListener
from P4PCore.model.NodeIdentify import NodeIdentify
from P4PCore.protocol.Protocol import MAX_SEQ_OF_SECURE_NET

class TestSecureNetOverflowedEncrypterSeqOnRecverEvent:
    @pytest.mark.asyncio
    async def testOverflow(self):
        runner = await P4PRunner.create()
        await runner.begin()

        runner2 = await P4PRunner.create()
        await runner2.begin()

        l = []

        class OnSecureNetOverflowedEncrypterSeqOnRecverListener:
            @EventListener
            async def onSecureNetOverflowedEncrypterSeqOnRecver(self, event:SecureNetOverflowedEncrypterSeqOnRecverEvent) -> None:
                if event.seqWhenOverflowed != MAX_SEQ_OF_SECURE_NET:
                    return
                elif event.decryptedData != b"test":
                    return
                l.append(1)
        await runner.eventsManager.registerListener(OnSecureNetOverflowedEncrypterSeqOnRecverListener())

        addr = runner.net._protocolV4.transport.get_extra_info("sockname")
        await runner2.secureNet.hello(
            NodeIdentify(
                ip=addr[0],
                port=addr[1],
                hashableEd25519PublicKey=runner.ed25519Signer.publicKey
            )
        )

        await asyncio.sleep(0.1)

        encrypter = runner.secureNet._encrypters._dict[runner2.net._protocolV4.transport.get_extra_info("sockname")]
        encrypter._encryptSeqLimits = MAX_SEQ_OF_SECURE_NET-1

        encrypter2 = runner2.secureNet._encrypters._dict[addr]
        encrypter2._seq = MAX_SEQ_OF_SECURE_NET-1
        encrypter2._encryptSeqLimits = MAX_SEQ_OF_SECURE_NET

        await runner2.secureNet.sendToSecure(b"test", addr)

        await asyncio.sleep(0.1)

        assert l == [1]

