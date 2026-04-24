import asyncio
import os
from typing import Hashable

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ED25519_KEY_SIZE = 32

class HashableEd25519PublicKey(Hashable):
    def __init__(self, key:Ed25519PublicKey):
        self._bytes = key.public_bytes(
            encoding=Encoding.Raw,
            format=PublicFormat.Raw
        )
    @classmethod
    def createByBytes(cls, bytesKey:bytes) -> "HashableEd25519PublicKey":
        self = cls.__new__(cls)
        self._bytes = bytesKey
        return self
    @property
    def bytesKey(self) -> bytes:
        return self._bytes
    
    def _verify(self, signed:bytes, data:bytes) -> bool:
        try:
            Ed25519PublicKey.from_public_bytes(self._bytes).verify(signed, data)
            return True
        except Exception:
            return False
    async def verify(self, signed:bytes, data:bytes) -> bool:
        return await asyncio.to_thread(self._verify, signed, data)

    def __hash__(self):
        return hash(self._bytes)

    def __eq__(self, obj):
        if not isinstance(obj, HashableEd25519PublicKey):
            return NotImplemented
        return self._bytes == obj._bytes
    
    