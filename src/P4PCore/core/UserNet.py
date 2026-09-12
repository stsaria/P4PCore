from P4PCore.abstract.NetHandler import NetHandler
from P4PCore.abstract.NetHandlerRegistry import NetHandlerRegistry
from P4PCore.interface.NetHandlerFlagRegistry import NetHandlerFlagRegistry
from P4PCore.manager.SimpleImpls import SimpleCannotOverwriteKVManager
from P4PCore.util import BytesSplitter

class UserNet(NetHandler, NetHandlerFlagRegistry):
    _flagSize:int
    _handlers:SimpleCannotOverwriteKVManager[bytes, NetHandler]

    @classmethod
    async def create(cls, flagSize:int, registry:NetHandlerRegistry | None = None) -> "UserNet":
        inst = cls()

        if flagSize <= 0:
            raise ValueError("flagSize > 0")
        inst._flagSize= flagSize
        inst._handlers = SimpleCannotOverwriteKVManager()

        if registry:
            if not await registry.registerHandler(inst):
                raise Exception("Cannot register for NetHandler.")

        return inst

    async def registerHandler(self, flag:bytes, handler:NetHandler) -> bool:
        """
        Register a new NetHandler for a given flag. Returns True if the handler was registered successfully, False if a handler for the same flag already exists.
        """
        return await self._handlers.add(flag, handler)

    async def deleteHandler(self, flag:bytes) -> NetHandler | None:
        """
        Delete a NetHandler from the registry for a given flag. Returns the deleted handler if it existed, None otherwise.
        """
        return await self._handlers.delete(flag)
    
    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        if len(data) < self._flagSize:
            return

        flag, payload = BytesSplitter.split(data, self._flagSize, includeRest=True)

        handler = await self._handlers.get(flag)
        if handler is not None:
            await handler.handle(payload, addr)