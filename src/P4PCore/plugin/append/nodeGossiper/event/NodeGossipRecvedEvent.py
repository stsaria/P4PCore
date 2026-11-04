from P4PCore.plugin.base.gossiper.event.GossipRecvedEvent import GossipRecvedEvent
from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.plugin.append.nodeGossiper.util.NodeIdentifyConverter import bytesToNodeIdentify

class NodeGossipRecvedEvent(GossipRecvedEvent):
    @property
    def recvedNode(self) -> NodeIdentify | None:
        """
        The identifying information of the received node.
        """
        return bytesToNodeIdentify(self._gossipContent)