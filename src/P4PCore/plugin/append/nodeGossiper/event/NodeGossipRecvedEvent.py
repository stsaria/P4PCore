from P4PCore.plugin.base.gossiper.event.GossipRecvedEvent import GossipRecvedEvent
from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.plugin.append.nodeGossiper.util.NodeIdentifyConverter import bytesToNodeIdentify

class NodeGossipRecvedEvent(GossipRecvedEvent):
    @property
    def recvedNode(self) -> NodeIdentify | None:
        """
        Returns the identifying information of the received node.

        The gossip payload is converted into a NodeIdentify instance so the
        details of the received node can be retrieved.
        """
        return bytesToNodeIdentify(self._gossipContent)