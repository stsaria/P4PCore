import logging

from P4PCore.model.Settings import Settings
from P4PCore.manager.Events import Events
from P4PCore.manager.SimpleImpls import SimpleCannotDeleteAndOverwriteBiKVManager
from P4PCore.model.HashableEd25519PublicKey import HashableEd25519PublicKey

from P4PCore.event.P4PRunnerBeginReqEvent import P4PRunnerBeginReqEvent
from P4PCore.event.P4PRunnerEndReqEvent import P4PRunnerEndReqEvent
from P4PCore.event.P4PRunnerGetSecureNetEvent import P4PRunnerGetSecureNetEvent

logger = logging.getLogger(__name__)

class PeerForPeers:
    _addrToEd25519PubKeys:SimpleCannotDeleteAndOverwriteBiKVManager[tuple[str, int], HashableEd25519PublicKey] = SimpleCannotDeleteAndOverwriteBiKVManager()
    _events:Events = Events()

    _settings:Settings = Settings()

    @classmethod
    def getAddrToEd25519PubkeysManager(cls) -> SimpleCannotDeleteAndOverwriteBiKVManager[tuple[str, int], HashableEd25519PublicKey]:
        """
        Get a manager for mapping addr to ed25519 public key.
        This manager can get ed25519 public key by addr, and get addr by ed25519 public key.
        """
        return cls._addrToEd25519PubKeys
    @classmethod
    def getEventsManager(cls) -> Events:
        """
        Get the events manager.
        """
        return cls._events
    
    @classmethod
    def getSettings(cls) -> Settings:
        """
        Get the settings.
        """
        return cls._settings
    
    @classmethod
    async def getNet(cls) -> P4PRunnerGetSecureNetEvent:
        """
        Get the net object.
        """
        e = P4PRunnerGetSecureNetEvent()
        await cls._events.triggerEvent(e)
        return e

    @classmethod
    async def begin(cls) -> None:
        """
        Begin the PeerForPeers.
        """
        await cls._events.triggerEvent(P4PRunnerBeginReqEvent())

    @classmethod
    async def end(cls) -> None:
        """
        End the PeerForPeers.
        """
        await cls._events.triggerEvent(P4PRunnerEndReqEvent())