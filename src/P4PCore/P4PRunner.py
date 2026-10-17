import logging
from asyncio import Lock
from logging import Handler, Logger

from P4PCore.common.abstract.HasLoop import HasLoop
from P4PCore.core.Net import Net
from P4PCore.core.PingPongNet import PingPongNet
from P4PCore.core.SecureNet import SecureNet
from P4PCore.core.UserNet import UserNet
from P4PCore.common.manager.Events import Events
from P4PCore.common.model.Ed25519Signer import Ed25519Signer
from P4PCore.common.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.core.protocol.Protocol import PacketElementSize, PacketFlag
from P4PCore.common.util.BytesCoverter import itob


class P4PRunner(HasLoop):
    """
    The Runner class is the main class of P4P. It manages the network, events, and other core functionalities.

    Basically, you most start you program with P4PRunner.begin() and end it with P4PRunner.end() (for saving resources and preventing errors).
    """
    def __init__(
        self,
        ed25519Signer:Ed25519Signer | None = None,
        loggerHandlers:list[Handler] = [],
        magic:bytes=b"P4P6",
        secureNetHelloingsMaxSize: int = 100,
        secureNetHelloingsTimeoutSeconds: float = 4
    ) -> "P4PRunner":
        """
        Create a new instance of P4PRunner.
        :param ed25519Signer: An optional Ed25519Signer instance. If not provided, a new instance will be created.
        :param magic: A byte string representing the packet flag. Default is b"P4P6".
        :return: An instance of P4PRunner.
        """

        self._ed25519Signer:Ed25519Signer = ed25519Signer or Ed25519Signer()
        self._magic:bytes = magic

        self._events:Events = Events()
        self._loggerHandlers:list[Handler] = loggerHandlers

        self._net:Net = Net(self._events, self._magic)
        self._baseUserNet:UserNet = UserNet(PacketElementSize.PACKET_FLAG, registry=self._net)
        self._secureNet:SecureNet = SecureNet(
            self._net,
            self._baseUserNet,
            self._ed25519Signer,
            self.getLogger,
            self._events,
            self._magic,
            secureNetHelloingsMaxSize,
            secureNetHelloingsTimeoutSeconds
        )
        self._pingPongNet:PingPongNet = PingPongNet(self._net, self._baseUserNet)

        self._userNet:UserNet = UserNet(PacketElementSize.UUID)
        self._baseUserNet.registerHandler(itob(PacketFlag.USER, PacketElementSize.PACKET_FLAG), self._userNet)
        self._secureUserNet:UserNet = UserNet(PacketElementSize.UUID, registry=self._secureNet)
        
    @property
    def eventsManager(self) -> Events:
        """
        A manager that maps between event class and handler instances in this instance and its subordinates instances.
        """
        return self._events
    @property
    def ed25519Signer(self) -> Ed25519Signer:
        """
        Settings for P4P in this instance and its subordinates instances.
        """
        return self._ed25519Signer
    @property
    def net(self) -> Net:
        """
        A net instance.
        """
        return self._net
    @property
    def baseUserNet(self) -> UserNet:
        """
        The base net instance for user communications in this instance and its subordinates instances.
        If you want to disable default function for user communications(e.g. SecureNet) or want to put your own function in lower layer, you can use this instance.
        """
        return self._baseUserNet
    @property
    def secureNet(self) -> SecureNet:
        """
        A net instance for secure communications in this instance and its subordinates instances.
        """
        return self._secureNet
    @property
    def pingPongNet(self) -> PingPongNet:
        """
        A net instance for checking if communication is possible in this instance and its subordinates instances.
        """
        return self._pingPongNet
    def getLogger(self, name:str, level:int=logging.INFO) -> Logger:
        """
        Get a logger instance standard of this instnace.
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers = self._loggerHandlers
        return logger
    @property
    def userNet(self) -> UserNet:
        """
        A net instance for user communications in this instance and its subordinates instances.
        """
        return self._userNet
    @property
    def secureUserNet(self) -> UserNet:
        """
        A net instance for secure user communications in this instance and its subordinates instances.
        """
        return self._secureUserNet
    async def begin(self) -> None:
        """
        Begin the instance's all.
        In most cases, this function should be called at first.
        """
        await self._net.begin()
    async def end(self) -> None:
        """
        End the instance's all.
        In most cases, this function should be called at last.
        """
        await self._net.end()
