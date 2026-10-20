from abc import ABC, abstractmethod

class HasLoop(ABC):
    @abstractmethod
    async def begin(self) -> None: ...
    @abstractmethod
    async def end(self) -> None: ...