from P4PCore.abstract.P4PEvent import P4PEvent

class SecureNetStartedToHelloOnRecver(P4PEvent):
    @staticmethod
    def isAsync() -> bool:
        return True
    def __init__(self, addr:tuple[str, int]):
        self._addr:tuple[str, int] = addr
        self._helloVolume:int = 5
        self._encryptSeqWindowSize:int = 1
        self._timeoutSecOnHello:float = 5
    @property
    def addr(self) -> tuple[str, int]:
        return self._addr
    @property
    def helloVolume(self) -> int:
        """
        Number of retransmissions
        """
        return self._helloVolume
    @helloVolume.setter
    def helloVolume(self, volume:int) -> None:
        if volume <= 0:
            return ValueError("volume > 0")
        self._helloVolume = volume
    @property
    def encryptSeqWindowSize(self) -> int:
        """
        Acceptable limits of udp jitter on encryption
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
        Timeout seconds on hello
        """
        return self._timeoutSecOnHello
    @timeoutSecOnHello.setter
    def timeoutSecOnHello(self, timeoutSec:float) -> None:
        if timeoutSec < 0:
            raise ValueError("timeoutSec >= 0")
        self._timeoutSecOnHello = timeoutSec