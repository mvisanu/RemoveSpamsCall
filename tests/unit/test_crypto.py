"""Unit tests for crypto module."""

import pytest

from privacytool.core.crypto import decrypt, encrypt


def test_round_trip():
    plaintext = "sensitive data: name, email@example.com"
    passphrase = "super-secret-passphrase-123"
    ciphertext = encrypt(plaintext, passphrase)
    assert decrypt(ciphertext, passphrase) == plaintext


def test_wrong_passphrase_raises():
    ciphertext = encrypt("hello world", "correct-passphrase")
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt(ciphertext, "wrong-passphrase")


def test_different_salts_each_call():
    passphrase = "test"
    c1 = encrypt("hello", passphrase)
    c2 = encrypt("hello", passphrase)
    # Same plaintext + passphrase should produce different ciphertext (random salt)
    assert c1 != c2
    # But both should decrypt correctly
    assert decrypt(c1, passphrase) == "hello"
    assert decrypt(c2, passphrase) == "hello"


def test_file_encrypt_decrypt(tmp_path):
    from privacytool.core.crypto import decrypt_file, encrypt_file
    path = str(tmp_path / "test.enc")
    encrypt_file(path, "secret text", "mypassphrase")
    result = decrypt_file(path, "mypassphrase")
    assert result == "secret text"
