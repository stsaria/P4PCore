from typing import Protocol, TypeVar

from P4PCore.abstract.NetHandler import NetHandler

T = TypeVar("T")

class NetHandlerFlagRegistry(Protocol[T]):
    async def registerHandler(self, flag:T, handler:NetHandler) -> bool: ...