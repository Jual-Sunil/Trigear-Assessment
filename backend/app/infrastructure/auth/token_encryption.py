"""Token encryption and decryption facade for the authentication layer.

Re-exports the core security primitives under the auth namespace so that
auth-layer consumers import from a single, stable location without depending
directly on the core security module.
"""

from core.security import decrypt_token, encrypt_token


__all__ = ["encrypt_token", "decrypt_token"]


def encrypt_oauth_access_token(access_token: str) -> str:
    """Encrypt a raw Google OAuth access token for database persistence.

    Args:
        access_token: Plaintext access token received from Google.

    Returns:
        Fernet-encrypted, URL-safe base64-encoded ciphertext string.

    Raises:
        ValueError: If the access token is empty.
    """
    return encrypt_token(access_token)


def decrypt_oauth_access_token(ciphertext: str) -> str:
    """Decrypt a Google OAuth access token retrieved from the database.

    Args:
        ciphertext: Encrypted access token stored in the database.

    Returns:
        Plaintext access token ready for use with Google APIs.

    Raises:
        ValueError: If decryption fails or the ciphertext is empty.
    """
    return decrypt_token(ciphertext)


def encrypt_oauth_refresh_token(refresh_token: str) -> str:
    """Encrypt a raw Google OAuth refresh token for database persistence.

    Args:
        refresh_token: Plaintext refresh token received from Google.

    Returns:
        Fernet-encrypted, URL-safe base64-encoded ciphertext string.

    Raises:
        ValueError: If the refresh token is empty.
    """
    return encrypt_token(refresh_token)


def decrypt_oauth_refresh_token(ciphertext: str) -> str:
    """Decrypt a Google OAuth refresh token retrieved from the database.

    Args:
        ciphertext: Encrypted refresh token stored in the database.

    Returns:
        Plaintext refresh token ready for use with the Google token endpoint.

    Raises:
        ValueError: If decryption fails or the ciphertext is empty.
    """
    return decrypt_token(ciphertext)
