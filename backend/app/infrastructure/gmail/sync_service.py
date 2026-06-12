"""Gmail incremental email synchronisation service.

Orchestrates the full sync lifecycle for a single user:

- **Full sync** (no prior history cursor): pages through
  ``messages.list`` to backfill the inbox up to a configurable limit.
- **Incremental sync** (existing history cursor): calls
  ``users.history.list`` to fetch only the delta since the last run,
  processing only ``messagesAdded`` events.

Both paths share common normalisation and persistence helpers that decode
MIME bodies, extract RFC-2822 headers, prevent duplicate inserts, and advance
the stored history cursor on success.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import uuid
import httpx
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parseaddr
from time import perf_counter
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from application.services.email_processing_service import (
    EmailProcessingOutcome,
    EmailProcessingService,
)
from core.config import get_settings
from infrastructure.database.models.email import Email
from infrastructure.database.repositories.email_repository import EmailRepository
from infrastructure.database.repositories.email_sync_state_repository import (
    EmailSyncStateRepository,
)
from infrastructure.gmail.client import (
    GmailClient,
    GmailMessage,
    GmailMessagePart,
    GmailMessageRef,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FULL_SYNC_PAGE_LIMIT: int = 500
"""Maximum number of messages fetched per page during a full sync."""

_FULL_SYNC_MAX_MESSAGES: int = 10
"""Hard cap on messages imported during a single full-sync run."""

_INBOX_LABEL: str = "INBOX"
"""Gmail label used to restrict list queries to the inbox only."""

_HISTORY_TYPE_MESSAGES_ADDED: str = "messageAdded"
"""Gmail History API change type for newly delivered messages."""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Summary of a completed sync run for a single user.

    Attributes:
        user_id: UUID of the user whose mailbox was synced.
        synced: Number of new :class:`Email` records persisted.
        skipped: Number of messages skipped because they already existed.
        failed: Number of messages that raised an error during processing.
        history_id: The Gmail history cursor stored after this run.
        full_sync: ``True`` when a full backfill was performed.
    """

    user_id: uuid.UUID
    synced: int
    skipped: int
    failed: int
    history_id: str
    full_sync: bool


# ---------------------------------------------------------------------------
# EmailSyncService
# ---------------------------------------------------------------------------


class EmailSyncService:
    """Synchronises Gmail messages for a user into the local database.

    The service is intentionally stateless between calls: all mutable state
    is stored in :class:`EmailSyncState` and flushed through the provided
    repositories at the end of each run.

    Args:
        session: Active async SQLAlchemy session scoped to the current request
            or task.
        gmail_client: Authenticated :class:`GmailClient` already entered as an
            async context manager by the caller.
        email_repository: Repository for :class:`Email` persistence.
        sync_state_repository: Repository for :class:`EmailSyncState`
            persistence.
        email_processing_service: Service that executes the full AI processing
            pipeline for each newly persisted email.
    """

    def __init__(
        self,
        session: AsyncSession,
        gmail_client: GmailClient,
        email_repository: EmailRepository,
        sync_state_repository: EmailSyncStateRepository,
        email_processing_service: EmailProcessingService,
    ) -> None:
        """Initialise the service with injected collaborators."""
        self._session = session
        self._client = gmail_client
        self._email_repo = email_repository
        self._sync_state_repo = sync_state_repository
        self._processing_service = email_processing_service

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def sync(self, user_id: uuid.UUID) -> SyncResult:
        """Run a full or incremental sync for the given user.

        Determines the sync strategy based on whether a prior history cursor
        exists in :class:`EmailSyncState`:

        - No cursor → full backfill via ``messages.list``.
        - Cursor present → incremental delta via ``users.history.list``.

        The Gmail history cursor and ``last_synced_at`` timestamp are updated
        in the database only after the run completes successfully, ensuring the
        state always reflects the last *clean* sync boundary.

        Args:
            user_id: UUID of the user whose mailbox should be synced.

        Returns:
            A :class:`SyncResult` summarising what was persisted.
        """
        sync_start = perf_counter()
        state = await self._sync_state_repo.get_or_create_for_user(user_id)

        if state.history_id is None:
            logger.info("No history cursor for user %s; performing full sync.", user_id)
            result = await self._full_sync(user_id)
        else:
            logger.info(
                "History cursor %r found for user %s; performing incremental sync.",
                state.history_id,
                user_id,
            )
            result = await self._incremental_sync(user_id, state.history_id)

        await self._sync_state_repo.update_history_id(user_id, result.history_id)
        await self._sync_state_repo.update_last_synced_at(user_id)

        total_duration = perf_counter() - sync_start
        logger.info(
            "sync_completed",
            extra={
                "user_id": str(user_id),
                "synced": result.synced,
                "skipped": result.skipped,
                "failed": result.failed,
                "history_id": result.history_id,
                "full_sync": result.full_sync,
                "total_sync_seconds": round(total_duration, 4),
            },
        )
        return result

    # ------------------------------------------------------------------
    # Sync strategies
    # ------------------------------------------------------------------

    async def _full_sync(self, user_id: uuid.UUID) -> SyncResult:
        """Backfill the inbox by paging through ``messages.list``.

        Fetches lightweight message references page-by-page, hydrates each
        reference into a full :class:`GmailMessage`, and persists new records.
        Stops when all pages are exhausted or ``_FULL_SYNC_MAX_MESSAGES`` is
        reached.

        Args:
            user_id: UUID of the target user.

        Returns:
            A :class:`SyncResult` with ``full_sync=True``.
        """
        synced = skipped = failed = 0
        page_token: str | None = None
        total_processed = 0

        # Capture the current mailbox history ID upfront so the cursor stored
        # at the end of the run is valid even if no messages were ingested.
        profile = await self._client.fetch_profile()
        latest_history_id = profile.history_id

        while total_processed < _FULL_SYNC_MAX_MESSAGES:
            remaining = _FULL_SYNC_MAX_MESSAGES - total_processed
            page = await self._client.fetch_messages(
                label_ids=[_INBOX_LABEL],
                max_results=min(_FULL_SYNC_PAGE_LIMIT, remaining),
                page_token=page_token,
            )

            if not page.messages:
                break

            refs: list[GmailMessageRef] = page.messages
            s, sk, f = await self._process_message_refs(user_id, refs)
            synced += s
            skipped += sk
            failed += f
            total_processed += len(refs)

            if page.next_page_token is None:
                break
            page_token = page.next_page_token

        return SyncResult(
            user_id=user_id,
            synced=synced,
            skipped=skipped,
            failed=failed,
            history_id=latest_history_id,
            full_sync=True,
        )

    async def _incremental_sync(
        self, user_id: uuid.UUID, start_history_id: str
    ) -> SyncResult:
        """Fetch only new messages since ``start_history_id``.

        Pages through ``users.history.list``, collecting ``messagesAdded``
        references, then hydrates and persists each new message.

        Args:
            user_id: UUID of the target user.
            start_history_id: Gmail history cursor from the previous sync run.

        Returns:
            A :class:`SyncResult` with ``full_sync=False``.
        """
        synced = skipped = failed = 0
        page_token: str | None = None
        latest_history_id = start_history_id
        added_refs: list[GmailMessageRef] = []

        try:
            while True:
                history_page = await self._client.fetch_history(
                    start_history_id,
                    history_types=[_HISTORY_TYPE_MESSAGES_ADDED],
                    page_token=page_token,
                )

                if history_page.history_id:
                    latest_history_id = history_page.history_id

                for record in history_page.history:
                    added_refs.extend(record.messages_added)

                if history_page.next_page_token is None:
                    break
                page_token = history_page.next_page_token

            if added_refs:
                synced, skipped, failed = await self._process_message_refs(
                    user_id, added_refs
                )

            return SyncResult(
                user_id=user_id,
                synced=synced,
                skipped=skipped,
                failed=failed,
                history_id=latest_history_id,
                full_sync=False,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning(
                    "History ID %r expired for user %s; falling back to full sync.",
                    start_history_id,
                    user_id,
                )
                return await self._full_sync(user_id)
            raise

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------

    async def _process_message_refs(
        self,
        user_id: uuid.UUID,
        refs: Sequence[GmailMessageRef],
    ) -> tuple[int, int, int]:
        """Hydrate, persist, and AI-process a batch of message references.

        The batch is processed in distinct phases to maximise throughput while
        keeping the shared, non-concurrency-safe :class:`AsyncSession` writes
        serialized:

        1. **Dedup** — a single batched existence query removes refs already
           persisted (and in-batch duplicates).
        2. **Fetch** — full message payloads are fetched from Gmail
           concurrently, bounded by ``gmail_fetch_concurrency``.
        3. **Persist new records** — email rows are created serially on the
           session.
        4. **Classify** — all new emails are classified in a single batched
           zero-shot inference call.
        5. **Compute** — the remaining AI stages run concurrently across emails,
           bounded by ``email_processing_concurrency`` (blocking LLM/ML calls
           are offloaded to worker threads), performing no database writes.
        6. **Persist results** — computed outcomes are written serially.

        Per-message failures are isolated and do not affect other messages.

        Args:
            user_id: UUID of the owning user.
            refs: Sequence of lightweight :class:`GmailMessageRef` objects.

        Returns:
            A three-tuple of ``(synced, skipped, failed)`` counts.
        """
        settings = get_settings()
        synced = failed = 0
        timings = {
            "gmail_fetch": 0.0,
            "classification": 0.0,
            "ai_processing": 0.0,
            "db_persist": 0.0,
        }

        # Phase 1 — batched dedup (existing records + in-batch duplicates).
        ordered_ids: list[str] = []
        seen: set[str] = set()
        for ref in refs:
            if ref.message_id not in seen:
                seen.add(ref.message_id)
                ordered_ids.append(ref.message_id)

        existing = await self._email_repo.existing_gmail_message_ids(ordered_ids)
        new_ids = [mid for mid in ordered_ids if mid not in existing]
        skipped = len(refs) - len(new_ids)

        if not new_ids:
            return synced, skipped, failed

        # Phase 2 — concurrent message fetch, bounded by a semaphore.
        fetch_sem = asyncio.Semaphore(settings.gmail_fetch_concurrency)

        async def _fetch(message_id: str) -> GmailMessage:
            async with fetch_sem:
                return await self._client.fetch_message(message_id)

        fetch_start = perf_counter()
        fetch_results = await asyncio.gather(
            *(_fetch(mid) for mid in new_ids),
            return_exceptions=True,
        )
        timings["gmail_fetch"] = perf_counter() - fetch_start

        # Phase 3 — create email records serially on the shared session.
        db_start = perf_counter()
        emails: list[Email] = []
        for message_id, fetch_result in zip(new_ids, fetch_results):
            if isinstance(fetch_result, BaseException):
                if (
                    isinstance(fetch_result, httpx.HTTPStatusError)
                    and fetch_result.response.status_code == 404
                ):
                    logger.debug(
                        "Message %r no longer exists (404); skipping (deleted/trashed before sync).",
                        message_id,
                    )
                    skipped += 1
                else:
                    logger.exception(
                        "Failed to fetch message %r for user %s.",
                        message_id,
                        user_id,
                        exc_info=fetch_result,
                    )
                    failed += 1
                continue
            try:
                email_record = _normalize_message(user_id, fetch_result)
                await self._email_repo.create(email_record)
                emails.append(email_record)
            except Exception:
                logger.exception(
                    "Failed to persist message %r for user %s.",
                    message_id,
                    user_id,
                )
                failed += 1
        timings["db_persist"] += perf_counter() - db_start

        if not emails:
            self._log_batch_timings(user_id, len(emails), timings)
            return synced, skipped, failed

        # Phase 4 — batched classification (single zero-shot inference call).
        classifications: list = [None] * len(emails)
        per_email_classification_duration: float | None = None
        if settings.classification_batch_enabled:
            classification_start = perf_counter()
            classifications = await asyncio.to_thread(
                self._processing_service.classify_batch, emails
            )
            classification_elapsed = perf_counter() - classification_start
            timings["classification"] = classification_elapsed
            per_email_classification_duration = (
                classification_elapsed / len(emails) if emails else None
            )

        # Phase 5 — concurrent AI compute (no DB writes), bounded by a semaphore.
        # Content-hash dedup: reuse the outcome of a previous email in this
        # batch when the normalised body content is identical.
        content_cache: dict[str, EmailProcessingOutcome] = {}
        process_sem = asyncio.Semaphore(settings.email_processing_concurrency)

        async def _compute(
            email: Email, classification
        ) -> EmailProcessingOutcome:
            body = (email.body_text or email.snippet or "").strip()
            content_hash = hashlib.sha256(body.encode()).hexdigest() if body else ""

            if content_hash and content_hash in content_cache:
                logger.debug(
                    "content_hash_cache_hit",
                    extra={
                        "email_id": str(email.id),
                        "content_hash": content_hash[:12],
                    },
                )
                cached = content_cache[content_hash]
                # Re-apply classification from this email's own batch result.
                return EmailProcessingOutcome(
                    classification=classification or cached.classification,
                    priority=cached.priority,
                    summary=cached.summary,
                    task_result=cached.task_result,
                    career_result=cached.career_result,
                    skip_tasks=False,
                    skip_job=False,
                    skip_interview=False,
                    timings=cached.timings.copy(),
                )

            async with process_sem:
                outcome = await self._processing_service.compute(
                    email,
                    has_tasks=False,
                    has_job=False,
                    has_interview=False,
                    precomputed_classification=classification,
                    classification_duration=per_email_classification_duration,
                )

            if content_hash:
                content_cache[content_hash] = outcome
            return outcome

        ai_start = perf_counter()
        outcomes = await asyncio.gather(
            *(
                _compute(email, classification)
                for email, classification in zip(emails, classifications)
            ),
            return_exceptions=True,
        )
        timings["ai_processing"] = perf_counter() - ai_start

        # Phase 6 — persist computed outcomes serially on the shared session.
        persist_start = perf_counter()
        for email, outcome in zip(emails, outcomes):
            if isinstance(outcome, BaseException):
                logger.exception(
                    "Failed to process message %r for user %s.",
                    email.gmail_message_id,
                    user_id,
                    exc_info=outcome,
                )
                failed += 1
                continue
            try:
                await self._processing_service.persist(email, outcome)
                synced += 1
            except Exception:
                logger.exception(
                    "Failed to persist AI results for message %r (user %s).",
                    email.gmail_message_id,
                    user_id,
                )
                failed += 1
        timings["db_persist"] += perf_counter() - persist_start

        self._log_batch_timings(user_id, len(emails), timings)
        return synced, skipped, failed

    @staticmethod
    def _log_batch_timings(
        user_id: uuid.UUID,
        email_count: int,
        timings: dict[str, float],
    ) -> None:
        """Emit a structured per-batch timing log to surface phase bottlenecks."""
        logger.info(
            "message_batch_processed",
            extra={
                "user_id": str(user_id),
                "email_count": email_count,
                "gmail_fetch_seconds": round(timings["gmail_fetch"], 4),
                "classification_seconds": round(timings["classification"], 4),
                "ai_processing_seconds": round(timings["ai_processing"], 4),
                "db_persist_seconds": round(timings["db_persist"], 4),
            },
        )


# ---------------------------------------------------------------------------
# Normalisation helpers (module-level, pure functions)
# ---------------------------------------------------------------------------


def _normalize_message(user_id: uuid.UUID, message: GmailMessage) -> Email:
    """Convert a :class:`GmailMessage` into a persistable :class:`Email` record.

    Extracts headers (``From``, ``Subject``), decodes MIME body parts, and
    converts the Gmail ``internalDate`` epoch milliseconds into a timezone-aware
    ``datetime``.

    Args:
        user_id: UUID of the owning user.
        message: Fully hydrated Gmail message returned by the API.

    Returns:
        An unsaved :class:`Email` ORM instance ready for ``session.add``.
    """
    headers = _collect_headers(message)

    raw_from = headers.get("from", "")
    sender_name, sender_email = _parse_from_header(raw_from)
    subject = headers.get("subject") or None

    body_text, body_html = _extract_body(message.payload)

    received_at = datetime.fromtimestamp(
        message.internal_date / 1000,
        tz=timezone.utc,
    )

    return Email(
        user_id=user_id,
        gmail_message_id=message.message_id,
        gmail_thread_id=message.thread_id,
        sender_name=sender_name or None,
        sender_email=sender_email,
        subject=subject,
        body_text=body_text or None,
        body_html=body_html or None,
        snippet=message.snippet or None,
        received_at=received_at,
        # AI-derived fields are populated by downstream pipeline stages.
        classification=None,
        confidence_score=None,
        priority_score=None,
        summary=None,
        is_action_required=None,
        embedding=None,
    )


def _collect_headers(message: GmailMessage) -> dict[str, str]:
    """Build a case-normalised header lookup dict from the message payload.

    Only the root payload part is inspected; header names are lower-cased so
    callers can use ``headers.get("subject")`` without case sensitivity.

    Args:
        message: The :class:`GmailMessage` whose payload headers are read.

    Returns:
        Dict mapping lower-cased header names to their string values.  When
        the same header appears multiple times, the last occurrence wins.
    """
    if message.payload is None:
        return {}
    return {h.name.lower(): h.value for h in message.payload.headers}


def _parse_from_header(raw_from: str) -> tuple[str, str]:
    """Split a raw ``From`` header value into display name and email address.

    Uses :func:`email.utils.parseaddr` for RFC-2822-compliant parsing.

    Args:
        raw_from: Raw ``From`` header string, e.g.
            ``"Alice Smith <alice@example.com>"`` or ``"bob@example.com"``.

    Returns:
        A two-tuple of ``(display_name, email_address)``.  When parsing fails
        or the address is empty, ``("", raw_from)`` is returned so the caller
        always receives a non-``None`` email value.
    """
    display_name, email_address = parseaddr(raw_from)
    if not email_address:
        return "", raw_from
    return display_name, email_address


def _extract_body(
    part: GmailMessagePart | None,
) -> tuple[str | None, str | None]:
    """Recursively decode plain-text and HTML body content from MIME parts.

    Walks the MIME tree depth-first, collecting the first ``text/plain`` and
    ``text/html`` leaf parts encountered.  Base64url-encoded body data is
    decoded using standard library primitives.

    Args:
        part: Root MIME part from a :class:`GmailMessage` payload, or ``None``
            when the message has no payload (e.g. ``minimal`` format).

    Returns:
        A two-tuple of ``(plain_text, html_text)``.  Either value may be
        ``None`` when no matching MIME part is found.
    """
    if part is None:
        return None, None

    plain: str | None = None
    html: str | None = None

    def _walk(node: GmailMessagePart) -> None:
        nonlocal plain, html

        if node.mime_type == "text/plain" and plain is None and node.body_data:
            plain = _decode_base64url(node.body_data)
        elif node.mime_type == "text/html" and html is None and node.body_data:
            html = _decode_base64url(node.body_data)

        for child in node.parts:
            _walk(child)

    _walk(part)
    return plain, html


def _decode_base64url(data: str) -> str | None:
    """Decode a base64url-encoded string to UTF-8 text.

    Gmail encodes message body data using URL-safe base64 without padding.
    Standard library :func:`base64.urlsafe_b64decode` is used after restoring
    the ``=`` padding characters.

    Args:
        data: Base64url-encoded string as returned by the Gmail API.

    Returns:
        Decoded UTF-8 string, or ``None`` if decoding fails for any reason
        (malformed data, non-UTF-8 encoding).
    """
    try:
        padded = data + "=" * (-len(data) % 4)
        decoded_bytes = base64.urlsafe_b64decode(padded)
        return decoded_bytes.decode("utf-8", errors="replace")
    except Exception:
        logger.warning("Failed to base64-decode message body part; skipping.")
        return None