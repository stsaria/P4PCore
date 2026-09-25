import asyncio

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from P4PCore.model.HashableEd25519PublicKey import HashableEd25519PublicKey

class Ed25519Signer:
    """
    Sign data with an Ed25519 private key and expose the corresponding public key.
    """
    def __init__(self, ed25519PrivateKeyBytes:bytes | None = None):
        """
        Initialize the signer with an existing private key or generate a new one.
        :param ed25519PrivateKeyBytes: The raw 32-byte Ed25519 private key, or None to generate a new key.
        """
        self._privateKey:Ed25519PrivateKey = Ed25519PrivateKey.generate() if ed25519PrivateKeyBytes is None else Ed25519PrivateKey.from_private_bytes(ed25519PrivateKeyBytes)
    async def sign(self, data:bytes) -> bytes:
        """
        Sign the given data using the Ed25519 private key.
        :param data: The data to sign.
        :return: The raw signature bytes.
        """
        return await asyncio.to_thread(self._privateKey.sign, data)
    @property
    def publicKey(self) -> HashableEd25519PublicKey:
        """
        Get the public key corresponding to the private key.
        :return: A hashable representation of the public key.
        """
        return HashableEd25519PublicKey(self._privateKey.public_key().public_bytes_raw())