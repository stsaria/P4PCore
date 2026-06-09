import os
import asyncio
from logging import Logger
from enum import auto as a
from typing import Awaitable, Callable
from uuid import UUID

from P4PCore.event.NetLikeRecvedEvent import NetLikeRecvedEvent
from P4PCore.event.SecureNetFinishedToHelloOnRecverEvent import SecureNetFinishedToHelloOnRecverEvent, SecureNetFinishedToHelloOnRecverEventResult
from P4PCore.event.NetOccurredUnhandledExceptionEvent import NetOccurredUnhandledExceptionEvent
from P4PCore.event.SecureNetOverflowedEncrypterSeqOnRecverEvent import SecureNetOverflowedEncrypterSeqOnRecverEvent
from P4PCore.event.SecureNetOverflowedEncrypterSeqOnSenderEvent import SecureNetOverflowedEncrypterSeqOnSenderEvent
from P4PCore.event.SecureNetStartedToHelloOnRecver import SecureNetStartedToHelloOnRecver
from P4PCore.manager.Events import Events
from P4PCore.exception import CancelException
from P4PCore.model.Ed25519Signer import Ed25519Signer
from P4PCore.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.abstract.NetHandler import NetHandler
from P4PCore.interface.NetHandlerRegistry import NetHandlerRegistry
from P4PCore.model.Response import Response
from P4PCore.model.NodeIdentify import NodeIdentify
from P4PCore.manager.WaitingResponses import WaitingResponses
from P4PCore.model.WaitingResponse import WaitingResponse
from P4PCore.model.WaitingResponseInfo import WaitingResponseInfo, WAITING_RESPONSE_INFO_KEY
from P4PCore.core.Net import Net
from P4PCore.util.BytesCoverter import *
from P4PCore.protocol.Protocol import *
from P4PCore.manager.SimpleImpls import SimpleCannotDeleteAndOverwriteBiKVManager, SimpleCannotOverwriteKVManager, SimpleCannotDeleteAndOverwriteKVManager, SimpleSetManager
from P4PCore.model.X25519AndAesEncrypter import EncrypterOverflowException, X25519AndAesgcmEncrypter
from P4PCore.util import BytesSplitter

class SecureNet(NetHandler, NetHandlerRegistry):
    _net:Net
    _ed25519Signer:Ed25519Signer
    _waitingResponses:WaitingResponses
    _encrypters:SimpleCannotOverwriteKVManager[tuple[str, int], X25519AndAesgcmEncrypter]
    _handlers:SimpleCannotDeleteAndOverwriteKVManager[UUID, NetHandler]
    _helloingAddrs:SimpleSetManager[tuple[str, int]]

    _addrToEd25519PublicKeys:SimpleCannotDeleteAndOverwriteBiKVManager[tuple[str, int], HashableEd25519PublicKey]
    _events:Events

    _logger:Logger
    @classmethod
    async def create(
        cls,
        net:Net,
        ed25519Signer:Ed25519Signer,
        addrToed25519PublicKeys:SimpleCannotDeleteAndOverwriteBiKVManager[tuple[str, int], HashableEd25519PublicKey],
        events:Events
    ) -> "SecureNet":
        inst = cls()

        inst._net = net
        inst._ed25519Signer = ed25519Signer
        inst._waitingResponses = WaitingResponses()
        inst._encrypters = SimpleCannotOverwriteKVManager()
        inst._handlers = SimpleCannotDeleteAndOverwriteKVManager()
        inst._helloingAddrs = SimpleSetManager()

        inst._addrToEd25519PublicKeys = addrToed25519PublicKeys
        inst._events = events

        await inst._net.registerHandler(PacketFlag.SECURE, inst)
        return inst
    async def registerHandler(self, flag:UUID, handler:NetHandler) -> bool:
        """
        Register a handler for handling secure packets with the given app flag.
        """
        return await self._handlers.add(flag, handler)
    @property
    def rawNet(self) -> Net:
        """
        The raw net object.
        """
        return self._net
    class HelloResult(IntEnum):
        SUCCESS = a()
        NET_HAS_STAERED_YET = a()
        OTHER_FUNC_IS_ALREADY_TRYING_TO_CONNECT = a()
        ALREADY_CONNECTED = a()
        ALREADY_CONNECTED_BUT_DIFFERENT_PUBLIC_KEY = a()
        FAILED_FIRST_HELLO = a()
    async def hello(self, nodeIdentify:NodeIdentify, firstHelloAttempts:int=0, secondHelloVolume:int=1, timeoutSec:float | None = None, encryptionSeqWindowSize:int=1) -> HelloResult:
        """
        Connect to the node and return the result of the connection.
        After calling this function, you can communicate with the node securely.
        """
        if not await self._helloingAddrs.add(nodeIdentify.addr):
            return self.HelloResult.OTHER_FUNC_IS_ALREADY_TRYING_TO_CONNECT
        elif await self._encrypters.get(nodeIdentify.addr):
            if nodeIdentify.hashableEd25519PublicKey in await self._addrToEd25519PublicKeys.getAll():
                return self.HelloResult.ALREADY_CONNECTED
            else:
                return self.HelloResult.ALREADY_CONNECTED_BUT_DIFFERENT_PUBLIC_KEY
        async with self._waitingResponses.open(
            WaitingResponse[tuple[HashableEd25519PublicKey, bytes], tuple[bytes, bytes, bytes]](
                WaitingResponseInfo(nodeIdentify.addr),
                otherInfo=(nodeIdentify.hashableEd25519PublicKey, (nextChallengeToken := os.urandom(ANY_UNIQUE_RANDOM_BYTES_SIZE)))
            )
        ) as c:
            success = False
            i = 0
            while not firstHelloAttempts or i < firstHelloAttempts:
                async with self._waitingResponses.open(
                    WaitingResponse[tuple[HashableEd25519PublicKey, bytes], tuple[bytes, bytes, bytes]](
                        WaitingResponseInfo(nodeIdentify.addr),
                        otherInfo=(nodeIdentify.hashableEd25519PublicKey, (nextChallengeToken := os.urandom(ANY_UNIQUE_RANDOM_BYTES_SIZE)))
                    )
                ) as c:
                    if not self._net.sendTo(
                        (
                            itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
                            +itob(ModeFlag.HELLO, SecurePacketElementSize.MODE_FLAG)
                            +c.waitingResponse.waitingResponseInfo.identify
                            +nextChallengeToken
                            +self._ed25519Signer.publicKey.publicKeyBytes
                        ),
                        nodeIdentify.addr
                    ):
                        return self.HelloResult.NET_HAS_STAERED_YET
                    r = await c.waitingResponse.waitAndGet(timeoutSec)
                    if r and not r.nextResponseId is None:
                        success = True
                        break
                i += 1
            if not success:
                return self.HelloResult.FAILED_FIRST_HELLO
        nextChallengeToken, recversX25519PubKeyB, aesSalt = r.value
        encrypter = X25519AndAesgcmEncrypter(
            True,
            encryptionSeqWindowSize,
            salt=aesSalt
        )
        for _ in range(secondHelloVolume):
            self._net.sendTo(
                (
                    itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
                    +itob(ModeFlag.SECOND_HELLO, SecurePacketElementSize.MODE_FLAG)
                    +r.nextResponseId
                    +(pubKeyRaw := encrypter.myX25519PublicKeyBytes)
                    +await self._ed25519Signer.sign(nextChallengeToken+pubKeyRaw)
                ),
                nodeIdentify.addr
            )
        await encrypter.derive(recversX25519PubKeyB)
        await self._addrToEd25519PublicKeys.add(nodeIdentify.addr, nodeIdentify.hashableEd25519PublicKey)
        await self._encrypters.add((nodeIdentify.ip, nodeIdentify.port), encrypter)

        return self.HelloResult.SUCCESS
    class SendToSecureResult(IntEnum):
        SUCCESS = a()
        DATA_IS_TOO_LARGE = a()
        NODE_HASNT_CONNECTED = a()
        ENCRYPTER_OVERFLOWED = a()
        NET_DIDNT_BEGIN = a()
    async def sendToSecure(self, data:bytes, to:tuple[str, int] | NodeIdentify) -> SendToSecureResult:
        """
        Send data to the node securely.
        If the node hasn't connected, this function will return details about the failure.
        """
        if isinstance(to, NodeIdentify):
            to = to.addr
        
        if len(data) > MAX_DATA_SIZE_ON_ENCRYPTED_AES:
            return self.SendToSecureResult.DATA_IS_TOO_LARGE
        elif not (encrypter := await self._encrypters.get(to)):
            return self.SendToSecureResult.NODE_HASNT_CONNECTED
        try:
            seq, encryptedData = await encrypter.encrypt(data)
        except EncrypterOverflowException as e:
            await self._events.triggerEvent(SecureNetOverflowedEncrypterSeqOnSenderEvent(e.seqWhenOverflowed, e.originalData, to))
            return self.SendToSecureResult.ENCRYPTER_OVERFLOWED
        return self.SendToSecureResult.SUCCESS if self._net.sendTo(
            itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
            +itob(ModeFlag.MAIN_DATA, SecurePacketElementSize.MODE_FLAG)
            +itob(seq, SecurePacketElementSize.SEQ)
            +encryptedData,
            to
        ) else self.SendToSecureResult.NET_DIDNT_BEGIN
    async def deleteNode(self, node:tuple[str, int] | NodeIdentify) -> bool:
        """
        Delete node from encrypters
        Warn: If you deleted node, You can't call sendToSecure method until call hello again.
        """
        await self._encrypters.delete(node.addr if isinstance(node, NodeIdentify) else node)

    async def getAddrs(self) -> list[tuple[str, int]]:
        return list((await self._encrypters.getAll()).keys())
    
    async def _recvHello(self, data:bytes, addr:tuple[str, int]) -> None:
        if not await self._helloingAddrs.add(addr):
            return
        if await self._encrypters.get(addr):
            await self._helloingAddrs.remove(addr)
            return
        sendersResponseIdentify, sendersChallengeToken, sendersEd25519PubKeyB = BytesSplitter.split(
            data,
            SecurePacketElementSize.RESPONSE_IDENTIFY,
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            SecurePacketElementSize.ED25519_PUBLIC_KEY
        )
        try:
            sendersPubKey = HashableEd25519PublicKey(sendersEd25519PubKeyB)
        except ValueError:
            return
        if pk := await self._addrToEd25519PublicKeys.get(addr) and not pk == sendersPubKey:
            return

        await self._events.triggerEvent(startedEvent := SecureNetStartedToHelloOnRecver(addr))

        encrypter = X25519AndAesgcmEncrypter(False, startedEvent.encryptSeqWindowSize)
        async with self._waitingResponses.open(
            WaitingResponse[tuple[HashableEd25519PublicKey, bytes], bytes](
                WaitingResponseInfo(addr),
                (sendersPubKey, nextChallengetoken := os.urandom(ANY_UNIQUE_RANDOM_BYTES_SIZE))
            )
        ) as c:
            for _ in range(startedEvent.helloVolume):
                self._net.sendTo(
                    (
                        itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
                        +itob(ModeFlag.RESP_HELLO, SecurePacketElementSize.MODE_FLAG)
                        +sendersResponseIdentify
                        +c.waitingResponse.waitingResponseInfo.identify
                        +(signEndPart := nextChallengetoken+encrypter.myX25519PublicKeyBytes+encrypter.salt)
                        +await self._ed25519Signer.sign(sendersChallengeToken+signEndPart)
                    ),
                    addr
                )
                if (r := await c.waitingResponse.waitAndGet(startedEvent.timeoutSecOnHello)) and r.value:
                    await self._helloingAddrs.remove(addr)
                    break
        if not r:
            await self._events.triggerEvent(SecureNetFinishedToHelloOnRecverEvent(addr, SecureNetFinishedToHelloOnRecverEventResult.FAILED_CHALLENGE))
            return
        await self._addrToEd25519PublicKeys.add(addr, sendersPubKey)
        await encrypter.derive(r.value)
        await self._encrypters.add(addr, encrypter)
        await self._events.triggerEvent(SecureNetFinishedToHelloOnRecverEvent(addr, SecureNetFinishedToHelloOnRecverEventResult.SUCCESS))
    async def _recvRespHello(self, data:bytes, addr:tuple[str, int]) -> None:
        myResponseIdentify, nextResponseIdentify, nextChallengeToken, recversX25519PubKeyB, aesSalt, recversSigned = BytesSplitter.split(
            data, 
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            SecurePacketElementSize.X25519_PUBLIC_KEY,
            SecurePacketElementSize.AES_SALT,
            SecurePacketElementSize.ED25519_SIGN
        )
        wR:WaitingResponse[tuple[HashableEd25519PublicKey, bytes], tuple[bytes, bytes, bytes]] = await self._waitingResponses.get(
            (addr, myResponseIdentify)
        )
        if not wR:
            return
        recversEd25519PubKey, previousChallengeToken = wR.otherInfo
        if not await recversEd25519PubKey.verify(recversSigned, previousChallengeToken+nextChallengeToken+recversX25519PubKeyB+aesSalt):
            return
        wR.setResponse(Response((nextChallengeToken, recversX25519PubKeyB, aesSalt), nextResponseIdentify=nextResponseIdentify))
    async def _recvSecondHello(self, data:bytes, addr:tuple[str, int]) -> None:
        sendersResponseIdentify, sendersX25519PubKeyB, sendersSigned = BytesSplitter.split(
            data,
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            SecurePacketElementSize.X25519_PUBLIC_KEY,
            SecurePacketElementSize.ED25519_SIGN
        )
        wR:WaitingResponse[tuple[HashableEd25519PublicKey, bytes], bytes] = await self._waitingResponses.get(
            (addr, sendersResponseIdentify)
        )
        if not wR:
            return
        sendersEd25519PubKey, previousChallengeToken = wR.otherInfo
        try:
            if not await sendersEd25519PubKey.verify(sendersSigned, previousChallengeToken+sendersX25519PubKeyB):
                return
        except Exception:
            return
        wR.setResponse(Response(sendersX25519PubKeyB))
    async def _recvMainData(self, data:bytes, addr:tuple[str, int]) -> None:
        if len(data) < SecurePacketElementSize.SEQ:
            return
        seqB, encryptedData = BytesSplitter.split(
            data,
            SecurePacketElementSize.SEQ,
            includeRest=True
        )
        if not (encrypter := await self._encrypters.get(addr)):
            return
        try:
            data = await encrypter.decrypt(encryptedData, btoi(seqB))
        except EncrypterOverflowException as encrypter:
            await self._events.triggerEvent(SecureNetOverflowedEncrypterSeqOnRecverEvent(encrypter.seqWhenOverflowed, encrypter.originalData, addr))
            return
        if len(data) < SecurePacketElementSize.CONTENT_UUID:
            return
        contentUuid, data = BytesSplitter.split(
            data,
            SecurePacketElementSize.CONTENT_UUID,
            includeRest=True
        )
        if (h := await self._handlers.get(UUID(bytes=contentUuid))) is None:
            return
        await h.handle(data, addr)
    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        recvedTime = asyncio.get_running_loop().time()
        await self._events.triggerEvent(e := NetLikeRecvedEvent(self, data, addr, recvedTime))
        if e.isCancelled:
            return
        if len(data) < SecurePacketElementSize.MODE_FLAG:
            return
        modeFlag, data = BytesSplitter.split(
            data,
            SecurePacketElementSize.MODE_FLAG,
            includeRest=True
        )
        try:
            modeFlag = ModeFlag(btoi(modeFlag))
        except ValueError:
            return
        
        target = {
            ModeFlag.HELLO: self._recvHello,
            ModeFlag.RESP_HELLO: self._recvRespHello,
            ModeFlag.SECOND_HELLO: self._recvSecondHello,
            ModeFlag.MAIN_DATA: self._recvMainData,
        }.get(modeFlag)
        if not target:
            return
        try:
            await target(data, addr)
        except CancelException:
            pass
