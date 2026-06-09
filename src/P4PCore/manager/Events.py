import asyncio
from typing import Callable, Type
import typing

from P4PCore.manager.SimpleImpls import SimpleCannotDeleteKVManager
from P4PCore.abstract.P4PEvent import P4PEvent

_pendingInsts:list[object] = []

class Events:
    def __init__(self):
        self._events:SimpleCannotDeleteKVManager[Type[P4PEvent], Callable] = SimpleCannotDeleteKVManager()
        for inst in _pendingInsts:
            asyncio.run(self.registerListener(inst))
    async def registerListener(self, inst:object) -> None:
        """
        Register an instance to listen to events.
        
        The instance in argument should have methods decorated with @EventListener, and the type hint of the first argument of these methods should be a subclass of P4PEvent.
        """
        for n in dir(inst):
            m = getattr(inst, n)
            if not hasattr(m, "_isAEventListener"):
                continue
            for funcName, funcType in typing.get_type_hints(m).items():
                if funcName == "return":
                    continue
                elif not issubclass(funcType, P4PEvent):
                    continue
                await self._events.atomic(lambda d: d.setdefault(funcType, set()).add(m))
    async def triggerEvent(self, event:P4PEvent) -> None:
        """
        Trigger an event. All the listeners registered to listen to this type of event will be called.
        """
        callbacks = await self._events.get(type(event))
        if not callbacks:
            return
        
        if event.isAsync():
            await asyncio.gather(
                *(callback(event) for callback in callbacks),
                return_exceptions=True
            )
        else:
            for callback in callbacks:
                callback(event)

def EventListener(func:Callable) -> Callable:
    setattr(func, "_isAEventListener", True)
    return func