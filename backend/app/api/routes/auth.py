"""
Authentication routes.

Exposes OAuth2 login initiation and callback handling. Sets a session
cookie on successful authentication. Token exchange and user upsert
are delegated to AuthService which owns the full PKCE flow.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from api.deps.repositories import get_oauth_token_repository, get_user_repository
from api.deps.auth import get_current_user
from infrastructure.database.models.user import User
from core.logging import get_logger
from core.config import get_settings
from infrastructure.database.repositories.oauth_token_repository import (
    OAuthTokenRepository,
)
from infrastructure.database.repositories.user_repository import UserRepository
from infrastructure.auth.auth_service import AuthService


logger = get_logger(__name__)
router = APIRouter()


_SESSION_COOKIE = "session_user_id"
_SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class LoginResponse(BaseModel):
    """Response body for the login URL endpoint."""

    authorization_url: str


class CallbackResponse(BaseModel):
    """Response body for the OAuth callback endpoint."""

    success: bool

class CurrentUserResponse(BaseModel):
    """Response body for the current authenticated user endpoint."""

    id: str
    email: str
    name: str | None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/login",
    response_model=LoginResponse,
    summary="Initiate OAuth2 login",
    description=(
        "Returns the Google OAuth2 authorization URL. "
        "The client must redirect the user's browser to this URL to begin "
        "the consent flow. A PKCE challenge and CSRF state token are embedded "
        "in the URL and stored in Redis for later validation."
    ),
)
async def login(
    user_repo: UserRepository = Depends(get_user_repository),
    token_repo: OAuthTokenRepository = Depends(get_oauth_token_repository),
) -> LoginResponse:
    """
    Generate and return the Google OAuth2 authorization URL.

    Delegates to :meth:`AuthService.build_authorization_url` which generates
    a PKCE pair, stores the state token in Redis, and builds the fully-formed
    Google authorization URL.

    Args:
        user_repo: Injected UserRepository for AuthService construction.
        token_repo: Injected OAuthTokenRepository for AuthService construction.

    Returns:
        LoginResponse: Object containing the authorization URL string.
    """

    service = AuthService(user_repo=user_repo, token_repo=token_repo)
    result = await service.build_authorization_url()
    return LoginResponse(authorization_url=result.authorization_url)


@router.get(
    "/callback",
    summary="Handle OAuth2 callback",
    description=(
        "Exchanges the Google authorization code for access and refresh tokens, "
        "upserts the authenticated user, persists encrypted tokens, and sets a "
        "session cookie identifying the user."
    ),
)
async def callback(
    code: str,
    state: str,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
    token_repo: OAuthTokenRepository = Depends(get_oauth_token_repository),
) -> CallbackResponse:
    """
    Handle the Google OAuth2 redirect callback.

    Validates the CSRF state token, exchanges the authorization code using
    the stored PKCE verifier, fetches the Google user profile, upserts the
    User record, and persists freshly encrypted tokens. Sets an HttpOnly
    session cookie on success.

    Args:
        code: Authorization code provided by Google in the redirect.
        state: CSRF state token provided by Google for validation.
        response: FastAPI Response used to set the session cookie.
        user_repo: Injected UserRepository for AuthService construction.
        token_repo: Injected OAuthTokenRepository for AuthService construction.

    Returns:
        CallbackResponse: Indicates whether authentication succeeded.

    Raises:
        HTTPException: 400 if state validation fails or code exchange is rejected.
        HTTPException: 502 if the Google API returns an unexpected error.
    """
    settings = get_settings()
    service = AuthService(user_repo=user_repo, token_repo=token_repo)

    try:
        user = await service.handle_callback(code=code, state=state)
    except ValueError as exc:
        logger.warning("OAuth callback validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Google API error during OAuth callback: status=%s",
            exc.response.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication failed due to a Google API error.",
        )

    logger.info("User authenticated via OAuth callback: user_id=%s", user.id)
    frontend_url = settings.frontend_url.rstrip("/")

    redirect_response = RedirectResponse(
        url=f"{frontend_url}/auth/callback",
        status_code=303,
    )

    redirect_response.set_cookie(
        key=_SESSION_COOKIE,
        value=str(user.id),
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=_SESSION_MAX_AGE,
    )

    return redirect_response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out the current user",
    description="Clears the session cookie, effectively ending the user session.",
)
async def logout(response: Response) -> None:
    """
    Clear the session cookie, effectively logging the user out.

    No database state is modified; only the client-side cookie is deleted.
    The user must re-authenticate via /auth/login to obtain a new session.

    Args:
        response: FastAPI Response used to delete the session cookie.
    """
    response.delete_cookie(key=_SESSION_COOKIE)
    logger.info("Session cookie cleared on logout.")

@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get current authenticated user",
    description=(
        "Returns the profile of the user identified by the current session cookie. "
        "Returns 401 if no valid session cookie is present."
    ),
)
async def me(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    """
    Return the authenticated user's profile.

    Reads the session cookie set during OAuth callback, resolves the user
    from the database via get_current_user dependency, and returns their
    public profile fields.

    Args:
        current_user: User entity resolved from the session cookie.

    Returns:
        CurrentUserResponse: Public profile fields for the authenticated user.
    """
    return CurrentUserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
    )