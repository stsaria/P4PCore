import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from P4PCore.common.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.core.event.SecureNetStartedToHelloOnRecver import SecureNetStartedToHelloOnRecver


class TestSecureNetStartedToHelloOnRecver:
    def testHelloVolumeRejectsNonPositiveValues(self):
        publicKey = HashableEd25519PublicKey(
            Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        )
        event = SecureNetStartedToHelloOnRecver(("127.0.0.1", 1), publicKey)

        with pytest.raises(ValueError, match="helloVolume > 0"):
            event.helloVolume = 0

        assert event.helloVolume == 5

    def testHelloVolumeAcceptsPositiveValues(self):
        publicKey = HashableEd25519PublicKey(
            Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        )
        event = SecureNetStartedToHelloOnRecver(("127.0.0.1", 1), publicKey)

        event.helloVolume = 3

        assert event.helloVolume == 3
