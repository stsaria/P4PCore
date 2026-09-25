from P4PCore.abstract.NetHandler import NetHandler
from P4PCore.abstract.NetHandlerRegistry import NetHandlerRegistry
from P4PCore.interface.NetHandlerFlagRegistry import NetHandlerFlagRegistry
from P4PCore.manager.SimpleImpls import SimpleCannotOverwriteKVManager
from P4PCore.util import BytesSplitter

class UserNet(NetHandler, NetHandlerFlagRegistry):
    """
    Route incoming network data to the appropriate registered handler by flag.
    """
    _flagSize:int
    _handlers:SimpleCannotOverwriteKVManager[bytes, NetHandler]

    @classmethod
    async def create(cls, flagSize:int, registry:NetHandlerRegistry | None = None) -> "UserNet":
        """
        Create a user network instance and optionally register it with a parent registry.
        :param flagSize: The byte size of the flag prefix used to route incoming data (> 0).
        :param registry: The optional registry to register this instance with.
        :return: The initialized UserNet instance.
        """
        inst = cls()

        if flagSize <= 0:
            raise ValueError("flagSize > 0")
        inst._flagSize = flagSize
        inst._handlers = SimpleCannotOverwriteKVManager()

        if registry:
            if not await registry.registerHandler(inst):
                raise Exception("Cannot register for NetHandler.")

        return inst

    async def registerHandler(self, flag:bytes, handler:NetHandler) -> bool:
        """
        Register a new NetHandler for a given flag.
        :param flag: The identifying flag bytes used to route incoming packets.
        :param handler: The handler to register for the flag.
        :return: True if the handler was registered successfully; otherwise False.
        """
        return await self._handlers.add(flag, handler)

    async def deleteHandler(self, flag:bytes) -> NetHandler | None:
        """
        Delete a NetHandler for a given flag.
        :param flag: The flag bytes whose registered handler should be removed.
        :return: The removed handler, or None if no handler was registered for that flag.
        """
        return await self._handlers.delete(flag)
    
    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        if len(data) < self._flagSize:
            return

        flag, payload = BytesSplitter.split(data, self._flagSize, includeRest=True)

        handler = await self._handlers.get(flag)
        if handler is not None:
            await handler.handle(payload, addr)