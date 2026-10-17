import time
from unittest.mock import patch
import pytest

from P4PCore.common.manager.MinCountTTLCache import MinCountTTLCache


class TestMinCountTTLCache:
    @pytest.mark.asyncio
    async def testBasicOperations(self):
        cache = MinCountTTLCache[str, str](maxsize=3, ttl=10.0, minSize=0)

        cache["a"] = "apple"
        cache["b"] = "banana"
        assert cache["a"] == "apple"
        assert cache["b"] == "banana"
        assert len(cache) == 2
        assert set(iter(cache)) == {"a", "b"}

        del cache["a"]
        assert "a" not in cache
        assert len(cache) == 1

        with pytest.raises(KeyError):
            _ = cache["non_existent"]

    @pytest.mark.asyncio
    async def testMaxsizeEviction(self):
        cache = MinCountTTLCache[str, str](maxsize=2, ttl=10.0, minSize=0)

        cache["a"] = "1"
        cache["b"] = "2"
        assert len(cache) == 2

        cache["c"] = "3"
        assert "a" not in cache
        assert "b" in cache
        assert "c" in cache
        assert len(cache) == 2

    @pytest.mark.asyncio
    async def testTtlExpiration(self):
        currentTime = 100.0
        with patch("time.monotonic", side_effect=lambda: currentTime):
            cache = MinCountTTLCache[str, str](maxsize=5, ttl=5.0, minSize=0)

            cache["a"] = "apple"
            cache["b"] = "banana"

            currentTime = 106.0

            with pytest.raises(KeyError):
                _ = cache["a"]

            assert len(cache) == 0

    @pytest.mark.asyncio
    async def testMinSizeRetention(self):
        currentTime = 100.0
        with patch("time.monotonic", side_effect=lambda: currentTime):
            cache = MinCountTTLCache[str, str](maxsize=5, ttl=5.0, minSize=2)

            cache["a"] = "1"
            cache["b"] = "2"
            cache["c"] = "3"
            assert len(cache) == 3

            currentTime = 106.0
            assert len(cache) == 2

    @pytest.mark.asyncio
    async def testLenTriggersCleanupWithoutLen(self):
        currentTime = 100.0
        with patch("time.monotonic", side_effect=lambda: currentTime):
            cache = MinCountTTLCache[str, str](maxsize=5, ttl=5.0, minSize=1)

            cache["x"] = "10"
            cache["y"] = "20"

            currentTime = 106.0
            assert len(cache) == 1