import os

from P4PCore.protocol.Protocol import ANY_UNIQUE_RANDOM_BYTES_SIZE

WAITING_RESPONSE_INFO_KEY = tuple[tuple[str, int], bytes]

class WaitingResponseInfo:
    """
    Store the address and a random identifier for a waiting response.
    """
    def __init__(self, addr:tuple[str, int], uniqueBytesSize:int=ANY_UNIQUE_RANDOM_BYTES_SIZE):
        """
        Initialize the waiting response metadata.
        :param addr: The network address associated with the waiting response.
        """
        self._addr:tuple[str, int] = addr
        
        self._identify:bytes = os.urandom(uniqueBytesSize)
    @property
    def identify(self) -> bytes:
        """
        The unique identifier used to distinguish this waiting response.
        """
        return self._identify
    @property
    def key(self) -> WAITING_RESPONSE_INFO_KEY:
        """
        A tuple of the address and unique identifier.
        """
        return self._addr, self._identify