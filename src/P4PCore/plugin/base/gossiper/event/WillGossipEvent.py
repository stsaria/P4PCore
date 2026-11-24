from P4PCore.common.abstract.P4PEvent import P4PEvent

class WillGossipEvent(P4PEvent):
    """
    Will gossip event is fired when a node is about to gossip its information to other nodes.
    If you don't want to send the gossip, you can call the cancel() method to prevent the gossip message from being sent.

    You should use this class with inherited class to add more information about the gossip message.
    """
    @staticmethod
    def isAsync() -> bool:
        return False
    def __init__(self, gossipContent:bytes, to:tuple[str, int]):
        """
        Initialize the event with the gossip payload and the address of the node that will receive it.
        :param gossipContent: The gossip payload that will be sent.
        :param to: The address of the node that will receive the payload.
        """
        self._gossipContent:bytes = gossipContent
        self._to:tuple[str, int] = to
        self._canceled:bool = False

    @property
    def gossipContent(self) -> bytes:
        """
        The gossip payload that will be sent.
        """
        return self._gossipContent
    @gossipContent.setter
    def gossipContent(self, gossipContent:bytes) -> None:
        self._gossipContent = gossipContent

    @property
    def to(self) -> tuple[str, int]:
        """
        The address of the node that will receive the payload.
        """
        return self._to

    @property
    def canceled(self) -> bool:
        """
        Whether the event has been canceled. If True, the gossip message will not be sent.
        """
        return self._canceled
    def cancel(self) -> None:
        """
        Cancel the event. If called, the gossip message will not be sent.
        """
        self._canceled = True