from asyncio import Lock
import logging
from logging import Handler, Logger

from P4PCore.abstract.HasLoop import HasLoop
from P4PCore.core.PingPongNet import PingPongNet
from P4PCore.core.SecureNet import SecureNet
from P4PCore.core.UserNet import UserNet
from P4PCore.event.CalledEndFunctionOfRunnerEvent import CalledEndFunctionOfRunnerEvent
from P4PCore.event.CalledBeginFunctionOfRunnerEvent import CalledBeginFunctionOfRunnerEvent
from P4PCore.manager.SimpleImpls import SimpleCannotDeleteAndOverwriteBiKVManager, SimpleListManager
from P4PCore.model.Ed25519Signer import Ed25519Signer
from P4PCore.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.core.Net import Net
from P4PCore.manager.Events import Events
from P4PCore.protocol.Protocol import PacketFlag, PacketElementSize
from P4PCore.util.BytesCoverter import itob

class P4PRunner(HasLoop):
    _ed25519Signer:Ed25519Signer
    _net:Net
    _baseUserNet:UserNet
    _secureNet:SecureNet
    _pingPongNet:PingPongNet
    _addrToEd25519PubKeys:SimpleCannotDeleteAndOverwriteBiKVManager[tuple[str, int], HashableEd25519PublicKey]
    _events:Events
    _loggerHandlers:SimpleListManager[Handler]
    _started:bool
    _startedLock:Lock
    _logger:Logger

    _userNet:UserNet
    _secureUserNet:UserNet
    @classmethod
    async def create(cls, ed25519Signer:Ed25519Signer | None = None) -> "P4PRunner":
        """
        Create a new instance of P4PRunner.
        """
        inst = cls()

        inst._ed25519Signer = ed25519Signer or Ed25519Signer()
        inst._loggerHandlers = SimpleListManager()
        inst._events = Events()
        inst._net = Net(inst._events)
        inst._baseUserNet = await UserNet.create(PacketElementSize.PACKET_FLAG, registry=inst._net)
        inst._addrToEd25519PubKeys = SimpleCannotDeleteAndOverwriteBiKVManager()
        inst._secureNet = await SecureNet.create(inst._net, inst._baseUserNet, inst._ed25519Signer, inst._addrToEd25519PubKeys, inst._events)
        inst._pingPongNet = await PingPongNet.create(inst._net, inst._baseUserNet)
        inst._loggerHandlers = SimpleListManager()
        inst._started = False
        inst._startedLock = Lock()
        inst._logger = await inst.getLogger(__name__)

        inst._userNet = await UserNet.create(PacketElementSize.UUID)
        await inst._baseUserNet.registerHandler(itob(PacketFlag.USER, PacketElementSize.PACKET_FLAG), inst._userNet)
        inst._secureUserNet = await UserNet.create(PacketElementSize.UUID, registry=inst._secureNet)
        
        return inst
    @property
    def addrToEd25519PubkeysManager(self) -> SimpleCannotDeleteAndOverwriteBiKVManager[tuple[str, int], HashableEd25519PublicKey]:
        """
        A manager that maps bidirectional between addr and ed25519 in this instance and its subordinates instances.
        """
        return self._addrToEd25519PubKeys
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
    @property
    def loggerHandlersManager(self) -> SimpleListManager[Handler]:
        """
        A manager that stores handlers used by all logger in this instance and its subordinates instances.
        """
        return self._loggerHandlers
    async def getLogger(self, name:str) -> Logger:
        """
        Get a logger instance standard of this instnace.
        """
        logger = logging.getLogger(name)
        logger.handlers = await self._loggerHandlers.getAll()
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
        """
        await self._net.begin()
        await self._events.triggerEvent(CalledBeginFunctionOfRunnerEvent())
    async def end(self) -> None:
        """
        End the instance's all.
        """
        await self._net.end()
        await self._events.triggerEvent(CalledEndFunctionOfRunnerEvent())