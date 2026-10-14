import pytest

from P4PCore.model.X25519AndAesEncrypter import EncrypterOverflowException, X25519AndAesgcmEncrypter

class TestX25519AndAesgcmEncrypter:
    def testDerive(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1)
        encrypter2.salt = encrypter1.salt

        encrypter1.otherPartyX25519PublicKeyBytes = encrypter2.myX25519PublicKeyBytes
        encrypter2.otherPartyX25519PublicKeyBytes = encrypter1.myX25519PublicKeyBytes
        encrypter1.derive()
        encrypter2.derive()

        assert encrypter1._sharedSecret == encrypter2._sharedSecret

    def testEncryptDecrypt(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1)
        encrypter2.salt = encrypter1.salt

        encrypter1.otherPartyX25519PublicKeyBytes = encrypter2.myX25519PublicKeyBytes
        encrypter2.otherPartyX25519PublicKeyBytes = encrypter1.myX25519PublicKeyBytes
        encrypter1.derive()
        encrypter2.derive()

        data = b"hello world"
        s, encrypted = encrypter1.encrypt(data)
        decrypted = encrypter2.decrypt(encrypted, s)
        assert decrypted == data

    def testEncryptWithoutDerive(self):
        encrypter = X25519AndAesgcmEncrypter(True, 1)
        with pytest.raises(Exception):
            encrypter.encrypt(b"data")

    def testDecryptWithoutDerive(self):
        encrypter = X25519AndAesgcmEncrypter(True, 1)
        with pytest.raises(Exception):
            encrypter.decrypt(b"encrypted", 1)

    def testDecryptInvalidData(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1)
        encrypter2.salt = encrypter1.salt

        encrypter1.otherPartyX25519PublicKeyBytes = encrypter2.myX25519PublicKeyBytes
        encrypter2.otherPartyX25519PublicKeyBytes = encrypter1.myX25519PublicKeyBytes
        encrypter1.derive()
        encrypter2.derive()

        result = encrypter2.decrypt(b"invalid data", 1)
        assert result is None
    
    def testDecryptWithWrongSeq(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1)
        encrypter2.salt = encrypter1.salt

        encrypter1.otherPartyX25519PublicKeyBytes = encrypter2.myX25519PublicKeyBytes
        encrypter2.otherPartyX25519PublicKeyBytes = encrypter1.myX25519PublicKeyBytes
        encrypter1.derive()
        encrypter2.derive()

        data = b"hello world"
        s, encrypted = encrypter1.encrypt(data)
        result = encrypter2.decrypt(encrypted, s+1)  # Wrong sequence number
        assert result is None

    def testMultipleEncryptions(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1)
        encrypter2.salt = encrypter1.salt

        encrypter1.otherPartyX25519PublicKeyBytes = encrypter2.myX25519PublicKeyBytes
        encrypter2.otherPartyX25519PublicKeyBytes = encrypter1.myX25519PublicKeyBytes
        encrypter1.derive()
        encrypter2.derive()

        data1 = b"first message"
        data2 = b"second message"
        data3 = b"third message"

        s1, enc1 = encrypter1.encrypt(data1)
        s2, enc2 = encrypter1.encrypt(data2)
        s3, enc3 = encrypter1.encrypt(data3)

        assert encrypter2.decrypt(enc1, s1) == data1
        assert encrypter2.decrypt(enc2, s2) == data2
        assert encrypter2.decrypt(enc3, s3) == data3
    
    def testDecryptWithUnorderSeqs(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 2)
        encrypter2 = X25519AndAesgcmEncrypter(False, 2)
        encrypter2.salt = encrypter1.salt

        encrypter1.otherPartyX25519PublicKeyBytes = encrypter2.myX25519PublicKeyBytes
        encrypter2.otherPartyX25519PublicKeyBytes = encrypter1.myX25519PublicKeyBytes
        encrypter1.derive()
        encrypter2.derive()

        data1 = b"first message"
        data2 = b"second message"

        s1, enc1 = encrypter1.encrypt(data1)
        s2, enc2 = encrypter1.encrypt(data2)


        assert encrypter2.decrypt(enc2, s2) == data2
        assert encrypter2.decrypt(enc1, s1) == data1
    
    def testDecryptWithUnorderSeqsButOutOfWindow(self):
        windowSize = 10

        encrypter1 = X25519AndAesgcmEncrypter(True, windowSize)
        encrypter2 = X25519AndAesgcmEncrypter(False, windowSize)
        encrypter2.salt = encrypter1.salt

        encrypter1.otherPartyX25519PublicKeyBytes = encrypter2.myX25519PublicKeyBytes
        encrypter2.otherPartyX25519PublicKeyBytes = encrypter1.myX25519PublicKeyBytes
        encrypter1.derive()
        encrypter2.derive()

        encs = [
            ((data := f"{i}st message".encode(),) + encrypter1.encrypt(data))
            for i in range(windowSize+1)
        ]
        encs.reverse()

        for i in range(windowSize):
            assert encrypter2.decrypt(encs[i][2], encs[i][1])
        assert encrypter2.decrypt(encs[windowSize][2], encs[windowSize][1]) is None

class TestEncrypterOverflowException:
    def testEncrypterOverflowExceptionOnEncryption(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1, encryptSeqLimits=1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1)
        encrypter2.salt = encrypter1.salt
        encrypter1.otherPartyX25519PublicKeyBytes = encrypter2.myX25519PublicKeyBytes
        encrypter1.derive()
        assert encrypter1.encrypt(b"data1")
        with pytest.raises(EncrypterOverflowException):
            encrypter1.encrypt(b"data2")
    def testEncrypterOverflowExceptionOnDecryption(self):
        encrypter1 = X25519AndAesgcmEncrypter(True, 1)
        encrypter2 = X25519AndAesgcmEncrypter(False, 1, encryptSeqLimits=1)
        encrypter2.salt = encrypter1.salt

        encrypter1.otherPartyX25519PublicKeyBytes = encrypter2.myX25519PublicKeyBytes
        encrypter2.otherPartyX25519PublicKeyBytes = encrypter1.myX25519PublicKeyBytes
        encrypter1.derive()
        encrypter2.derive()

        data = b"hello world"
        s, encrypted = encrypter1.encrypt(data+b"1")
        s2, encrypted2 = encrypter1.encrypt(data+b"2")

        assert encrypter2.decrypt(encrypted, s) == data+b"1"
        with pytest.raises(EncrypterOverflowException):
            encrypter2.decrypt(encrypted2, s2)
