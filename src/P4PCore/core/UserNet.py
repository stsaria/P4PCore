from P4PCore.core.abstract.NetHandler import NetHandler
from P4PCore.core.abstract.NetHandlerRegistry import NetHandlerRegistry
from P4PCore.common.util import BytesSplitter

class UserNet(NetHandler):
    """
    Route incoming network data to the appropriate registered handler by flag.
    """
    def __init__(self, flagSize:int, registry:NetHandlerRegistry | None = None):
        """
        Create a user network instance and optionally register it with a parent registry.
        :param flagSize: The byte size of the flag prefix used to route incoming data (> 0).
        :param registry: The optional registry to register this instance with.
        :return: The initialized UserNet instance.
        """

        if flagSize <= 0:
            raise ValueError("flagSize > 0")
        self._flagSize:int = flagSize
        self._handlers:dict[bytes, NetHandler] = {}

        if registry:
            if not registry.registerHandler(self):
                raise Exception("Cannot register for NetHandler.")

    def registerHandler(self, flag:bytes, handler:NetHandler) -> bool:
        """
        Register a new NetHandler for a given flag.
        :param flag: The identifying flag bytes used to route incoming packets.
        :param handler: The handler to register for the flag.
        :return: True if the handler was registered successfully; otherwise False.
        """
        if flag in self._handlers:
            return False
        self._handlers[flag] = handler
        return True

    def deleteHandler(self, flag:bytes) -> NetHandler | None:
        """
        Delete a NetHandler for a given flag.
        :param flag: The flag bytes whose registered handler should be removed.
        :return: The removed handler, or None if no handler was registered for that flag.
        """
        return self._handlers.pop(flag, None)
    
    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        if len(data) < self._flagSize:
            return

        flag, payload = BytesSplitter.split(data, self._flagSize, includeRest=True)
        
        if handler := self._handlers.get(flag):
            await handler.handle(payload, addr)