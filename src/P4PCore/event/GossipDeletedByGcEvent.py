from P4PCore.abstract.P4PEvent import P4PEvent

class GossipDeletedByGcEvent(P4PEvent):
    """
        
    It is recommended to extend this class and decouple the implementation.
    """
    @staticmethod
    def isAsync() -> bool:
        return True
    def __init__(self, gossipContent:bytes):
        self._gossipContent = gossipContent

    @property
    def gossipContent(self) -> bytes:
        return self._gossipContent