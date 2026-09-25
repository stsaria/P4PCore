from P4PCore.abstract.P4PEvent import P4PEvent

class GossipRecvedEvent(P4PEvent):
    """Event fired when a gossip message is received from a node."""
    @staticmethod
    def isAsync() -> bool:
        return True
    def __init__(self, gossipContent:bytes, addr:tuple[str, int]):
        """
        Initialize the event with the received gossip payload and sender address.
        :param gossipContent: The gossip payload that was received.
        :param addr: The address of the node that sent the payload.
        """
        self._gossipContent:bytes = gossipContent
        self._addr:tuple[str, int] = addr

    @property
    def gossipContent(self) -> bytes:
        """
        The received gossip payload.
        :return: The gossip content sent by the node.
        """
        return self._gossipContent

    @property
    def addr(self) -> tuple[str, int]:
        """
        The sender's address.
        :return: The address of the sender.
        """
        return self._addr