from enum import Enum
from typing import Protocol, TypeVar

from abstract.NetHandler import NetHandler

T = TypeVar("T")

class NetHandlerRegistry(Protocol[T]):
    async def registerHandler(self, flag:T, handler:NetHandler) -> bool: ...