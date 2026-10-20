from dataclasses import dataclass
from logging import Logger
import os
from enum import auto as a
from collections.abc import Callable
from cachetools import TTLCache

from P4PCore.core.abstract.NetHandlerRegistry import NetHandlerRegistry
from P4PCore.core.UserNet import UserNet
from P4PCore.core.event.SecureNetFinishedToHelloOnRecverEvent import SecureNetFinishedToHelloOnRecverEvent, SecureNetFinishedToHelloOnRecverEventResult
from P4PCore.core.event.SecureNetStartedToHelloOnRecver import SecureNetStartedToHelloOnRecver
from P4PCore.common.manager.Events import Events
from P4PCore.common.model.Ed25519Signer import Ed25519Signer
from P4PCore.common.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.core.abstract.NetHandler import NetHandler
from P4PCore.common.model.Response import Response
from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.common.manager.WaitingResponses import WaitingResponses
from P4PCore.common.model.WaitingResponse import WaitingResponse
from P4PCore.common.model.WaitingResponseInfo import WaitingResponseInfo
from P4PCore.core.Net import Net
from P4PCore.common.util.BytesCoverter import *
from P4PCore.core.protocol.Protocol import *
from P4PCore.core.model.X25519AndAesEncrypter import X25519AndAesgcmEncrypter
from P4PCore.common.util import BytesSplitter

@dataclass
class _HelloStorage:
    otherPartyEd25519PublicKey:HashableEd25519PublicKey | None = None
    myChallengeToken:bytes | None = None
    encrypter:X25519AndAesgcmEncrypter | None = None

class SecureNet(NetHandler):
    """
    Provide secure peer-to-peer communication with Ed25519/X25519-based and AES handshakes and encryption.
    """
    def __init__(
        self,
        net:Net,
        userNet:UserNet,
        ed25519Signer:Ed25519Signer,
        getLoggerFunc:Callable[[str], Logger],
        events:Events,
        magic:bytes,
        helloingsMaxSize:int = 100,
        helloingsTimeoutSeconds:float = 4
    ):
        """
        Create a new secure network handler and register it with the user network.
        :param net: The underlying network instance to use for secure communication.
        :param userNet: The user network registry used to register this secure handler.
        :param ed25519Signer: The signer used to authenticate secure connections.
        :param events: The event manager used for secure network event notifications.
        :param magic: A byte string representing the packet flag.
        :param helloingsMaxSize: Maximum size of the ongoing hello handshake cache (> 0).
        :param helloingsTimeoutSeconds: Timeout in seconds for the hello handshake cache TTL (> 0).
        """

        self._net:Net = net
        self._ed25519Signer:Ed25519Signer = ed25519Signer
        self._logger:Logger = getLoggerFunc(__name__)
        self._waitingResponses:WaitingResponses = WaitingResponses()
        self._encrypters:dict[tuple[str, int], X25519AndAesgcmEncrypter] = {}
        self._handlers:set[NetHandler] = set()

        self._events:Events = events
        self._magic:bytes = magic

        if helloingsMaxSize <= 0:
            raise ValueError("helloingsMaxSize > 0")
        elif helloingsTimeoutSeconds <= 0:
            raise ValueError("helloingsTimeoutSeconds > 0")
        self._helloings:TTLCache[tuple[str, int], _HelloStorage | None] = TTLCache(maxsize=helloingsMaxSize, ttl=helloingsTimeoutSeconds)

        self._confirmedAddrsToEd25519PublicKeys:dict[tuple[str, int], HashableEd25519PublicKey] = {}

        if not userNet.registerHandler(itob(PacketFlag.SECURE, PacketElementSize.PACKET_FLAG), self):
            raise Exception("Cannot register for NetHandler. May be another handler registered for the same flag.")

    def registerHandler(self, handler:NetHandler) -> bool:
        """
        Register a handler that will receive decrypted secure packets.
        :param handler: The handler to register for secure packet dispatch.
        :return: True if the handler was successfully registered; otherwise False.
        """
        if handler in self._handlers:
            return False
        self._handlers.add(handler)
        return True

    @property
    def confirmedAddrsToEd25519PublicKeys(self) -> dict[tuple[str, int], HashableEd25519PublicKey]:
        return self._confirmedAddrsToEd25519PublicKeys.copy()

    class HelloResult(IntEnum):
        SUCCESS = a()
        NET_HAS_STAERED_YET = a()
        OTHER_FUNC_IS_ALREADY_TRYING_TO_CONNECT = a()
        ALREADY_CONNECTED = a()
        ALREADY_CONNECTED_BUT_DIFFERENT_PUBLIC_KEY = a()
        FAILED_FIRST_HELLO = a()
    async def hello(self, nodeIdentify:NodeIdentify, timeoutSeconds:float | None = 2, firstHelloAttempts:int | None=3, secondHelloVolume:int=1, encryptionSeqWindowSize:int=1) -> HelloResult:
        """
        Establish a secure connection with the given node.
        :param nodeIdentify: The remote node identity to connect to.
        :param timeoutSec: The timeout used while waiting for challenge responses.
        :param firstHelloAttempts: The number of first-hello attempts to make before failing (> 0 || == None).
        :param secondHelloVolume: The number of second-hello attempts to send once the first stage succeeds (> 0).
        :param encryptionSeqWindowSize: The sequence window size used by the X25519/AES encrypter (> 0).
        :return: The result of the connection attempt.
        """

        if firstHelloAttempts is not None and firstHelloAttempts <= 0:
            raise ValueError("firstHelloAttempts > 0 || firstHelloAttempts == None")
        elif secondHelloVolume <= 0:
            raise ValueError("secondHelloVolume > 0")
        elif encryptionSeqWindowSize <= 0:
            raise ValueError("encryptionSeqWindowSize > 0")

        if nodeIdentify.addr in self._helloings:
            return self.HelloResult.OTHER_FUNC_IS_ALREADY_TRYING_TO_CONNECT
        self._helloings[nodeIdentify.addr] = _HelloStorage()
        
        if self._encrypters.get(nodeIdentify.addr):
            if nodeIdentify.hashableEd25519PublicKey in self._confirmedAddrsToEd25519PublicKeys.keys():
                return self.HelloResult.ALREADY_CONNECTED
            else:
                return self.HelloResult.ALREADY_CONNECTED_BUT_DIFFERENT_PUBLIC_KEY
        
        encrypter = X25519AndAesgcmEncrypter(
            True,
            encryptionSeqWindowSize,
        )
        with self._waitingResponses.open(
            WaitingResponse[tuple[HashableEd25519PublicKey, bytes], tuple[bytes, bytes, bytes]](
                WaitingResponseInfo(nodeIdentify.addr),
                otherInfo=(nodeIdentify.hashableEd25519PublicKey, (nextChallengeToken := os.urandom(ANY_UNIQUE_RANDOM_BYTES_SIZE)))
            )
        ) as c:
            success = False
            i = 0
            while firstHelloAttempts is None or i < firstHelloAttempts:
                if not self._net.sendTo(
                    (
                        itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
                        +itob(ModeFlag.HELLO, SecurePacketElementSize.MODE_FLAG)
                        +c.waitingResponse.waitingResponseInfo.identify
                        +nextChallengeToken
                        +self._ed25519Signer.publicKey.publicKeyBytes
                        +encrypter.myX25519PublicKeyBytes
                    ),
                    nodeIdentify.addr
                ):
                    return self.HelloResult.NET_HAS_STAERED_YET
                r = await c.waitingResponse.waitAndGet(timeoutSeconds)
                if r is not None:
                    success = True
                    break
                c.waitingResponse.newFuture()
                i += 1
        if not success:
            return self.HelloResult.FAILED_FIRST_HELLO
        
        nextChallengeToken, recversX25519PubKeyB, aesSalt = r.value
        encrypter.salt = aesSalt

        for _ in range(secondHelloVolume):
            self._net.sendTo(
                (
                    itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
                    +itob(ModeFlag.SECOND_HELLO, SecurePacketElementSize.MODE_FLAG)
                    +await self._ed25519Signer.sign(nextChallengeToken+encrypter.myX25519PublicKeyBytes)
                ),
                nodeIdentify.addr
            )

        encrypter.otherPartyX25519PublicKeyBytes = recversX25519PubKeyB
        encrypter.derive()
        self._confirmedAddrsToEd25519PublicKeys.setdefault(nodeIdentify.addr, nodeIdentify.hashableEd25519PublicKey)
        self._encrypters.setdefault(nodeIdentify.addr, encrypter)
        self._helloings.pop(nodeIdentify.addr)

        return self.HelloResult.SUCCESS

    class SendToSecureResult(IntEnum):
        SUCCESS = a()
        DATA_IS_TOO_LARGE = a()
        NODE_HASNT_BEEN_CONNECTED = a()
        LOW_LEVEL_ERROR = a()
    def sendToSecure(self, data:bytes, node:tuple[str, int] | NodeIdentify) -> SendToSecureResult:
        """
        Send encrypted data to the target node.
        :param data: The plaintext payload to encrypt and send.
        :param node: The destination addr or node identity.
        :return: The status of the send operation.
        """
        addr = node.addr if isinstance(node, NodeIdentify) else node
        
        if len(data) > MAX_DATA_SIZE_ON_ENCRYPTED_AES_EXCLUDING_MAGIC-len(self._magic):
            return self.SendToSecureResult.DATA_IS_TOO_LARGE
        elif not (encrypter := self._encrypters.get(addr)):
            return self.SendToSecureResult.NODE_HASNT_BEEN_CONNECTED
        
        seq, encryptedData = encrypter.encrypt(data)
        
        return self.SendToSecureResult.SUCCESS if self._net.sendTo(
            itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
            +itob(ModeFlag.MAIN_DATA, SecurePacketElementSize.MODE_FLAG)
            +itob(seq, SecurePacketElementSize.SEQ)
            +encryptedData,
            addr
        ) else self.SendToSecureResult.LOW_LEVEL_ERROR

    def bye(self, node:NodeIdentify | tuple[str, int]) -> bool:
        """
        """
        addr = node.addr if isinstance(node, NodeIdentify) else node
        return not not self._encrypters.pop(addr, False)

    async def _recvHello(self, data:bytes, addr:tuple[str, int]) -> None:
        # for recvers
        if addr in self._helloings:
            return
        helloStorage = self._helloings[addr] = _HelloStorage()
        if self._encrypters.get(addr):
            self._helloings.pop(addr)
            return
        
        sendersResponseIdentify, sendersChallengeToken, sendersEd25519PubKeyB, sendersX25519PubKeyB = BytesSplitter.split(
            data,
            SecurePacketElementSize.RESPONSE_IDENTIFY,
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            SecurePacketElementSize.ED25519_PUBLIC_KEY,
            SecurePacketElementSize.X25519_PUBLIC_KEY
        )
        try:
            sendersPubKey = HashableEd25519PublicKey(sendersEd25519PubKeyB)
        except Exception:
            return
        
        if (pK := self._confirmedAddrsToEd25519PublicKeys.get(addr)) and pK == sendersPubKey:
            return
        try:
            await self._events.triggerEvent(startedEvent := SecureNetStartedToHelloOnRecver(addr))
        except Exception:
            self._helloings.pop(addr, None)

        helloStorage.otherPartyEd25519PublicKey = sendersPubKey
        helloStorage.myChallengeToken = os.urandom(ANY_UNIQUE_RANDOM_BYTES_SIZE)
        helloStorage.encrypter = X25519AndAesgcmEncrypter(False, startedEvent.encryptSeqWindowSize)
        helloStorage.encrypter.otherPartyX25519PublicKeyBytes = sendersX25519PubKeyB

        for _ in range(startedEvent.helloVolume):
            self._net.sendTo(
                (
                    itob(PacketFlag.SECURE, SecurePacketElementSize.PACKET_FLAG)
                    +itob(ModeFlag.RESP_HELLO, SecurePacketElementSize.MODE_FLAG)
                    +sendersResponseIdentify
                    +(
                        signEndPart := 
                            helloStorage.myChallengeToken
                            +helloStorage.encrypter.myX25519PublicKeyBytes
                            +helloStorage.encrypter.salt
                    )
                    +await self._ed25519Signer.sign(sendersChallengeToken+signEndPart)
                ),
                addr
            )

    async def _recvRespHello(self, data:bytes, addr:tuple[str, int]) -> None:
        # for senders
        myResponseIdentify, nextChallengeToken, recversX25519PubKeyB, aesSalt, recversSigned = BytesSplitter.split(
            data, 
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            ANY_UNIQUE_RANDOM_BYTES_SIZE,
            SecurePacketElementSize.X25519_PUBLIC_KEY,
            SecurePacketElementSize.AES_SALT,
            SecurePacketElementSize.ED25519_SIGN
        )
        wR:WaitingResponse[tuple[HashableEd25519PublicKey, bytes], tuple[bytes, bytes, bytes]] = self._waitingResponses.get(
            (addr, myResponseIdentify)
        )
        if not wR:
            return
        recversEd25519PubKey, previousChallengeToken = wR.otherInfo
        if not await recversEd25519PubKey.verify(recversSigned, previousChallengeToken+nextChallengeToken+recversX25519PubKeyB+aesSalt):
            return
        wR.setResponse(Response((nextChallengeToken, recversX25519PubKeyB, aesSalt)))

    async def _recvSecondHello(self, data:bytes, addr:tuple[str, int]) -> None:
        # for recvers
        sendersSigned = data

        if not (helloing := self._helloings.get(addr)):
            return
        elif not (
            helloing.otherPartyEd25519PublicKey and
            helloing.myChallengeToken and
            helloing.encrypter and
            helloing.encrypter.otherPartyX25519PublicKeyBytes
        ):
            return
        elif not await helloing.otherPartyEd25519PublicKey.verify(sendersSigned, helloing.myChallengeToken+helloing.encrypter.otherPartyX25519PublicKeyBytes):
                return

        helloing.encrypter.derive()
        self._confirmedAddrsToEd25519PublicKeys.setdefault(addr, helloing.otherPartyEd25519PublicKey)
        self._encrypters.setdefault(addr, helloing.encrypter)
        self._helloings.pop(addr, None)

        await self._events.triggerEvent(SecureNetFinishedToHelloOnRecverEvent(addr, SecureNetFinishedToHelloOnRecverEventResult.SUCCESS))
    
    async def _recvMainData(self, data:bytes, addr:tuple[str, int]) -> None:
        if len(data) < SecurePacketElementSize.SEQ:
            return
        seqB, encryptedData = BytesSplitter.split(
            data,
            SecurePacketElementSize.SEQ,
            includeRest=True
        )
        if not (encrypter := self._encrypters.get(addr)):
            return
        if not (data := encrypter.decrypt(encryptedData, btoi(seqB))):
            return
        for handler in self._handlers:
            await handler.handle(data, addr)
    
    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
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
        await target(data, addr)