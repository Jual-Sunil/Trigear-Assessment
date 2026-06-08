"""OAuth2 state and PKCE code-verifier management.

Generates, stores, and validates the ``state`` parameter used for CSRF
protection in the Authorization Code Flow, as well as the PKCE
``code_verifier`` / ``code_challenge`` pair required by the PKCE extension
(RFC 7636).

State tokens and code verifiers are stored in Redis with a short TTL so
that abandoned flows expire automatically without manual cleanup.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

import redis.asyncio as aioredis

from core.config import get_settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STATE_TTL_SECONDS: int = 600  # 10 minutes — ample time to complete login
_STATE_KEY_PREFIX: str = "oauth:state:"
_VERIFIER_KEY_PREFIX: str = "oauth:pkce:"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PKCEPair:
    """Holds a PKCE ``code_verifier`` / ``code_challenge`` pair.

    Attributes:
        code_verifier: High-entropy random string sent at token exchange.
        code_challenge: SHA-256 hash of the verifier, sent in the auth URL.
        code_challenge_method: Always ``S256`` for this implementation.
    """

    code_verifier: str
    code_challenge: str
    code_challenge_method: str = "S256"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _redis_client() -> aioredis.Redis:
    """Create a short-lived Redis client from application settings.

    Returns:
        An async Redis client configured from ``REDIS_URL``.
    """
    settings = get_settings()
    return aioredis.from_url(
        str(settings.redis_url),
        max_connections=2,
        decode_responses=True,
    )


def _state_redis_key(state: str) -> str:
    """Build the Redis key for a given state token.

    Args:
        state: The raw state token string.

    Returns:
        Namespaced Redis key string.
    """
    return f"{_STATE_KEY_PREFIX}{state}"


def _verifier_redis_key(state: str) -> str:
    """Build the Redis key for the PKCE verifier paired with a state token.

    Args:
        state: The raw state token string used as the pairing key.

    Returns:
        Namespaced Redis key string.
    """
    return f"{_VERIFIER_KEY_PREFIX}{state}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_state_token() -> str:
    """Generate a cryptographically secure random OAuth2 state token.

    Returns:
        A 64-character URL-safe hex string.
    """
    return os.urandom(32).hex()


def generate_pkce_pair() -> PKCEPair:
    """Generate a PKCE ``code_verifier`` / ``code_challenge`` pair.

    The verifier is a 96-byte random value encoded as URL-safe base64
    (no padding), satisfying the 43-128 character requirement of RFC 7636.
    The challenge is the URL-safe base64 encoding of its SHA-256 digest.

    Returns:
        A :class:`PKCEPair` containing the verifier and challenge.
    """
    raw_verifier = os.urandom(96)
    code_verifier = base64.urlsafe_b64encode(raw_verifier).rstrip(b"=").decode("ascii")

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return PKCEPair(
        code_verifier=code_verifier,
        code_challenge=code_challenge,
    )


async def store_state(state: str, code_verifier: str) -> None:
    """Persist a state token and its paired PKCE verifier in Redis.

    Both entries share the same TTL defined by ``_STATE_TTL_SECONDS`` so
    they expire atomically once the login window closes.

    Args:
        state: The state token to persist.
        code_verifier: The PKCE code verifier paired with this state.
    """
    client = _redis_client()
    async with client:
        pipe = client.pipeline()
        pipe.setex(_state_redis_key(state), _STATE_TTL_SECONDS, "1")
        pipe.setex(_verifier_redis_key(state), _STATE_TTL_SECONDS, code_verifier)
        await pipe.execute()


async def validate_and_consume_state(state: str) -> str:
    """Validate a returned OAuth2 state token and retrieve its PKCE verifier.

    Atomically deletes both the state marker and the PKCE verifier entry
    after a successful lookup so they cannot be replayed.

    Args:
        state: The ``state`` parameter returned by Google's callback.

    Returns:
        The ``code_verifier`` paired with this state token.

    Raises:
        ValueError: If the state token is absent, expired, or already consumed.
    """
    if not state:
        raise ValueError("State token must not be empty.")

    state_key = _state_redis_key(state)
    verifier_key = _verifier_redis_key(state)

    client = _redis_client()
    async with client:
        pipe = client.pipeline()
        pipe.getdel(state_key)
        pipe.getdel(verifier_key)
        results = await pipe.execute()

        state_exists: str | None = results[0]
        code_verifier: str | None = results[1]

        if not state_exists or not code_verifier:
            raise ValueError(
                "Invalid or expired OAuth state token. "
                "The login session may have timed out; please try again."
            )

    return code_verifier


def constant_time_compare(val1: str, val2: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks.

    Args:
        val1: First string to compare.
        val2: Second string to compare.

    Returns:
        ``True`` if the strings are equal, ``False`` otherwise.
    """
    return hmac.compare_digest(
        val1.encode("utf-8"),
        val2.encode("utf-8"),
    )
