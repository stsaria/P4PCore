import asyncio
from typing import Callable, Type
import typing

from src.manager.SimpleImpls import SimpleCannotDeleteKVManager
from src.abstract.P4PEvent import P4PEvent

_pendingInsts:list[object] = []

class Events:
    def __init__(self):
        self._events:SimpleCannotDeleteKVManager[Type[P4PEvent], Callable] = SimpleCannotDeleteKVManager()
        for inst in _pendingInsts:
            asyncio.run(self.registerEvent(inst))
    async def registerEvent(self, inst:object) -> None:
        for n in dir(inst):
            m = getattr(inst, n)
            if not hasattr(m, "_isAEventListener"):
                continue
            for aN, aT in typing.get_type_hints(m).items():
                if aN == "return":
                    continue
                elif not issubclass(aT, P4PEvent):
                    continue
                await self._events.atomic(lambda d: d.setdefault(aT, set()).add(m))
    async def triggerEvent(self, event:P4PEvent) -> None:
        if event.isAsync():
            await asyncio.gather(*(callback(event) for callback in await self._events.get(type(event)) or set()))
        else:
            for callback in await self._events.get(type(event)) or set():
                callback(event)

def EventListener(func:Callable) -> Callable:
    setattr(func, "_isAEventListener", True)
    return func