import asyncio
import os
from typing import Hashable

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ED25519_KEY_SIZE = 32

class HashableEd25519PublicKey(Hashable):
    def __init__(self, publicKeyBytes:bytes):
        self._publicKey:Ed25519PublicKey = Ed25519PublicKey.from_public_bytes(publicKeyBytes)
    @property
    def publicKeyBytes(self) -> bytes:
        return self._publicKey.public_bytes_raw()
    
    def _verify(self, signed:bytes, data:bytes) -> bool:
        try:
            self._publicKey.verify(signed, data)
            return True
        except Exception:
            return False
    async def verify(self, signed:bytes, data:bytes) -> bool:
        return await asyncio.to_thread(self._verify, signed, data)

    def __hash__(self):
        return hash(self.publicKeyBytes)

    def __eq__(self, obj):
        if not isinstance(obj, HashableEd25519PublicKey):
            return NotImplemented
        return self.publicKeyBytes == obj.publicKeyBytes