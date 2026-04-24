from abc import ABC, abstractmethod
from typing import Awaitable

class NetHandler(ABC):
    """
    A NetHandler is an object that can handle packets received by something NetClass.
    You should not call heavy sync functions in a NetHandler.handle because it may block NetClass's event loop.
    """
    @abstractmethod
    async def handle(self, data:bytes, addr:tuple[str, int]) -> Awaitable:
        pass
