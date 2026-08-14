from typing import Protocol, TypeVar

from P4PCore.abstract.NetHandler import NetHandler

class NetHandlerRegistry:
    """
    Protocol for a registry of NetHandlers.
    """
    async def registerHandler(self, handler:NetHandler) -> bool: ...