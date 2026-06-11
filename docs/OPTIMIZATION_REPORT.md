# Email Sync Pipeline — Optimization Report

## Baseline (V2 before this PR)

A full sync of **10 emails** took approximately **5 minutes 14 seconds**
(`06:41:11` → `06:46:25`), broken down as:

| Phase | Duration | Notes |
|---|---|---|
| Model cold-start (BART-large-mnli) | ~2 min 34 s | Lazy-loaded on first classification |
| Gmail fetch + classification batch | ~0.5 s | Already batched & concurrent |
| Priority scoring (all 10) | < 0.1 s | Local heuristic, fast |
| Summarization (10 LLM calls) | ~5–12 s | Concurrent via `asyncio.gather` |
| Task extraction (10 LLM calls) | ~20–30 s | Concurrent, with retries |
| Career extraction (10 × 2 LLM calls) | ~60–100 s | Sequential job+interview calls, 3 retries with 2 s delay each |

Two bottlenecks dominated wall-clock time:
1. **Classification model cold-start** — first invocation loads the 1.6 GB
   BART model from disk into memory on CPU, blocking for ~2.5 minutes.
2. **Career extraction** — runs for *every* email regardless of category,
   makes **two sequential LLM calls** (job + interview) per email, and
   retries up to 3 × with 2 s delays on validation failures.

---

## Optimizations Implemented

### 1. Career Extraction — Category-Gated (Token Savings)

**File:** `application/services/email_processing_service.py`

Career extraction now only executes for emails classified as one of:
- `"Work"`
- `"Interview"`
- `"Job Opportunity"`

All other categories (`Finance`, `Personal`, `Promotion`, `Newsletter`,
`Spam`, `Other`) skip career extraction entirely.

**Impact:**
- For a typical inbox where ~30 % of emails are career-related, this
  **eliminates ~70 % of career-extraction LLM calls** (2 calls per email ×
  ~7 skipped emails = 14 fewer OpenRouter requests).
- Estimated **token savings of ~40–60 %** of the total pipeline token
  budget, since career extraction prompts are among the longest.
- Time savings: **~40–70 s** per 10-email sync (career extraction was the
  single slowest stage).

### 2. Classification Model Pre-loading (Cold-Start Elimination)

**File:** `main.py`

The BART-large-mnli zero-shot classification model is now loaded eagerly
during the FastAPI lifespan startup hook via `asyncio.to_thread`. The model
is shared across all requests (thread-safe singleton on
`ZeroShotClassifier._pipeline`).

**Impact:**
- First sync request no longer blocks for ~2.5 minutes waiting for model
  download + initialization.
- Server startup takes slightly longer (one-time ~2 min on cold cache,
  < 5 s with warm HuggingFace cache), but all subsequent requests benefit.
- **Net savings: ~2 min 30 s** on the first sync after server start.

### 3. Concurrent Career Extraction LLM Calls (Parallelism)

**File:** `infrastructure/ai/career_extraction/career_extraction_service.py`

The two LLM calls inside `_extract_once` (job-opportunity extraction and
interview extraction) previously ran **sequentially**.  They now run
**concurrently** via a `ThreadPoolExecutor(max_workers=2)`.

**Impact:**
- Each career extraction attempt now takes `max(job_call, interview_call)`
  instead of `job_call + interview_call`.
- Typical per-email savings: **3–7 s** (from ~6–14 s down to ~3–7 s).
- Across the ~3 career-eligible emails in a 10-email batch: **~9–21 s**
  saved.

### 4. Celery + Redis Background Processing (User-Facing Latency)

**Files:** `celery_app.py`, `tasks/sync_tasks.py`, `api/routes/sync.py`

The sync endpoint now **dispatches to a Celery background worker** by
default (HTTP 202 Accepted), returning a `task_id` within < 1 second.
The heavy AI pipeline runs asynchronously in the Celery worker.

- **Default:** `POST /api/v1/sync` → dispatches to Celery, returns
  immediately with `{"status": "queued", "task_id": "..."}`.
- **Fallback:** `POST /api/v1/sync?async=false` → runs inline (blocking),
  preserving the original V2 behaviour for development or environments
  without a Celery worker.

**Starting the worker:**
```bash
cd backend/app
celery -A celery_app.celery worker --loglevel=info --concurrency=4
```

**Impact:**
- User-perceived sync latency drops from **~5 minutes → < 1 second**.
- Background processing time is unchanged but no longer blocks the UI.
- Worker concurrency can be tuned via `--concurrency` flag.

---

## Estimated Total Time Reduction

| Scenario | Before | After (estimated) |
|---|---|---|
| First sync (cold model) | ~5 min 14 s | ~1 min 30 s (inline) / < 1 s (Celery) |
| Subsequent sync (warm model) | ~2 min 40 s | ~45–90 s (inline) / < 1 s (Celery) |
| Sync with 0 career emails | ~2 min 40 s | ~30–45 s (inline) / < 1 s (Celery) |

**Key drivers of the reduction (inline mode):**
1. Cold-start eliminated: −2 min 30 s
2. Career extraction skipped for ~7/10 emails: −40–70 s
3. Career extraction parallelized for remaining: −9–21 s

**Key driver (Celery mode):**
- User-facing latency is < 1 s regardless of pipeline duration.

---

## Architecture Summary

```
                  ┌─────────────────────┐
  POST /sync ──▶  │  FastAPI endpoint    │
                  │  (returns < 1 s)     │
                  └────────┬────────────┘
                           │ Celery .delay()
                           ▼
                  ┌─────────────────────┐
                  │  Redis broker        │
                  └────────┬────────────┘
                           │
                           ▼
                  ┌─────────────────────┐
                  │  Celery worker       │
                  │  ┌───────────────┐  │
                  │  │ Gmail fetch   │  │
                  │  │ (concurrent)  │  │
                  │  └───────┬───────┘  │
                  │          ▼          │
                  │  ┌───────────────┐  │
                  │  │ Classification│  │
                  │  │ (batched)     │  │
                  │  └───────┬───────┘  │
                  │          ▼          │
                  │  ┌───────────────┐  │
                  │  │ Per-email AI  │  │
                  │  │ (concurrent)  │  │
                  │  │ ┌───────────┐ │  │
                  │  │ │ Priority  │ │  │
                  │  │ │ Summary   │ │  │
                  │  │ │ Tasks     │ │  │
                  │  │ │ Career*   │ │  │
                  │  │ └───────────┘ │  │
                  │  └───────────────┘  │
                  └─────────────────────┘

  * Career extraction only for Work/Interview/Job Opportunity
    categories; job + interview LLM calls run concurrently.
```

---

## New Constants

```python
# core/constants.py
CAREER_ELIGIBLE_CATEGORIES: Final[frozenset[str]] = frozenset({
    "Work",
    "Interview",
    "Job Opportunity",
})
```

## New Files

| File | Purpose |
|---|---|
| `celery_app.py` | Celery application factory (`celery -A celery_app.celery worker`) |
| `tasks/__init__.py` | Tasks package |
| `tasks/sync_tasks.py` | `sync_emails` Celery task |
| `docs/OPTIMIZATION_REPORT.md` | This document |
