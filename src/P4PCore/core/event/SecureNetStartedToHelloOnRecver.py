from P4PCore.common.abstract.P4PEvent import P4PEvent
from P4PCore.common.model.HashableEd25519PublicKey import HashableEd25519PublicKey

class SecureNetStartedToHelloOnRecver(P4PEvent):
    """
    Event fired when the receiver starts the secure hello process for a node.
    """
    @staticmethod
    def isAsync() -> bool:
        return True
    def __init__(self, addr:tuple[str, int], hashableEd25519PublicKey:HashableEd25519PublicKey):
        """
        Initialize the event with the node address.
        :param addr: The node address starting the hello exchange.
        :param hashableEd25519PublicKey: The Ed25519 public key of the node starting the hello exchange.
        """
        self._addr:tuple[str, int] = addr
        self._hashableEd25519PublicKey:HashableEd25519PublicKey = hashableEd25519PublicKey
        self._helloVolume:int = 5
        self._encryptSeqWindowSize:int = 1
        self._timeoutSecOnHello:float = 5
    @property
    def addr(self) -> tuple[str, int]:
        """
        The node's addr.
        """
        return self._addr
    @property
    def hashableEd25519PublicKey(self) -> HashableEd25519PublicKey:
        """
        The node's Ed25519 public key (Not approved by challenge).
        """
        return self._hashableEd25519PublicKey
    @property
    def helloVolume(self) -> int:
        """
        The number of retransmissions (> 0).
        """
        return self._helloVolume
    @helloVolume.setter
    def helloVolume(self, volume:int) -> None:
        if volume <= 0:
            return ValueError("helloVolume > 0")
        self._helloVolume = volume
    @property
    def encryptSeqWindowSize(self) -> int:
        """
        The allowed retry window size for encryption sequence jitter (> 0).
        """
        return self._encryptSeqWindowSize
    @encryptSeqWindowSize.setter
    def encryptSeqWindowSize(self, windowSize:int) -> None:
        if windowSize <= 0:
            raise ValueError("windowSize > 0")
        self._encryptSeqWindowSize = windowSize
    @property
    def timeoutSecOnHello(self) -> float:
        """
        The hello timeout duration (>= 0).
        """
        return self._timeoutSecOnHello
    @timeoutSecOnHello.setter
    def timeoutSecOnHello(self, timeoutSec:float) -> None:
        if timeoutSec < 0:
            raise ValueError("timeoutSec >= 0")
        self._timeoutSecOnHello = timeoutSec