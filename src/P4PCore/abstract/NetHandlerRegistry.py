from P4PCore.abstract.NetHandler import NetHandler

class NetHandlerRegistry:
    """
    Protocol for a registry of NetHandlers.
    """
    def registerHandler(self, handler:NetHandler) -> bool: ...