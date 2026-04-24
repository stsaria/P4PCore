import os
import asyncio
import logging
from enum import auto as a
from uuid import UUID

from P4PCore.interface.ISecureNet import ISecureNet
from P4PCore.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.PeerForPeers import PeerForPeers
from P4PCore.abstract.NetHandler import NetHandler
from P4PCore.interface.NetHandlerRegistry import NetHandlerRegistry
from P4PCore.model.Response import Response
from P4PCore.model.NodeIdentify import NodeIdentify
from P4PCore.manager.WaitingResponses import WaitingResponses
from P4PCore.model.WaitingResponse import WaitingResponse
from P4PCore.model.WaitingResponseInfo import WaitingResponseInfo, WAITING_RESPONSE_INFO_KEY
from P4PCore.core.ExNet import ExNet
from P4PCore.model.Ed25519Signer import Ed25519Signer
from P4PCore.util.BytesCoverter import *
from P4PCore.protocol.Protocol import *
from P4PCore.protocol.ProgramProtocol import *
from P4PCore.manager.SimpleImpls import SimpleCannotOverwriteKVManager, SimpleCannotDeleteAndOverwriteKVManager, SimpleSetManager
from P4PCore.util.Result import Result
from P4PCore.model.X25519AndAesEncrypter import X25519AndAesgcmEncrypter
from P4PCore.util.NonNone import nonNone
from P4PCore.util import BytesSplitter
from P4PCore.util.AddrLogger import AddrLogger

_logger = logging.getLogger()
_sAddrLogger = AddrLogger(_logger, True)
_rAddrLogger = AddrLogger(_logger, False)

class SecureNet(ISecureNet, NetHandler, NetHandlerRegistry):
    def __init__(self, exNet:ExNet, myEd25519Signer:Ed25519Signer):
        self.__ed25519Signer:Ed25519Signer = myEd25519Signer

        self.__waitingResponses:WaitingResponses = WaitingResponses()
        self.__encrypters:SimpleCannotOverwriteKVManager[tuple[str, int], X25519AndAesgcmEncrypter] = SimpleCannotOverwriteKVManager()
        self.__handlers:SimpleCannotDeleteAndOverwriteKVManager[UUID, NetHandler] = SimpleCannotDeleteAndOverwriteKVManager()
        self._helloingAddrs:SimpleSetManager[tuple[str, int]] = SimpleSetManager()

        self._net:ExNet = exNet

        asyncio.run(self._net.registerHandler(PacketFlag.SECURE, self))
    async def registerHandler(self, flag:UUID, handler:NetHandler) -> bool:
        """
        Register a handler for handling secure packets with the flag of the content type.
        The content type is a UUID that identifies the type of the content of the secure packet.
        """
        return await self.__handlers.add(flag, handler)
    def getExNet(self) -> ExNet:
        """
        Get the extended net object.
        """
        return self._net
    class HelloResult(Result):
        OTHER_FUNC_IS_TRYING_TO_CONNECT = a()
        ALREADY_CONNECTED = a()
        FAILED_FIRST_HI = a() 
    async def hello(self, nodeIdentify:NodeIdentify) -> HelloResult:
        """
        Connect to the node and return the result of the connection.
        After calling this function, you can communicate with the node securely.
        """
        if not await self._helloingAddrs.add(nodeIdentify.addr):
            return self.HelloResult.OTHER_FUNC_IS_TRYING_TO_CONNECT
        elif await self.__encrypters.get(nodeIdentify.addr):
            return self.HelloResult.ALREADY_CONNECTED
        async with self.__waitingResponses.open(
            WaitingResponse[tuple[HashableEd25519PublicKey, bytes], tuple[bytes, bytes, bytes]](
                WaitingResponseInfo(nodeIdentify.addr),
                otherInfo=(nodeIdentify.hashableEd25519PublicKey, (cT := os.urandom(ANY_UNIQUE_RANDOM_BYTES_SIZE)))
            )
        ) as c:
            success = False
            for _ in range(HELLO_ATTEMPTS):
                self._net.sendTo(
                    (
                        itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
                        +itob(PacketModeFlag.HELLO, SecurePacketElementSize.MODE_FLAG)
                        +c.waitingResponse.waitingResponseInfo.identify
                        +cT
                        +self.__ed25519Signer.publicKey.bytesKey
                    ),
                    nodeIdentify
                )
                if (r := await c.waitingResponse.waitAndGet(TIME_OUT_MILLI_SEC)) and not r.nextResponseId is None:
                    success = True
                    break
            if not success:
                return self.HelloResult.FAILED_FIRST_HI
        cT, aesSalt, oPX25519PKB = r.value
        e = X25519AndAesgcmEncrypter(
            True,
            salt=aesSalt
        )
        await self._net.sendToIncludeRedundancy(
            (
                itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
                +itob(PacketModeFlag.SECOND_HELLO, SecurePacketElementSize.MODE_FLAG)
                +r.nextResponseId
                +(pubKeyRaw := e.myX25519PublicKeyBytes)
                +await self.__ed25519Signer.sign(cT+pubKeyRaw)
            ),
            nodeIdentify
        )
        await e.derive(oPX25519PKB)
        await PeerForPeers.getAddrToEd25519PubkeysManager().add(nodeIdentify.addr, nodeIdentify.hashableEd25519PublicKey)
        await self.__encrypters.add((nodeIdentify.ip, nodeIdentify.port), e)
        return self.HelloResult.SUCCESS
    async def sendToSecure(self, data:bytes, nodeIdentify:NodeIdentify) -> bool:
        """
        Send data to the node securely and return whether the sending is successful.
        This function only returns whether the sending is successful, but it does not return whether the node has received the data.
        """
        if getMaxDataSizeOnAesEncrypted()-AESGCM_NONCE_SIZE < len(data):
            return False
        if not (e := await self.__encrypters.get(nodeIdentify.addr)):
            return False
        return self._net.sendTo(await e.encrypt(data), nodeIdentify)
    
    async def _recvHello(self, mD:bytes, addr:tuple[str, int]) -> None:
        if not await self._helloingAddrs.add(addr):
            return
        if await self.__encrypters.get(addr):
            await self._helloingAddrs.remove(addr)
            return
        _rAddrLogger.dbg(addr, "Recved hello")
        rI, cT, ed25519PubKeyB = BytesSplitter.split(
            mD,
            SecurePacketElementSize.RESPONSE_TOKEN,
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            SecurePacketElementSize.ED25519_PUBLIC_KEY
        )
        e = X25519AndAesgcmEncrypter(False)
        async with self.__waitingResponses.open(
            WaitingResponse[tuple[bytes, bytes], bytes](
                WaitingResponseInfo(addr),
                (ed25519PubKeyB, nextT := os.urandom(ANY_UNIQUE_RANDOM_BYTES_SIZE))
            )
        ) as c:
            await self._net.sendToIncludeRedundancy(
                (
                    itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
                    +itob(PacketModeFlag.RESP_HELLO, SecurePacketElementSize.MODE_FLAG)
                    +c.waitingResponse.waitingResponseInfo.identify
                    +rI
                    +(signEndPart := nextT+e.myX25519PublicKeyBytes+e.salt)
                    +await self.__ed25519Signer.sign(cT+signEndPart)
                )
            )
            if (r := await c.waitingResponse.waitAndGet(TIME_OUT_MILLI_SEC)) is None:
                return
        if not await PeerForPeers.getAddrToEd25519PubkeysManager().add(addr, ed25519PubKeyB):
            return
        await e.derive(r.value)
        await self.__encrypters.add(addr, e)
    async def _recvRespHello(self, mD:bytes, addr:tuple[str, int]) -> None:
        nRI, rI, nCT, x25519PubKeyB, aesSaltB, signedB = BytesSplitter.split(
            mD, 
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            SecurePacketElementSize.X25519_PUBLIC_KEY,
            SecurePacketElementSize.AES_SALT,
            SecurePacketElementSize.ED25519_SIGN
        )
        key:WAITING_RESPONSE_INFO_KEY = (addr, rI)
        wR:WaitingResponse[tuple[HashableEd25519PublicKey, bytes], tuple[bytes, bytes, bytes]] = await self.__waitingResponses.get(key)
        if wR is None or wR:
            return
        otherPartyEd25519PK, cT = wR.otherInfo
        if not await otherPartyEd25519PK.verify(signedB, cT+nCT+x25519PubKeyB+aesSaltB):
            return
        await wR.setResponse(Response((nCT, x25519PubKeyB, aesSaltB), nextResponseId=nRI))
    async def _recvSecondHello(self, mD:bytes, addr:tuple[str, int]) -> None:
        rI, x25519PubKeyB, signedB = BytesSplitter.split(
            mD,
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            SecurePacketElementSize.X25519_PUBLIC_KEY,
            SecurePacketElementSize.ED25519_SIGN
        )
        key:WAITING_RESPONSE_INFO_KEY = (addr, rI)
        wR:WaitingResponse[tuple[bytes, bytes], tuple[bytes, bytes]] = await self.__waitingResponses.get(key)
        if wR is None or wR:
            return
        otherPartyEd25519PKB, t = wR.otherInfo
        if not await HashableEd25519PublicKey.createByBytes(otherPartyEd25519PKB).verify(signedB, t+x25519PubKeyB):
            return
        wR.setResponse(Response(x25519PubKeyB))
    async def _recvMainData(self, mD:bytes, addr:tuple[str, int]) -> None:
        seqB, eData = BytesSplitter.split(
            mD,
            SecurePacketElementSize.SEQ,
            includeRest=True
        )
        e = await self.__encrypters.get(addr)
        if e is None:
            return
        cType, mainData = BytesSplitter.split(
            await e.decrypt(eData, btoi(seqB, ENDIAN)),
            SecurePacketElementSize.CONTENT_TYPE_UUID,
            includeRest=True
        )
        if (h := await self.__handlers.get(UUID(cType))) is None:
            return
        asyncio.create_task(h.handle(mainData, addr))
    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        if len(data) < SecurePacketElementSize.MODE_FLAG:
            return
        mFlag, mainData = BytesSplitter.split(
            data+b"\x00",
            SecurePacketElementSize.PACKET_FLAG,
            SecurePacketElementSize.MODE_FLAG,
            includeRest=True
        )
        mainData = mainData[:-1]
        try:
            mFlag = PacketModeFlag(btoi(mFlag, ENDIAN))
        except ValueError:
            return
        
        target = {
            PacketModeFlag.HELLO: self._recvHello,
            PacketModeFlag.RESP_HELLO: self._recvRespHello,
            PacketModeFlag.SECOND_HELLO: self._recvSecondHello,
            PacketModeFlag.MAIN_DATA: self._recvMainData
        }.get(mFlag)
        if not target:
            return
        try:
            await target(mainData, addr)
        except Exception as e:
            _logger.exception("An Exception has occurred on handle func")
        finally:
            pass

        
