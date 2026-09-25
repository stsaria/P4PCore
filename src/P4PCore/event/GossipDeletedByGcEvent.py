from P4PCore.abstract.P4PEvent import P4PEvent

class GossipDeletedByGcEvent(P4PEvent):
    """Event fired when a gossip item is removed by the garbage collector."""
    @staticmethod
    def isAsync() -> bool:
        return True
    def __init__(self, gossipContent:bytes):
        """
        Initialize the event with the deleted gossip payload.
        :param gossipContent: The gossip content that was removed by the GC.
        """
        self._gossipContent = gossipContent

    @property
    def gossipContent(self) -> bytes:
        """
        Get the deleted gossip payload.
        :return: The gossip content that was removed.
        """
        return self._gossipContent