from typing import TypeVar

T = TypeVar("T")

def nonNone(x:T) -> T:
    if x is None:
        raise ValueError(f"It's none.")
    return x