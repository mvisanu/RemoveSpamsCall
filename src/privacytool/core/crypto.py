"""Encryption utilities using PBKDF2 + Fernet.

Key derivation: PBKDF2-HMAC-SHA256, 600 000 iterations, random 16-byte salt.
On-disk format for encrypted files:
    salt (16 bytes) || Fernet token (variable length)
The passphrase is never stored; it must be supplied each session.
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


_ITERATIONS = 600_000
_SALT_LEN = 16


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 32-byte Fernet-compatible key from a passphrase and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


def encrypt(plaintext: str, passphrase: str) -> bytes:
    """Encrypt *plaintext* with *passphrase*.  Returns raw bytes ready to write to disk."""
    salt = os.urandom(_SALT_LEN)
    key = _derive_key(passphrase, salt)
    token = Fernet(key).encrypt(plaintext.encode())
    return salt + token


def decrypt(ciphertext: bytes, passphrase: str) -> str:
    """Decrypt bytes previously produced by :func:`encrypt`.

    Raises ``ValueError`` if the passphrase is wrong or the data is corrupt.
    """
    salt = ciphertext[:_SALT_LEN]
    token = ciphertext[_SALT_LEN:]
    key = _derive_key(passphrase, salt)
    try:
        return Fernet(key).decrypt(token).decode()
    except InvalidToken as exc:
        raise ValueError("Decryption failed — wrong passphrase or corrupted file.") from exc


def encrypt_file(path: str, plaintext: str, passphrase: str) -> None:
    """Encrypt *plaintext* and write it to *path*."""
    with open(path, "wb") as fh:
        fh.write(encrypt(plaintext, passphrase))


def decrypt_file(path: str, passphrase: str) -> str:
    """Read *path* and decrypt its contents."""
    with open(path, "rb") as fh:
        return decrypt(fh.read(), passphrase)
