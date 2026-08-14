from P4PCore.abstract.P4PEvent import P4PEvent

class GossipRecvedEvent(P4PEvent):
    """
    
    It is recommended to extend this class and decouple the implementation.
    """
    @staticmethod
    def isAsync() -> bool:
        return True
    def __init__(self, gossipContent:bytes, addr:tuple[str, int]):
        self._gossipContent:bytes = gossipContent
        self._addr:tuple[str, int] = addr

    @property
    def gossipContent(self) -> bytes:
        return self._gossipContent

    @property
    def addr(self) -> tuple[str, int]:
        return self._addr