import pytest
from P4PCore.manager.SimpleImpls import *

class TestSimpleImplsManager:
    @pytest.mark.asyncio
    async def testSimpleSetManagerAdd(self):
        manager: SimpleSetManager[int] = SimpleSetManager()
        assert await manager.add(1) is True
        assert await manager.add(1) is False  
        assert await manager.contains(1) is True

    @pytest.mark.asyncio
    async def testSimpleSetManagerRemove(self):
        manager: SimpleSetManager[int] = SimpleSetManager()
        await manager.add(1)
        assert await manager.remove(1) is True
        assert await manager.remove(1) is False  
        assert await manager.contains(1) is False

    @pytest.mark.asyncio
    async def testSimpleSetManagerClear(self):
        manager: SimpleSetManager[int] = SimpleSetManager()
        await manager.add(1)
        await manager.add(2)
        await manager.add(3)
        await manager.clear()
        assert await manager.contains(1) is False
        assert await manager.contains(2) is False
        assert await manager.contains(3) is False

    @pytest.mark.asyncio
    async def testSimpleSetManagerGetAll(self):
        manager: SimpleSetManager[int] = SimpleSetManager()
        await manager.add(1)
        await manager.add(2)
        await manager.add(3)
        all_items = await manager.getAll()
        assert all_items == {1, 2, 3}

    @pytest.mark.asyncio
    async def testSimpleSetManagerAtomic(self):
        manager: SimpleSetManager[int] = SimpleSetManager()
        await manager.add(1)
        await manager.add(2)
        
        def atomic(s: set[int], x: int) -> int:
            assert x == 3
            s.add(3)
            return len(s)
        
        result = await manager.atomic(atomic, 3)
        assert result == 3
        assert await manager.contains(3) is True
    
    @pytest.mark.asyncio
    async def testSimpleSetManagerAtomicAsync(self):
        manager: SimpleSetManager[int] = SimpleSetManager()
        await manager.add(1)
        await manager.add(2)
        
        async def atomic(s: set[int], x: int) -> int:
            assert x == 3
            s.add(3)
            return len(s)
        
        result = await manager.atomic(atomic, 3)
        assert result == 3
        assert await manager.contains(3) is True

    @pytest.mark.asyncio
    async def testSimpleListManagerInsertNext(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        await manager.insertNext(0, 0)  
        assert await manager.get(0) == 1
        assert await manager.get(1) == 0

    @pytest.mark.asyncio
    async def testSimpleListManagerChange(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        await manager.change(0, 10)
        assert await manager.get(0) == 10

    @pytest.mark.asyncio
    async def testSimpleListManagerGet(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        await manager.insertNext(3)
        assert await manager.get(0) == 1
        assert await manager.get(-1) == 3
        assert await manager.get(10) is None  

    @pytest.mark.asyncio
    async def testSimpleListManagerGetLength(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        assert await manager.getLength() == 2

    @pytest.mark.asyncio
    async def testSimpleListManagerGetIndex(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        await manager.insertNext(3)
        assert await manager.getIndex(2) == 1
        assert await manager.getIndex(99) == -1

    @pytest.mark.asyncio
    async def testSimpleListManagerDelete(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        await manager.insertNext(3)
        await manager.delete(1)
        assert await manager.get(0) == 1
        assert await manager.get(1) == 3

    @pytest.mark.asyncio
    async def testSimpleListManagerPop(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        await manager.insertNext(3)
        popped = await manager.pop(0)
        assert popped == 1
        assert await manager.getLength() == 2

    @pytest.mark.asyncio
    async def testSimpleListManagerDeleteValue(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        await manager.insertNext(3)
        await manager.deleteValue(2)
        assert await manager.get(0) == 1
        assert await manager.get(1) == 3

    @pytest.mark.asyncio
    async def testSimpleListManagerClear(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        await manager.clear()
        assert await manager.getLength() == 0
    
    @pytest.mark.asyncio
    async def testSimpleListManagerAtomic(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        
        def atomic(l: list[int], x: int) -> int:
            assert x == 3
            l.append(3)
            return len(l)
        
        result = await manager.atomic(atomic, 3)
        assert result == 3
        assert await manager.get(2) is 3
    
    @pytest.mark.asyncio
    async def testSimpleListManagerAtomicAsync(self):
        manager: SimpleListManager[int] = SimpleListManager()
        await manager.insertNext(1)
        await manager.insertNext(2)
        
        async def atomic(l: list[int], x: int) -> int:
            assert x == 3
            l.append(3)
            return len(l)
        
        result = await manager.atomic(atomic, 3)
        assert result == 3
        assert await manager.get(2) is 3

    @pytest.mark.asyncio
    async def testSimpleKvManagerPut(self):
        manager: SimpleKVManager[str, int] = SimpleKVManager()
        old = await manager.put("key1", 100)
        assert old is None
        old = await manager.put("key1", 200)
        assert old == 100

    @pytest.mark.asyncio
    async def testSimpleKvManagerGet(self):
        manager: SimpleKVManager[str, int] = SimpleKVManager()
        await manager.put("key1", 100)
        assert await manager.get("key1") == 100
        assert await manager.get("nonexistent") is None

    @pytest.mark.asyncio
    async def testSimpleKvManagerGetAll(self):
        manager: SimpleKVManager[str, int] = SimpleKVManager()
        await manager.put("key1", 100)
        await manager.put("key2", 200)
        all_items = await manager.getAll()
        assert all_items == {"key1": 100, "key2": 200}

    @pytest.mark.asyncio
    async def testSimpleKvManagerDelete(self):
        manager: SimpleKVManager[str, int] = SimpleKVManager()
        await manager.put("key1", 100)
        deleted = await manager.delete("key1")
        assert deleted == 100
        assert await manager.get("key1") is None

    @pytest.mark.asyncio
    async def testSimpleKvManagerClear(self):
        manager: SimpleKVManager[str, int] = SimpleKVManager()
        await manager.put("key1", 100)
        await manager.put("key2", 200)
        await manager.clear()
        assert await manager.getAll() == {}
    
    @pytest.mark.asyncio
    async def testSimpleKVManagerAtomic(self):
        manager: SimpleKVManager[str, int] = SimpleKVManager()
        await manager.put("key1", 1)
        await manager.put("key2", 2)
        
        def atomic(d: dict[str, int], x: int) -> int:
            assert x == 3
            d["key3"] = 3
            return len(d)
        
        result = await manager.atomic(atomic, 3)
        assert result == 3
        assert await manager.get("key3") is 3
    
    @pytest.mark.asyncio
    async def testSimpleKVManagerAtomicAsync(self):
        manager: SimpleKVManager[str, int] = SimpleKVManager()
        await manager.put("key1", 1)
        await manager.put("key2", 2)
        
        async def atomic(d: dict[str, int], x: int) -> int:
            assert x == 3
            d["key3"] = 3
            return len(d)
        
        result = await manager.atomic(atomic, 3)
        assert result == 3
        assert await manager.get("key3") is 3




    @pytest.mark.asyncio
    async def testSimpleCannotOverwriteKvManagerAdd(self):
        manager: SimpleCannotOverwriteKVManager[str, int] = SimpleCannotOverwriteKVManager()
        assert await manager.add("key1", 100) is True
        assert await manager.add("key1", 200) is False  
        assert await manager.get("key1") == 100

    @pytest.mark.asyncio
    async def testSimpleCannotOverwriteKvManagerSameValue(self):
        manager: SimpleCannotOverwriteKVManager[str, int] = SimpleCannotOverwriteKVManager()
        await manager.add("key1", 100)
        assert await manager.add("key1", 100) is True  




    @pytest.mark.asyncio
    async def testSimpleCannotDeleteKvManagerPut(self):
        manager: SimpleCannotDeleteKVManager[str, int] = SimpleCannotDeleteKVManager()
        await manager.put("key1", 100)
        await manager.put("key1", 200)  
        assert await manager.get("key1") == 200




    @pytest.mark.asyncio
    async def testSimpleCannotDeleteAndOverwriteKvManagerAdd(self):
        manager: SimpleCannotDeleteAndOverwriteKVManager[str, int] = SimpleCannotDeleteAndOverwriteKVManager()
        assert await manager.add("key1", 100) is True
        assert await manager.add("key1", 200) is False
        assert await manager.get("key1") == 100




    @pytest.mark.asyncio
    async def testSimpleCannotDeleteAndOverwriteBiKvManagerAdd(self):
        manager: SimpleCannotDeleteAndOverwriteBiKVManager[str, int] = SimpleCannotDeleteAndOverwriteBiKVManager()
        assert await manager.add("key1", 100) is True
        assert await manager.add("key1", 200) is False
        assert await manager.add("key2", 100) is False  

    @pytest.mark.asyncio
    async def testSimpleCannotDeleteAndOverwriteBiKvManagerGetKey(self):
        manager: SimpleCannotDeleteAndOverwriteBiKVManager[str, int] = SimpleCannotDeleteAndOverwriteBiKVManager()
        await manager.add("key1", 100)
        key = await manager.getKey(100)
        assert key == "key1"
    
    @pytest.mark.asyncio
    async def testSimpleBiKVManagerAtomic(self):
        manager: SimpleCannotDeleteAndOverwriteBiKVManager[str, int] = SimpleCannotDeleteAndOverwriteBiKVManager()
        await manager.add("key1", 1)
        await manager.add("key2", 2)
        
        def atomic(d: dict[str, int], rD: dict[int, str], x: int) -> int:
            assert x == 3
            d["key3"] = 3
            rD[3] = "key3"
            return int((len(d) + len(rD)) / 2)
        
        result = await manager.atomic(atomic, 3)
        assert result == 3
        assert await manager.get("key3") is 3
        assert await manager.getKey(3) is "key3"
    
    @pytest.mark.asyncio
    async def testSimpleBiKVManagerAtomicAsync(self):
        manager: SimpleCannotDeleteAndOverwriteBiKVManager[str, int] = SimpleCannotDeleteAndOverwriteBiKVManager()
        await manager.add("key1", 1)
        await manager.add("key2", 2)
        
        async def atomic(d: dict[str, int], rD: dict[int, str], x: int) -> int:
            assert x == 3
            d["key3"] = 3
            rD[3] = "key3"
            return int((len(d) + len(rD)) / 2)
        
        result = await manager.atomic(atomic, 3)
        assert result == 3
        assert await manager.get("key3") is 3
        assert await manager.getKey(3) is "key3"