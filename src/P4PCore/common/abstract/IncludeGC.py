from abc import ABC, abstractmethod

class IncludeGC(ABC):
    @abstractmethod
    async def gc(self) -> None: ...
    @abstractmethod
    async def gcLoop(self) -> None: ...
    