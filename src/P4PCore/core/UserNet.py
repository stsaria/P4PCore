from P4PCore.abstract.NetHandler import NetHandler
from P4PCore.abstract.NetHandlerRegistry import NetHandlerRegistry
from P4PCore.interface.NetHandlerFlagRegistry import NetHandlerFlagRegistry
from P4PCore.manager.SimpleImpls import SimpleCannotDeleteAndOverwriteKVManager
from P4PCore.util import BytesSplitter

class UserNet(NetHandler, NetHandlerFlagRegistry):
    _flagSize:int
    _handlers:SimpleCannotDeleteAndOverwriteKVManager[bytes, NetHandler]

    @classmethod
    async def create(cls, flagSize:int, registry:NetHandlerRegistry | None = None) -> "UserNet":
        inst = cls()

        if flagSize <= 0:
            raise ValueError("flagSize > 0")
        inst._flagSize= flagSize
        inst._handlers = SimpleCannotDeleteAndOverwriteKVManager()

        if registry:
            if not await registry.registerHandler(inst):
                raise Exception("Cannot register for NetHandler.")

        return inst

    async def registerHandler(self, flag:bytes, handler:NetHandler) -> bool:
        """
        Register a new NetHandler for a given flag.
        """
        return await self._handlers.add(flag, handler)

    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        if len(data) < self._flagSize:
            return

        flag, payload = BytesSplitter.split(data, self._flagSize, includeRest=True)

        handler = await self._handlers.get(flag)
        if handler is not None:
            await handler.handle(payload, addr)