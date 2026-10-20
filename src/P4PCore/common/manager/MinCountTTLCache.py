import time
from collections.abc import MutableMapping
from collections.abc import Iterator
from typing import TypeVar

K = TypeVar("K")
V = TypeVar("V")

class MinCountTTLCache[K, V](MutableMapping):
    """
    A TTL cache with capacity limits and a protected minimum size.
    """
    def __init__(self, maxsize:int, ttl:float, minSize:int):
        self._maxSize = maxsize
        self._ttl = ttl
        self._minSize = minSize

        self._data: dict[K, tuple[V, float]] = {}

    def __getitem__(self, key: K) -> V:
        self._cleanup()
        if key not in self._data:
            raise KeyError(key)
        return self._data[key][0]

    def __setitem__(self, key: K, value: V) -> None:
        self._cleanup()
        if key not in self._data and len(self._data) >= self._maxSize:
            oldest_key = min(self._data, key=lambda k: self._data[k][1])
            del self._data[oldest_key]
        expire = time.monotonic() + self._ttl
        self._data[key] = (value, expire)

    def __delitem__(self, key: K) -> None:
        del self._data[key]

    def __iter__(self) -> Iterator[K]:
        self._cleanup()
        return iter(self._data)

    def snapshotItems(self) -> list[tuple[K, V]]:
        self._cleanup()
        return [
            (key, value)
            for key, (value, _) in self._data.items()
        ]

    def __len__(self) -> int:
        self._cleanupWithoutLen()
        return len(self._data)

    def _cleanup(self) -> None:
        now = time.monotonic()

        expiredKeys = sorted(
            [
                k
                for k, (_, expire) in self._data.items()
                if now > expire
            ],
            key=lambda k: self._data[k][1],
        )
        for key in expiredKeys:
            if len(self._data) <= self._minSize:
                break
            del self._data[key]

    def _cleanupWithoutLen(self) -> None:
        now = time.monotonic()
        expiredKeys = sorted(
            [
                k
                for k, (_, expireTime) in self._data.items()
                if now > expireTime
            ],
            key=lambda k: self._data[k][1],
        )

        currentSize = len(self._data)
        for key in expiredKeys:
            if currentSize <= self._minSize:
                break
            del self._data[key]
            currentSize -= 1