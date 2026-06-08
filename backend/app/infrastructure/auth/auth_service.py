"""Google OAuth2 Authorization Code Flow service.

Implements the full server-side OAuth2 Authorization Code Flow with PKCE
(RFC 7636) for Google account authentication. Responsibilities:

- Build the authorization URL with state and PKCE challenge.
- Exchange the authorization code for access and refresh tokens.
- Fetch the authenticated user's profile from Google's userinfo endpoint.
- Encrypt and persist tokens via :class:`OAuthTokenRepository`.
- Refresh expired access tokens using the stored refresh token.

All token values are encrypted at rest; plaintext tokens are never logged.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from core.config import get_settings
from infrastructure.auth.oauth_state import (
    generate_pkce_pair,
    generate_state_token,
    store_state,
    validate_and_consume_state,
)
from infrastructure.auth.token_encryption import (
    decrypt_oauth_access_token,
    decrypt_oauth_refresh_token,
    encrypt_oauth_access_token,
    encrypt_oauth_refresh_token,
)
from infrastructure.database.models.oauth_token import OAuthToken
from infrastructure.database.models.user import User
from infrastructure.database.repositories.oauth_token_repository import (
    OAuthTokenRepository,
)
from infrastructure.database.repositories.user_repository import UserRepository

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL: str = "https://www.googleapis.com/oauth2/v3/userinfo"
_TOKEN_EXPIRY_BUFFER_SECONDS: int = 300  # Refresh 5 min before actual expiry


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuthorizationURLResult:
    """Result of building the OAuth2 authorization URL.

    Attributes:
        authorization_url: The fully-formed URL to redirect the user to.
        state: The CSRF state token stored in Redis for later validation.
    """

    authorization_url: str
    state: str


@dataclass(frozen=True, slots=True)
class GoogleUserInfo:
    """User profile information returned by Google's userinfo endpoint.

    Attributes:
        google_id: Google account subject identifier (``sub`` claim).
        email: Verified email address.
        name: Display name.
        picture: Profile picture URL (may be empty).
    """

    google_id: str
    email: str
    name: str
    picture: str


@dataclass(frozen=True, slots=True)
class TokenSet:
    """Raw (plaintext) token values returned after code exchange or refresh.

    Attributes:
        access_token: Bearer token for Google API calls.
        refresh_token: Long-lived token for obtaining new access tokens.
        expires_at: UTC datetime when the access token expires.
    """

    access_token: str
    refresh_token: str
    expires_at: datetime


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_flow(redirect_uri: str | None = None) -> Flow:
    """Build a :class:`Flow` instance from application configuration.

    Args:
        redirect_uri: Override the default redirect URI from settings.
            Useful during tests.

    Returns:
        A configured :class:`google_auth_oauthlib.flow.Flow` instance.
    """
    settings = get_settings()
    client_config: dict[str, Any] = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": _GOOGLE_TOKEN_URL,
            "redirect_uris": [redirect_uri or settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.google_oauth_scopes,
        redirect_uri=redirect_uri or settings.google_redirect_uri,
    )
    return flow


async def _fetch_userinfo(access_token: str) -> GoogleUserInfo:
    """Fetch the authenticated user's profile from Google's userinfo endpoint.

    Args:
        access_token: A valid Google OAuth2 access token.

    Returns:
        A :class:`GoogleUserInfo` populated from the userinfo response.

    Raises:
        httpx.HTTPStatusError: If Google returns a non-2xx response.
        ValueError: If required fields are missing from the response.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()

    google_id: str = payload.get("sub", "")
    email: str = payload.get("email", "")
    if not google_id or not email:
        raise ValueError(
            "Google userinfo response is missing required 'sub' or 'email' fields."
        )

    return GoogleUserInfo(
        google_id=google_id,
        email=email,
        name=payload.get("name") or "",
        picture=payload.get("picture") or "",
    )


def _expires_at_from_seconds(expires_in: int) -> datetime:
    """Compute the UTC expiry datetime from an ``expires_in`` seconds value.

    A buffer of :data:`_TOKEN_EXPIRY_BUFFER_SECONDS` is subtracted so that
    callers pre-emptively refresh before the token truly expires.

    Args:
        expires_in: Seconds until the access token expires (from Google).

    Returns:
        Timezone-naive UTC :class:`datetime` representing the effective expiry.
    """
    effective_seconds = max(0, expires_in - _TOKEN_EXPIRY_BUFFER_SECONDS)
    aware = datetime.now(tz=timezone.utc) + timedelta(seconds=effective_seconds)
    # Convert to timezone-naive for storage in database (timezone=False column)
    return aware.replace(tzinfo=None)


# ---------------------------------------------------------------------------
# AuthService
# ---------------------------------------------------------------------------


class AuthService:
    """Orchestrates Google OAuth2 Authentication Code Flow with PKCE.

    All public methods are async to integrate cleanly with FastAPI's
    dependency injection and the async SQLAlchemy session layer.

    Args:
        user_repo: Repository for :class:`User` persistence operations.
        token_repo: Repository for :class:`OAuthToken` persistence operations.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: OAuthTokenRepository,
    ) -> None:
        """Initialise the service with injected repository dependencies."""
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Authorization URL
    # ------------------------------------------------------------------

    async def build_authorization_url(self) -> AuthorizationURLResult:
        """Generate the Google authorization URL and persist the CSRF state.

        Generates a PKCE pair and a random state token, stores them in Redis,
        then builds the full Google authorization URL including the PKCE
        challenge and state parameter.

        Returns:
            An :class:`AuthorizationURLResult` with the URL and state token.
        """
        state = generate_state_token()
        pkce = generate_pkce_pair()

        await store_state(state, pkce.code_verifier)

        flow = _build_flow()
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
            code_challenge=pkce.code_challenge,
            code_challenge_method=pkce.code_challenge_method,
        )

        return AuthorizationURLResult(
            authorization_url=authorization_url,
            state=state,
        )

    # ------------------------------------------------------------------
    # Callback / code exchange
    # ------------------------------------------------------------------

    async def handle_callback(
        self,
        code: str,
        state: str,
    ) -> User:
        """Process the OAuth2 callback, exchange the code, and upsert the user.

        Steps:
        1. Validate and consume the state token from Redis (CSRF check).
        2. Exchange the authorization code for tokens using the PKCE verifier.
        3. Fetch user profile from Google's userinfo endpoint.
        4. Upsert the :class:`User` record (create or update).
        5. Replace stale tokens with freshly encrypted ones.

        Args:
            code: Authorization code returned by Google in the callback.
            state: State parameter returned by Google, used for CSRF validation.

        Returns:
            The upserted :class:`User` instance.

        Raises:
            ValueError: If state validation fails or token exchange is rejected.
            httpx.HTTPStatusError: If Google API calls fail.
        """
        code_verifier = await validate_and_consume_state(state)

        token_set = await self._exchange_code(code, code_verifier)
        user_info = await _fetch_userinfo(token_set.access_token)

        user = await self._upsert_user(user_info)
        await self._replace_tokens(user.id, token_set)

        return user

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    async def refresh_access_token(self, user_id: uuid.UUID) -> OAuthToken:
        """Refresh the access token for a user and persist the updated record.

        Retrieves the stored (encrypted) refresh token, calls the Google
        token endpoint to obtain a new access token, then overwrites the
        existing token record with the refreshed values.

        Args:
            user_id: UUID of the :class:`User` whose token needs refreshing.

        Returns:
            The updated :class:`OAuthToken` with the new access token.

        Raises:
            ValueError: If no token record exists for the user or if the
                Google token endpoint rejects the refresh request.
            httpx.HTTPStatusError: If the token endpoint returns an error.
        """
        existing = await self._token_repo.get_by_user_id(user_id)
        if existing is None:
            raise ValueError(
                f"No OAuth token found for user {user_id}. "
                "The user must re-authenticate."
            )

        plaintext_refresh_token = decrypt_oauth_refresh_token(
            existing.encrypted_refresh_token
        )

        credentials = Credentials(
            token=None,
            refresh_token=plaintext_refresh_token,
            token_uri=_GOOGLE_TOKEN_URL,
            client_id=self._settings.google_client_id,
            client_secret=self._settings.google_client_secret,
            scopes=self._settings.google_oauth_scopes,
        )

        refreshed_token_set = await self._call_token_refresh_endpoint(credentials)
        await self._replace_tokens(user_id, refreshed_token_set)

        updated = await self._token_repo.get_by_user_id(user_id)
        if updated is None:
            raise ValueError(
                f"Token refresh succeeded but record is missing for user {user_id}."
            )
        return updated

    # ------------------------------------------------------------------
    # Access token retrieval (for API callers)
    # ------------------------------------------------------------------

    async def get_valid_access_token(self, user_id: uuid.UUID) -> str:
        """Return a valid plaintext access token, refreshing if necessary.

        Checks whether the stored token is still valid. If not, triggers a
        refresh before returning the decrypted access token.

        Args:
            user_id: UUID of the :class:`User` requesting API access.

        Returns:
            Plaintext Google OAuth access token ready for use.

        Raises:
            ValueError: If no token exists or refresh fails.
        """
        valid_token = await self._token_repo.get_valid_token(user_id)
        if valid_token is not None:
            return decrypt_oauth_access_token(valid_token.encrypted_access_token)

        refreshed = await self.refresh_access_token(user_id)
        return decrypt_oauth_access_token(refreshed.encrypted_access_token)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _exchange_code(self, code: str, code_verifier: str) -> TokenSet:
        """Exchange an authorization code for access and refresh tokens.

        Args:
            code: Authorization code from the Google callback.
            code_verifier: PKCE verifier paired with the original state.

        Returns:
            A :class:`TokenSet` containing the decrypted token values.

        Raises:
            ValueError: If Google's response is missing expected fields.
            httpx.HTTPStatusError: On HTTP-level errors from the token endpoint.
        """
        payload: dict[str, str] = {
            "code": code,
            "client_id": self._settings.google_client_id,
            "client_secret": self._settings.google_client_secret,
            "redirect_uri": self._settings.google_redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(_GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()

        data: dict[str, Any] = response.json()

        access_token: str = data.get("access_token", "")
        refresh_token: str = data.get("refresh_token", "")
        expires_in: int = int(data.get("expires_in", 3600))

        if not access_token:
            raise ValueError("Token exchange response is missing 'access_token'.")
        if not refresh_token:
            raise ValueError(
                "Token exchange response is missing 'refresh_token'. "
                "Ensure 'access_type=offline' and 'prompt=consent' are set."
            )
        return TokenSet(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=_expires_at_from_seconds(expires_in),
        )

    async def _call_token_refresh_endpoint(
        self, credentials: Credentials
    ) -> TokenSet:
        """Call the Google token endpoint to refresh an access token.

        Args:
            credentials: A :class:`Credentials` object populated with the
                refresh token and client secrets.

        Returns:
            A :class:`TokenSet` containing the new access token values.

        Raises:
            ValueError: If the response is missing 'access_token'.
            httpx.HTTPStatusError: On HTTP-level errors.
        """
        payload: dict[str, str] = {
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "refresh_token": credentials.refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(_GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()

        data: dict[str, Any] = response.json()

        access_token: str = data.get("access_token", "")
        if not access_token:
            raise ValueError("Token refresh response is missing 'access_token'.")

        expires_in: int = int(data.get("expires_in", 3600))

        # Google does not always return a new refresh token on refresh;
        # keep the existing one when omitted.
        refresh_token: str = data.get("refresh_token", "") or credentials.refresh_token

        return TokenSet(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=_expires_at_from_seconds(expires_in),
        )

    async def _upsert_user(self, user_info: GoogleUserInfo) -> User:
        """Create or update the :class:`User` record from Google profile data.

        Looks up the user by their Google ID. If found, updates the email and
        name fields in case they have changed. If not found, creates a new record.

        Args:
            user_info: Profile information from Google's userinfo endpoint.

        Returns:
            The persisted (and flushed) :class:`User` instance.
        """
        existing = await self._user_repo.get_by_google_id(user_info.google_id)
        if existing is not None:
            existing.email = user_info.email
            existing.name = user_info.name
            await self._user_repo.update(existing, {"email": user_info.email, "name": user_info.name})
            return existing

        new_user = User(
            email=user_info.email,
            name=user_info.name,
            google_id=user_info.google_id,
        )
        return await self._user_repo.create(new_user)

    async def _replace_tokens(
        self,
        user_id: uuid.UUID,
        token_set: TokenSet,
    ) -> OAuthToken:
        """Delete all existing tokens for a user and persist fresh encrypted ones.

        Args:
            user_id: UUID of the owning :class:`User`.
            token_set: Plaintext token values to encrypt and persist.

        Returns:
            The newly created :class:`OAuthToken` record.
        """
        await self._token_repo.delete_all_for_user(user_id)

        new_token = OAuthToken(
            user_id=user_id,
            encrypted_access_token=encrypt_oauth_access_token(token_set.access_token),
            encrypted_refresh_token=encrypt_oauth_refresh_token(
                token_set.refresh_token
            ),
            expires_at=token_set.expires_at,
        )
        return await self._token_repo.create(new_token)
