from src.event.P4PRunnerBeginReqEvent import P4PRunnerBeginReqEvent
from src.event.P4PRunnerEndReqEvent import P4PRunnerEndReqEvent
from src.manager.Events import EventListener
from src.PeerForPeers import PeerForPeers

class P4PRunner:
    def __init__(self) -> None:
        pass
    @EventListener
    async def onRunnerEndReqEvent(self, _:P4PRunnerEndReqEvent) -> None:
        await PeerForPeers.getTasksManager().stopAllTasks()
    @EventListener
    async def onRunnerBeginReqEvent(self, _:P4PRunnerBeginReqEvent) -> None:
        pass