import asyncio
from typing import Callable, Type
import typing

from P4PCore.manager.SimpleImpls import SimpleCannotDeleteKVManager
from P4PCore.abstract.P4PEvent import P4PEvent

class Events:
    """
    Manage event listeners and dispatch matching events to them.
    """
    def __init__(self):
        """
        Initialize the event registry.
        """
        self._events:SimpleCannotDeleteKVManager[Type[P4PEvent], Callable] = SimpleCannotDeleteKVManager()
    async def registerListener(self, inst:object) -> None:
        """
        Register an instance to listen to events.
        :param inst: The instance whose methods are decorated with @EventListener.
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
        :param event: The event instance to trigger.
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
    """
    Mark a method as a listener for a specific P4P event type.
    """
    setattr(func, "_isAEventListener", True)
    return func