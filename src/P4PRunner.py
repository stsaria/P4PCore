from core.SecureNet import SecureNet
from event.P4PRunnerGetSecureNetEvent import P4PRunnerGetSecureNetEvent

from event.P4PRunnerReBeginReqEvent import P4PRunnerReBeginReqEvent
from model.NetConfig import NetConfig
from core.ExNet import ExNet
from event.P4PRunnerBeginReqEvent import P4PRunnerBeginReqEvent
from event.P4PRunnerEndReqEvent import P4PRunnerEndReqEvent
from manager.Events import EventListener
from PeerForPeers import PeerForPeers

class P4PRunner:
    def __init__(self) -> None:
        s = PeerForPeers.getSettings()
        self._exNet:ExNet = ExNet(NetConfig(s.v4ListeningAddr, s.v6ListeningAddr))
        self._secureNet:SecureNet = SecureNet(self._exNet, PeerForPeers.getAddrToEd25519PubkeysManager())
    @EventListener
    async def onRunnerBeginReqEvent(self, _:P4PRunnerBeginReqEvent) -> None:
        await self._exNet.begin()
    @EventListener
    async def onRunnerReBeginReqEvent(self, _:P4PRunnerReBeginReqEvent) -> None:
        s = PeerForPeers.getSettings()
        self._exNet:ExNet = ExNet(NetConfig(s.v4ListeningAddr, s.v6ListeningAddr))
        self._secureNet:SecureNet = SecureNet(self._exNet, PeerForPeers.getAddrToEd25519PubkeysManager())
        await self.onRunnerBeginReqEvent(P4PRunnerBeginReqEvent())
    @EventListener
    async def onRunnerEndReqEvent(self, _:P4PRunnerEndReqEvent) -> None:
        await self._exNet.end()
    @EventListener
    def onRunnerGetSecureNetEvent(self, e:P4PRunnerGetSecureNetEvent) -> None:
        e.setSecureNet(self._secureNet)