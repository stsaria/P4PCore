from abc import ABC, abstractmethod
from typing import Awaitable

class NetHandler(ABC):
    @abstractmethod
    async def handle(self, data:bytes, addr:tuple[str, int]) -> Awaitable:
        pass
