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
    def __init__(self, sequenceWhenOverflowed:int, originalData:bytes):
        self._sequenceWhenOverflowed = sequenceWhenOverflowed
        self._originalData = originalData
        super().__init__(f"Sequence number already have hit {self._sequenceWhenOverflowed} max")
    @property
    def seqWhenOverflowed(self) -> int:
        return self._sequenceWhenOverflowed
    @property
    def originalData(self) -> bytes:
        return self._originalData

class X25519AndAesgcmEncrypter:
    def __init__(self, amIFirstNodeToHello:bool, encryptSeqWindowSize:int, salt:bytes | None = None, encryptSeqLimits:int = MAX_SEQ_OF_SECURE_NET):
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
        oPK = X25519PublicKey.from_public_bytes(
            otherPartyX25519PublicKeyBytes
        )
        async with self._secretsLock:
            await asyncio.to_thread(self._deriveSharedSecretSyncronized, oPK)
            await asyncio.to_thread(self._deriveAesKeySyncronized, X25519S_SHARED_SECRET_AND_AES_KEY_INFO)
    async def encrypt(self, data:bytes) -> tuple[int, bytes]:
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
        return self._salt
    @property
    def myX25519PublicKeyBytes(self) -> bytes:
        return self._myX25519PrivateKey.public_key().public_bytes_raw()