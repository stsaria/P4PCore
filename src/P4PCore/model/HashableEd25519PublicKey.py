import asyncio
from typing import Hashable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

class HashableEd25519PublicKey(Hashable):
    """
    Wrap an Ed25519 public key so it can be hashed and compared by raw public key bytes.
    """
    def __init__(self, publicKeyBytes:bytes):
        """
        Initialize the wrapper from raw public key bytes.
        :param publicKeyBytes: The raw 32-byte Ed25519 public key.
        """
        self._publicKey:Ed25519PublicKey = Ed25519PublicKey.from_public_bytes(publicKeyBytes)
    @property
    def publicKeyBytes(self) -> bytes:
        """
        The encoded raw Ed25519 public key.
        """
        return self._publicKey.public_bytes_raw()
    
    def _verify(self, signed:bytes, data:bytes) -> bool:
        try:
            self._publicKey.verify(signed, data)
            return True
        except Exception:
            return False
    
    async def verify(self, signed:bytes, data:bytes) -> bool:
        """
        Verify a signature asynchronously.
        :param signed: The signature bytes to verify.
        :param data: The original data that was signed.
        :return: True if the signature is valid, otherwise False.
        """
        return await asyncio.to_thread(self._verify, signed, data)

    def __hash__(self):
        return hash(self.publicKeyBytes)

    def __eq__(self, obj):
        if not isinstance(obj, HashableEd25519PublicKey):
            return NotImplemented
        return self.publicKeyBytes == obj.publicKeyBytes