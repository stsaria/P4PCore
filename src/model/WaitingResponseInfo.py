import os

from src.protocol.Protocol import ANY_UNIQUE_RANDOM_BYTES_SIZE

WAITING_RESPONSE_INFO_KEY = tuple[tuple[str, int], bytes]

class WaitingResponseInfo:
    def __init__(self, addr:tuple[str, int]):
        self._addr:tuple[str, int] = addr
        
        self._identify:bytes = os.urandom(ANY_UNIQUE_RANDOM_BYTES_SIZE)
    @property
    def identify(self) -> bytes:
        return self._identify
    @property
    def key(self) -> WAITING_RESPONSE_INFO_KEY:
        return self._addr, self._identify