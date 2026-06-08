"""Security utilities: token encryption, decryption, and key derivation."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from core.config import get_settings


def _derive_fernet_key(raw_key: str) -> bytes:
    """Derive a 32-byte URL-safe base64-encoded Fernet key from a raw string.

    Uses SHA-256 to normalize arbitrary-length secrets into the fixed-width
    key that Fernet requires.

    Args:
        raw_key: Arbitrary-length secret string from configuration.

    Returns:
        A 44-byte URL-safe base64-encoded key suitable for Fernet.
    """
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    """Instantiate a Fernet cipher using the configured encryption key.

    Returns:
        A ready-to-use Fernet instance.
    """
    settings = get_settings()
    key = _derive_fernet_key(settings.token_encryption_key)
    return Fernet(key)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a plaintext token string for secure database storage.

    Args:
        plaintext: The raw token value to encrypt.

    Returns:
        A URL-safe base64-encoded ciphertext string.

    Raises:
        ValueError: If plaintext is empty.
    """
    if not plaintext:
        raise ValueError("Cannot encrypt an empty token.")
    fernet = _get_fernet()
    ciphertext = fernet.encrypt(plaintext.encode("utf-8"))
    return ciphertext.decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a previously encrypted token string.

    Args:
        ciphertext: The encrypted token value retrieved from the database.

    Returns:
        The original plaintext token.

    Raises:
        ValueError: If decryption fails due to tampering or wrong key.
    """
    if not ciphertext:
        raise ValueError("Cannot decrypt an empty ciphertext.")
    fernet = _get_fernet()
    try:
        plaintext = fernet.decrypt(ciphertext.encode("utf-8"))
        return plaintext.decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Token decryption failed: invalid ciphertext or key.") from exc

