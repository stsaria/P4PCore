import signal
import sys
import logging
import asyncio

from src.manager.Events import Events
from src.manager.SimpleImpls import SimpleCannotDeleteAndOverwriteBiKVManager
from src.manager.Tasks import Tasks
from src.model.HashableEd25519PublicKey import HashableEd25519PublicKey

from src.event.P4PRunnerBeginReqEvent import P4PRunnerBeginReqEvent
from src.event.P4PRunnerEndReqEvent import P4PRunnerEndReqEvent

logger = logging.getLogger(__name__)

class PeerForPeers:
    _tasks:Tasks = Tasks()
    _events:Events = Events()

    _addrToEd25519PubKeys:SimpleCannotDeleteAndOverwriteBiKVManager[tuple[str, int], HashableEd25519PublicKey] = SimpleCannotDeleteAndOverwriteBiKVManager()

    @classmethod
    def getAddrToEd25519PubkeysManager(cls) -> SimpleCannotDeleteAndOverwriteBiKVManager[tuple[str, int], HashableEd25519PublicKey]:
        return cls._addrToEd25519PubKeys
    @classmethod
    def getTasksManager(cls) -> Tasks:
        return cls._tasks
    @classmethod
    def getEventsManager(cls) -> Events:
        return cls._events

    @classmethod
    async def begin(cls) -> None:
        await cls._events.triggerEvent(P4PRunnerBeginReqEvent())

    @classmethod
    async def end(cls) -> None:
        await cls._events.triggerEvent(P4PRunnerEndReqEvent())

def sigRecved(sig:int, _):
    logger.info(f"Signal {sig} received, shutting down...")
    asyncio.run(PeerForPeers.end())
    sys.exit(0)

signal.signal(signal.SIGINT, sigRecved)
signal.signal(signal.SIGTERM, sigRecved)