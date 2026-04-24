from P4PCore.core.SecureNet import SecureNet
from P4PCore.event.P4PRunnerGetSecureNetEvent import P4PRunnerGetSecureNetEvent

from P4PCore.event.P4PRunnerReBeginReqEvent import P4PRunnerReBeginReqEvent
from P4PCore.model.NetConfig import NetConfig
from P4PCore.core.ExNet import ExNet
from P4PCore.event.P4PRunnerBeginReqEvent import P4PRunnerBeginReqEvent
from P4PCore.event.P4PRunnerEndReqEvent import P4PRunnerEndReqEvent
from P4PCore.manager.Events import EventListener
from P4PCore.PeerForPeers import PeerForPeers

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