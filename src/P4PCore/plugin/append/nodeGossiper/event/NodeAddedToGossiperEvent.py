from P4PCore.common.abstract.P4PEvent import P4PEvent
from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.plugin.append.nodeGossiper.util.NodeIdentifyConverter import bytesToNodeIdentify

class NodeAddedToGossiperEvent(P4PEvent):
    def __init__(self, addedNodeIdentify:NodeIdentify):
        """
        Initialize the event with the added node's identifying information.
        :param addedNodeBytes: The bytes representing the added node's identifying information.
        """
        self._addedNodeIdentify:NodeIdentify = addedNodeIdentify
    @staticmethod
    def isAsync() -> bool:
        return False    
    @property
    def addedNodeIdentify(self) -> NodeIdentify | None:
        """
        The identifying information of the node that was added to the gossiper.
        """
        return self._addedNodeIdentify