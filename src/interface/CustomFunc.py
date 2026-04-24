from typing import Protocol, TypeVar, TypeVarTuple, Unpack, Coroutine, Any

A = TypeVarTuple("A")
R = TypeVar("R")

class CustomFunc(Protocol[Unpack[A], R]):
    @staticmethod
    async def run(*args:Unpack[A]) -> R:
        pass