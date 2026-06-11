# Trigear Assessment — Full Application Deep Dive

> **Purpose:** This document explains the entire Mail Intel application from start to finish. Every script, class, and function is covered. The goal is to give you a clear mental model of how the system works so you can confidently answer any question about it.

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Backend — Configuration & Startup](#4-backend--configuration--startup)
5. [Authentication Flow (Google OAuth2 + PKCE)](#5-authentication-flow-google-oauth2--pkce)
6. [The Email Pipeline — End to End](#6-the-email-pipeline--end-to-end)
   - 6.1 [Sync Trigger (API Route)](#61-sync-trigger-api-route)
   - 6.2 [Gmail Client — Fetching Emails](#62-gmail-client--fetching-emails)
   - 6.3 [Email Sync Service — Full & Incremental Sync](#63-email-sync-service--full--incremental-sync)
   - 6.4 [Email Processing Service — AI Pipeline](#64-email-processing-service--ai-pipeline)
   - 6.5 [Stage 1: Classification (Zero-Shot BART)](#65-stage-1-classification-zero-shot-bart)
   - 6.6 [Stage 2: Priority Scoring (Deterministic Factors)](#66-stage-2-priority-scoring-deterministic-factors)
   - 6.7 [Stage 3: Summarization (LLM)](#67-stage-3-summarization-llm)
   - 6.8 [Stage 4: Task Extraction (LLM)](#68-stage-4-task-extraction-llm)
   - 6.9 [Stage 5: Career Extraction (LLM)](#69-stage-5-career-extraction-llm)
   - 6.10 [Persisting Results to Database](#610-persisting-results-to-database)
7. [LLM Provider Infrastructure](#7-llm-provider-infrastructure)
8. [Embeddings Service](#8-embeddings-service)
9. [Database Layer](#9-database-layer)
   - 9.1 [Engine & Session Management](#91-engine--session-management)
   - 9.2 [Base Classes & Mixins](#92-base-classes--mixins)
   - 9.3 [All Database Models](#93-all-database-models)
   - 9.4 [Repository Pattern](#94-repository-pattern)
10. [API Endpoints](#10-api-endpoints)
11. [Dependency Injection (FastAPI Deps)](#11-dependency-injection-fastapi-deps)
12. [Security — Token Encryption](#12-security--token-encryption)
13. [Frontend](#13-frontend)
    - 13.1 [Entry Point & Routing](#131-entry-point--routing)
    - 13.2 [State Management (Zustand)](#132-state-management-zustand)
    - 13.3 [API Client (Axios)](#133-api-client-axios)
    - 13.4 [Pages & Layout](#134-pages--layout)
14. [How Everything Connects — A Complete User Journey](#14-how-everything-connects--a-complete-user-journey)
15. [Potential Improvements](#15-potential-improvements)

---

## 1. High-Level Architecture

```
┌──────────────────┐      HTTPS       ┌──────────────────────────────────┐
│   React + Vite   │ ───────────────► │     FastAPI Backend (async)      │
│   Frontend SPA   │ ◄─────────────── │                                  │
└──────────────────┘                  │  ┌──────────┐  ┌──────────────┐  │
                                      │  │ Auth     │  │ Gmail Client │  │
                                      │  │ Service  │  │ (httpx)      │  │
                                      │  └──────────┘  └──────┬───────┘  │
                                      │                       │          │
                                      │  ┌─────────────────────▼───────┐ │
                                      │  │  Email Processing Service   │ │
                                      │  │  (Classification → Priority │ │
                                      │  │   → Summary → Tasks →       │ │
                                      │  │   Career Extraction)        │ │
                                      │  └─────────────┬───────────────┘ │
                                      │                │                 │
                                      │  ┌─────────────▼───────────────┐ │
                                      │  │  Repositories (SQLAlchemy)  │ │
                                      │  └─────────────┬───────────────┘ │
                                      └────────────────┼─────────────────┘
                                                       │
                                      ┌────────────────▼─────────────────┐
                                      │  PostgreSQL + pgvector            │
                                      └──────────────────────────────────┘
```

The application is a **monorepo** with two main parts:
- **Backend:** A Python FastAPI server that handles auth, talks to Gmail, runs AI processing, and stores everything in PostgreSQL.
- **Frontend:** A React + TypeScript SPA that provides the user interface — dashboard, email list, tasks, jobs, interviews, and semantic search.

---

## 2. Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend framework | FastAPI (async) | High-performance async Python web framework with automatic OpenAPI docs |
| Database | PostgreSQL + pgvector extension | Relational DB with native vector similarity search for embeddings |
| ORM | SQLAlchemy 2.x (async) | Modern Python ORM with async support via `asyncpg` driver |
| Gmail integration | httpx (async HTTP) | Async HTTP client to call the Gmail REST API directly |
| Classification | HuggingFace `facebook/bart-large-mnli` | Zero-shot text classification — no training data needed |
| Embeddings | `sentence-transformers` | Generates semantic vector embeddings for similarity search |
| LLM providers | Gemini (default), OpenAI, Claude, OpenRouter | Pluggable LLM for summarization, task extraction, career extraction |
| Auth | Google OAuth2 + PKCE | Secure login without exposing secrets to the frontend |
| Token storage | Fernet (AES) encryption | Encrypts OAuth tokens at rest in the database |
| State cache | Redis | Stores PKCE state and code verifiers with TTL (10 min) |
| Frontend framework | React 18 + TypeScript | Component-based UI with type safety |
| Build tool | Vite | Fast dev server and production bundler |
| UI library | Tailwind CSS + Lucide icons | Utility-first CSS with clean icon set |
| Data fetching | TanStack Query (React Query) | Caching, refetching, loading/error states for API calls |
| Client state | Zustand | Minimal, hook-based global state (auth store) |
| Animations | Framer Motion | Smooth page transitions and component animations |
| HTTP client | Axios | Promise-based HTTP client with interceptors |

---

## 3. Project Structure

```
Trigear-Assessment/
├── backend/
│   └── app/
│       ├── main.py                          # FastAPI app factory & ASGI entry
│       ├── core/
│       │   ├── config.py                    # All environment variables & settings
│       │   ├── constants.py                 # App-wide constants (categories, thresholds)
│       │   ├── security.py                  # Fernet token encryption/decryption
│       │   └── logging.py                   # Structured logging setup
│       ├── api/
│       │   ├── router.py                    # Central API router
│       │   ├── routes/
│       │   │   ├── auth.py                  # /auth/login, /auth/callback, /auth/me
│       │   │   ├── sync.py                  # /sync (trigger email sync)
│       │   │   ├── email.py                 # /emails (list & detail)
│       │   │   ├── task.py                  # /tasks (list & update)
│       │   │   ├── job.py                   # /jobs (list)
│       │   │   ├── interview.py             # /interviews (list)
│       │   │   └── dashboard.py             # /dashboard (aggregated stats)
│       │   └── deps/
│       │       ├── auth.py                  # get_current_user dependency
│       │       ├── database.py              # get_db session dependency
│       │       └── pagination.py            # Pagination params dependency
│       ├── application/
│       │   └── services/
│       │       └── email_processing_service.py  # AI pipeline orchestrator
│       └── infrastructure/
│           ├── auth/
│           │   ├── auth_service.py          # OAuth2 PKCE flow
│           │   ├── oauth_state.py           # PKCE state + Redis storage
│           │   └── token_encryption.py      # Token encrypt/decrypt facade
│           ├── gmail/
│           │   ├── client.py                # Async Gmail REST API client
│           │   └── sync_service.py          # Full & incremental sync logic
│           ├── ai/
│           │   ├── classification/
│           │   │   ├── zero_shot_classifier.py  # BART-MNLI classifier
│           │   │   ├── classification_service.py # Classification orchestration
│           │   │   └── schemas.py           # Classification DTOs
│           │   ├── priority/
│           │   │   ├── priority_scoring_service.py # Weighted factor scoring
│           │   │   └── factors.py           # Individual scoring factors
│           │   ├── summarization/
│           │   │   └── summarization_service.py # LLM-based email summarization
│           │   ├── task_extraction/
│           │   │   ├── task_extraction_service.py # LLM-based task extraction
│           │   │   ├── prompts.py           # Task extraction prompt templates
│           │   │   └── deduplication.py     # Task deduplication
│           │   ├── career_extraction/
│           │   │   ├── career_extraction_service.py # LLM job/interview extraction
│           │   │   └── prompts.py           # Career extraction prompt templates
│           │   ├── embeddings/
│           │   │   └── embedding_service.py # Sentence-transformer embeddings
│           │   └── llm/
│           │       ├── base.py              # Abstract LLM provider interface
│           │       ├── provider_factory.py   # Factory to create providers
│           │       └── providers/
│           │           ├── gemini_provider.py
│           │           ├── openai_provider.py
│           │           ├── claude_provider.py
│           │           └── openrouter_provider.py
│           └── database/
│               ├── session.py               # Engine & session factory
│               ├── base.py                  # Declarative base & mixins
│               ├── models/
│               │   ├── user.py
│               │   ├── email.py
│               │   ├── oauth_token.py
│               │   ├── task.py
│               │   ├── job_opportunity.py
│               │   ├── interview.py
│               │   ├── email_sync_state.py
│               │   ├── email_classification_audit.py
│               │   └── processing_job.py
│               └── repositories/
│                   ├── base.py              # Generic CRUD repository
│                   ├── email_repository.py
│                   ├── user_repository.py
│                   ├── task_repository.py
│                   ├── job_opportunity_repository.py
│                   ├── interview_repository.py
│                   └── ...
├── frontend/
│   └── src/
│       ├── main.tsx                         # React app entry point
│       ├── App.tsx                          # Root component with page transitions
│       ├── router/index.tsx                 # All routes + auth guard
│       ├── store/authStore.tsx              # Zustand auth state
│       ├── layouts/AppLayout.tsx            # Sidebar + header layout shell
│       ├── services/api/
│       │   ├── client.ts                    # Axios instance + interceptors
│       │   ├── types.ts                     # All API response/request types
│       │   ├── authApi.ts                   # Auth API calls
│       │   ├── emailApi.ts                  # Email API calls
│       │   ├── sync.ts                      # Sync trigger call
│       │   ├── dashboardApi.ts              # Dashboard API call
│       │   ├── taskApi.ts                   # Task API calls
│       │   ├── jobApi.ts                    # Job API calls
│       │   └── interviewApi.ts              # Interview API calls
│       ├── pages/
│       │   ├── Auth/LoginPage.tsx           # Login screen
│       │   ├── Auth/CallbackPage.tsx        # OAuth callback handler
│       │   ├── Dashboard/DashboardPage.tsx  # Dashboard with stats
│       │   ├── Emails/EmailsPage.tsx        # Email list with filters
│       │   ├── Emails/EmailDetailPage.tsx   # Individual email view
│       │   ├── Tasks/TasksPage.tsx          # Task list
│       │   ├── Jobs/JobsPage.tsx            # Job opportunities list
│       │   ├── Interviews/InterviewsPage.tsx # Interviews list
│       │   └── Search/SearchPage.tsx        # Semantic search
│       ├── components/                      # Reusable UI components
│       ├── hooks/                           # Custom React hooks (useAuth, etc.)
│       └── providers/QueryProvider.tsx      # TanStack Query configuration
└── alembic/                                 # Database migration scripts
```

---

## 4. Backend — Configuration & Startup

### `core/config.py` — Settings

This is the central configuration file. It uses **Pydantic Settings** which reads values from environment variables.

Key settings grouped by area:

| Group | Settings | Purpose |
|-------|----------|---------|
| **App** | `app_name`, `app_version`, `environment`, `debug` | Basic app identity and mode |
| **Database** | `database_url`, `database_echo`, `database_pool_size`, `database_max_overflow` | PostgreSQL connection + connection pool tuning |
| **Redis** | `redis_url` | Used for OAuth state storage |
| **Google OAuth** | `google_client_id`, `google_client_secret`, `google_redirect_uri` | OAuth credentials |
| **Security** | `secret_key`, `token_encryption_key` | JWT signing + Fernet encryption key |
| **LLM** | `llm_provider` (default: `"gemini"`), `gemini_api_key`, `openai_api_key`, etc. | Which AI provider to use |
| **Processing** | `email_processing_concurrency`, `gmail_fetch_concurrency` | How many emails to process/fetch in parallel |
| **Classification** | `classification_confidence_threshold`, `classification_batch_enabled` | Threshold for "confident enough" classification |

**How it works:** `get_settings()` returns a cached singleton. Once loaded, settings are reused everywhere.

### `main.py` — Application Factory

```python
def create_app() -> FastAPI:
```

This function:
1. Creates a `FastAPI` instance with the `lifespan` context manager.
2. Adds CORS middleware (allows the frontend to talk to the backend).
3. Registers all API routes under the `/api/v1` prefix.
4. Adds a `/health` endpoint for health checks.

**`lifespan` context manager:**
- **On startup:** Calls `get_engine()` to eagerly validate the database connection pool.
- **On shutdown:** Calls `dispose_engine()` to cleanly close all database connections.

---

## 5. Authentication Flow (Google OAuth2 + PKCE)

The app uses **Google OAuth2 Authorization Code Flow with PKCE** (Proof Key for Code Exchange). PKCE adds an extra layer of security — it prevents authorization code interception attacks without requiring a client secret to be exposed to the frontend.

### Step-by-step flow:

```
  Frontend                    Backend                     Google
     │                           │                          │
     │  1. Click "Sign in"       │                          │
     │──GET /auth/login─────────►│                          │
     │                           │  2. Generate:            │
     │                           │     - state token        │
     │                           │     - PKCE code_verifier │
     │                           │     - code_challenge     │
     │                           │  3. Store in Redis       │
     │                           │     (10 min TTL)         │
     │  4. Return auth URL  ◄────│                          │
     │                           │                          │
     │  5. Redirect browser ─────┼─────────────────────────►│
     │                           │                          │  6. User consents
     │  7. Google redirects ◄────┼──────────────────────────│
     │     with ?code=...&state=...                         │
     │                           │                          │
     │  8. GET /auth/callback────►                          │
     │     ?code=...&state=...   │  9. Validate state       │
     │                           │     from Redis           │
     │                           │  10. Exchange code ──────►│
     │                           │      + code_verifier     │  11. Return tokens
     │                           │  ◄───────────────────────│
     │                           │  12. Encrypt tokens      │
     │                           │      (Fernet AES)        │
     │                           │  13. Save to DB          │
     │                           │  14. Set session cookie  │
     │  15. Cookie set       ◄───│                          │
     │  16. Redirect to /        │                          │
```

### Key files:

**`infrastructure/auth/auth_service.py` — `AuthService`**

- `build_authorization_url()` — Generates the Google OAuth URL with PKCE parameters. Creates a random `state` token and a PKCE `code_verifier`/`code_challenge` pair, stores them in Redis, and returns the URL.
- `handle_callback(code, state)` — Called when Google redirects back. Validates the state from Redis (prevents CSRF), exchanges the authorization code + `code_verifier` for tokens, fetches the user's Google profile, encrypts the tokens, and stores everything in the database.
- `refresh_access_token(user_id)` — Decrypts the stored refresh token, sends it to Google for a new access token, encrypts and saves the new token.
- `_fetch_userinfo(access_token)` — Calls Google's userinfo endpoint to get the user's name and email.

**`infrastructure/auth/oauth_state.py` — PKCE & State Management**

- `generate_state_token()` — Creates a cryptographically random 32-byte hex string.
- `generate_pkce_pair()` — Creates a random `code_verifier` (43-128 chars) and computes its SHA-256 hash as the `code_challenge`.
- `store_state(state, pkce_pair)` — Stores the state→PKCE mapping in Redis with a 10-minute TTL.
- `validate_and_consume_state(state)` — Retrieves and deletes the state from Redis (one-time use). Returns the `code_verifier` needed for the token exchange.

**`infrastructure/auth/token_encryption.py` — Token Encryption Facade**

Provides four simple functions:
- `encrypt_oauth_access_token(token)` → encrypted string
- `decrypt_oauth_access_token(encrypted)` → plain token
- `encrypt_oauth_refresh_token(token)` → encrypted string
- `decrypt_oauth_refresh_token(encrypted)` → plain token

Under the hood, these call `core/security.py`:
- `_derive_fernet_key(key_string)` — Takes the `TOKEN_ENCRYPTION_KEY` from settings, hashes it with SHA-256, and Base64-encodes it to create a valid Fernet key.
- `_get_fernet()` — Returns a cached `Fernet` cipher instance.
- `encrypt_token(token)` / `decrypt_token(encrypted)` — Uses the Fernet cipher for AES-128-CBC encryption.

---

## 6. The Email Pipeline — End to End

This is the core of the application. Here's what happens when a user clicks "Sync Emails":

```
User clicks Sync → API route → Gmail Client fetches emails → Sync Service persists raw emails
→ Processing Service runs AI pipeline on each email → Results saved to database
```

### 6.1 Sync Trigger (API Route)

**File:** `api/routes/sync.py`

```
POST /api/v1/sync
```

This endpoint:
1. Gets the current authenticated user (via session cookie).
2. Creates a `GmailClient` — an async HTTP client pointed at Gmail's REST API.
3. Creates an `EmailSyncService` and calls `sync(user_id)`.
4. Returns a JSON response with counts: `{ synced: N, skipped: N, failed: N }`.

The route creates all the necessary services and repositories in-line, passing them the database session.

### 6.2 Gmail Client — Fetching Emails

**File:** `infrastructure/gmail/client.py`

The `GmailClient` is an async context manager that wraps `httpx.AsyncClient`. It talks directly to Gmail's REST API (`https://gmail.googleapis.com/gmail/v1`).

**Data classes** (immutable, defined as frozen `@dataclass`):

| Class | Purpose |
|-------|---------|
| `GmailHeader` | A single email header (name + value) |
| `GmailMessagePart` | One MIME part of an email (could be text/plain, text/html, or nested) |
| `GmailMessage` | A full email: id, thread_id, labels, snippet, payload (nested parts) |
| `GmailMessageRef` | Lightweight reference — just message_id and thread_id |
| `GmailHistoryRecord` | One history change — messages added/deleted/labels changed |
| `GmailHistoryPage` | A page of history records |
| `GmailMessagesPage` | A page of message references |
| `GmailProfile` | Mailbox profile — email address, total messages, history_id |

**Key methods:**

- `fetch_profile()` — Gets the user's Gmail profile. The `history_id` from here is used as the sync cursor.
- `fetch_message(message_id)` — Fetches a single complete email (with full MIME payload).
- `fetch_messages(label_ids, query, page_token)` — Fetches a page of lightweight message references. Used for full sync.
- `fetch_history(start_history_id, history_types)` — Fetches changes since a given history ID. Used for incremental sync.

**Internal helpers:**
- `_request(method, path, params)` — Core HTTP method that handles auth headers, retries with exponential backoff (for 429/500/503 errors), and token refresh (for 401 errors).
- `_parse_header()`, `_parse_part()`, `_parse_message()` — Convert raw JSON dicts from the API into typed data classes. `_parse_part()` is recursive because MIME parts can contain nested parts.

### 6.3 Email Sync Service — Full & Incremental Sync

**File:** `infrastructure/gmail/sync_service.py`

The `EmailSyncService` is responsible for getting emails from Gmail into the database. It supports two sync strategies:

**`sync(user_id)` — The main entry point:**
1. Checks the `email_sync_state` table for a stored `history_id` cursor.
2. If no cursor exists → runs `_full_sync()` (first time ever).
3. If a cursor exists → runs `_incremental_sync()` (only new emails since last sync).
4. Updates the stored `history_id` and `last_synced_at` timestamp.

**`_full_sync(user_id)` — Backfill:**
1. Calls `fetch_profile()` to capture the current `history_id` as the starting cursor.
2. Pages through `fetch_messages(label_ids=["INBOX"])` getting lightweight refs.
3. Passes each batch of refs to `_process_message_refs()`.
4. Stops after all pages are exhausted or the max limit (500 messages) is reached.

**`_incremental_sync(user_id, start_history_id)` — Delta:**
1. Pages through `fetch_history(start_history_id)` to get only new messages.
2. Collects all `messagesAdded` references.
3. Passes them to `_process_message_refs()`.

**`_process_message_refs(user_id, refs)` — The Heavy Lifter:**

This method orchestrates the entire pipeline for a batch of message references, running in 6 distinct phases:

1. **Dedup** — Queries the database for which Gmail message IDs already exist. Filters them out. Also deduplicates within the batch itself.
2. **Fetch** — Fetches full message payloads from Gmail concurrently (bounded by `gmail_fetch_concurrency` semaphore).
3. **Persist new records** — Creates `Email` ORM records serially (the DB session isn't safe for concurrent writes).
4. **Classify** — Runs batched zero-shot classification on all new emails in a single inference call.
5. **Compute** — Runs the remaining AI stages (priority, summary, task extraction, career extraction) concurrently across emails (bounded by `email_processing_concurrency` semaphore). Blocking ML/LLM calls are offloaded to worker threads via `asyncio.to_thread`.
6. **Persist results** — Writes the AI results back to the database serially.

**`_normalize_message(user_id, gmail_message)` — Transform Gmail data to ORM:**

This function converts a `GmailMessage` into an `Email` database record. It:
- Extracts headers (From, Subject, Date) from the MIME payload.
- Recursively walks the MIME tree to find `text/plain` and `text/html` body parts.
- Base64-decodes the body data.
- Parses the sender into `sender_name` and `sender_email`.
- Converts `internalDate` (millisecond timestamp) to a Python `datetime`.

### 6.4 Email Processing Service — AI Pipeline

**File:** `application/services/email_processing_service.py`

The `EmailProcessingService` is the **orchestrator** that runs all AI stages on a single email. It follows a strict dependency order:

```
Classification → Priority Scoring → Summarization → Task Extraction ─┐
                                                                      ├→ Persist
                                                   Career Extraction ─┘
```

**Key design decisions:**
- **Idempotent:** Skips any stage whose output already exists on the email.
- **Compute/Persist separation:** `compute()` runs all AI stages in memory (no DB access). `persist()` writes results to the database. This lets you run `compute()` concurrently across emails but serialize `persist()` calls.
- **Graceful failures:** Task and career extraction failures are logged as warnings but don't block the pipeline.

**`__init__` — Constructor:**
Takes repositories for emails, tasks, jobs, and interviews, plus optional overrides for each AI service. If no overrides are given, it creates default instances.

**`process(email)` — Convenience wrapper:**
1. Checks what already exists (tasks? jobs? interviews?) via repository calls.
2. Calls `compute()` to run all AI stages.
3. Calls `persist()` to save results.

**`compute(email, has_tasks, has_job, has_interview)` — Pure AI computation:**
1. **Classification** — If `email.classification` is None, runs classification. Updates `email.classification` and `email.confidence_score` in memory.
2. **Priority scoring** — If `email.priority_score` is None, runs priority scoring. Updates `email.priority_score` in memory.
3. **Summarization** — If `email.summary` is None, runs summarization. Updates `email.summary` in memory.
4. **Task + Career extraction** — Runs concurrently via `asyncio.gather()`. Both depend on the summary/body but are independent of each other.
5. Returns an `EmailProcessingOutcome` dataclass with all results + per-stage timing data.

**`persist(email, outcome)` — Database writes:**
1. Calls `email_repo.update_ai_fields()` to write classification, confidence, priority, and summary in a single update.
2. If tasks were extracted, creates task records.
3. If jobs were extracted, creates job opportunity records.
4. If interviews were extracted, creates interview records.

**`_stage_timer(timings, stage_name)` — Context manager:**
Records wall-clock time for each pipeline stage. Used for performance instrumentation.

### 6.5 Stage 1: Classification (Zero-Shot BART)

**Files:** `infrastructure/ai/classification/`

The classification stage categorizes each email into one of these categories:
- Work, Personal, Finance, Interview, Job Opportunity, Newsletter, Promotion, Spam, Other

**`ZeroShotClassifier`** — The core classifier:
- Uses HuggingFace's `facebook/bart-large-mnli` model.
- The model is loaded **lazily** (on first use) and **shared** across all instances (class-level singleton with thread-safe locking).
- `load()` — Downloads and initializes the model pipeline.
- `classify(input_data)` — Takes an `EmailClassificationInput`, builds a classification text from the subject + sender + body snippet, passes it through the zero-shot pipeline, and returns a `ClassificationResult` with the winning category and confidence score.
- `classify_many(inputs)` — Batched version that classifies multiple emails in a single inference call (more efficient than calling `classify()` in a loop).
- `_strip_invisible_unicode(text)` — Cleans zero-width Unicode characters that job board emails embed (e.g., LinkedIn, Glassdoor). These waste the 512-char classification window without adding meaning.

**`ClassificationService`** — Orchestration layer:
- Wraps the zero-shot classifier.
- After getting a raw classification result, applies a **confidence threshold** (configurable). If the score is below the threshold, the category falls back to "Other".
- `classify(input_data)` — Single email classification.
- `classify_batch(inputs)` — Batch classification for multiple emails.

**How zero-shot classification works:**
The model receives the email text and a list of candidate labels (the categories). It uses Natural Language Inference (NLI) to score how well each label describes the text. The label with the highest score wins. No training data is needed — the model generalizes from its pre-training on MNLI (Multi-Genre NLI).

### 6.6 Stage 2: Priority Scoring (Deterministic Factors)

**Files:** `infrastructure/ai/priority/`

Priority scoring is **deterministic** — it doesn't use any AI model. Instead, it combines four rule-based "factor scorers" with configurable weights:

| Factor | Weight | What it checks |
|--------|--------|---------------|
| **Sender Reputation** | 30% | Is the sender a no-reply address? Corporate domain vs. public (gmail.com)? Known sender? |
| **Deadline Detection** | 25% | Does the email contain date patterns, urgent keywords ("ASAP", "deadline", "due by")? |
| **Action Required** | 25% | Does the email contain action keywords ("please reply", "approval needed", "confirm")? |
| **Classification Weight** | 20% | Category-based boost. Work and Interview get high scores. Newsletter and Spam get low scores. |

**`PriorityScoringService`:**
1. Builds a `PriorityScoreInput` from the email (subject, body, sender, classification).
2. Runs each factor scorer independently.
3. Combines scores using weighted sum.
4. Clamps the final score to [0, 100].

**Factor details:**

**`SenderReputationFactor`:**
- Starts at 55 (neutral).
- **No-reply address?** → 20 (low).
- **Public email domain (gmail, outlook)?** → 50 (slightly below neutral).
- **Corporate domain?** → 70 (trusted).
- **Malformed email?** → 20 (low).

**`DeadlineDetectionFactor`:**
- Searches the subject + body for urgent keywords and date patterns.
- Starts at 30 (no deadline detected).
- Each keyword match adds 15 points.
- Date pattern match adds 20 points.
- Capped at 100.

**`ActionRequiredFactor`:**
- Similar to deadline detection but checks for action-oriented language.
- Starts at 20.
- Each action keyword match adds 15 points.
- Capped at 100.

**`ClassificationWeightFactor`:**
- Maps each email category to a base score:
  - Work → 80, Interview → 90, Job Opportunity → 75, Finance → 70
  - Personal → 50, Newsletter → 25, Promotion → 20, Spam → 10, Other → 40

### 6.7 Stage 3: Summarization (LLM)

**File:** `infrastructure/ai/summarization/summarization_service.py`

This stage uses an LLM to generate a structured summary of each email.

**`SummarizationService`:**
- Takes an LLM provider (defaults to whatever is configured — usually Gemini).
- `summarize(request)` — The main method:
  1. Builds a prompt from the email content (subject, sender, body — truncated to 8,000 chars).
  2. Sends it to the LLM with a system prompt that instructs it to return JSON:
     ```json
     {
       "summary": "one-to-three sentence plain-text summary",
       "key_points": ["fact 1", "fact 2"],
       "action_items": ["follow up on X", "reply to Y"]
     }
     ```
  3. Parses the JSON response.
  4. Retries up to 3 times with exponential backoff on transient failures.

### 6.8 Stage 4: Task Extraction (LLM)

**File:** `infrastructure/ai/task_extraction/task_extraction_service.py`

Extracts actionable tasks from email content.

**`TaskExtractionService`:**
- `extract_tasks(request)` — The main method:
  1. Builds a prompt using `build_task_extraction_prompts()`.
  2. The prompt instructs the LLM to:
     - Identify actionable tasks in the email.
     - Detect deadlines and due dates.
     - Assess urgency signals.
     - Infer a priority score (0-100).
     - Identify company names.
  3. Expected JSON output:
     ```json
     {
       "tasks": [{
         "title": "Review proposal",
         "description": "Review the Q4 budget proposal",
         "priority": 75,
         "due_date": "2024-01-15T00:00:00Z",
         "confidence_score": 0.85,
         "source_company": "Acme Corp"
       }]
     }
     ```
  4. Validates and deduplicates extracted tasks using `TaskDeduplicationService`.
  5. Retries on failure with backoff.

**`TaskDeduplicationService`:**
Removes duplicate tasks that the LLM might extract (e.g., if the same task is mentioned twice in the email).

### 6.9 Stage 5: Career Extraction (LLM)

**File:** `infrastructure/ai/career_extraction/career_extraction_service.py`

Extracts job opportunities and interview details from email content.

**`CareerExtractionService`:**
- `extract_career(request)` — Runs two separate LLM calls:
  1. **Job opportunity extraction** — Prompt asks for: company, role, location, salary, apply_link, deadline.
  2. **Interview extraction** — Prompt asks for: company, role, interview_date, meeting_link.
- Each call uses a dedicated prompt from `career_extraction/prompts.py`.
- Returns a `CareerExtractionResult` containing lists of job opportunities and interviews.
- Retries with backoff on failure.

**Prompt structure:**
Both prompts follow the same pattern:
1. System prompt sets the role ("information extraction assistant").
2. User prompt provides the exact JSON schema to follow.
3. Email subject and body are appended at the end.

### 6.10 Persisting Results to Database

After `compute()` finishes, `persist()` saves everything:

1. **AI scalar fields** — A single `UPDATE` on the email record sets `classification`, `confidence_score`, `priority_score`, and `summary`.
2. **Tasks** — Each extracted task becomes a row in the `tasks` table, linked to the email via `email_id`.
3. **Job Opportunities** — Each extracted job becomes a row in `job_opportunities`, linked via `email_id`.
4. **Interviews** — Each extracted interview becomes a row in `interviews`, linked via `email_id`.

The `_UNSET` sentinel pattern is used to distinguish "don't change this field" from "set this field to None". This prevents overwriting good data with nulls during partial re-processing.

---

## 7. LLM Provider Infrastructure

**Files:** `infrastructure/ai/llm/`

The app supports four LLM providers through a **strategy pattern**:

**`BaseLLMProvider`** — Abstract base class defining the interface:
- `summarize(request)` → `SummaryResponse` — For structured email summarization.
- `complete(system_prompt, user_prompt)` → raw text — For task/career extraction.
- `health_check()` → bool — Is the provider available?

**`LLMProviderFactory`** — Creates the right provider based on settings:
```python
if provider_name == "openai":   return OpenAIProvider(settings)
if provider_name == "claude":   return ClaudeProvider(settings)
if provider_name == "gemini":   return GeminiProvider(settings)
if provider_name == "openrouter": return OpenRouterProvider(settings)
```

**`GeminiProvider`** (default):
- Uses the official `google.generativeai` SDK.
- `_build_model()` — Configures the Gemini API key and creates a `GenerativeModel` instance.
- `summarize()` — Sends a structured prompt with `response_mime_type: "application/json"` to get guaranteed JSON output.
- `complete()` — Sends raw system + user prompts and returns the text response.
- The `_extract_text(response)` helper handles cases where Gemini returns blocked or empty responses.

---

## 8. Embeddings Service

**File:** `infrastructure/ai/embeddings/embedding_service.py`

Generates semantic vector embeddings used for the search feature.

**`EmbeddingService`:**
- **Singleton pattern** — One instance per process, created via `__new__`.
- **Lazy model loading** — The `SentenceTransformer` model is loaded on first use and shared across all calls. Thread-safe via a lock.
- `embed_text(text)` — Generates a single embedding vector (1D numpy array).
- `embed_texts(texts)` — Batch embedding for multiple texts (2D numpy array).
- `unload()` — Releases the model from memory.

The model name is configurable via `embedding_model_name` in settings. Embeddings are stored in the `embedding` column on the `Email` model using pgvector.

---

## 9. Database Layer

### 9.1 Engine & Session Management

**File:** `infrastructure/database/session.py`

- `get_engine()` — Creates and caches a singleton `AsyncEngine`. Uses `asyncpg` as the driver. In development mode, uses `NullPool` to avoid connection leaks during rapid restarts. In production, uses a properly sized connection pool with `pool_pre_ping` for stale connection detection.
- `get_session_factory()` — Creates and caches an `async_sessionmaker` bound to the engine. Sessions are configured with `expire_on_commit=False` (so objects remain usable after commit) and `autoflush=False` (explicit flushing for control).
- `get_session()` — Async generator used as a FastAPI dependency. Yields a session, commits on success, rolls back on exception.
- `dispose_engine()` — Called on shutdown to close all connections cleanly.

### 9.2 Base Classes & Mixins

**File:** `infrastructure/database/base.py`

- `Base` — SQLAlchemy `DeclarativeBase`. All models inherit from this. Configures `datetime` → `DateTime(timezone=True)` and `uuid.UUID` → `UUID(as_uuid=True)` type mappings.
- `TimestampMixin` — Adds `created_at` and `updated_at` columns. Both use `server_default=func.now()` (set by the DB). `updated_at` also uses `onupdate=func.now()`.
- `UUIDPrimaryKeyMixin` — Adds a UUID `id` column as the primary key with `default=uuid4`.

### 9.3 All Database Models

**`User`** (`users` table):
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated UUID |
| `email` | String | Google email address (unique) |
| `name` | String | Display name from Google profile |
| `google_id` | String | Google account ID (unique) |
| Relationships | | `oauth_tokens`, `emails`, `email_sync_states` |

**`OAuthToken`** (`oauth_tokens` table):
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | |
| `user_id` | UUID (FK → users) | |
| `encrypted_access_token` | Text | Fernet-encrypted access token |
| `encrypted_refresh_token` | Text | Fernet-encrypted refresh token |
| `token_type` | String | Usually "Bearer" |
| `expires_at` | DateTime | When the access token expires |
| `scopes` | String | OAuth scopes granted |

**`Email`** (`emails` table):
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | |
| `user_id` | UUID (FK → users) | |
| `gmail_message_id` | String (unique) | Gmail API message ID |
| `gmail_thread_id` | String | Gmail thread ID |
| `sender_name` | String | Parsed from "From" header |
| `sender_email` | String | Parsed from "From" header |
| `subject` | String | Email subject |
| `body_text` | Text | Plain text body |
| `body_html` | Text | HTML body |
| `snippet` | String | Gmail snippet (preview text) |
| `received_at` | DateTime | When the email was received |
| `classification` | String | AI-assigned category |
| `confidence_score` | Float | Classification confidence (0-1) |
| `priority_score` | Integer | Priority score (0-100) |
| `summary` | Text | AI-generated summary |
| `is_action_required` | Boolean | Whether the email needs action |
| `embedding` | Vector (pgvector) | Semantic embedding for search |
| Relationships | | `tasks`, `job_opportunities`, `interviews`, `classification_audits`, `processing_jobs` |

**`Task`** (`tasks` table):
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | |
| `email_id` | UUID (FK → emails) | Source email |
| `title` | String | Task title |
| `description` | Text | Task description |
| `priority` | Integer | Task priority (0-100) |
| `status` | String | pending, in_progress, completed |
| `due_date` | DateTime | Extracted deadline |

**`JobOpportunity`** (`job_opportunities` table):
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | |
| `email_id` | UUID (FK → emails) | Source email |
| `company` | String | Company name |
| `role` | String | Job title |
| `location` | String | Job location |
| `salary` | String | Salary info |
| `apply_link` | String | Application URL |
| `deadline` | String | Application deadline |

**`Interview`** (`interviews` table):
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | |
| `email_id` | UUID (FK → emails) | Source email |
| `company` | String | Company name |
| `role` | String | Job title |
| `interview_date` | DateTime | Interview date/time |
| `meeting_link` | String | Meeting URL (Zoom, etc.) |

**`EmailSyncState`** (`email_sync_states` table):
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | |
| `user_id` | UUID (FK → users) | |
| `history_id` | String | Gmail history cursor |
| `last_synced_at` | DateTime | Timestamp of last successful sync |

**`EmailClassificationAudit`** (`email_classification_audits` table):
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | |
| `email_id` | UUID (FK → emails) | |
| `classification_method` | String | "zero_shot" |
| `classification_result` | String | The assigned category |
| `confidence_score` | Float | The confidence score |

**`ProcessingJob`** (`processing_jobs` table):
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | |
| `email_id` | UUID (FK → emails) | |
| `pipeline_stage` | String | Which stage (classification, priority, etc.) |
| `status` | String | pending, processing, completed, failed |
| `error_message` | Text | Error details if failed |
| `completed_at` | DateTime | When the stage finished |

### 9.4 Repository Pattern

**File:** `infrastructure/database/repositories/base.py`

All repositories extend `BaseRepository[ModelT]` — a generic class typed to a specific ORM model.

**`BaseRepository` provides:**
- `get_by_id(record_id)` — Fetch by primary key.
- `get_all(offset, limit, filters, order_by)` — Paginated listing with optional WHERE and ORDER BY.
- `count(filters)` — Count matching records.
- `create(instance)` — Insert a new record (flush + refresh).
- `update(instance, data)` — Apply field updates and flush.
- `delete(instance)` — Delete a record.
- `exists(filters)` — Check if any matching record exists.

**Specialized repositories add domain-specific queries:**

**`EmailRepository`:**
- `get_by_gmail_message_id(id)` — Duplicate detection during sync.
- `gmail_message_exists(id)` — Lightweight existence check.
- `existing_gmail_message_ids(ids)` — Batched dedup with `WHERE IN (...)`.
- `get_by_user_id(user_id)` — Paginated email list for a user.
- `get_by_user_and_classification(user_id, classification)` — Filtered by category.
- `get_high_priority(user_id, min_priority)` — Filtered by priority threshold.
- `update_ai_fields(email, ...)` — Single update for classification/priority/summary.

Other repositories (`TaskRepository`, `JobOpportunityRepository`, `InterviewRepository`, `UserRepository`, etc.) follow the same pattern with their domain-specific queries.

---

## 10. API Endpoints

All endpoints are versioned under `/api/v1`.

### Auth (`/auth`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/auth/login` | Returns the Google OAuth authorization URL |
| `GET` | `/auth/callback` | Handles the Google OAuth redirect. Exchanges code for tokens, sets session cookie |
| `GET` | `/auth/me` | Returns the current authenticated user's profile |

### Sync (`/sync`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/sync` | Triggers email sync (full or incremental) + AI processing |
| `GET` | `/sync/status` | Returns the current sync state (last synced time, history ID) |

### Emails (`/emails`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/emails` | Paginated email list. Supports `?classification=Work&priority_min=50` filters |
| `GET` | `/emails/{id}` | Full email detail including body text, body HTML, and all AI fields |

### Tasks (`/tasks`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/tasks` | List all extracted tasks for the current user |
| `PATCH` | `/tasks/{id}` | Update a task (change status, priority, due date) |

### Jobs (`/jobs`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/jobs` | List all extracted job opportunities |

### Interviews (`/interviews`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/interviews` | List all extracted interviews |

### Dashboard (`/dashboard`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/dashboard` | Aggregated counts: total emails, important emails, pending tasks, upcoming interviews, active jobs |

### Search (`/search`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/search?q=...` | Semantic vector search across emails using pgvector |

---

## 11. Dependency Injection (FastAPI Deps)

FastAPI uses Python's `Depends()` system for dependency injection.

**`api/deps/auth.py`:**
- `get_current_user(session_user_id, db)` — Reads the `session_user_id` cookie, looks up the user in the database. Returns the `User` ORM instance or raises HTTP 401.
- `get_optional_current_user(...)` — Same but returns `None` instead of raising 401 for unauthenticated requests.

**`api/deps/database.py`:**
- `get_db()` — Yields an `AsyncSession` scoped to the request. Commits on success, rolls back on exception. Every route that needs the database depends on this.

**`api/deps/pagination.py`:**
- `get_pagination(page, page_size)` — Parses `?page=1&page_size=20` query params into a `PaginationParams` dataclass. Enforces max page size of 100.
- `PaginationParams` has an `offset` property: `(page - 1) * page_size`.

---

## 12. Security — Token Encryption

**File:** `core/security.py`

OAuth tokens are encrypted at rest using **Fernet symmetric encryption** (AES-128-CBC with HMAC authentication).

**How the key is derived:**
1. Take the `TOKEN_ENCRYPTION_KEY` from settings (must be ≥32 characters).
2. Hash it with SHA-256 to get a 32-byte key.
3. Base64url-encode it to create a valid Fernet key.

**Why Fernet?**
- It's a high-level encryption recipe from the `cryptography` library.
- It handles IV generation, padding, and HMAC verification automatically.
- Decryption fails with an exception if the data has been tampered with.

---

## 13. Frontend

### 13.1 Entry Point & Routing

**`main.tsx`:**
- Renders the React app into the DOM.
- Wraps everything in `QueryProvider` (TanStack Query) and `RouterProvider` (React Router).

**`router/index.tsx`:**
- Defines all routes using `createBrowserRouter`.
- **`RequireAuth`** component — A route guard that checks `useAuthStore().isAuthenticated`. If not authenticated, redirects to `/login`.
- All authenticated pages are nested under `AppLayout` (sidebar + header).
- Pages use **lazy loading** (`lazy: () => import(...)`) — components are only loaded when the route is visited, reducing initial bundle size.

Routes:
| Path | Page | Auth required? |
|------|------|---------------|
| `/login` | LoginPage | No |
| `/auth/callback` | CallbackPage | No |
| `/` | DashboardPage | Yes |
| `/emails` | EmailsPage | Yes |
| `/emails/:id` | EmailDetailPage | Yes |
| `/tasks` | TasksPage | Yes |
| `/jobs` | JobsPage | Yes |
| `/interviews` | InterviewsPage | Yes |
| `/search` | SearchPage | Yes |

### 13.2 State Management (Zustand)

**`store/authStore.tsx`:**
- Uses **Zustand** with the `persist` middleware to save auth state to `sessionStorage`.
- State shape:
  ```typescript
  {
    user: { id, email, name } | null,
    isAuthenticated: boolean,
    setUser(user): void,
    clearAuth(): void
  }
  ```
- `setUser()` sets the user and marks `isAuthenticated = true`.
- `clearAuth()` clears the user and marks `isAuthenticated = false`.
- Session storage means the state survives page refreshes within the same tab but is cleared when the tab closes.

### 13.3 API Client (Axios)

**`services/api/client.ts`:**
- Creates a singleton Axios instance with `withCredentials: true` (sends cookies cross-origin).
- **Request interceptor** — Currently a pass-through (ready for future auth header injection).
- **Response interceptor** — On HTTP 401, clears the auth store and redirects to `/login`. Normalizes errors into `{ status, message }` shape.

**API service files** (one per domain):
- `authApi.ts` — `fetchLoginUrl()`, `fetchCurrentUser()`, `postLogout()`
- `emailApi.ts` — `fetchEmails(params)`, `fetchEmailById(id)`
- `sync.ts` — `syncEmails()`
- `dashboardApi.ts` — `fetchDashboard()`
- `taskApi.ts` — `fetchTasks()`, `updateTask(id, data)`
- `jobApi.ts` — `fetchJobs()`
- `interviewApi.ts` — `fetchInterviews()`

### 13.4 Pages & Layout

**`App.tsx`:**
- Root component that wraps page content in `AnimatePresence` + `motion.div` from Framer Motion.
- Provides smooth page transitions (fade + slide) when navigating between routes.

**`layouts/AppLayout.tsx`:**
- The authenticated layout shell. Contains:
  - **Sidebar** with navigation links (Dashboard, Emails, Tasks, Jobs, Interviews, Search).
  - **Sync button** — Triggers `syncEmails()` and shows a toast notification (loading → success/error).
  - **User menu** — Shows user name/email, avatar initials, and a logout button.
  - **Mobile responsive** — Sidebar collapses to a hamburger menu on small screens.
- After a successful sync, invalidates the `["dashboard"]` and `["emails"]` TanStack Query caches so the UI refreshes with new data.

**`LoginPage.tsx`:**
- Full-screen login page with branding, feature list, and a "Sign in with Google" button.
- Redirects already-authenticated users to the dashboard.
- The `LoginButton` component calls `fetchLoginUrl()` and redirects the browser to Google's consent screen.

**`CallbackPage.tsx`:**
- Handles the OAuth redirect from Google.
- Shows a loading animation with progress steps (Verifying credentials → Setting up session → Finishing).
- Calls `GET /auth/me` to hydrate the Zustand store with the authenticated user.
- On success, navigates to the dashboard.
- On error, shows a friendly error message with a "Try again" button.

**`DashboardPage.tsx`:**
- Shows greeting based on time of day.
- Displays stats cards (total emails, important emails, pending tasks, upcoming interviews, active jobs).
- Shows an "Important Emails" widget.
- Uses TanStack Query for data fetching with automatic caching.

**Other pages** (Emails, Tasks, Jobs, Interviews, Search) follow the same pattern:
- Use TanStack Query hooks to fetch data.
- Display paginated lists with filtering/sorting.
- Individual items link to detail views.

**`services/api/types.ts`:**
Defines all TypeScript interfaces for API responses:
- `EmailSummary`, `EmailDetail`, `EmailListResponse`
- `Task`, `TaskListResponse`, `TaskUpdateRequest`
- `JobOpportunity`, `JobListResponse`
- `Interview`, `InterviewListResponse`
- `SearchResult`, `SearchResponse`
- `DashboardResponse`
- `PaginationMeta`

---

## 14. How Everything Connects — A Complete User Journey

Here's what happens from the moment a user opens the app to seeing their AI-processed emails:

1. **User opens the app** → React Router loads the root `App` component → `RequireAuth` checks `authStore.isAuthenticated` → redirects to `/login`.

2. **User clicks "Sign in with Google"** → Frontend calls `GET /auth/login` → Backend generates PKCE pair + state token, stores in Redis, returns Google auth URL → Browser redirects to Google.

3. **User consents on Google** → Google redirects to `/auth/callback?code=...&state=...` → Backend validates state from Redis, exchanges code for tokens using PKCE verifier, fetches Google profile, encrypts tokens, stores user + tokens in PostgreSQL, sets `session_user_id` cookie.

4. **Callback page loads** → Frontend calls `GET /auth/me` → Backend reads cookie, looks up user → Returns user profile → Zustand store sets `isAuthenticated = true` → Navigate to dashboard.

5. **Dashboard loads** → TanStack Query calls `GET /dashboard` → Backend counts emails, tasks, interviews, jobs → Returns stats → UI renders cards and widgets.

6. **User clicks "Sync Emails"** → Frontend calls `POST /sync` → Backend:
   - Creates `GmailClient` with the user's decrypted access token.
   - `EmailSyncService.sync()` checks for existing `history_id`:
     - **First time:** Full sync — pages through all inbox messages.
     - **Subsequent:** Incremental sync — only fetches changes since last sync.
   - For each batch of new messages:
     - Deduplicates against existing DB records.
     - Fetches full message payloads from Gmail concurrently.
     - Saves raw email records to database.
     - Runs batched zero-shot classification.
     - Runs remaining AI stages concurrently (priority, summary, tasks, careers).
     - Persists all AI results.
   - Returns `{ synced, skipped, failed }`.

7. **Frontend receives sync response** → Invalidates TanStack Query caches → Dashboard and email list auto-refresh → User sees their emails with AI-generated classifications, priorities, summaries, tasks, jobs, and interviews.

8. **User browses emails** → `GET /emails` with optional `?classification=Work&priority_min=50` → Backend queries PostgreSQL with filters → Returns paginated list.

9. **User clicks an email** → `GET /emails/{id}` → Backend returns full detail including body, summary, and all AI metadata.

10. **User checks tasks** → `GET /tasks` → Backend returns all AI-extracted tasks linked to the user's emails.

11. **User updates a task** → `PATCH /tasks/{id}` with `{ status: "completed" }` → Backend updates the task record.

12. **User searches** → `GET /search?q=project deadline` → Backend generates an embedding for the query using `EmbeddingService`, runs a pgvector similarity search against email embeddings, returns ranked results.

---

## 15. Potential Improvements

### Performance & Scalability

1. **Background job queue (Celery/Redis)** — Currently, email processing happens synchronously within the sync request. Moving AI processing to a background task queue would make sync responses instant and allow processing to continue even if the user closes the browser. The infrastructure for Celery is already partially configured in settings.

2. **Streaming sync progress** — Use WebSockets or Server-Sent Events (SSE) to push real-time sync progress to the frontend (e.g., "Processing 15/50 emails...") instead of the current blocking request.

3. **Caching layer** — Add Redis caching for frequently-accessed endpoints like `/dashboard` and `/emails` to reduce database load. Dashboard stats change infrequently and are good candidates for short-TTL caching.

4. **Database connection pooling tuning** — Monitor and tune `pool_size` and `max_overflow` based on actual production load. Consider using PgBouncer as an external connection pooler for high-concurrency scenarios.

5. **Pagination with cursor-based approach** — Replace offset-based pagination with cursor-based (keyset) pagination for the emails list. This is more efficient for large datasets because offset pagination degrades as the offset grows.

### AI & Processing

6. **Fine-tuned classification model** — The zero-shot BART classifier works well for general categories but could be significantly improved by fine-tuning on actual user email data. Even a small labeled dataset (500-1000 examples) would boost accuracy.

7. **Embedding-based classification fallback** — Use the existing embeddings to implement a kNN classifier as a fallback when zero-shot confidence is low. Cluster known-good classifications and assign the nearest category.

8. **Smarter summarization prompts** — Add email thread context to summarization. Currently each email is summarized in isolation; thread-aware summaries would be more useful for ongoing conversations.

9. **Batch LLM calls for extraction** — Currently, task and career extraction make separate LLM calls per email. Batching multiple emails into a single prompt (where token limits allow) would reduce API costs and latency.

10. **Confidence-based processing skip** — Skip task/career extraction for emails classified as Spam or Newsletter with high confidence. These rarely contain actionable tasks or job opportunities.

### Architecture & Code Quality

11. **Event-driven architecture** — Replace the monolithic sync → process flow with an event-driven pattern. When a new email is persisted, emit an event. Separate consumers handle classification, summarization, etc. This decouples stages and allows independent scaling.

12. **Rate limiting** — Add rate limiting to the sync endpoint to prevent abuse. A user rapidly clicking "Sync" shouldn't trigger multiple simultaneous sync operations.

13. **API versioning strategy** — The current `/api/v1` prefix is a good start. Consider implementing proper API versioning (header-based or path-based) with deprecation policies for when breaking changes are needed.

14. **Request/response DTOs** — Add Pydantic response models to all endpoints for automatic validation and documentation. Some endpoints currently return raw dict responses.

15. **Test coverage** — Add integration tests for the full sync → process → persist pipeline. Current tests appear to be primarily unit tests. End-to-end tests with a test Gmail account would catch integration issues.

### Security

16. **Token refresh automation** — Implement proactive token refresh before expiry rather than waiting for a 401. A background job could refresh tokens within a window before they expire.

17. **CSRF protection** — Add CSRF tokens to state-changing endpoints (POST, PATCH, DELETE) to prevent cross-site request forgery attacks.

18. **Input sanitization on HTML body** — When rendering email HTML in the frontend, sanitize it to prevent XSS attacks. The raw `body_html` from Gmail could contain malicious scripts.

19. **Session expiry** — Add explicit session TTL and idle timeout to the session cookie. Currently the cookie has no explicit expiration beyond the browser session.

### User Experience

20. **Email thread grouping** — Group related emails by `gmail_thread_id` instead of showing them as flat list. This gives context for conversations.

21. **Smart notifications** — Use the priority scoring system to send push notifications for high-priority emails that need immediate attention.

22. **Auto-sync schedule** — Implement periodic background sync (e.g., every 5 minutes) using Gmail push notifications (pub/sub) instead of requiring manual sync.

23. **Dashboard analytics** — Add time-series charts showing email volume trends, response times, and category distribution over time.

24. **Undo task completion** — Add the ability to revert a task status change. Currently PATCH only moves forward.

25. **Multi-account support** — Allow users to connect multiple Gmail accounts and view a unified inbox across all of them.

---

*This document covers the complete application architecture, every service, every function's purpose, and the full email processing pipeline. If you have questions about any specific area, refer back to the relevant section above.*
