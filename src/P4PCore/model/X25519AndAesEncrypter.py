import os
import asyncio
from asyncio import Lock
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey, X25519PrivateKey
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from P4PCore.protocol.Protocol import *
from P4PCore.util.BytesCoverter import itob

class EncrypterOverflowException(OverflowError):
    """
    Raised when the encryption sequence number exceeds the configured limit.
    This class is required at overflowed sequence, but sequence length is uint64, so it won't happen in most cases.
    """
    def __init__(self, sequenceWhenOverflowed:int, originalData:bytes):
        """
        Initialize the overflow exception with the sequence number and original data.
        :param sequenceWhenOverflowed: The sequence number when the overflow happened.
        :param originalData: The original data that caused the overflow context.
        """
        self._sequenceWhenOverflowed = sequenceWhenOverflowed
        self._originalData = originalData
        super().__init__(f"Sequence number already have hit {self._sequenceWhenOverflowed} max")
    @property
    def seqWhenOverflowed(self) -> int:
        """
        The sequence number when the overflow occurred.
        """
        return self._sequenceWhenOverflowed
    @property
    def originalData(self) -> bytes:
        """
        The original data associated with the overflow.
        """
        return self._originalData

class X25519AndAesgcmEncrypter:
    """
    Encrypt and decrypt data using X25519 key agreement and AES-GCM with sequence tracking.
    """
    def __init__(self, amIFirstNodeToHello:bool, encryptSeqWindowSize:int, salt:bytes | None = None, encryptSeqLimits:int = MAX_SEQ_OF_SECURE_NET):
        """
        Initialize the encrypter with hello-order and sequence-window settings.
        :param amIFirstNodeToHello: True when this node initiates the hello exchange, otherwise False.
        :param encryptSeqWindowSize: The size of the sequence window used to detect duplicate or out-of-order packets.
        :param salt: Optional salt bytes for key derivation, or None to generate a random one.
        :param encryptSeqLimits: The maximum valid encryption sequence value.
        """
        self._amIFirstNodeToHello:bool = amIFirstNodeToHello
        self._encryptSeqWindowSize:int = encryptSeqWindowSize
        self._encryptSeqLimits:int = encryptSeqLimits

        self._salt:bytes = salt if not salt is None else os.urandom(SecurePacketElementSize.AES_SALT)
        self._myX25519PrivateKey:X25519PrivateKey = X25519PrivateKey.generate()
        
        self._sharedSecret:bytes | None = None
        self._aesKey:AESGCM | None = None
        self._secretsLock:Lock = Lock()

        self._seq:int = 0
        self._seqLock:Lock = Lock()

        self._otherPartySeq:int = 0
        self._otherPartySeqBitmap:int = 0
        self._otherPartySeqLock:Lock = Lock()
    def _deriveSharedSecretSyncronized(self, otherPartyX25519PublicKey:X25519PublicKey) -> None:
        self._sharedSecret = HKDF(
            algorithm=SHA256(),
            length=32,
            salt=self._salt,
            info=X25519_DERIVE_KEY_INFO
        ).derive(self._myX25519PrivateKey.exchange(otherPartyX25519PublicKey))
    def _deriveAesKeySyncronized(self, info:bytes) -> None:
        self._aesKey = AESGCM(
            HKDF(
                algorithm=SHA256(),
                length=32,
                salt=self._salt,
                info=info
            ).derive(self._sharedSecret)
        )
    async def derive(self, otherPartyX25519PublicKeyBytes:bytes) -> None:
        """
        Derive the shared secret and AES key using the peer public key bytes.
        :param otherPartyX25519PublicKeyBytes: The raw X25519 public key bytes of the peer.
        """
        oPK = X25519PublicKey.from_public_bytes(
            otherPartyX25519PublicKeyBytes
        )
        async with self._secretsLock:
            await asyncio.to_thread(self._deriveSharedSecretSyncronized, oPK)
            await asyncio.to_thread(self._deriveAesKeySyncronized, X25519S_SHARED_SECRET_AND_AES_KEY_INFO)
    async def encrypt(self, data:bytes) -> tuple[int, bytes]:
        """
        Encrypt data using the derived AES-GCM key and incrementing sequence number.
        :param data: The plaintext bytes to encrypt.
        :return: A tuple containing the sequence number and the ciphertext bytes.
        """
        async with self._secretsLock:
            if self._aesKey is None:
                raise Exception("Shared secret and AES key are not derived yet.")
        async with self._seqLock:
            self._seq += 1
            seq = self._seq
            if seq > self._encryptSeqLimits:
                raise EncrypterOverflowException(seq, data)
        nonceBA = bytearray(AESGCM_NONCE_SIZE)
        nonceBA[0] = 0x01 if self._amIFirstNodeToHello else 0x00
        nonceBA[AESGCM_NONCE_SIZE-PacketElementSize.SEQ:] = itob(seq, PacketElementSize.SEQ)
        return seq, await asyncio.to_thread(self._aesKey.encrypt, bytes(nonceBA), data, None)
    async def decrypt(self, encryptedData:bytes, seq:int) -> bytes | None:
        """
        Decrypt data using the sequence number and reject replayed or out-of-window packets.
        :param encryptedData: The ciphertext bytes to decrypt.
        :param seq: The sequence number associated with the ciphertext.
        :return: The decrypted plaintext bytes if valid, otherwise None.
        """
        async with self._secretsLock:
            if self._aesKey is None:
                raise Exception("Shared secret and AES key are not derived yet.")
        nonceBA = bytearray(AESGCM_NONCE_SIZE)
        nonceBA[0] = 0x00 if self._amIFirstNodeToHello else 0x01
        nonceBA[AESGCM_NONCE_SIZE-PacketElementSize.SEQ:] = itob(seq, PacketElementSize.SEQ)
        try:
            data = await asyncio.to_thread(self._aesKey.decrypt, bytes(nonceBA), encryptedData, None)
        except InvalidTag:
            return None
        async with self._otherPartySeqLock:
            diff = self._otherPartySeq - seq
            if seq > self._otherPartySeq:
                diff = seq - self._otherPartySeq
                self._otherPartySeqBitmap = (self._otherPartySeqBitmap << diff) & ((1 << self._encryptSeqWindowSize)-1)
                self._otherPartySeqBitmap |= 1
                self._otherPartySeq = seq
                if seq > self._encryptSeqLimits:
                    raise EncrypterOverflowException(seq, data)
            elif diff < self._encryptSeqWindowSize:
                if (self._otherPartySeqBitmap >> diff) & 1:
                    return None
                self._otherPartySeqBitmap |= (1 << diff)
            else:
                return None
        return data
    @property
    def salt(self) -> bytes:
        """
        The salt bytes used in the HKDF derivation.
        """
        return self._salt
    @property
    def myX25519PublicKeyBytes(self) -> bytes:
        """
        The raw public X25519 key bytes.
        """
        return self._myX25519PrivateKey.public_key().public_bytes_raw()