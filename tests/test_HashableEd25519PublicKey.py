import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from P4PCore.model.HashableEd25519PublicKey import HashableEd25519PublicKey


class TestHashableEd25519PublicKey:
    @pytest.mark.asyncio
    async def testCreateByKey(self):
        privateKey = Ed25519PrivateKey.generate()
        pubKeyB = privateKey.public_key().public_bytes_raw()
        hashablePubKey = HashableEd25519PublicKey(pubKeyB)
        assert hashablePubKey.publicKeyBytes is not None
        assert len(hashablePubKey.publicKeyBytes) == 32

    def testHash(self):
        privateKey = Ed25519PrivateKey.generate()
        pubKeyB = privateKey.public_key().public_bytes_raw()
        hashablePubKey = HashableEd25519PublicKey(pubKeyB)
        h1 = hash(hashablePubKey)
        h2 = hash(hashablePubKey)
        assert h1 == h2

    def testEquality(self):
        privateKey = Ed25519PrivateKey.generate()
        pubKeyB = privateKey.public_key().public_bytes_raw()
        hashablePubKey1 = HashableEd25519PublicKey(pubKeyB)
        hashablePubKey2 = HashableEd25519PublicKey(pubKeyB)
        assert hashablePubKey1 == hashablePubKey2

    def testInequality(self):
        privateKey1 = Ed25519PrivateKey.generate()
        privateKey2 = Ed25519PrivateKey.generate()
        pubKeyB1 = privateKey1.public_key().public_bytes_raw()
        pubKeyB2 = privateKey2.public_key().public_bytes_raw()
        hashablePubKey1 = HashableEd25519PublicKey(pubKeyB1)
        hashablePubKey2 = HashableEd25519PublicKey(pubKeyB2)
        assert hashablePubKey1 != hashablePubKey2

    @pytest.mark.asyncio
    async def testVerifyValid(self):
        privateKey = Ed25519PrivateKey.generate()
        pubKeyB = privateKey.public_key().public_bytes_raw()
        hashablePubKey = HashableEd25519PublicKey(pubKeyB)
        data = b"test data"
        signature = privateKey.sign(data)
        result = await hashablePubKey.verify(signature, data)
        assert result is True

    @pytest.mark.asyncio
    async def testVerifyInvalid(self):
        privateKey1 = Ed25519PrivateKey.generate()
        privateKey2 = Ed25519PrivateKey.generate()
        pubKeyB1 = privateKey1.public_key().public_bytes_raw()
        hashablePubKeyB1 = HashableEd25519PublicKey(pubKeyB1)
        data = b"test data"
        signature = privateKey2.sign(data)
        result = await hashablePubKeyB1.verify(signature, data)
        assert result is False