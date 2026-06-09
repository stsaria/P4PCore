import pytest

from P4PCore.model.X25519AndAesEncrypter import EncrypterOverflowException, X25519AndAesgcmEncrypter

class TestX25519AndAesgcmEncrypter:
    @pytest.mark.asyncio
    async def testDerive(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1, salt=encrypter1.salt)

        pubKeyB1 = encrypter1._myX25519PrivateKey.public_key().public_bytes_raw()
        pubKeyB2 = encrypter2._myX25519PrivateKey.public_key().public_bytes_raw()

        await encrypter1.derive(pubKeyB2)
        await encrypter2.derive(pubKeyB1)

        assert encrypter1._sharedSecret == encrypter2._sharedSecret

    @pytest.mark.asyncio
    async def testEncryptDecrypt(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1, salt=encrypter1.salt)

        pubKeyB1 = encrypter1._myX25519PrivateKey.public_key().public_bytes_raw()
        pubKeyB2 = encrypter2._myX25519PrivateKey.public_key().public_bytes_raw()

        await encrypter1.derive(pubKeyB2)
        await encrypter2.derive(pubKeyB1)

        data = b"hello world"
        s, encrypted = await encrypter1.encrypt(data)
        decrypted = await encrypter2.decrypt(encrypted, s)
        assert decrypted == data

    @pytest.mark.asyncio
    async def testEncryptWithoutDerive(self):
        encrypter = X25519AndAesgcmEncrypter(True, 1)
        with pytest.raises(Exception):
            await encrypter.encrypt(b"data")

    @pytest.mark.asyncio
    async def testDecryptWithoutDerive(self):
        encrypter = X25519AndAesgcmEncrypter(True, 1)
        with pytest.raises(Exception):
            await encrypter.decrypt(b"encrypted", 1)

    @pytest.mark.asyncio
    async def testDecryptInvalidData(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1, salt=encrypter1.salt)

        pubKeyB1 = encrypter1._myX25519PrivateKey.public_key().public_bytes_raw()
        pubKeyB2 = encrypter2._myX25519PrivateKey.public_key().public_bytes_raw()

        await encrypter1.derive(pubKeyB2)
        await encrypter2.derive(pubKeyB1)

        result = await encrypter2.decrypt(b"invalid data", 1)
        assert result is None
    
    @pytest.mark.asyncio
    async def testDecryptWithWrongSeq(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1, salt=encrypter1.salt)

        pubKeyB1 = encrypter1._myX25519PrivateKey.public_key().public_bytes_raw()
        pubKeyB2 = encrypter2._myX25519PrivateKey.public_key().public_bytes_raw()

        await encrypter1.derive(pubKeyB2)
        await encrypter2.derive(pubKeyB1)

        data = b"hello world"
        s, encrypted = await encrypter1.encrypt(data)
        result = await encrypter2.decrypt(encrypted, s+1)  # Wrong sequence number
        assert result is None

    @pytest.mark.asyncio
    async def testMultipleEncryptions(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1, salt=encrypter1.salt)

        pubKeyB1 = encrypter1._myX25519PrivateKey.public_key().public_bytes_raw()
        pubKeyB2 = encrypter2._myX25519PrivateKey.public_key().public_bytes_raw()

        await encrypter1.derive(pubKeyB2)
        await encrypter2.derive(pubKeyB1)

        data1 = b"first message"
        data2 = b"second message"
        data3 = b"third message"

        s1, enc1 = await encrypter1.encrypt(data1)
        s2, enc2 = await encrypter1.encrypt(data2)
        s3, enc3 = await encrypter1.encrypt(data3)

        assert await encrypter2.decrypt(enc1, s1) == data1
        assert await encrypter2.decrypt(enc2, s2) == data2
        assert await encrypter2.decrypt(enc3, s3) == data3
    
    @pytest.mark.asyncio
    async def testDecryptWithUnorderSeqs(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 2)
        encrypter2 = X25519AndAesgcmEncrypter(False, 2, salt=encrypter1.salt)

        pubKeyB1 = encrypter1._myX25519PrivateKey.public_key().public_bytes_raw()
        pubKeyB2 = encrypter2._myX25519PrivateKey.public_key().public_bytes_raw()

        await encrypter1.derive(pubKeyB2)
        await encrypter2.derive(pubKeyB1)

        data1 = b"first message"
        data2 = b"second message"

        s1, enc1 = await encrypter1.encrypt(data1)
        s2, enc2 = await encrypter1.encrypt(data2)


        assert await encrypter2.decrypt(enc2, s2) == data2
        assert await encrypter2.decrypt(enc1, s1) == data1
    
    @pytest.mark.asyncio
    async def testDecryptWithUnorderSeqsButOutOfWindow(self):
        windowSize = 10

        encrypter1 = X25519AndAesgcmEncrypter(True, windowSize)
        encrypter2 = X25519AndAesgcmEncrypter(False, windowSize, salt=encrypter1.salt)

        pubKeyB1 = encrypter1._myX25519PrivateKey.public_key().public_bytes_raw()
        pubKeyB2 = encrypter2._myX25519PrivateKey.public_key().public_bytes_raw()

        await encrypter1.derive(pubKeyB2)
        await encrypter2.derive(pubKeyB1)

        encs = [
            ((data := f"{i}st message".encode(),) + await encrypter1.encrypt(data))
            for i in range(windowSize+1)
        ]
        encs.reverse()

        for i in range(windowSize):
            assert await encrypter2.decrypt(encs[i][2], encs[i][1])
        assert await encrypter2.decrypt(encs[windowSize][2], encs[windowSize][1]) is None

class TestEncrypterOverflowException:
    @pytest.mark.asyncio
    async def testEncrypterOverflowExceptionOnEncryption(self):
        encrypter = X25519AndAesgcmEncrypter(True, 1, encryptSeqLimits=1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1, salt=encrypter.salt)
        await encrypter.derive(encrypter2.myX25519PublicKeyBytes)
        assert await encrypter.encrypt(b"data1")
        with pytest.raises(EncrypterOverflowException):
            await encrypter.encrypt(b"data2")
    @pytest.mark.asyncio
    async def testEncrypterOverflowExceptionOnDecryption(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1, salt=encrypter1.salt, encryptSeqLimits=1)

        pubKeyB1 = encrypter1._myX25519PrivateKey.public_key().public_bytes_raw()
        pubKeyB2 = encrypter2._myX25519PrivateKey.public_key().public_bytes_raw()

        await encrypter1.derive(pubKeyB2)
        await encrypter2.derive(pubKeyB1)

        data = b"hello world"
        s, encrypted = await encrypter1.encrypt(data+b"1")
        s2, encrypted2 = await encrypter1.encrypt(data+b"2")

        assert await encrypter2.decrypt(encrypted, s) == data+b"1"
        with pytest.raises(EncrypterOverflowException):
            await encrypter2.decrypt(encrypted2, s2)
