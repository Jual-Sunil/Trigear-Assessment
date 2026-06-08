"""Async Gmail REST API client.

Provides typed, async access to the Gmail API v1 over raw ``httpx`` — no
Google API Python client library — keeping the dependency surface small and
the I/O model fully async.

Capabilities
------------
- :meth:`GmailClient.fetch_profile` — mailbox metadata for the authenticated user.
- :meth:`GmailClient.fetch_message` — a single message by ID.
- :meth:`GmailClient.fetch_messages` — paginated message listing with optional
  label and query filters.
- :meth:`GmailClient.fetch_thread` — a complete thread by ID.
- :meth:`GmailClient.fetch_history` — incremental history records since a
  ``history_id``, used for delta synchronisation.

All methods share a single :class:`httpx.AsyncClient` that is managed via
async context manager.  Retry logic with exponential back-off is applied to
transient 429 / 5xx errors.  ``401`` responses trigger a single token-refresh
attempt before re-raising.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from core.config import get_settings
from infrastructure.auth.auth_service import AuthService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GMAIL_API_BASE: str = "https://gmail.googleapis.com/gmail/v1"
_DEFAULT_MESSAGE_FORMAT: str = "full"  # full | metadata | minimal | raw

# Retry configuration
_MAX_RETRIES: int = 3
_RETRY_BACKOFF_BASE: float = 1.5  # seconds; multiplied by 2^attempt
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


# ---------------------------------------------------------------------------
# Typed response dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GmailHeader:
    """A single RFC-2822 header from a Gmail message part.

    Attributes:
        name: Header field name (e.g. ``From``, ``Subject``).
        value: Header field value.
    """

    name: str
    value: str


@dataclass(frozen=True, slots=True)
class GmailMessagePart:
    """A MIME part of a Gmail message body.

    Attributes:
        part_id: Hierarchical part identifier (e.g. ``0``, ``1.1``).
        mime_type: MIME type of this part (e.g. ``text/plain``).
        filename: Attachment filename, empty string when not an attachment.
        headers: List of RFC-2822 headers on this part.
        body_data: Base64url-encoded body data; may be empty for container parts.
        body_size: Declared byte-size of the body before decoding.
        parts: Nested child parts for ``multipart/*`` containers.
    """

    part_id: str
    mime_type: str
    filename: str
    headers: list[GmailHeader]
    body_data: str
    body_size: int
    parts: list[GmailMessagePart]


@dataclass(frozen=True, slots=True)
class GmailMessage:
    """A Gmail message resource returned by the Messages API.

    Attributes:
        message_id: Stable Gmail message identifier.
        thread_id: Thread this message belongs to.
        label_ids: List of label identifiers applied to the message.
        snippet: Short plain-text preview of the message body.
        history_id: Mailbox history record ID at time of this message.
        internal_date: Unix-epoch milliseconds when the message was received.
        size_estimate: Estimated message size in bytes.
        payload: Root MIME part (``None`` for ``minimal`` format responses).
        raw: Base64url-encoded RFC-2822 message (only for ``raw`` format).
    """

    message_id: str
    thread_id: str
    label_ids: list[str]
    snippet: str
    history_id: str
    internal_date: int
    size_estimate: int
    payload: GmailMessagePart | None
    raw: str


@dataclass(frozen=True, slots=True)
class GmailMessageRef:
    """A lightweight message reference from list and history responses.

    Attributes:
        message_id: Stable Gmail message identifier.
        thread_id: Thread this message belongs to.
    """

    message_id: str
    thread_id: str


@dataclass(frozen=True, slots=True)
class GmailThread:
    """A Gmail thread resource returned by the Threads API.

    Attributes:
        thread_id: Stable Gmail thread identifier.
        snippet: Short preview of the most recent message.
        history_id: Mailbox history record ID at time of this thread.
        messages: Ordered list of messages in the thread.
    """

    thread_id: str
    snippet: str
    history_id: str
    messages: list[GmailMessage]


@dataclass(frozen=True, slots=True)
class GmailHistoryRecord:
    """One record in the mailbox history stream.

    Attributes:
        history_id: Identifier for this history record.
        messages_added: Message references for newly arrived messages.
        messages_deleted: Message references for deleted messages.
        labels_added: Message references for which labels were added.
        labels_removed: Message references for which labels were removed.
    """

    history_id: str
    messages_added: list[GmailMessageRef]
    messages_deleted: list[GmailMessageRef]
    labels_added: list[GmailMessageRef]
    labels_removed: list[GmailMessageRef]


@dataclass(frozen=True, slots=True)
class GmailHistoryPage:
    """A page of history records from the History API.

    Attributes:
        history: Ordered list of history records since the requested ID.
        next_page_token: Token to fetch the next page; ``None`` when exhausted.
        history_id: Current mailbox history ID at the time of this response.
    """

    history: list[GmailHistoryRecord]
    next_page_token: str | None
    history_id: str


@dataclass(frozen=True, slots=True)
class GmailMessagesPage:
    """A single page from a messages.list response.

    Attributes:
        messages: Message references on this page.
        next_page_token: Token to fetch the next page; ``None`` when exhausted.
        result_size_estimate: Server-side estimate of total matching messages.
    """

    messages: list[GmailMessageRef]
    next_page_token: str | None
    result_size_estimate: int


@dataclass(frozen=True, slots=True)
class GmailProfile:
    """Mailbox profile for the authenticated Gmail user.

    Attributes:
        email_address: Primary email address of the mailbox.
        messages_total: Total number of messages in the mailbox.
        threads_total: Total number of threads in the mailbox.
        history_id: Current mailbox history ID.
    """

    email_address: str
    messages_total: int
    threads_total: int
    history_id: str


# ---------------------------------------------------------------------------
# Internal parsing helpers
# ---------------------------------------------------------------------------


def _parse_header(raw: dict[str, Any]) -> GmailHeader:
    """Parse a raw header dict into a :class:`GmailHeader`.

    Args:
        raw: Dict with ``name`` and ``value`` keys from the API response.

    Returns:
        A typed :class:`GmailHeader`.
    """
    return GmailHeader(
        name=raw.get("name", ""),
        value=raw.get("value", ""),
    )


def _parse_part(raw: dict[str, Any]) -> GmailMessagePart:
    """Recursively parse a raw MIME part dict into a :class:`GmailMessagePart`.

    Args:
        raw: Dict representing one MIME part from the API response.

    Returns:
        A typed :class:`GmailMessagePart` with nested children parsed.
    """
    body: dict[str, Any] = raw.get("body", {})
    child_parts: list[dict[str, Any]] = raw.get("parts", [])

    return GmailMessagePart(
        part_id=raw.get("partId", ""),
        mime_type=raw.get("mimeType", ""),
        filename=raw.get("filename", ""),
        headers=[_parse_header(h) for h in raw.get("headers", [])],
        body_data=body.get("data", ""),
        body_size=int(body.get("size", 0)),
        parts=[_parse_part(p) for p in child_parts],
    )


def _parse_message(raw: dict[str, Any]) -> GmailMessage:
    """Parse a raw message dict into a :class:`GmailMessage`.

    Args:
        raw: Dict from the Gmail Messages.get or Messages.list response.

    Returns:
        A typed :class:`GmailMessage`.
    """
    payload_raw: dict[str, Any] | None = raw.get("payload")
    return GmailMessage(
        message_id=raw.get("id", ""),
        thread_id=raw.get("threadId", ""),
        label_ids=raw.get("labelIds", []),
        snippet=raw.get("snippet", ""),
        history_id=raw.get("historyId", ""),
        internal_date=int(raw.get("internalDate", 0)),
        size_estimate=int(raw.get("sizeEstimate", 0)),
        payload=_parse_part(payload_raw) if payload_raw else None,
        raw=raw.get("raw", ""),
    )


def _parse_message_ref(raw: dict[str, Any]) -> GmailMessageRef:
    """Parse a lightweight message reference dict.

    Args:
        raw: Dict with ``id`` and ``threadId`` keys.

    Returns:
        A typed :class:`GmailMessageRef`.
    """
    return GmailMessageRef(
        message_id=raw.get("id", ""),
        thread_id=raw.get("threadId", ""),
    )


def _parse_history_record(raw: dict[str, Any]) -> GmailHistoryRecord:
    """Parse a raw history record dict into a :class:`GmailHistoryRecord`.

    Each history record may contain lists of ``messagesAdded``,
    ``messagesDeleted``, ``labelsAdded``, and ``labelsRemoved`` changes.
    Only the message reference (``message`` sub-key) is extracted from each
    change entry.

    Args:
        raw: Dict representing one history record from the API response.

    Returns:
        A typed :class:`GmailHistoryRecord`.
    """

    def _refs_from_changes(changes: list[dict[str, Any]]) -> list[GmailMessageRef]:
        refs: list[GmailMessageRef] = []
        for change in changes:
            msg = change.get("message")
            if msg:
                refs.append(_parse_message_ref(msg))
        return refs

    return GmailHistoryRecord(
        history_id=str(raw.get("id", "")),
        messages_added=_refs_from_changes(raw.get("messagesAdded", [])),
        messages_deleted=_refs_from_changes(raw.get("messagesDeleted", [])),
        labels_added=_refs_from_changes(raw.get("labelsAdded", [])),
        labels_removed=_refs_from_changes(raw.get("labelsRemoved", [])),
    )


# ---------------------------------------------------------------------------
# GmailClient
# ---------------------------------------------------------------------------


class GmailClient:
    """Async client for the Gmail REST API v1.

    Manages a single :class:`httpx.AsyncClient` for connection reuse.  Must
    be used as an async context manager so the underlying transport is properly
    opened and closed.

    Args:
        user_id: UUID of the authenticated user whose mailbox is accessed.
        auth_service: Service used to obtain (and refresh) a valid access token.

    Example::

        async with GmailClient(user_id=uid, auth_service=svc) as client:
            profile = await client.fetch_profile()
    """

    def __init__(
        self,
        user_id: uuid.UUID,
        auth_service: AuthService,
    ) -> None:
        """Initialise the client without opening the HTTP transport."""
        self._user_id = user_id
        self._auth_service = auth_service
        self._settings = get_settings()
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> GmailClient:
        """Open the underlying HTTP transport."""
        self._http = httpx.AsyncClient(
            base_url=_GMAIL_API_BASE,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close the underlying HTTP transport."""
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_profile(self) -> GmailProfile:
        """Fetch the authenticated user's Gmail mailbox profile.

        Returns:
            A :class:`GmailProfile` containing email address, message count,
            thread count, and current history ID.

        Raises:
            RuntimeError: If called outside an async context manager.
            httpx.HTTPStatusError: On unrecoverable API errors.
        """
        data = await self._request("GET", "/users/me/profile")
        return GmailProfile(
            email_address=data.get("emailAddress", ""),
            messages_total=int(data.get("messagesTotal", 0)),
            threads_total=int(data.get("threadsTotal", 0)),
            history_id=str(data.get("historyId", "")),
        )

    async def fetch_message(
        self,
        message_id: str,
        fmt: str = _DEFAULT_MESSAGE_FORMAT,
    ) -> GmailMessage:
        """Fetch a single Gmail message by its ID.

        Args:
            message_id: The Gmail message identifier.
            fmt: Response format — one of ``full``, ``metadata``, ``minimal``,
                ``raw``.  Defaults to ``full``.

        Returns:
            A fully parsed :class:`GmailMessage`.

        Raises:
            RuntimeError: If called outside an async context manager.
            httpx.HTTPStatusError: On unrecoverable API errors.
        """
        data = await self._request(
            "GET",
            f"/users/me/messages/{message_id}",
            params={"format": fmt},
        )
        return _parse_message(data)

    async def fetch_messages(
        self,
        *,
        label_ids: list[str] | None = None,
        query: str | None = None,
        page_token: str | None = None,
        max_results: int | None = None,
        include_spam_trash: bool = False,
    ) -> GmailMessagesPage:
        """Fetch one page of message references from the user's mailbox.

        This method returns lightweight references only.  Use
        :meth:`fetch_message` to hydrate individual messages.

        Args:
            label_ids: Restrict results to messages with all these label IDs.
            query: Gmail search query string (same syntax as the Gmail UI).
            page_token: Continuation token from a previous response.
            max_results: Maximum number of references to return (server cap:
                500).  Defaults to ``gmail_sync_max_results`` from settings.
            include_spam_trash: When ``True``, include SPAM and TRASH messages.

        Returns:
            A :class:`GmailMessagesPage` with references and pagination token.

        Raises:
            RuntimeError: If called outside an async context manager.
            httpx.HTTPStatusError: On unrecoverable API errors.
        """
        effective_max = max_results or self._settings.gmail_sync_max_results
        params: dict[str, Any] = {
            "maxResults": min(effective_max, 500),
            "includeSpamTrash": str(include_spam_trash).lower(),
        }
        if label_ids:
            params["labelIds"] = label_ids
        if query:
            params["q"] = query
        if page_token:
            params["pageToken"] = page_token

        data = await self._request("GET", "/users/me/messages", params=params)

        raw_refs: list[dict[str, Any]] = data.get("messages", [])
        return GmailMessagesPage(
            messages=[_parse_message_ref(r) for r in raw_refs],
            next_page_token=data.get("nextPageToken"),
            result_size_estimate=int(data.get("resultSizeEstimate", 0)),
        )

    async def fetch_thread(self, thread_id: str) -> GmailThread:
        """Fetch a complete Gmail thread including all its messages.

        Args:
            thread_id: The Gmail thread identifier.

        Returns:
            A :class:`GmailThread` with all messages parsed at ``full`` format.

        Raises:
            RuntimeError: If called outside an async context manager.
            httpx.HTTPStatusError: On unrecoverable API errors.
        """
        data = await self._request(
            "GET",
            f"/users/me/threads/{thread_id}",
            params={"format": _DEFAULT_MESSAGE_FORMAT},
        )
        return GmailThread(
            thread_id=data.get("id", ""),
            snippet=data.get("snippet", ""),
            history_id=str(data.get("historyId", "")),
            messages=[_parse_message(m) for m in data.get("messages", [])],
        )

    async def fetch_history(
        self,
        start_history_id: str,
        *,
        label_id: str | None = None,
        history_types: list[str] | None = None,
        page_token: str | None = None,
        max_results: int = 500,
    ) -> GmailHistoryPage:
        """Fetch incremental history records since a given history ID.

        Used for delta-synchronisation: only changes since ``start_history_id``
        are returned, avoiding a full re-sync on each poll.

        Args:
            start_history_id: History ID to start listing from (exclusive).
                Obtain the initial value from :meth:`fetch_profile`.
            label_id: Filter history records to those affecting this label.
            history_types: List of change types to include — any subset of
                ``messageAdded``, ``messageDeleted``, ``labelAdded``,
                ``labelRemoved``.  Defaults to all types when ``None``.
            page_token: Continuation token from a previous response.
            max_results: Maximum history records to return per page (max 500).

        Returns:
            A :class:`GmailHistoryPage` with records and pagination token.

        Raises:
            RuntimeError: If called outside an async context manager.
            httpx.HTTPStatusError: On unrecoverable API errors (including 404
                when the history ID has expired and a full re-sync is required).
        """
        params: dict[str, Any] = {
            "startHistoryId": start_history_id,
            "maxResults": min(max_results, 500),
        }
        if label_id:
            params["labelId"] = label_id
        if history_types:
            params["historyTypes"] = history_types
        if page_token:
            params["pageToken"] = page_token

        data = await self._request("GET", "/users/me/history", params=params)

        raw_records: list[dict[str, Any]] = data.get("history", [])
        return GmailHistoryPage(
            history=[_parse_history_record(r) for r in raw_records],
            next_page_token=data.get("nextPageToken"),
            history_id=str(data.get("historyId", "")),
        )

    # ------------------------------------------------------------------
    # Private HTTP helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        _retry_count: int = 0,
        _refreshed_token: bool = False,
    ) -> dict[str, Any]:
        """Execute an authenticated request with retry and refresh logic.

        Handles:
        - Bearer token injection on every request.
        - Transparent token refresh on ``401 Unauthorized`` (once per call).
        - Exponential back-off retry on ``429`` and ``5xx`` responses.

        Args:
            method: HTTP method (``GET``, ``POST``, …).
            path: API path relative to ``_GMAIL_API_BASE``.
            params: Query parameters dict.
            _retry_count: Internal recursion counter — do not set externally.
            _refreshed_token: Internal flag tracking whether a token refresh
                has already been attempted — do not set externally.

        Returns:
            Parsed JSON response body as a plain dict.

        Raises:
            RuntimeError: If called outside an async context manager.
            httpx.HTTPStatusError: When the error is not retryable or retries
                are exhausted.
        """
        if self._http is None:
            raise RuntimeError(
                "GmailClient must be used as an async context manager. "
                "Use 'async with GmailClient(...) as client:'."
            )

        access_token = await self._auth_service.get_valid_access_token(self._user_id)
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self._http.request(
            method,
            path,
            params=params,
            headers=headers,
        )

        # -- 401: attempt a single token refresh then retry -----------------
        if response.status_code == 401 and not _refreshed_token:
            logger.warning(
                "Gmail API returned 401 for user %s; refreshing access token.",
                self._user_id,
            )
            await self._auth_service.refresh_access_token(self._user_id)
            return await self._request(
                method,
                path,
                params=params,
                _retry_count=_retry_count,
                _refreshed_token=True,
            )

        # -- Retryable errors: 429 and 5xx ----------------------------------
        if response.status_code in _RETRYABLE_STATUS_CODES:
            if _retry_count >= _MAX_RETRIES:
                logger.error(
                    "Gmail API request %s %s failed after %d retries "
                    "(status=%d) for user %s.",
                    method,
                    path,
                    _MAX_RETRIES,
                    response.status_code,
                    self._user_id,
                )
                response.raise_for_status()

            backoff = _RETRY_BACKOFF_BASE * (2 ** _retry_count)

            # Respect Retry-After header when present (429).
            retry_after_header = response.headers.get("Retry-After")
            if retry_after_header:
                try:
                    backoff = max(backoff, float(retry_after_header))
                except ValueError:
                    pass

            logger.warning(
                "Gmail API request %s %s returned %d for user %s; "
                "retrying in %.1fs (attempt %d/%d).",
                method,
                path,
                response.status_code,
                self._user_id,
                backoff,
                _retry_count + 1,
                _MAX_RETRIES,
            )
            await asyncio.sleep(backoff)
            return await self._request(
                method,
                path,
                params=params,
                _retry_count=_retry_count + 1,
                _refreshed_token=_refreshed_token,
            )

        # -- All other errors -----------------------------------------------
        response.raise_for_status()

        return response.json()  # type: ignore[no-any-return]
