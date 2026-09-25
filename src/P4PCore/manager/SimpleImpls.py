from asyncio import Lock
from typing import Awaitable, Callable, TypeVar, ParamSpec, Concatenate, Generic

from P4PCore.interface.Manager import *

P = ParamSpec("P")
R = TypeVar("R", covariant=True)

K = TypeVar("K")
V = TypeVar("V")
I = TypeVar("I")

class SimpleSetManager(SetManager, Generic[I]):
    """
    A simple implementation of a set manager that provides thread-safe operations on a set.
    """
    def __init__(self):
        """
        Initialize the manager.
        """
        self._set:set[I] = set()
        self._setLock:Lock = Lock()
    async def add(self, item:I) -> bool:
        """
        Add an item to the set.
        :param item: The item to add.
        :return: True if the item was added, False if it was already present.
        """
        async with self._setLock:
            if item in self._set:
                return False
            self._set.add(item)
        return True
    async def contains(self, item:I) -> bool:
        """
        Check if the set contains an item.
        :param item: The item to check.
        :return: True if the item is present, False otherwise.
        """
        async with self._setLock:
            return item in self._set
    async def remove(self, item:I) -> bool:
        """
        Remove an item from the set.
        :param item: The item to remove.
        :return: True if the item was removed, False if it was not present.
        """
        async with self._setLock:
            if not item in self._set:
                return False
            self._set.remove(item)
        return True
    async def clear(self) -> None:
        """
        Clear all items from the set.
        """
        async with self._setLock:
            self._set.clear()
    async def getAll(self) -> set[I]:
        """
        Get all items in the set.
        :return: A set containing all items.
        """
        async with self._setLock:
            return set(self._set)
    async def atomic(self, func:Callable[Concatenate[set[I], P], R], *args:P.args, **kwargs:P.kwargs) -> R:
        """
        Perform an atomic operation on the set.
        :param func: A callable that takes the set and additional arguments, and returns a result.
        :param args: Additional positional arguments to pass to the callable.
        :param kwargs: Additional keyword arguments to pass to the callable.
        :return: The result of the callable.
        """
        async with self._setLock:
            r = func(self._set, *args, **kwargs)
            if isinstance(r, Awaitable):
                return await r
            return r

class SimpleListManager(ListManager, Generic[I]):
    """
    A simple implementation of a list manager that provides thread-safe operations on a list.
    """
    def __init__(self):
        """
        Initialize the manager.
        """
        self._list:list[I] = []
        self._listLock:Lock = Lock()
    async def insertNext(self, value:I, index:int = -1) -> None:
        """
        Insert a value into the list at the specified index.
        :param value: The value to insert.
        :param index: The index at which to insert the value. Defaults to -1 (insert at the end).
        """
        async with self._listLock:
            if index < 0:
                index = len(self._list) - abs(index)
            self._list.insert(index+1, value)
    async def change(self, index:int, value:I) -> None:
        """
        Change the value at the specified index in the list.
        :param index: The index of the value to change.
        :param value: The new value to set at the specified index.
        """
        async with self._listLock:
            self._list[index] = value
    async def get(self, index:int) -> I | None:
        """
        Get the value at the specified index in the list.
        :param index: The index of the value to get.
        :return: The value at the specified index, or None if the index is out of bounds.
        """
        async with self._listLock:
            l = len(self._list)
            if -l <= index < l:
                return self._list[index]
        return None
    async def getLength(self) -> int:
        """
        Get the length of the list.
        :return: The length of the list.
        """
        async with self._listLock:
            return len(self._list)
    async def getIndex(self, value:I) -> int:
        """
        Get the index of the specified value in the list.
        :param value: The value to find.
        :return: The index of the value, or -1 if the value is not found.
        """
        async with self._listLock:
            if not value in self._list:
                return -1
            return self._list.index(value)
    async def getAll(self) -> list[I]:
        """
        Get all values in the list.
        :return: A list containing all values.
        """
        async with self._listLock:
            return self._list.copy()
    async def delete(self, index:int) -> None:
        """
        Delete the value at the specified index in the list.
        :param index: The index of the value to delete.
        """
        async with self._listLock:
            del self._list[index]
    async def pop(self, index:int) -> I | None:
        """
        Pop the value at the specified index in the list.
        :param index: The index of the value to pop.
        :return: The value that was popped, or None if the index is out of bounds
        """
        async with self._listLock:
            return self._list.pop(index)
    async def deleteValue(self, value:I) -> None:
        """
        Delete the first matching value from the list.
        :param value: The value to delete.
        """
        async with self._listLock:
            self._list.remove(value)
    async def clear(self) -> None:
        """
        Clear all values from the list.
        """
        async with self._listLock:
            self._list.clear()
    async def atomic(self, func:Callable[Concatenate[list[I], P], R], *args:P.args, **kwargs:P.kwargs) -> R:
        """
        Perform an atomic operation on the list.
        :param func: A callable that takes the list and additional arguments, and returns a result.
        :param args: Additional positional arguments to pass to the callable.
        :param kwargs: Additional keyword arguments to pass to the callable.
        :return: The result of the callable.
        """
        async with self._listLock:
            r = func(self._list, *args, **kwargs)
            if isinstance(r, Awaitable):
                return await r
            return r

class _BaseKVManager(Generic[K, V]):
    def __init__(self):
        """
        Initialize the manager.
        """
        self._dict:dict[K, V] = {}
        self._dictLock:Lock = Lock()
    async def atomic(self, func:Callable[Concatenate[dict[K, V], P], R], *args:P.args, **kwargs:P.kwargs) -> R:
        """
        Perform an atomic operation on the underlying dictionary.
        :param func: A callable that takes the dictionary and additional arguments, and returns a result.
        :param args: Additional positional arguments to pass to the callable.
        :param kwargs: Additional keyword arguments to pass to the callable.
        :return: The result of the callable.
        """
        async with self._dictLock:
            r = func(self._dict, *args, **kwargs)
            if isinstance(r, Awaitable):
                return await r
            return r
class _BaseBiKVManager(Generic[K, V]):
    def __init__(self):
        """
        Initialize the manager.
        """
        self._dict:dict[K, V] = {}
        self._dictLock:Lock = Lock()
        self._rDict:dict[V, K] = {}
    async def atomic(self, func:Callable[Concatenate[dict[K, V], dict[V, K], P], R], *args:P.args, **kwargs:P.kwargs) -> R:
        """
        Perform an atomic operation on both dictionary views.
        :param func: A callable that takes the forward and reverse dictionaries and additional arguments, and returns a result.
        :param args: Additional positional arguments to pass to the callable.
        :param kwargs: Additional keyword arguments to pass to the callable.
        :return: The result of the callable.
        """
        async with self._dictLock:
            r = func(self._dict, self._rDict, *args, **kwargs)
            if isinstance(r, Awaitable):
                return await r
            return r
class _WriteKVMixin(WriteableKV, Generic[K, V]):
    async def put(self:_BaseKVManager[K, V], key:K, value:V) -> V | None:
        """
        Put a value for the specified key and return the previous value if one existed.
        :param key: The key to write.
        :param value: The value to store.
        :return: The previous value for the key, or None if it was absent.
        """
        async with self._dictLock:
            oV = self._dict.get(key)
            self._dict[key] = value
        return oV
class _AddKVMixin(AddableKV, Generic[K, V]):
    async def add(self:_BaseKVManager[K, V], key:K, value:V) -> bool:
        """
        Add a key-value pair only when the key is not already present.
        :param key: The key to add.
        :param value: The value to assign.
        :return: True if the key was added, or False if the key already existed with the same value.
        """
        async with self._dictLock:
            if key in self._dict:
                return self._dict[key] == value
            self._dict[key] = value
        return True
class _AddBiKVMixin(AddableBiKV, Generic[K, V]):
    async def add(self:_BaseBiKVManager[K, V], key:K, value:V) -> bool:
        """
        Add a bidirectional mapping only when both the key and value are absent.
        :param key: The key to add.
        :param value: The value to associate.
        :return: True if the mapping was added, False if it already existed.
        """
        async with self._dictLock:
            if (oK := self._dict.get(key)) or (oV := self._rDict.get(value)):
                return oK == key and oV == value
            self._dict[key] = value
            self._rDict[value] = key
        return True
class _ReadKVMixin(ReadableKV, Generic[K, V]):
    async def get(self:_BaseKVManager[K, V], key:K) -> V | None:
        """
        Get the value associated with the specified key.
        :param key: The key to look up.
        :return: The stored value, or None if the key does not exist.
        """
        async with self._dictLock:
            return self._dict.get(key)
    async def getAll(self:_BaseKVManager[K, V]) -> dict[K, V]:
        """
        Get a copy of all key-value pairs.
        :return: A dictionary copy of the current contents.
        """
        async with self._dictLock:
            return dict(self._dict)
    async def len(self:_BaseKVManager[K, V]) -> int:
        """
        Get the number of stored key-value pairs.
        :return: The current dictionary length.
        """
        async with self._dictLock:
            return len(self._dict)
class _ReadBiKVMixin(ReadableBiKV, Generic[K, V]):
    async def get(self:_BaseBiKVManager[K, V], key:K) -> V | None:
        """
        Get the value associated with the specified key.
        :param key: The key to look up.
        :return: The stored value, or None if the key does not exist.
        """
        async with self._dictLock:
            return self._dict.get(key)
    async def getKey(self:_BaseBiKVManager[K, V], value:V) -> K | None:
        """
        Get the key associated with the specified value.
        :param value: The value to look up.
        :return: The matching key, or None if the value does not exist.
        """
        async with self._dictLock:
            return self._rDict.get(value)
    async def getAll(self:_BaseBiKVManager[K, V]) -> dict[K, V]:
        """
        Get a copy of all key-value pairs.
        :return: A dictionary copy of the current contents.
        """
        async with self._dictLock:
            return dict(self._dict)
    async def len(self:_BaseBiKVManager[K, V]) -> int:
        """
        Get the number of stored key-value pairs.
        :return: The current dictionary length.
        """
        async with self._dictLock:
            return len(self._dict)
class _DeleteKVMixin(DeletableKV, Generic[K, V]):
    async def delete(self:_BaseKVManager[K, V], key:K) -> V | None:
        """
        Delete the value for the specified key and return the removed value.
        :param key: The key to delete.
        :return: The removed value, or None if the key was absent.
        """
        async with self._dictLock:
            return self._dict.pop(key, None)
    async def clear(self:_BaseKVManager[K, V]) -> None:
        """
        Remove all key-value pairs from the dictionary.
        """
        async with self._dictLock:
            self._dict.clear()
class _DeleteBiKVMixin(DeletableBiKV, Generic[K, V]):
    async def delete(self:_BaseBiKVManager[K, V], key:K) -> bool:
        """
        Delete a mapping for the specified key and remove its reverse lookup entry.
        :param key: The key to delete.
        :return: True if the key existed and was removed, False otherwise.
        """
        async with self._dictLock:
            s = key in self._dict
            self._rDict.pop(self._dict.pop(key, None), None)
            return s
    async def deleteByValue(self:_BaseBiKVManager[K, V], value:V) -> bool:
        """
        Delete the mapping associated with the specified value.
        :param value: The value to remove.
        :return: True if the value existed and was removed, False otherwise.
        """
        async with self._dictLock:
            s = value in self._rDict
            self._dict.pop(self._rDict.pop(value, None), None)
            return s
    async def clear(self:_BaseBiKVManager[K, V]) -> None:
        """
        Remove all forward and reverse mappings from the dictionary.
        """
        async with self._dictLock:
            self._dict.clear()
            self._rDict.clear()

class SimpleKVManager(Generic[K, V], _BaseKVManager[K, V], _ReadKVMixin[K, V], _WriteKVMixin[K, V], _DeleteKVMixin[K, V]):
    """
    A simple implementation of a key-value manager that provides thread-safe dictionary operations.
    """
    pass
class SimpleCannotOverwriteKVManager(Generic[K, V], _BaseKVManager[K, V], _ReadKVMixin[K, V], _AddKVMixin[K, V], _DeleteKVMixin[K, V]):
    """
    A simple implementation of a key-value manager that prevents overwriting existing entries.
    """
    pass
class SimpleCannotDeleteKVManager(Generic[K, V], _BaseKVManager[K, V], _ReadKVMixin[K, V], _WriteKVMixin[K, V]):
    """
    A simple implementation of a key-value manager that prevents deletion while allowing updates.
    """
    pass
class SimpleCannotDeleteAndOverwriteKVManager(Generic[K, V], _BaseKVManager[K, V], _ReadKVMixin[K, V], _AddKVMixin[K, V]):
    """
    A simple implementation of a key-value manager that prevents deletion and overwriting existing entries.
    """
    pass
class SimpleCannotDeleteAndOverwriteBiKVManager(Generic[K, V], _BaseBiKVManager[K, V], _ReadBiKVMixin[K, V], _AddBiKVMixin[K, V]):
    """
    A simple implementation of a bidirectional key-value manager that prevents deletion and overwriting existing entries.
    """
    pass