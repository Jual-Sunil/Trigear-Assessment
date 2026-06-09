# Trigear Assessment — Codebase Documentation

> **Purpose of this document.** A complete, script-by-script reference for the entire `backend/` and `frontend/` codebase. For every file it lists the file path, each class/component (with a brief explanation of what it does and the functions it contains), and every function/method within it (with a simple explanation and its inputs and outputs). Use it to understand the project end-to-end and to explain any class or function on request.

## 1. What the project is

**Mail Intel** is an **AI Email Intelligence Platform**. A user signs in with Google (OAuth2 + PKCE), the backend syncs their Gmail (read-only), and an AI pipeline processes each email through five stages:

1. **Classification** — zero-shot category labelling (Work, Interview, Job Opportunity, Finance, Personal, Promotion, Newsletter, Spam, Other).
2. **Priority scoring** — a deterministic 0–100 score from weighted factors (sender reputation, deadline detection, action-required, classification weight).
3. **Summarization** — an LLM-generated structured summary.
4. **Task extraction** — actionable tasks pulled from the email (with deduplication).
5. **Career extraction** — job opportunities and interview invitations.

Results are stored in PostgreSQL (with the **pgvector** extension for semantic embeddings) and surfaced through a REST API consumed by a React dashboard (emails, tasks, jobs, interviews, dashboard counts).

## 2. Technology stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI (async/await) |
| ORM / migrations | SQLAlchemy 2.0 (async, `Mapped`) + Alembic |
| Database | PostgreSQL (asyncpg driver) + pgvector |
| Auth | Google OAuth2 with PKCE; Fernet-encrypted token storage; HttpOnly session cookie |
| AI/ML | HuggingFace transformers (zero-shot `bart-large-mnli`), sentence-transformers (`all-MiniLM-L6-v2`, 384-dim), pluggable LLM providers (OpenAI / Claude / Gemini / OpenRouter) |
| External APIs | Gmail REST API (async client with retry + token refresh) |
| Config / logging | Pydantic Settings; Structlog with sensitive-field redaction |
| Frontend framework | React 18 + TypeScript + Vite |
| UI / state / data | Material UI, Zustand (auth), TanStack Query (server state), React Router, Axios, Framer Motion |

## 3. How the backend is organised (Clean Architecture)

```
backend/app/
├── main.py                 # FastAPI app factory + ASGI entrypoint
├── api/                    # HTTP layer
│   ├── deps/               #   request-scoped dependencies (auth, db, pagination, repos)
│   ├── routes/             #   endpoint handlers + request/response Pydantic schemas
│   └── router.py           #   aggregates all routers
├── application/services/   # use-case orchestration (the AI pipeline, dashboard assembly)
├── core/                   # config, constants, logging, security primitives
├── dependencies/           # cross-cutting DI wiring
└── infrastructure/         # external concerns
    ├── ai/                 #   classification, llm, priority, summarization,
    │                       #   task_extraction, career_extraction, embeddings
    ├── auth/               #   Google OAuth2 service, PKCE/state store, token encryption
    ├── database/           #   Base, ORM models, repositories, session factory
    └── gmail/              #   Gmail REST client + sync service
```

**Reading conventions used below.** `*Inputs:*` lists each parameter as it appears in the signature (defaults like `Depends(...)`, `Cookie(...)`, `Query(...)` indicate FastAPI dependency injection; `self`/`cls` are omitted). `*Output:*` is the function's return type annotation. `FIELD`s under a class are its declared attributes (Pydantic fields, SQLAlchemy mapped columns, or dataclass fields).

---

# Backend (`backend/app/`)

## API Layer (`api/`)

### `backend/app/api/deps/auth.py`

*Module purpose:* Authentication dependencies.

#### Module-level functions

- **`get_current_user`** — Resolve and return the authenticated User from the session cookie.
  - *Inputs:* `session_user_id=Cookie(default=None, alias=_SESSION_COOKIE)`, `db=Depends(get_db)`
  - *Output:* `User`
- **`get_optional_current_user`** — Resolve the authenticated user if a valid session exists, otherwise None.
  - *Inputs:* `session_user_id=Cookie(default=None, alias=_SESSION_COOKIE)`, `db=Depends(get_db)`
  - *Output:* `Optional[User]`


---

### `backend/app/api/deps/database.py`

*Module purpose:* Database session dependency.

#### Module-level functions

- **`get_db`** — Yield an async database session for the duration of a request.
  - *Inputs:* None
  - *Output:* `AsyncGenerator[AsyncSession, None]`


---

### `backend/app/api/deps/pagination.py`

*Module purpose:* Pagination dependency.

#### Class: `PaginationParams`

Immutable container for validated pagination parameters.

**Attributes / fields:**

- `page: int`
- `page_size: int`

**Functions within the class:**

- **`offset`** — Compute the zero-based row offset for the current page.
  - *Inputs:* None
  - *Output:* `int`

#### Module-level functions

- **`get_pagination`** — Parse and validate pagination query parameters.
  - *Inputs:* `page=Query(default=1, ge=1, description='Page number (1-based)')`, `page_size=Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE, description=f'Items per page (max {_MAX_PAGE_SIZE})')`
  - *Output:* `PaginationParams`


---

### `backend/app/api/deps/repositories.py`

*Module purpose:* Repository dependencies.

#### Module-level functions

- **`get_user_repository`** — Construct a UserRepository bound to the current request session.
  - *Inputs:* `db=Depends(get_db)`
  - *Output:* `UserRepository`
- **`get_oauth_token_repository`** — Construct an OAuthTokenRepository bound to the current request session.
  - *Inputs:* `db=Depends(get_db)`
  - *Output:* `OAuthTokenRepository`
- **`get_email_sync_state_repository`** — Construct an EmailSyncStateRepository bound to the current request session.
  - *Inputs:* `db=Depends(get_db)`
  - *Output:* `EmailSyncStateRepository`
- **`get_email_repository`** — Construct an EmailRepository bound to the current request session.
  - *Inputs:* `db=Depends(get_db)`
  - *Output:* `EmailRepository`
- **`get_task_repository`** — Construct a TaskRepository bound to the current request session.
  - *Inputs:* `db=Depends(get_db)`
  - *Output:* `TaskRepository`
- **`get_job_repository`** — Construct a JobOpportunityRepository bound to the current request session.
  - *Inputs:* `db=Depends(get_db)`
  - *Output:* `JobOpportunityRepository`
- **`get_interview_repository`** — Construct an InterviewRepository bound to the current request session.
  - *Inputs:* `db=Depends(get_db)`
  - *Output:* `InterviewRepository`
- **`get_processing_job_repository`** — Construct a ProcessingJobRepository bound to the current request session.
  - *Inputs:* `db=Depends(get_db)`
  - *Output:* `ProcessingJobRepository`


---

### `backend/app/api/router.py`

*Module purpose:* Central API router.

_No classes or functions defined (configuration/wiring module)._


---

### `backend/app/api/routes/auth.py`

*Module purpose:* Authentication routes.

#### Class: `LoginResponse` (extends `BaseModel`)

Response body for the login URL endpoint.

**Attributes / fields:**

- `authorization_url: str`


#### Class: `CallbackResponse` (extends `BaseModel`)

Response body for the OAuth callback endpoint.

**Attributes / fields:**

- `success: bool`


#### Class: `CurrentUserResponse` (extends `BaseModel`)

Response body for the current authenticated user endpoint.

**Attributes / fields:**

- `id: str`
- `email: str`
- `name: str | None`


#### Module-level functions

- **`login`** — Generate and return the Google OAuth2 authorization URL.
  - *Inputs:* `user_repo=Depends(get_user_repository)`, `token_repo=Depends(get_oauth_token_repository)`
  - *Output:* `LoginResponse`
- **`callback`** — Handle the Google OAuth2 redirect callback.
  - *Inputs:* `code`, `state`, `response`, `user_repo=Depends(get_user_repository)`, `token_repo=Depends(get_oauth_token_repository)`
  - *Output:* `CallbackResponse`
- **`logout`** — Clear the session cookie, effectively logging the user out.
  - *Inputs:* `response`
  - *Output:* `None`
- **`me`** — Return the authenticated user's profile.
  - *Inputs:* `current_user=Depends(get_current_user)`
  - *Output:* `CurrentUserResponse`


---

### `backend/app/api/routes/dashboard.py`

*Module purpose:* Dashboard routes.

#### Class: `DashboardResponse` (extends `BaseModel`)

Aggregated counts for the dashboard overview.

**Attributes / fields:**

- `total_emails: int`
- `important_emails: int`
- `pending_tasks: int`
- `upcoming_interviews: int`
- `active_jobs: int`


#### Module-level functions

- **`get_dashboard`** — Compute and return dashboard overview counts for the authenticated user.
  - *Inputs:* `current_user=Depends(get_current_user)`, `db=Depends(get_db)`
  - *Output:* `DashboardResponse`


---

### `backend/app/api/routes/email.py`

*Module purpose:* Email routes.

#### Class: `EmailSummary` (extends `BaseModel`)

Lightweight email representation for list views.

**Attributes / fields:**

- `id: UUID`
- `subject: Optional[str]`
- `sender_name: Optional[str]`
- `sender_email: str`
- `received_at: datetime`
- `classification: Optional[str]`
- `confidence_score: Optional[float]`
- `priority_score: Optional[int]`
- `summary: Optional[str]`
- `is_action_required: Optional[bool]`
- `snippet: Optional[str]`
- `model_config = {'from_attributes': True}`


#### Class: `EmailDetail` (extends `EmailSummary`)

Full email representation including body content.

**Attributes / fields:**

- `body_text: Optional[str]`
- `body_html: Optional[str]`
- `gmail_message_id: str`
- `gmail_thread_id: str`
- `model_config = {'from_attributes': True}`


#### Class: `EmailListResponse` (extends `BaseModel`)

Paginated list response for emails.

**Attributes / fields:**

- `items: List[EmailSummary]`
- `total: int`
- `page: int`
- `page_size: int`


#### Module-level functions

- **`list_emails`** — Return a paginated, optionally filtered list of emails for the current user.
  - *Inputs:* `classification=Query(default=None, description='Filter by classification label')`, `priority_min=Query(default=None, ge=0, le=100, description='Minimum priority score')`, `pagination=Depends(get_pagination)`, `current_user=Depends(get_current_user)`, `db=Depends(get_db)`
  - *Output:* `EmailListResponse`
- **`get_email`** — Return full detail for a single email owned by the current user.
  - *Inputs:* `email_id`, `current_user=Depends(get_current_user)`, `db=Depends(get_db)`
  - *Output:* `EmailDetail`


---

### `backend/app/api/routes/interview.py`

*Module purpose:* Interview routes.

#### Class: `InterviewResponse` (extends `BaseModel`)

Interview representation for API responses.

**Attributes / fields:**

- `id: UUID`
- `email_id: UUID`
- `company: Optional[str]`
- `role: Optional[str]`
- `interview_date: Optional[datetime]`
- `meeting_link: Optional[str]`
- `model_config = {'from_attributes': True}`


#### Class: `InterviewListResponse` (extends `BaseModel`)

List response for interviews.

**Attributes / fields:**

- `items: List[InterviewResponse]`


#### Module-level functions

- **`list_interviews`** — Return all interviews belonging to the authenticated user.
  - *Inputs:* `current_user=Depends(get_current_user)`, `db=Depends(get_db)`
  - *Output:* `InterviewListResponse`


---

### `backend/app/api/routes/job.py`

*Module purpose:* Job opportunity routes.

#### Class: `JobResponse` (extends `BaseModel`)

Job opportunity representation for API responses.

**Attributes / fields:**

- `id: UUID`
- `email_id: UUID`
- `company: Optional[str]`
- `role: Optional[str]`
- `location: Optional[str]`
- `salary: Optional[str]`
- `apply_link: Optional[str]`
- `deadline: Optional[datetime]`
- `model_config = {'from_attributes': True}`


#### Class: `JobListResponse` (extends `BaseModel`)

List response for job opportunities.

**Attributes / fields:**

- `items: List[JobResponse]`


#### Module-level functions

- **`list_jobs`** — Return all job opportunities belonging to the authenticated user.
  - *Inputs:* `current_user=Depends(get_current_user)`, `db=Depends(get_db)`
  - *Output:* `JobListResponse`


---

### `backend/app/api/routes/search.py`

*Module purpose:* Semantic search routes.

_No classes or functions defined (configuration/wiring module)._


---

### `backend/app/api/routes/sync.py`

*Module purpose:* Email synchronization routes.

#### Class: `SyncTriggerResponse` (extends `BaseModel`)

Response body returned when a sync completes or is initiated.

**Attributes / fields:**

- `status: str`
- `user_id: str`


#### Class: `SyncStatusResponse` (extends `BaseModel`)

Response body describing the current sync state for a user.

**Attributes / fields:**

- `has_synced: bool`
- `history_id: Optional[str]`
- `last_synced_at: Optional[datetime]`


#### Module-level functions

- **`trigger_sync`** — Execute a Gmail synchronization for the authenticated user.
  - *Inputs:* `current_user=Depends(get_current_user)`, `db=Depends(get_db)`
  - *Output:* `SyncTriggerResponse`
- **`get_sync_status`** — Return the current sync state for the authenticated user.
  - *Inputs:* `current_user=Depends(get_current_user)`, `db=Depends(get_db)`
  - *Output:* `SyncStatusResponse`


---

### `backend/app/api/routes/task.py`

*Module purpose:* Task routes.

#### Class: `TaskResponse` (extends `BaseModel`)

Task representation for API responses.

**Attributes / fields:**

- `id: UUID`
- `email_id: UUID`
- `title: Optional[str]`
- `description: Optional[str]`
- `priority: Optional[int]`
- `status: Optional[str]`
- `due_date: Optional[datetime]`
- `model_config = {'from_attributes': True}`


#### Class: `TaskListResponse` (extends `BaseModel`)

List response for tasks.

**Attributes / fields:**

- `items: List[TaskResponse]`


#### Class: `TaskUpdateRequest` (extends `BaseModel`)

Request body for partial task updates.

**Attributes / fields:**

- `status: Optional[str] = None`
- `priority: Optional[int] = None`
- `due_date: Optional[datetime] = None`


#### Class: `TaskUpdateResponse` (extends `BaseModel`)

Response confirming a task update.

**Attributes / fields:**

- `success: bool`


#### Module-level functions

- **`list_tasks`** — Return all tasks belonging to the authenticated user.
  - *Inputs:* `current_user=Depends(get_current_user)`, `db=Depends(get_db)`
  - *Output:* `TaskListResponse`
- **`update_task`** — Partially update a task owned by the current user.
  - *Inputs:* `task_id`, `payload`, `current_user=Depends(get_current_user)`, `db=Depends(get_db)`
  - *Output:* `TaskUpdateResponse`


---

## Application Services (`application/`)

### `backend/app/application/services/career_dashboard_service.py`

*Module purpose:* Service for assembling career-related dashboard data.

#### Class: `CareerDashboardData`

Immutable snapshot of career-related data for the dashboard.

**Attributes / fields:**

- `active_job_opportunities: list[JobOpportunity] = field(default_factory=list)`
- `upcoming_interviews: list[Interview] = field(default_factory=list)`
- `total_active_jobs: int = 0`
- `total_upcoming_interviews: int = 0`


#### Class: `CareerDashboardRequest`

Parameters that scope a career dashboard data fetch.

**Attributes / fields:**

- `email_ids: list[uuid.UUID]`
- `job_offset: int = 0`
- `job_limit: int = 20`
- `interview_offset: int = 0`
- `interview_limit: int = 20`


#### Class: `CareerDashboardService`

Assembles career-related data from the jobs and interviews repositories.

**Functions within the class:**

- **`__init__`** — Initialise the service with pre-constructed repository instances.
  - *Inputs:* `job_repo`, `interview_repo`
  - *Output:* `None`
- **`get_dashboard_data`** — Fetch and assemble all career dashboard data for the given email scope.
  - *Inputs:* `request`
  - *Output:* `CareerDashboardData`
- **`get_active_job_opportunities`** — Return active job opportunities for a set of email IDs.
  - *Inputs:* `email_ids`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[JobOpportunity]`
- **`get_upcoming_interviews`** — Return upcoming interviews for a set of email IDs.
  - *Inputs:* `email_ids`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Interview]`
- **`get_next_interview`** — Return the single nearest upcoming scheduled interview.
  - *Inputs:* `email_ids`
  - *Output:* `Interview | None`
- **`get_upcoming_job_deadlines`** — Return job opportunities whose deadline falls within a future time window.
  - *Inputs:* `email_ids`, `*`, `days=14`, `offset=0`, `limit=20`
  - *Output:* `list[JobOpportunity]`


---

### `backend/app/application/services/email_processing_service.py`

*Module purpose:* Email processing orchestration service.

#### Class: `EmailProcessingService`

Orchestrate all AI processing stages for a single email entity.

**Functions within the class:**

- **`__init__`** — Initialise the service with repositories and optional AI service overrides.
  - *Inputs:* `*`, `email_repository`, `task_repository`, `job_opportunity_repository`, `interview_repository`, `classification_service=None`, `priority_scoring_service=None`, `summarization_service=None`, `task_extraction_service=None`, `career_extraction_service=None`
  - *Output:* `None`
- **`process`** — Execute the full AI processing pipeline for a single email.
  - *Inputs:* `email`
  - *Output:* `None`
- **`_run_classification`** — Run email classification unless a result already exists.
  - *Inputs:* `email`
  - *Output:* `ClassificationResult | None`
- **`_persist_classification`** — Persist classification and confidence score to the email record.
  - *Inputs:* `email`, `result`
  - *Output:* `None`
- **`_run_priority_scoring`** — Compute a priority score for the email unless one already exists.
  - *Inputs:* `email`
  - *Output:* `PriorityScoreResult | None`
- **`_persist_priority_score`** — Persist the computed priority score to the email record.
  - *Inputs:* `email`, `result`
  - *Output:* `None`
- **`_run_summarization`** — Generate a structured email summary unless one already exists.
  - *Inputs:* `email`
  - *Output:* `EmailSummaryResult | None`
- **`_persist_summary`** — See signature.
  - *Inputs:* `email`, `result`
  - *Output:* `None`
- **`_run_task_extraction`** — Extract and persist tasks from the email.
  - *Inputs:* `email`, `summary_result`
  - *Output:* `None`
- **`_persist_tasks`** — Persist extracted task records to the database.
  - *Inputs:* `email_id`, `result`
  - *Output:* `None`
- **`_run_career_extraction`** — Extract and persist job opportunities and interviews from the email.
  - *Inputs:* `email`, `summary_result`
  - *Output:* `None`
- **`_persist_job_opportunities`** — Persist extracted job opportunity records to the database.
  - *Inputs:* `email_id`, `result`
  - *Output:* `None`
- **`_persist_interviews`** — Persist extracted interview records to the database.
  - *Inputs:* `email_id`, `result`
  - *Output:* `None`


---

### `backend/app/application/services/task_dashboard_service.py`

*Module purpose:* Task dashboard application service.

#### Class: `DashboardTaskDTO`

Dashboard-ready task representation.

**Attributes / fields:**

- `id: str`
- `title: str`
- `description: str | None`
- `priority: int | None`
- `due_date: datetime | None`
- `status: str`


#### Class: `TaskDashboardService`

Prepare dashboard task data from pending tasks.

**Functions within the class:**

- **`__init__`** — Initialise the service.
  - *Inputs:* `*`, `task_repository`, `min_confidence_score=0.0`
  - *Output:* `None`
- **`get_dashboard_tasks`** — Retrieve, sort, and format tasks for the dashboard.
  - *Inputs:* `*`, `offset=0`, `limit=50`, `high_priority_min=0`
  - *Output:* `dict[str, Any]`
- **`_passes_confidence_filter`** — Apply a confidence filter.
  - *Inputs:* `task`
  - *Output:* `bool`
- **`_to_dto`** — Convert a Task model into a dashboard DTO.
  - *Inputs:* `task`
  - *Output:* `DashboardTaskDTO`


---

## Core (`core/`)

### `backend/app/core/__init__.py`

*Module purpose:* Core application infrastructure: configuration, security, logging, constants.

_No classes or functions defined (configuration/wiring module)._


---

### `backend/app/core/config.py`

*Module purpose:* Application configuration management using Pydantic Settings.

#### Class: `Settings` (extends `BaseSettings`)

Central application settings loaded from environment variables.

**Attributes / fields:**

- `model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False, extra='ignore')`
- `app_name: str = Field(default='AI Email Intelligence Platform')`
- `app_version: str = Field(default='1.0.0')`
- `environment: Literal['development', 'staging', 'production'] = Field(default='development')`
- `debug: bool = Field(default=False)`
- `secret_key: str = Field(..., min_length=32)`
- `api_v1_prefix: str = Field(default='/api/v1')`
- `allowed_origins: list[str] = Field(default=['http://localhost:5173'])`
- `request_max_size_bytes: int = Field(default=10 * 1024 * 1024)`
- `frontend_url: str = Field(default='http://localhost:5173')`
- `database_url: PostgresDsn = Field(...)`
- `database_pool_size: int = Field(default=10)`
- `database_max_overflow: int = Field(default=20)`
- `database_pool_timeout: int = Field(default=30)`
- `database_echo: bool = Field(default=False)`
- `redis_url: RedisDsn = Field(...)`
- `redis_max_connections: int = Field(default=20)`
- `celery_broker_url: str = Field(...)`
- `celery_result_backend: str = Field(...)`
- `celery_task_serializer: str = Field(default='json')`
- `celery_result_serializer: str = Field(default='json')`
- `celery_accept_content: list[str] = Field(default=['json'])`
- `celery_task_max_retries: int = Field(default=3)`
- `celery_task_retry_backoff: int = Field(default=60)`
- `google_client_id: str = Field(...)`
- `google_client_secret: str = Field(...)`
- `google_redirect_uri: str = Field(...)`
- `google_oauth_scopes: list[str] = Field(default=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/gmail.readonly'])`
- `token_encryption_key: str = Field(..., min_length=32)`
- `gmail_sync_max_results: int = Field(default=500)`
- `gmail_sync_batch_size: int = Field(default=50)`
- `huggingface_cache_dir: str = Field(default='/tmp/hf_cache')`
- `embedding_model_name: str = Field(default='sentence-transformers/all-MiniLM-L6-v2')`
- `classification_model_name: str = Field(default='facebook/bart-large-mnli')`
- `classification_confidence_threshold: float = Field(default=0.35)`
- `embedding_dimension: int = Field(default=384)`
- `llm_provider: Literal['openai', 'claude', 'gemini', 'openrouter'] = Field(default='gemini')`
- `openai_api_key: str = Field(default='')`
- `openai_model: str = Field(default='gpt-4o')`
- `anthropic_api_key: str = Field(default='')`
- `anthropic_model: str = Field(default='claude-opus-4-5')`
- `gemini_api_key: str = Field(default='')`
- `gemini_model: str = Field(default='gemini-1.5-pro')`
- `openrouter_api_key: str = Field(default='')`
- `openrouter_model: str = Field(default='')`
- `llm_max_tokens: int = Field(default=2048)`
- `llm_temperature: float = Field(default=0.1)`
- `llm_max_retries: int = Field(default=3)`
- `llm_retry_delay: float = Field(default=2.0)`
- `rate_limit_requests_per_minute: int = Field(default=60)`
- `rate_limit_burst: int = Field(default=10)`
- `log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = Field(default='INFO')`
- `log_format: Literal['json', 'text'] = Field(default='json')`

**Functions within the class:**

- **`assemble_db_url`** — Ensure the database URL uses the asyncpg driver.
  - *Inputs:* `v`
  - *Output:* `str`
- **`is_production`** — Return True when running in the production environment.
  - *Inputs:* None
  - *Output:* `bool`
- **`is_development`** — Return True when running in the development environment.
  - *Inputs:* None
  - *Output:* `bool`

#### Module-level functions

- **`get_settings`** — Return a cached singleton Settings instance.
  - *Inputs:* None
  - *Output:* `Settings`


---

### `backend/app/core/constants.py`

*Module purpose:* Application-wide constants used across multiple modules.

_No classes or functions defined (configuration/wiring module)._


---

### `backend/app/core/logging.py`

*Module purpose:* Structured logging setup for the application.

#### Module-level functions

- **`_redact_sensitive_fields`** — Structlog processor that removes sensitive fields from log events.
  - *Inputs:* `_logger`, `_method_name`, `event_dict`
  - *Output:* `EventDict`
- **`configure_logging`** — Initialize structlog and the standard library logging bridge.
  - *Inputs:* None
  - *Output:* `None`
- **`get_logger`** — Return a bound structlog logger for the given module name.
  - *Inputs:* `name`
  - *Output:* `structlog.stdlib.BoundLogger`


---

### `backend/app/core/security.py`

*Module purpose:* Security utilities: token encryption, decryption, and key derivation.

#### Module-level functions

- **`_derive_fernet_key`** — Derive a 32-byte URL-safe base64-encoded Fernet key from a raw string.
  - *Inputs:* `raw_key`
  - *Output:* `bytes`
- **`_get_fernet`** — Instantiate a Fernet cipher using the configured encryption key.
  - *Inputs:* None
  - *Output:* `Fernet`
- **`encrypt_token`** — Encrypt a plaintext token string for secure database storage.
  - *Inputs:* `plaintext`
  - *Output:* `str`
- **`decrypt_token`** — Decrypt a previously encrypted token string.
  - *Inputs:* `ciphertext`
  - *Output:* `str`


---

## Dependency Wiring (`dependencies/`)

### `backend/app/dependencies/deps.py`

*Module purpose:* FastAPI dependency providers.

#### Module-level functions

- **`settings_dependency`** — Return the application settings singleton.
  - *Inputs:* None
  - *Output:* `Settings`
- **`db_session_dependency`** — Yield the active async database session for the current request.
  - *Inputs:* `session=Depends(get_session)`
  - *Output:* `AsyncGenerator[AsyncSession, None]`


---

## Infrastructure — AI/ML (`infrastructure/ai/`)

### `backend/app/infrastructure/ai/career_extraction/career_extraction_service.py`

*Module purpose:* Career extraction service.

#### Class: `CareerExtractionService`

Orchestrate career extraction using the configured LLM provider.

**Functions within the class:**

- **`__init__`** — Initialise the service.
  - *Inputs:* `*`, `provider=None`, `provider_factory=None`, `settings=None`, `max_retries=None`, `retry_delay_seconds=None`
  - *Output:* `None`
- **`extract_career`** — Extract job opportunities and interviews from the provided email.
  - *Inputs:* `request`
  - *Output:* `CareerExtractionResult`
- **`_extract_once`** — Execute a single extraction attempt deterministically.
  - *Inputs:* `*`, `provider`, `request`
  - *Output:* `CareerExtractionResult`
- **`_merge_confidence`** — Merge per-branch confidence as the mean of two values.
  - *Inputs:* `*`, `job_conf`, `interview_conf`
  - *Output:* `float`
- **`_parse_json_object`** — Parse a JSON object from provider output, stripping markdown fences if present.
  - *Inputs:* `text`
  - *Output:* `dict[str, Any]`
- **`_call_provider`** — Call the LLM provider via the standard complete() interface and return raw text.
  - *Inputs:* `provider`, `*`, `system_prompt`, `user_prompt`
  - *Output:* `str`


---

### `backend/app/infrastructure/ai/career_extraction/exceptions.py`

*Module purpose:* Exception hierarchy for the career extraction subsystem.

#### Class: `CareerExtractionError` (extends `Exception`)

Base exception for all career extraction failures.

**Functions within the class:**

- **`__init__`** — Initialise the exception with an optional chained cause.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `CareerExtractionFailureError` (extends `CareerExtractionError`)

Raised when career extraction fails due to an upstream error.

**Functions within the class:**

- **`__init__`** — Initialise the exception.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `CareerExtractionValidationError` (extends `CareerExtractionError`)

Raised when extracted career data fails schema validation.

**Functions within the class:**

- **`__init__`** — Initialise the exception.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `CareerExtractionMalformedResponseError` (extends `CareerExtractionError`)

Raised when the AI provider returns a structurally malformed response.

**Functions within the class:**

- **`__init__`** — Initialise the exception.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`


---

### `backend/app/infrastructure/ai/career_extraction/prompts.py`

*Module purpose:* Prompt builders for the career extraction subsystem.

#### Module-level functions

- **`build_job_opportunity_extraction_prompt`** — Build system and user prompts for extracting job opportunities from email content.
  - *Inputs:* `*`, `subject`, `body`
  - *Output:* `tuple[str, str]`
- **`build_interview_extraction_prompt`** — Build system and user prompts for extracting interview details from email content.
  - *Inputs:* `*`, `subject`, `body`
  - *Output:* `tuple[str, str]`


---

### `backend/app/infrastructure/ai/career_extraction/schemas.py`

*Module purpose:* Pydantic schemas for the career extraction subsystem.

#### Class: `JobOpportunityData` (extends `BaseModel`)

Validated job opportunity data extracted from an email.

**Attributes / fields:**

- `company: NonEmptyCompanyName = Field(..., description='Company name.')`
- `role: str = Field(..., min_length=1, description='Role title.')`
- `location: str | None = Field(default=None, description='Job location.')`
- `salary: str | None = Field(default=None, description='Salary information.')`
- `apply_link: str | None = Field(default=None, description='HTTP(S) URL to apply.')`
- `deadline: str | None = Field(default=None, description='Optional application deadline.')`
- `confidence_score: ConfidenceScore = Field(default=0.5, description='Extraction confidence in the inclusive range [0.0, 1.0].')`
- `model_config = {'str_strip_whitespace': True, 'frozen': True}`

**Functions within the class:**

- **`validate_company`** — Validate that company name is not empty.
  - *Inputs:* `value`
  - *Output:* `str`
- **`validate_confidence`** — Validate confidence score range.
  - *Inputs:* `value`
  - *Output:* `float`
- **`validate_apply_link`** — Validate apply_link is a valid http/https URL when present.
  - *Inputs:* `value`
  - *Output:* `object`

#### Class: `InterviewData` (extends `BaseModel`)

Validated interview data extracted from an email.

**Attributes / fields:**

- `company: NonEmptyCompanyName = Field(..., description='Company name.')`
- `role: str = Field(..., min_length=1, description='Role title.')`
- `interview_date: str | None = Field(default=None, description='Optional interview date (as extracted text).')`
- `meeting_link: str | None = Field(default=None, description='HTTP(S) URL for the meeting.')`
- `confidence_score: ConfidenceScore = Field(default=0.5, description='Extraction confidence in the inclusive range [0.0, 1.0].')`
- `model_config = {'str_strip_whitespace': True, 'frozen': True}`

**Functions within the class:**

- **`validate_company`** — Validate that company name is not empty.
  - *Inputs:* `value`
  - *Output:* `str`
- **`validate_confidence`** — Validate confidence score range.
  - *Inputs:* `value`
  - *Output:* `float`
- **`validate_meeting_link`** — Validate meeting_link is a valid http/https URL when present.
  - *Inputs:* `value`
  - *Output:* `object`

#### Class: `CareerExtractionRequest` (extends `BaseModel`)

Carries the context required to extract jobs and interviews.

**Attributes / fields:**

- `subject: str | None = Field(default=None, description='Email subject line, when available.')`
- `sender: str | None = Field(default=None, description='Sender email address (or display context) when available.')`
- `body: str | None = Field(default=None, description='Email body text or summary context.')`
- `model_config = {'str_strip_whitespace': True, 'frozen': True}`


#### Class: `CareerExtractionResult` (extends `BaseModel`)

Encapsulates the validated career extraction output.

**Attributes / fields:**

- `job_opportunities: list[JobOpportunityData] = Field(default_factory=list, description='List of extracted job opportunities.')`
- `interviews: list[InterviewData] = Field(default_factory=list, description='List of extracted interviews.')`
- `extraction_confidence: ConfidenceScore = Field(..., description='Overall extraction confidence in the inclusive range [0.0, 1.0].')`
- `model_config = {'frozen': True, 'str_strip_whitespace': True}`

**Functions within the class:**

- **`validate_extraction_confidence`** — Validate overall extraction confidence range.
  - *Inputs:* `value`
  - *Output:* `float`

#### Module-level functions

- **`_validate_confidence_score_range`** — Validate that confidence_score is within [0.0, 1.0].
  - *Inputs:* `value`
  - *Output:* `float`
- **`_validate_non_empty_company_name`** — Reject empty or whitespace-only company names.
  - *Inputs:* `value`
  - *Output:* `str`
- **`_validate_http_url`** — Validate that the URL uses http/https scheme and is non-empty.
  - *Inputs:* `value`, `*`, `field_name`
  - *Output:* `str`


---

### `backend/app/infrastructure/ai/classification/__init__.py`

*Module purpose:* Classification subsystem public API.

_No classes or functions defined (configuration/wiring module)._


---

### `backend/app/infrastructure/ai/classification/base.py`

*Module purpose:* Abstract base classifier contract for the email classification subsystem.

#### Class: `BaseClassifier` (extends `ABC`)

Defines the interface that every classifier implementation must satisfy.

**Functions within the class:**

- **`method_name`** — Return the canonical method identifier for this classifier.
  - *Inputs:* None
  - *Output:* `str`
- **`is_ready`** — Report whether this classifier is initialised and ready to serve requests.
  - *Inputs:* None
  - *Output:* `bool`
- **`classify`** — Classify a single email and return a structured result.
  - *Inputs:* `input_data`
  - *Output:* `ClassificationResult`
- **`load`** — Load models and resources required by this classifier.
  - *Inputs:* None
  - *Output:* `None`
- **`unload`** — Release models and resources held by this classifier.
  - *Inputs:* None
  - *Output:* `None`
- **`_assert_ready`** — Raise :class:`~infrastructure.ai.classification.exceptions.ClassifierNotReadyError` if not ready.
  - *Inputs:* None
  - *Output:* `None`
- **`_assert_input_has_text`** — Return classification text or raise if the input yields an empty string.
  - *Inputs:* `input_data`
  - *Output:* `str`
- **`__repr__`** — Return a debug representation of this classifier instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/ai/classification/classification_service.py`

*Module purpose:* Classification orchestration service for email categorisation.

#### Class: `ClassificationService`

Coordinate embedding generation, zero-shot classification, and threshold evaluation.

**Functions within the class:**

- **`__init__`** — Initialise the classification service.
  - *Inputs:* `*`, `embedding_service=None`, `zero_shot_classifier=None`, `confidence_threshold=None`
  - *Output:* `None`
- **`classify`** — Classify an email using embeddings followed by zero-shot inference.
  - *Inputs:* `input_data`
  - *Output:* `ClassificationResult`


---

### `backend/app/infrastructure/ai/classification/exceptions.py`

*Module purpose:* Exception hierarchy for the email classification subsystem.

#### Class: `ClassificationError` (extends `Exception`)

Base exception for all classification failures.

**Functions within the class:**

- **`__init__`** — Initialise the exception with an optional chained cause.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `ClassifierNotReadyError` (extends `ClassificationError`)

Raised when a classifier is invoked before it has been initialised.

**Functions within the class:**

- **`__init__`** — Initialise with the name of the unready classifier.
  - *Inputs:* `classifier_name`
  - *Output:* `None`

#### Class: `ClassificationInputError` (extends `ClassificationError`)

Raised when the input provided to a classifier is invalid.

**Functions within the class:**

- **`__init__`** — Initialise with a description of the invalid input.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `ClassificationInferenceError` (extends `ClassificationError`)

Raised when model inference fails during classification.

**Functions within the class:**

- **`__init__`** — Initialise with the classifier name and a description of the failure.
  - *Inputs:* `classifier_name`, `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `ClassificationTimeoutError` (extends `ClassificationError`)

Raised when a classification call exceeds the configured timeout.

**Functions within the class:**

- **`__init__`** — Initialise with the classifier name and the elapsed timeout.
  - *Inputs:* `classifier_name`, `timeout_seconds`
  - *Output:* `None`

#### Class: `LowConfidenceError` (extends `ClassificationError`)

Raised when no category meets the minimum confidence threshold.

**Functions within the class:**

- **`__init__`** — Initialise with scoring context that explains the failure.
  - *Inputs:* `classifier_name`, `best_category`, `best_score`, `threshold`
  - *Output:* `None`


---

### `backend/app/infrastructure/ai/classification/schemas.py`

*Module purpose:* Data-transfer objects and value types for the classification subsystem.

#### Class: `EmailClassificationInput` (extends `BaseModel`)

Carries the text content required for classifying a single email.

**Attributes / fields:**

- `gmail_message_id: str = Field(description='Unique Gmail message identifier for the email being classified.')`
- `subject: str | None = Field(default=None, description='Email subject line.  May be absent for drafts or malformed messages.')`
- `body_text: str | None = Field(default=None, description='Plain-text body content.  May be absent for HTML-only emails.')`
- `snippet: str | None = Field(default=None, description='Short preview snippet provided by the Gmail API.')`
- `sender_email: str = Field(description='Envelope sender address used as an optional signal by some classifiers.')`
- `model_config = {'str_strip_whitespace': True}`

**Functions within the class:**

- **`at_least_one_text_field_present`** — Ensure there is at least one non-empty text source for classification.
  - *Inputs:* None
  - *Output:* `'EmailClassificationInput'`
- **`build_classification_text`** — Produce a single normalised string suitable for model input.
  - *Inputs:* `*`, `max_chars=512`
  - *Output:* `str`

#### Class: `CategoryScore` (extends `BaseModel`)

Holds the confidence score for a single candidate category.

**Attributes / fields:**

- `category: CategoryStr`
- `score: ConfidenceScore`

**Functions within the class:**

- **`category_must_be_valid`** — Reject category values that are not in the canonical list.
  - *Inputs:* `value`
  - *Output:* `str`

#### Class: `ClassificationResult` (extends `BaseModel`)

Encapsulates the output produced by a single classifier invocation.

**Attributes / fields:**

- `gmail_message_id: str = Field(description='Gmail message identifier that was classified.')`
- `category: CategoryStr = Field(description='The highest-confidence category assigned to the email.')`
- `confidence_score: ConfidenceScore = Field(description='Confidence of the winning category in the range [0.0, 1.0].')`
- `all_scores: list[CategoryScore] = Field(default_factory=list, description='Full score distribution across all candidate categories, ordered by descending score.')`
- `method: str = Field(description='Classification method that produced this result.  One of the CLASSIFICATION_METHOD_* constants.')`
- `classified_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc), description='UTC timestamp of when the classification was performed.')`
- `model_config = {'frozen': True}`

**Functions within the class:**

- **`category_must_be_valid`** — Reject category values that are not in the canonical list.
  - *Inputs:* `value`
  - *Output:* `str`
- **`method_must_be_valid`** — Reject method identifiers that are not in the known set.
  - *Inputs:* `value`
  - *Output:* `str`
- **`winning_category_present_in_all_scores`** — Ensure the winning category appears in the full score distribution.
  - *Inputs:* None
  - *Output:* `'ClassificationResult'`
- **`is_high_confidence`** — Return ``True`` when the result meets or exceeds a confidence threshold.
  - *Inputs:* `threshold`
  - *Output:* `bool`


---

### `backend/app/infrastructure/ai/classification/zero_shot_classifier.py`

*Module purpose:* Zero-shot email classifier backed by facebook/bart-large-mnli.

#### Class: `_LabelScore` (extends `TypedDict`)

Typed representation of a single zero-shot label score output.

**Attributes / fields:**

- `label: str`
- `score: float`


#### Class: `ZeroShotClassifier` (extends `BaseClassifier`)

Classify emails using HuggingFace's zero-shot classification pipeline.

**Attributes / fields:**

- `_model_name: str = 'facebook/bart-large-mnli'`
- `_pipeline: Callable[..., object] | None = None`
- `_pipeline_lock = threading.Lock()`

**Functions within the class:**

- **`__init__`** — Initialise classifier settings without loading the model.
  - *Inputs:* `*`, `top_k_labels=None`, `confidence_threshold=None`
  - *Output:* `None`
- **`method_name`** — Return the canonical method identifier for this classifier.
  - *Inputs:* None
  - *Output:* `str`
- **`is_ready`** — Return True when the HuggingFace pipeline has been loaded.
  - *Inputs:* None
  - *Output:* `bool`
- **`load`** — Load the HuggingFace zero-shot pipeline in a thread-safe manner.
  - *Inputs:* None
  - *Output:* `None`
- **`unload`** — Release the shared HuggingFace pipeline from memory.
  - *Inputs:* None
  - *Output:* `None`
- **`classify`** — Classify a single email using zero-shot inference.
  - *Inputs:* `input_data`
  - *Output:* `ClassificationResult`
- **`_normalize_predictions`** — Normalize HuggingFace output into sorted category scores.
  - *Inputs:* `raw_output`
  - *Output:* `list[CategoryScore]`
- **`_coerce_prediction_items`** — Coerce the pipeline output into a flat list of label-score items.
  - *Inputs:* `raw_output`
  - *Output:* `list[_LabelScore]`
- **`_coerce_result_dict`** — Convert a single pipeline result dict into a list of label-score pairs.
  - *Inputs:* `result`
  - *Output:* `list[_LabelScore]`

#### Module-level functions

- **`_strip_invisible_unicode`** — Remove zero-width and invisible Unicode characters from classifier input.
  - *Inputs:* `text`
  - *Output:* `str`


---

### `backend/app/infrastructure/ai/embeddings/embedding_service.py`

*Module purpose:* Sentence-transformers embedding service with thread-safe singleton model loading.

#### Class: `EmbeddingService`

Generate semantic embeddings using a lazily loaded singleton model.

**Attributes / fields:**

- `_model: SentenceTransformer | None = None`
- `_model_lock = threading.Lock()`
- `_instance: EmbeddingService | None = None`
- `_instance_lock = threading.Lock()`

**Functions within the class:**

- **`__new__`** — Return the process-wide EmbeddingService singleton.
  - *Inputs:* None
  - *Output:* `'EmbeddingService'`
- **`model`** — Return the shared embedding model, loading it on first use.
  - *Inputs:* None
  - *Output:* `SentenceTransformer`
- **`is_ready`** — Return True when the embedding model has already been loaded.
  - *Inputs:* None
  - *Output:* `bool`
- **`embed_text`** — Generate a single embedding vector for the provided text.
  - *Inputs:* `text`
  - *Output:* `NDArray[np.float32]`
- **`embed_texts`** — Generate embeddings for multiple texts in a single batch.
  - *Inputs:* `texts`
  - *Output:* `NDArray[np.float32]`
- **`unload`** — Release the loaded model from memory.
  - *Inputs:* None
  - *Output:* `None`
- **`reset_singleton`** — Reset the service and model singletons.
  - *Inputs:* None
  - *Output:* `None`


---

### `backend/app/infrastructure/ai/llm/base.py`

*Module purpose:* Abstract base provider contract for the LLM summarization subsystem.

#### Class: `BaseLLMProvider` (extends `ABC`)

Defines the interface that every LLM provider implementation must satisfy.

**Functions within the class:**

- **`summarize`** — Generate a validated summary for a single email.
  - *Inputs:* `request`
  - *Output:* `SummaryResponse`
- **`complete`** — Send a raw system/user prompt pair and return the model's text output.
  - *Inputs:* `system_prompt`, `user_prompt`
  - *Output:* `str`
- **`health_check`** — Report whether the provider is available and ready for use.
  - *Inputs:* None
  - *Output:* `bool`


---

### `backend/app/infrastructure/ai/llm/exceptions.py`

*Module purpose:* Exception hierarchy for the LLM summarization provider subsystem.

#### Class: `LLMProviderError` (extends `Exception`)

Base exception for all LLM provider failures.

**Functions within the class:**

- **`__init__`** — Initialise the exception with an optional chained cause.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `LLMProviderNotReadyError` (extends `LLMProviderError`)

Raised when a provider is invoked before it is ready.

**Functions within the class:**

- **`__init__`** — Initialise with the name of the unready provider.
  - *Inputs:* `provider_name`
  - *Output:* `None`

#### Class: `LLMProviderInputError` (extends `LLMProviderError`)

Raised when the input provided to a provider is invalid.

**Functions within the class:**

- **`__init__`** — Initialise with a description of the invalid input.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `LLMProviderResponseValidationError` (extends `LLMProviderError`)

Raised when provider output cannot be validated against the response schema.

**Functions within the class:**

- **`__init__`** — Initialise with the provider name and validation failure details.
  - *Inputs:* `provider_name`, `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `LLMProviderTimeoutError` (extends `LLMProviderError`)

Raised when a provider call exceeds the configured timeout.

**Functions within the class:**

- **`__init__`** — Initialise with the provider name and the elapsed timeout.
  - *Inputs:* `provider_name`, `timeout_seconds`
  - *Output:* `None`

#### Class: `LLMProviderHealthCheckError` (extends `LLMProviderError`)

Raised when a provider health check fails.

**Functions within the class:**

- **`__init__`** — Initialise with the provider name and health check failure details.
  - *Inputs:* `provider_name`, `message`, `*`, `cause=None`
  - *Output:* `None`


---

### `backend/app/infrastructure/ai/llm/provider_factory.py`

*Module purpose:* Factory for creating configured LLM provider instances.

#### Class: `LLMProviderFactory`

Create a concrete LLM provider based on application settings.

**Functions within the class:**

- **`__init__`** — Initialise the factory with application settings.
  - *Inputs:* `settings=None`
  - *Output:* `None`
- **`create_provider`** — Create the configured LLM provider.
  - *Inputs:* None
  - *Output:* `BaseLLMProvider`


---

### `backend/app/infrastructure/ai/llm/providers/claude_provider.py`

*Module purpose:* Claude provider implementation for LLM-based email summarization.

#### Class: `ClaudeProvider` (extends `BaseLLMProvider`)

Summarize emails using the official Anthropic SDK.

**Functions within the class:**

- **`__init__`** — Initialise the provider from application settings.
  - *Inputs:* `settings=None`
  - *Output:* `None`
- **`summarize`** — Generate a validated email summary for the supplied request.
  - *Inputs:* `request`
  - *Output:* `SummaryResponse`
- **`health_check`** — Report whether the Claude provider is configured and reachable.
  - *Inputs:* None
  - *Output:* `bool`
- **`complete`** — Send a raw prompt pair to Claude and return the model's text output.
  - *Inputs:* `system_prompt`, `user_prompt`
  - *Output:* `str`
- **`_assert_ready`** — Ensure the provider is configured before attempting a summary call.
  - *Inputs:* None
  - *Output:* `None`
- **`_build_client`** — Create an Anthropic client when an API key is configured.
  - *Inputs:* None
  - *Output:* `Anthropic | None`
- **`_build_system_prompt`** — Construct the system prompt used to request a JSON summary.
  - *Inputs:* None
  - *Output:* `str`
- **`_build_user_prompt`** — Construct the user prompt containing email context and content.
  - *Inputs:* `request`
  - *Output:* `str`
- **`_extract_text_content`** — Extract concatenated text blocks from the Claude response.
  - *Inputs:* `content`
  - *Output:* `str`
- **`_parse_json_payload`** — Parse the Claude response text into a JSON payload.
  - *Inputs:* `content`
  - *Output:* `dict[str, Any]`
- **`_extract_summary`** — Extract the summary text from a validated response payload.
  - *Inputs:* `payload`
  - *Output:* `str`


---

### `backend/app/infrastructure/ai/llm/providers/gemini_provider.py`

*Module purpose:* Gemini provider implementation for LLM-based email summarization.

#### Class: `GeminiProvider` (extends `BaseLLMProvider`)

Summarize emails using the official Google Generative AI SDK.

**Functions within the class:**

- **`__init__`** — Initialise the provider from application settings.
  - *Inputs:* `settings=None`
  - *Output:* `None`
- **`summarize`** — Generate a validated email summary for the supplied request.
  - *Inputs:* `request`
  - *Output:* `SummaryResponse`
- **`health_check`** — Report whether the Gemini provider is configured and reachable.
  - *Inputs:* None
  - *Output:* `bool`
- **`complete`** — Send a raw prompt pair to Gemini and return the model's text output.
  - *Inputs:* `system_prompt`, `user_prompt`
  - *Output:* `str`
- **`_assert_ready`** — Ensure the provider is configured before attempting a summary call.
  - *Inputs:* None
  - *Output:* `None`
- **`_build_model`** — Create a Gemini model instance when an API key is configured.
  - *Inputs:* None
  - *Output:* `genai.GenerativeModel | None`
- **`_build_prompt`** — Construct the prompt containing email context and content.
  - *Inputs:* `request`
  - *Output:* `str`
- **`_extract_text`** — Extract response text from the Gemini SDK response object.
  - *Inputs:* `response`
  - *Output:* `str`
- **`_parse_json_payload`** — Parse the Gemini response text into a JSON payload.
  - *Inputs:* `content`
  - *Output:* `dict[str, Any]`
- **`_extract_summary`** — Extract the summary text from a validated response payload.
  - *Inputs:* `payload`
  - *Output:* `str`


---

### `backend/app/infrastructure/ai/llm/providers/openai_provider.py`

*Module purpose:* OpenAI provider implementation for LLM-based email summarization.

#### Class: `OpenAIProvider` (extends `BaseLLMProvider`)

Summarize emails using the official OpenAI SDK.

**Functions within the class:**

- **`__init__`** — Initialise the provider from application settings.
  - *Inputs:* `settings=None`
  - *Output:* `None`
- **`summarize`** — Generate a validated email summary for the supplied request.
  - *Inputs:* `request`
  - *Output:* `SummaryResponse`
- **`health_check`** — Report whether the OpenAI provider is configured and reachable.
  - *Inputs:* None
  - *Output:* `bool`
- **`complete`** — Send a raw prompt pair to OpenAI and return the model's text output.
  - *Inputs:* `system_prompt`, `user_prompt`
  - *Output:* `str`
- **`_assert_ready`** — Ensure the provider is configured before attempting a summary call.
  - *Inputs:* None
  - *Output:* `None`
- **`_build_client`** — Create an OpenAI client when an API key is configured.
  - *Inputs:* None
  - *Output:* `OpenAI | None`
- **`_build_messages`** — Construct the chat messages used to request a JSON summary.
  - *Inputs:* `request`
  - *Output:* `list[dict[str, str]]`
- **`_build_user_prompt`** — Construct the user prompt containing email context and content.
  - *Inputs:* `request`
  - *Output:* `str`
- **`_parse_json_payload`** — Parse the SDK response content into a JSON payload.
  - *Inputs:* `content`
  - *Output:* `dict[str, Any]`
- **`_extract_summary`** — Extract the summary text from a validated response payload.
  - *Inputs:* `payload`
  - *Output:* `str`


---

### `backend/app/infrastructure/ai/llm/providers/openrouter_provider.py`

*Module purpose:* OpenRouter provider implementation for LLM-based email summarization.

#### Class: `OpenRouterProvider` (extends `BaseLLMProvider`)

Summarize emails by calling OpenRouter's OpenAI-compatible chat API.

**Functions within the class:**

- **`__init__`** — Initialise the provider from application settings.
  - *Inputs:* `settings=None`
  - *Output:* `None`
- **`summarize`** — Generate a validated email summary via the OpenRouter API.
  - *Inputs:* `request`
  - *Output:* `SummaryResponse`
- **`health_check`** — Report whether the OpenRouter provider is reachable and configured.
  - *Inputs:* None
  - *Output:* `bool`
- **`complete`** — Send a raw prompt pair to OpenRouter and return the model's text output.
  - *Inputs:* `system_prompt`, `user_prompt`
  - *Output:* `str`
- **`_assert_ready`** — Raise :class:`LLMProviderNotReadyError` when the client is absent.
  - *Inputs:* None
  - *Output:* `None`
- **`_build_client`** — Create a persistent ``httpx.Client`` when an API key is present.
  - *Inputs:* None
  - *Output:* `httpx.Client | None`
- **`_build_prompt`** — Construct the full prompt that will be sent as the user message.
  - *Inputs:* `request`
  - *Output:* `str`
- **`_call_api`** — Send a chat-completion request to OpenRouter and return the raw JSON.
  - *Inputs:* `prompt`
  - *Output:* `dict[str, Any]`
- **`_extract_text`** — Pull the assistant message content from the OpenAI-compatible envelope.
  - *Inputs:* `response`
  - *Output:* `str`
- **`_parse_json_payload`** — Decode the model's text output as a JSON object.
  - *Inputs:* `content`
  - *Output:* `dict[str, Any]`
- **`_extract_summary`** — Pull and validate the ``summary`` field from the decoded payload.
  - *Inputs:* `payload`
  - *Output:* `str`


---

### `backend/app/infrastructure/ai/llm/schemas.py`

*Module purpose:* Data-transfer objects for the LLM summarization provider contract.

#### Class: `SummaryRequest` (extends `BaseModel`)

Carries the data required to generate an email summary.

**Attributes / fields:**

- `email_id: UUID = Field(description='Database identifier for the email being summarised.')`
- `subject: str | None = Field(default=None, description='Email subject line, when available.')`
- `body_text: str | None = Field(default=None, description='Plain-text body content, when available.')`
- `sender_name: str | None = Field(default=None, description='Display name of the sender, when available.')`
- `sender_email: str = Field(min_length=1, description='Sender email address used as a contextual signal.')`
- `classification: str | None = Field(default=None, description='Current email classification category, when available.')`
- `confidence_score: ConfidenceScore | None = Field(default=None, description='Classification confidence score in the range [0.0, 1.0].')`
- `priority_score: PriorityScore | None = Field(default=None, description='Computed priority score in the range [0, 100].')`
- `is_action_required: bool | None = Field(default=None, description='Whether the email has been flagged as action required.')`
- `received_at: datetime = Field(description='UTC timestamp indicating when the message was received.')`
- `model_config = {'str_strip_whitespace': True}`

**Functions within the class:**

- **`require_email_text`** — Ensure the request contains at least one usable text field.
  - *Inputs:* None
  - *Output:* `'SummaryRequest'`

#### Class: `SummaryResponse` (extends `BaseModel`)

Encapsulates a validated LLM-generated summary.

**Attributes / fields:**

- `email_id: UUID = Field(description='Database identifier for the email that was summarised.')`
- `summary: str = Field(min_length=1, description='Human-readable summary produced by the LLM provider.')`
- `provider: str = Field(min_length=1, description='Canonical provider identifier that generated the summary.')`
- `model: str = Field(min_length=1, description='Underlying model identifier used for generation.')`
- `generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc), description='UTC timestamp when the summary was generated.')`
- `model_config = {'frozen': True, 'str_strip_whitespace': True}`

**Functions within the class:**

- **`summary_must_not_be_empty`** — Reject blank summary text.
  - *Inputs:* `value`
  - *Output:* `str`


---

### `backend/app/infrastructure/ai/priority/base.py`

*Module purpose:* Abstract base scorer contract for the email priority scoring subsystem.

#### Class: `BasePriorityScorer` (extends `ABC`)

Defines the interface that every priority scorer implementation must satisfy.

**Functions within the class:**

- **`method_name`** — Return the canonical method identifier for this scorer.
  - *Inputs:* None
  - *Output:* `str`
- **`is_ready`** — Report whether this scorer is initialised and ready to serve requests.
  - *Inputs:* None
  - *Output:* `bool`
- **`score`** — Score a single email and return a structured priority result.
  - *Inputs:* `input_data`
  - *Output:* `PriorityScoreResult`
- **`load`** — Load resources required by this scorer.
  - *Inputs:* None
  - *Output:* `None`
- **`unload`** — Release resources held by this scorer.
  - *Inputs:* None
  - *Output:* `None`
- **`_assert_ready`** — Raise :class:`PriorityScorerNotReadyError` if the scorer is not ready.
  - *Inputs:* None
  - *Output:* `None`
- **`_assert_score_in_range`** — Validate the final score is within the accepted priority range.
  - *Inputs:* `score`
  - *Output:* `int`
- **`__repr__`** — Return a debug representation of this scorer instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/ai/priority/exceptions.py`

*Module purpose:* Exception hierarchy for the priority scoring subsystem.

#### Class: `PriorityScoringError` (extends `Exception`)

Base exception for all priority scoring failures.

**Functions within the class:**

- **`__init__`** — Initialise the exception with an optional chained cause.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `PriorityScorerNotReadyError` (extends `PriorityScoringError`)

Raised when a scorer is invoked before it has been initialised.

**Functions within the class:**

- **`__init__`** — Initialise with the name of the unready scorer.
  - *Inputs:* `scorer_name`
  - *Output:* `None`

#### Class: `PriorityScoringInputError` (extends `PriorityScoringError`)

Raised when the input provided to a scorer is invalid.

**Functions within the class:**

- **`__init__`** — Initialise with a description of the invalid input.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `PriorityScoringInferenceError` (extends `PriorityScoringError`)

Raised when scoring fails during execution.

**Functions within the class:**

- **`__init__`** — Initialise with the scorer name and a description of the failure.
  - *Inputs:* `scorer_name`, `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `PriorityScoringTimeoutError` (extends `PriorityScoringError`)

Raised when a scoring call exceeds the configured timeout.

**Functions within the class:**

- **`__init__`** — Initialise with the scorer name and the elapsed timeout.
  - *Inputs:* `scorer_name`, `timeout_seconds`
  - *Output:* `None`

#### Class: `LowPriorityConfidenceError` (extends `PriorityScoringError`)

Raised when no scoring outcome meets the minimum confidence threshold.

**Functions within the class:**

- **`__init__`** — Initialise with scoring context that explains the failure.
  - *Inputs:* `scorer_name`, `best_score`, `threshold`
  - *Output:* `None`


---

### `backend/app/infrastructure/ai/priority/factors.py`

*Module purpose:* Deterministic factor scorers used by the priority scoring subsystem.

#### Class: `_BaseFactorScorer` (extends `BasePriorityScorer, ABC`)

Shared deterministic scorer behaviour for standalone priority factors.

**Functions within the class:**

- **`is_ready`** — Return ``True`` because these scorers are stateless and ready by default.
  - *Inputs:* None
  - *Output:* `bool`
- **`_make_factor`** — Create a validated :class:`PriorityFactor` instance.
  - *Inputs:* `*`, `name`, `score`, `weight`, `explanation`
  - *Output:* `PriorityFactor`
- **`load`** — Keep the default no-op lifecycle hook explicit for deterministic scorers.
  - *Inputs:* None
  - *Output:* `None`
- **`unload`** — Keep the default no-op lifecycle hook explicit for deterministic scorers.
  - *Inputs:* None
  - *Output:* `None`

#### Class: `SenderReputationFactor` (extends `_BaseFactorScorer`)

Score emails based on sender address signals that imply sender reputation.

**Functions within the class:**

- **`method_name`** — Return the canonical method name for sender reputation scoring.
  - *Inputs:* None
  - *Output:* `str`
- **`score`** — Score sender reputation signals and return a factor contribution.
  - *Inputs:* `input_data`
  - *Output:* `PriorityFactor`

#### Class: `DeadlineDetectionFactor` (extends `_BaseFactorScorer`)

Score emails that mention deadlines, dates, or time-sensitive language.

**Functions within the class:**

- **`method_name`** — Return the canonical method name for deadline detection scoring.
  - *Inputs:* None
  - *Output:* `str`
- **`score`** — Score deadline-related signals and return a factor contribution.
  - *Inputs:* `input_data`
  - *Output:* `PriorityFactor`

#### Class: `ActionRequiredFactor` (extends `_BaseFactorScorer`)

Score emails that explicitly ask the recipient to act or respond.

**Functions within the class:**

- **`method_name`** — Return the canonical method name for action-required scoring.
  - *Inputs:* None
  - *Output:* `str`
- **`score`** — Score action-request signals and return a factor contribution.
  - *Inputs:* `input_data`
  - *Output:* `PriorityFactor`

#### Class: `ClassificationWeightFactor` (extends `_BaseFactorScorer`)

Score emails using the existing classification category and confidence.

**Attributes / fields:**

- `CLASSIFICATION_BASE_SCORES: Final[dict[str, int]] = {EMAIL_CATEGORY_INTERVIEW: 100, EMAIL_CATEGORY_JOB_OPPORTUNITY: 92, EMAIL_CATEGORY_WORK: 80, EMAIL_CATEGORY_FINANCE: 72, EMAIL_CATEGORY_PERSONAL: 55, EMAIL_CATEGORY_PROMOTION: 30, EMAIL_CATEGORY_NEWSLETTER: 20, EMAIL_CATEGORY_OTHER: 45, EMAIL_CATEGORY_SPAM: 0}`

**Functions within the class:**

- **`method_name`** — Return the canonical method name for classification weighting.
  - *Inputs:* None
  - *Output:* `str`
- **`score`** — Score category weighting and return a factor contribution.
  - *Inputs:* `input_data`
  - *Output:* `PriorityFactor`

#### Module-level functions

- **`_combine_text`** — Build a normalised searchable text blob from the available email fields.
  - *Inputs:* `input_data`
  - *Output:* `str`
- **`_count_matches`** — Count how many distinct keyword signals are present in the text.
  - *Inputs:* `text`, `keywords`
  - *Output:* `int`
- **`_bounded_score`** — Clamp a score to the accepted priority range.
  - *Inputs:* `score`
  - *Output:* `int`


---

### `backend/app/infrastructure/ai/priority/priority_scoring_service.py`

*Module purpose:* Priority scoring orchestration service.

#### Class: `PriorityScoringWeights`

Service-level weights used to combine factor scores.

**Attributes / fields:**

- `sender_reputation: float = 0.3`
- `deadline_detection: float = 0.25`
- `action_required: float = 0.25`
- `classification_weight: float = 0.2`

**Functions within the class:**

- **`__post_init__`** — Validate the configured weights.
  - *Inputs:* None
  - *Output:* `None`
- **`normalize`** — Return weights scaled so their sum equals 1.0.
  - *Inputs:* None
  - *Output:* `'PriorityScoringWeights'`

#### Class: `_ReadySenderReputationFactor` (extends `SenderReputationFactor`)

Adapter that makes the imported factor usable with the base scorer contract.

**Functions within the class:**

- **`is_ready`** — Return ``True`` because the factor is stateless.
  - *Inputs:* None
  - *Output:* `bool`

#### Class: `_ReadyDeadlineDetectionFactor` (extends `DeadlineDetectionFactor`)

Adapter that makes the imported factor usable with the base scorer contract.

**Functions within the class:**

- **`is_ready`** — Return ``True`` because the factor is stateless.
  - *Inputs:* None
  - *Output:* `bool`

#### Class: `_ReadyActionRequiredFactor` (extends `ActionRequiredFactor`)

Adapter that makes the imported factor usable with the base scorer contract.

**Functions within the class:**

- **`is_ready`** — Return ``True`` because the factor is stateless.
  - *Inputs:* None
  - *Output:* `bool`

#### Class: `_ReadyClassificationWeightFactor` (extends `ClassificationWeightFactor`)

Adapter that makes the imported factor usable with the base scorer contract.

**Functions within the class:**

- **`is_ready`** — Return ``True`` because the factor is stateless.
  - *Inputs:* None
  - *Output:* `bool`

#### Class: `PriorityScoringService`

Combine deterministic factor scorers into a final priority score.

**Functions within the class:**

- **`__init__`** — Initialise the service with optional dependency overrides.
  - *Inputs:* `*`, `weights=None`, `sender_reputation_factor=None`, `deadline_detection_factor=None`, `action_required_factor=None`, `classification_weight_factor=None`
  - *Output:* `None`
- **`score`** — Score an email and return a structured priority result.
  - *Inputs:* `email`
  - *Output:* `PriorityScoreResult`
- **`_build_input`** — Convert an email entity into the scoring input contract.
  - *Inputs:* `email`
  - *Output:* `PriorityScoreInput`
- **`_combine_scores`** — Combine factor scores into a final bounded priority score.
  - *Inputs:* `factors`
  - *Output:* `int`


---

### `backend/app/infrastructure/ai/priority/schemas.py`

*Module purpose:* Data-transfer objects and value types for the priority scoring subsystem.

#### Class: `PriorityScoreInput` (extends `BaseModel`)

Carries the signals required to compute an email priority score.

**Attributes / fields:**

- `email_id: UUID = Field(description='Database identifier for the email being scored.')`
- `sender_email: str = Field(min_length=1, description='Sender email address used for reputation-based signals.')`
- `subject: str | None = Field(default=None, description='Email subject line, when available.')`
- `body_text: str | None = Field(default=None, description='Plain-text email body, when available.')`
- `classification: str | None = Field(default=None, description='Current email classification category, when available.')`
- `confidence_score: float | None = Field(default=None, ge=0.0, le=1.0, description='Classification confidence score in the range [0.0, 1.0].')`
- `is_action_required: bool | None = Field(default=None, description='Whether the email has been flagged as action required.')`
- `received_at: datetime = Field(description='UTC timestamp indicating when the email was received.')`
- `model_config = {'str_strip_whitespace': True}`


#### Class: `PriorityFactor` (extends `BaseModel`)

Represents one scored factor contributing to the final priority result.

**Attributes / fields:**

- `name: str = Field(min_length=1, description='Canonical factor name, such as sender reputation or deadline detection.')`
- `score: PriorityScore = Field(description='Factor score in the inclusive range [0, 100].')`
- `weight: PriorityFactorWeight = Field(description='Relative weight assigned to this factor.')`
- `explanation: str | None = Field(default=None, description='Human-readable explanation describing why the factor was assigned.')`
- `model_config = {'frozen': True, 'str_strip_whitespace': True}`


#### Class: `PriorityScoreResult` (extends `BaseModel`)

Encapsulates the output of a single priority scoring invocation.

**Attributes / fields:**

- `email_id: UUID = Field(description='Database identifier for the email that was scored.')`
- `priority_score: PriorityScore = Field(description='Final priority score in the inclusive range [0, 100].')`
- `factors: list[PriorityFactor] = Field(default_factory=list, description='Factor breakdown used to produce the final score.')`
- `method: str = Field(min_length=1, description='Canonical scoring method identifier used to produce this result.')`
- `scored_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc), description='UTC timestamp of when the score was computed.')`
- `model_config = {'frozen': True, 'str_strip_whitespace': True}`



---

### `backend/app/infrastructure/ai/summarization/exceptions.py`

*Module purpose:* Exception hierarchy for the email summarization subsystem.

#### Class: `EmailSummarizationError` (extends `Exception`)

Base exception for all email summarization failures.

**Functions within the class:**

- **`__init__`** — Initialise the exception with an optional chained cause.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `EmailSummaryInputError` (extends `EmailSummarizationError`)

Raised when the input provided to a summarization contract is invalid.

**Functions within the class:**

- **`__init__`** — Initialise with a description of the invalid input.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `EmailSummaryResultValidationError` (extends `EmailSummarizationError`)

Raised when generated summary output cannot be validated.

**Functions within the class:**

- **`__init__`** — Initialise with a description of the validation failure.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`


---

### `backend/app/infrastructure/ai/summarization/schemas.py`

*Module purpose:* Data-transfer objects for the email summarization subsystem.

#### Class: `EmailSummaryRequest` (extends `BaseModel`)

Carries the email content required to generate a structured summary.

**Attributes / fields:**

- `email_id: UUID | None = Field(default=None, description='Optional database identifier for the email being summarised.')`
- `subject: str | None = Field(default=None, description='Email subject line, when available.')`
- `sender: str | None = Field(default=None, description='Sender display name or sender email address, when available.')`
- `body: str | None = Field(default=None, description='Plain-text email body, when available.')`
- `received_at: datetime | None = Field(default=None, description='Optional UTC timestamp indicating when the email was received.')`
- `model_config = {'str_strip_whitespace': True}`

**Functions within the class:**

- **`require_content`** — Ensure the request contains at least one usable content field.
  - *Inputs:* None
  - *Output:* `'EmailSummaryRequest'`

#### Class: `EmailSummaryResult` (extends `BaseModel`)

Encapsulates a structured email summary produced by the AI layer.

**Attributes / fields:**

- `email_id: UUID | None = Field(default=None, description='Optional database identifier for the summarized email.')`
- `summary: SummaryText = Field(description='Concise natural-language summary of the email.')`
- `key_points: list[SummaryPoint] = Field(default_factory=list, description='Important facts or themes extracted from the email.')`
- `action_items: list[ActionItem] = Field(default_factory=list, description='Actionable follow-up items extracted from the email.')`
- `generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc), description='UTC timestamp when the summary was generated.')`
- `model_config = {'frozen': True, 'str_strip_whitespace': True}`

**Functions within the class:**

- **`items_must_not_be_blank`** — Reject blank list entries in structured summary fields.
  - *Inputs:* `value`
  - *Output:* `list[str]`


---

### `backend/app/infrastructure/ai/summarization/summarization_service.py`

*Module purpose:* Email summarization service coordinating LLM provider calls.

#### Class: `SummarizationService`

Orchestrates LLM-backed email summarisation.

**Functions within the class:**

- **`__init__`** — Initialise the service with an LLM provider.
  - *Inputs:* `provider=None`, `*`, `max_retries=3`, `retry_delay=2.0`
  - *Output:* `None`
- **`summarize`** — Generate a structured summary for a single email.
  - *Inputs:* `request`
  - *Output:* `EmailSummaryResult`
- **`_build_summary_request`** — Convert an :class:`EmailSummaryRequest` into a :class:`SummaryRequest`.
  - *Inputs:* `request`
  - *Output:* `SummaryRequest`
- **`_format_user_prompt`** — Assemble the user-facing portion of the LLM prompt.
  - *Inputs:* `*`, `subject`, `sender`, `body`, `received_at`
  - *Output:* `str`
- **`_invoke_with_retry`** — Attempt provider invocation with exponential back-off retry.
  - *Inputs:* `request`
  - *Output:* `SummaryResponse`
- **`_parse_response`** — Parse the raw provider response into a validated :class:`EmailSummaryResult`.
  - *Inputs:* `response`, `*`, `email_id`
  - *Output:* `EmailSummaryResult`
- **`_extract_json`** — Extract and decode a JSON object from LLM output.
  - *Inputs:* `raw_text`
  - *Output:* `dict[str, Any]`
- **`_validate_payload`** — Validate a decoded JSON payload against the :class:`EmailSummaryResult` schema.
  - *Inputs:* `payload`, `*`, `email_id`
  - *Output:* `EmailSummaryResult`
- **`_extract_string_list`** — Extract a list of non-empty strings from a JSON payload field.
  - *Inputs:* `payload`, `key`
  - *Output:* `list[str]`

#### Module-level functions

- **`_placeholder_uuid`** — Return a deterministic nil UUID used when no email identifier is present.
  - *Inputs:* None
  - *Output:* `UUID`


---

### `backend/app/infrastructure/ai/task_extraction/deduplication.py`

*Module purpose:* Task deduplication utilities for the task extraction subsystem.

#### Class: `TaskDeduplicationService`

Remove duplicate and near-duplicate extracted tasks.

**Attributes / fields:**

- `similarity_threshold: int = 90`

**Functions within the class:**

- **`deduplicate`** — Deduplicate tasks based on title and description similarity.
  - *Inputs:* `tasks`
  - *Output:* `list[ExtractedTask]`
- **`_find_match_index`** — Find the index of the best matching existing task.
  - *Inputs:* `candidate`, `existing_tasks`
  - *Output:* `int | None`
- **`_merge_preferred`** — Merge two tasks preserving highest confidence and earliest due date.
  - *Inputs:* `existing`, `incoming`
  - *Output:* `ExtractedTask`
- **`_earliest_due_date`** — Select the task with the earliest due date.
  - *Inputs:* `a`, `b`
  - *Output:* `ExtractedTask`
- **`_similarity_score`** — Compute a combined similarity score for two tasks.
  - *Inputs:* `a`, `b`
  - *Output:* `int`


---

### `backend/app/infrastructure/ai/task_extraction/exceptions.py`

*Module purpose:* Exception hierarchy for the task extraction subsystem.

#### Class: `TaskExtractionError` (extends `Exception`)

Base exception for all task extraction failures.

**Functions within the class:**

- **`__init__`** — Initialise the exception with an optional chained cause.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `TaskExtractionFailureError` (extends `TaskExtractionError`)

Raised when task extraction fails due to an upstream error.

**Functions within the class:**

- **`__init__`** — Initialise the exception.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `TaskExtractionValidationError` (extends `TaskExtractionError`)

Raised when extracted data fails schema validation.

**Functions within the class:**

- **`__init__`** — Initialise the exception.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`

#### Class: `TaskExtractionMalformedResponseError` (extends `TaskExtractionError`)

Raised when the AI provider returns a structurally malformed response.

**Functions within the class:**

- **`__init__`** — Initialise the exception.
  - *Inputs:* `message`, `*`, `cause=None`
  - *Output:* `None`


---

### `backend/app/infrastructure/ai/task_extraction/prompts.py`

*Module purpose:* Prompt builders for task extraction.

#### Class: `TaskExtractionPrompt`

Container for a task-extraction system/user prompt pair.

**Attributes / fields:**

- `system: str`
- `user: str`


#### Module-level functions

- **`build_task_extraction_prompts`** — Build prompts for the task extraction LLM.
  - *Inputs:* `*`, `email_title`, `email_description`, `source_sender`, `source_company=None`
  - *Output:* `TaskExtractionPrompt`


---

### `backend/app/infrastructure/ai/task_extraction/schemas.py`

*Module purpose:* Data-transfer objects for the task extraction subsystem.

#### Class: `TaskExtractionRequest` (extends `BaseModel`)

Carries the context required to extract tasks from an email.

**Attributes / fields:**

- `title: str | None = Field(default=None, description='Email subject or title context, when available.')`
- `description: str | None = Field(default=None, description='Email body/summary context, when available.')`
- `source_sender: str = Field(min_length=1, description='Sender of the source message (email address and/or display name).')`
- `source_company: str | None = Field(default=None, description='Associated company context when available.')`
- `model_config = {'str_strip_whitespace': True}`


#### Class: `ExtractedTask` (extends `BaseModel`)

A single validated task extracted from a source message.

**Attributes / fields:**

- `title: Annotated[str, Field(min_length=1, description='Human-readable task title.')]`
- `description: str | None = Field(default=None, description='Optional longer description of the task.')`
- `priority: PriorityValue = Field(..., description='Task priority score in the inclusive range [0, 100].')`
- `due_date: datetime | None = Field(default=None, description='Optional due date for the task.')`
- `confidence_score: ConfidenceScore = Field(..., description='Extraction confidence in the inclusive range [0.0, 1.0].')`
- `source_sender: str | None = Field(default=None, description='Sender of the source message used as extraction context.')`
- `source_company: str | None = Field(default=None, description='Company of the source message used as extraction context.')`
- `model_config = {'str_strip_whitespace': True, 'frozen': True}`

**Functions within the class:**

- **`validate_priority_values`** — Validate that priority is within the allowed range [0, 100].
  - *Inputs:* `value`
  - *Output:* `int`
- **`validate_confidence_score_range`** — Validate that confidence_score is within [0.0, 1.0].
  - *Inputs:* `value`
  - *Output:* `float`
- **`validate_empty_titles`** — Reject empty or whitespace-only task titles.
  - *Inputs:* `value`
  - *Output:* `str`

#### Class: `TaskExtractionResult` (extends `BaseModel`)

Encapsulates the task extraction output produced by the AI layer.

**Attributes / fields:**

- `tasks: list[ExtractedTask] = Field(default_factory=list, description='List of extracted tasks.')`
- `extraction_confidence: ConfidenceScore = Field(..., description='Overall extraction confidence in the inclusive range [0.0, 1.0].')`
- `extracted_task_count: int = Field(..., description='Total number of extracted tasks.')`
- `model_config = {'frozen': True, 'str_strip_whitespace': True}`

**Functions within the class:**

- **`validate_extracted_task_count`** — Ensure extracted_task_count matches the number of returned tasks.
  - *Inputs:* None
  - *Output:* `'TaskExtractionResult'`

#### Module-level functions

- **`_utcnow`** — Return the current UTC time with timezone information.
  - *Inputs:* None
  - *Output:* `datetime`


---

### `backend/app/infrastructure/ai/task_extraction/task_extraction_service.py`

*Module purpose:* Task extraction service.

#### Class: `TaskExtractionService`

Orchestrates task extraction from an email using an LLM provider.

**Functions within the class:**

- **`__init__`** — Initialise the task extraction service.
  - *Inputs:* `*`, `provider=None`, `provider_factory=None`, `deduplication_service=None`, `settings=None`, `max_retries=None`
  - *Output:* `None`
- **`extract_tasks`** — Extract tasks from an email using the configured LLM provider.
  - *Inputs:* `request`, `*`, `source_title=None`
  - *Output:* `TaskExtractionResult`
- **`_call_provider`** — Call the LLM provider and return the raw model output text.
  - *Inputs:* `provider`, `prompt`
  - *Output:* `str`
- **`_validate_and_process`** — Validate the model payload and post-process deterministically.
  - *Inputs:* `payload`, `request`
  - *Output:* `TaskExtractionResult`

#### Module-level functions

- **`_extract_json_object`** — Extract a JSON object from model output, stripping markdown fences if present.
  - *Inputs:* `text`
  - *Output:* `dict[str, Any]`
- **`_calculate_extraction_confidence`** — Calculate overall extraction confidence as the mean of individual scores.
  - *Inputs:* `tasks`
  - *Output:* `float`


---

## Infrastructure — Auth (`infrastructure/auth/`)

### `backend/app/infrastructure/auth/__init__.py`

*Module purpose:* Google OAuth2 authentication infrastructure package.

_No classes or functions defined (configuration/wiring module)._


---

### `backend/app/infrastructure/auth/auth_service.py`

*Module purpose:* Google OAuth2 Authorization Code Flow service.

#### Class: `AuthorizationURLResult`

Result of building the OAuth2 authorization URL.

**Attributes / fields:**

- `authorization_url: str`
- `state: str`


#### Class: `GoogleUserInfo`

User profile information returned by Google's userinfo endpoint.

**Attributes / fields:**

- `google_id: str`
- `email: str`
- `name: str`
- `picture: str`


#### Class: `TokenSet`

Raw (plaintext) token values returned after code exchange or refresh.

**Attributes / fields:**

- `access_token: str`
- `refresh_token: str`
- `expires_at: datetime`


#### Class: `AuthService`

Orchestrates Google OAuth2 Authentication Code Flow with PKCE.

**Functions within the class:**

- **`__init__`** — Initialise the service with injected repository dependencies.
  - *Inputs:* `user_repo`, `token_repo`
  - *Output:* `None`
- **`build_authorization_url`** — Generate the Google authorization URL and persist the CSRF state.
  - *Inputs:* None
  - *Output:* `AuthorizationURLResult`
- **`handle_callback`** — Process the OAuth2 callback, exchange the code, and upsert the user.
  - *Inputs:* `code`, `state`
  - *Output:* `User`
- **`refresh_access_token`** — Refresh the access token for a user and persist the updated record.
  - *Inputs:* `user_id`
  - *Output:* `OAuthToken`
- **`get_valid_access_token`** — Return a valid plaintext access token, refreshing if necessary.
  - *Inputs:* `user_id`
  - *Output:* `str`
- **`_exchange_code`** — Exchange an authorization code for access and refresh tokens.
  - *Inputs:* `code`, `code_verifier`
  - *Output:* `TokenSet`
- **`_call_token_refresh_endpoint`** — Call the Google token endpoint to refresh an access token.
  - *Inputs:* `credentials`
  - *Output:* `TokenSet`
- **`_upsert_user`** — Create or update the :class:`User` record from Google profile data.
  - *Inputs:* `user_info`
  - *Output:* `User`
- **`_replace_tokens`** — Delete all existing tokens for a user and persist fresh encrypted ones.
  - *Inputs:* `user_id`, `token_set`
  - *Output:* `OAuthToken`

#### Module-level functions

- **`_build_flow`** — Build a :class:`Flow` instance from application configuration.
  - *Inputs:* `redirect_uri=None`
  - *Output:* `Flow`
- **`_fetch_userinfo`** — Fetch the authenticated user's profile from Google's userinfo endpoint.
  - *Inputs:* `access_token`
  - *Output:* `GoogleUserInfo`
- **`_expires_at_from_seconds`** — Compute the UTC expiry datetime from an ``expires_in`` seconds value.
  - *Inputs:* `expires_in`
  - *Output:* `datetime`


---

### `backend/app/infrastructure/auth/oauth_state.py`

*Module purpose:* OAuth2 state and PKCE code-verifier management.

#### Class: `PKCEPair`

Holds a PKCE ``code_verifier`` / ``code_challenge`` pair.

**Attributes / fields:**

- `code_verifier: str`
- `code_challenge: str`
- `code_challenge_method: str = 'S256'`


#### Module-level functions

- **`_redis_client`** — Create a short-lived Redis client from application settings.
  - *Inputs:* None
  - *Output:* `aioredis.Redis`
- **`_state_redis_key`** — Build the Redis key for a given state token.
  - *Inputs:* `state`
  - *Output:* `str`
- **`_verifier_redis_key`** — Build the Redis key for the PKCE verifier paired with a state token.
  - *Inputs:* `state`
  - *Output:* `str`
- **`generate_state_token`** — Generate a cryptographically secure random OAuth2 state token.
  - *Inputs:* None
  - *Output:* `str`
- **`generate_pkce_pair`** — Generate a PKCE ``code_verifier`` / ``code_challenge`` pair.
  - *Inputs:* None
  - *Output:* `PKCEPair`
- **`store_state`** — Persist a state token and its paired PKCE verifier in Redis.
  - *Inputs:* `state`, `code_verifier`
  - *Output:* `None`
- **`validate_and_consume_state`** — Validate a returned OAuth2 state token and retrieve its PKCE verifier.
  - *Inputs:* `state`
  - *Output:* `str`
- **`constant_time_compare`** — Compare two strings in constant time to prevent timing attacks.
  - *Inputs:* `val1`, `val2`
  - *Output:* `bool`


---

### `backend/app/infrastructure/auth/token_encryption.py`

*Module purpose:* Token encryption and decryption facade for the authentication layer.

#### Module-level functions

- **`encrypt_oauth_access_token`** — Encrypt a raw Google OAuth access token for database persistence.
  - *Inputs:* `access_token`
  - *Output:* `str`
- **`decrypt_oauth_access_token`** — Decrypt a Google OAuth access token retrieved from the database.
  - *Inputs:* `ciphertext`
  - *Output:* `str`
- **`encrypt_oauth_refresh_token`** — Encrypt a raw Google OAuth refresh token for database persistence.
  - *Inputs:* `refresh_token`
  - *Output:* `str`
- **`decrypt_oauth_refresh_token`** — Decrypt a Google OAuth refresh token retrieved from the database.
  - *Inputs:* `ciphertext`
  - *Output:* `str`


---

## Infrastructure — Database (`infrastructure/database/`)

### `backend/app/infrastructure/database/base.py`

*Module purpose:* SQLAlchemy declarative base and shared column mixins.

#### Class: `Base` (extends `DeclarativeBase`)

Project-wide declarative base for all ORM models.

**Attributes / fields:**

- `type_annotation_map = {datetime: DateTime(timezone=True), uuid.UUID: UUID(as_uuid=True)}`


#### Class: `TimestampMixin`

Mixin that adds ``created_at`` and ``updated_at`` audit columns.

**Attributes / fields:**

- `created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)`
- `updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)`


#### Class: `UUIDPrimaryKeyMixin`

Mixin that adds a UUID primary key column named ``id``.

**Attributes / fields:**

- `id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)`



---

### `backend/app/infrastructure/database/models/__init__.py`

*Module purpose:* ORM model registry.

_No classes or functions defined (configuration/wiring module)._


---

### `backend/app/infrastructure/database/models/email.py`

*Module purpose:* SQLAlchemy ORM model for the Email entity.

#### Class: `Email` (extends `UUIDPrimaryKeyMixin, TimestampMixin, Base`)

Represents a single Gmail message that has been synced and processed.

**Attributes / fields:**

- `__tablename__ = 'emails'`
- `user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)`
- `gmail_message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)`
- `gmail_thread_id: Mapped[str] = mapped_column(String(255), nullable=False)`
- `sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)`
- `sender_email: Mapped[str] = mapped_column(String(320), nullable=False)`
- `subject: Mapped[str | None] = mapped_column(Text, nullable=True)`
- `body_text: Mapped[str | None] = mapped_column(Text, nullable=True)`
- `body_html: Mapped[str | None] = mapped_column(Text, nullable=True)`
- `snippet: Mapped[str | None] = mapped_column(Text, nullable=True)`
- `received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)`
- `classification: Mapped[str | None] = mapped_column(String(64), nullable=True)`
- `confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)`
- `priority_score: Mapped[int | None] = mapped_column(Integer, nullable=True)`
- `summary: Mapped[str | None] = mapped_column(Text, nullable=True)`
- `is_action_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)`
- `embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)`
- `user: Mapped[User] = relationship('User', back_populates='emails', lazy='select')`
- `tasks: Mapped[list[Task]] = relationship('Task', back_populates='email', cascade='all, delete-orphan', lazy='select')`
- `job_opportunities: Mapped[list[JobOpportunity]] = relationship('JobOpportunity', back_populates='email', cascade='all, delete-orphan', lazy='select')`
- `interviews: Mapped[list[Interview]] = relationship('Interview', back_populates='email', cascade='all, delete-orphan', lazy='select')`
- `classification_audits: Mapped[list[EmailClassificationAudit]] = relationship('EmailClassificationAudit', back_populates='email', cascade='all, delete-orphan', lazy='select')`
- `processing_jobs: Mapped[list[ProcessingJob]] = relationship('ProcessingJob', back_populates='email', cascade='all, delete-orphan', lazy='select')`
- `__table_args__ = (Index('ix_emails_gmail_message_id', 'gmail_message_id', unique=True), Index('ix_emails_gmail_thread_id', 'gmail_thread_id'), Index('ix_emails_sender_email', 'sender_email'), Index('ix_emails_classification', 'classification'), Index('ix_emails_priority_score', 'priority_score'), Index('ix_emails_received_at', 'received_at'), Index('ix_emails_user_id', 'user_id'))`

**Functions within the class:**

- **`__repr__`** — Return a debug representation of the Email instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/database/models/email_classification_audit.py`

*Module purpose:* SQLAlchemy ORM model for the EmailClassificationAudit entity.

#### Class: `EmailClassificationAudit` (extends `UUIDPrimaryKeyMixin, TimestampMixin, Base`)

Records each classification attempt made against an email.

**Attributes / fields:**

- `__tablename__ = 'email_classification_audits'`
- `email_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('emails.id', ondelete='CASCADE'), nullable=False, index=True)`
- `classification_method: Mapped[str] = mapped_column(String(100), nullable=False)`
- `classification_result: Mapped[str] = mapped_column(String(100), nullable=False)`
- `confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)`
- `email: Mapped[Email] = relationship('Email', back_populates='classification_audits', lazy='select')`
- `__table_args__ = (Index('ix_email_classification_audits_email_id', 'email_id'),)`

**Functions within the class:**

- **`__repr__`** — Return a debug representation of the EmailClassificationAudit instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/database/models/email_sync_state.py`

*Module purpose:* SQLAlchemy ORM model for the EmailSyncState entity.

#### Class: `EmailSyncState` (extends `UUIDPrimaryKeyMixin, TimestampMixin, Base`)

Tracks incremental Gmail synchronisation state per user.

**Attributes / fields:**

- `__tablename__ = 'email_sync_states'`
- `user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)`
- `history_id: Mapped[str | None] = mapped_column(String(255), nullable=True)`
- `last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`
- `user: Mapped[User] = relationship('User', back_populates='email_sync_states', lazy='select')`
- `__table_args__ = (Index('ix_email_sync_states_user_id', 'user_id'),)`

**Functions within the class:**

- **`__repr__`** — Return a debug representation of the EmailSyncState instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/database/models/interview.py`

*Module purpose:* SQLAlchemy ORM model for the Interview entity.

#### Class: `Interview` (extends `UUIDPrimaryKeyMixin, TimestampMixin, Base`)

Represents an interview event extracted from an email.

**Attributes / fields:**

- `__tablename__ = 'interviews'`
- `email_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('emails.id', ondelete='CASCADE'), nullable=False, index=True)`
- `company: Mapped[str | None] = mapped_column(String(255), nullable=True)`
- `role: Mapped[str | None] = mapped_column(String(255), nullable=True)`
- `interview_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`
- `meeting_link: Mapped[str | None] = mapped_column(Text, nullable=True)`
- `email: Mapped[Email] = relationship('Email', back_populates='interviews', lazy='select')`
- `__table_args__ = (Index('ix_interviews_email_id', 'email_id'), Index('ix_interviews_company', 'company'), Index('ix_interviews_interview_date', 'interview_date'))`

**Functions within the class:**

- **`__repr__`** — Return a debug representation of the Interview instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/database/models/job_opportunity.py`

*Module purpose:* SQLAlchemy ORM model for the JobOpportunity entity.

#### Class: `JobOpportunity` (extends `UUIDPrimaryKeyMixin, TimestampMixin, Base`)

Represents a job opportunity extracted from an email.

**Attributes / fields:**

- `__tablename__ = 'job_opportunities'`
- `email_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('emails.id', ondelete='CASCADE'), nullable=False, index=True)`
- `company: Mapped[str | None] = mapped_column(String(255), nullable=True)`
- `role: Mapped[str | None] = mapped_column(String(255), nullable=True)`
- `location: Mapped[str | None] = mapped_column(String(255), nullable=True)`
- `salary: Mapped[str | None] = mapped_column(String(255), nullable=True)`
- `apply_link: Mapped[str | None] = mapped_column(Text, nullable=True)`
- `deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`
- `email: Mapped[Email] = relationship('Email', back_populates='job_opportunities', lazy='select')`
- `__table_args__ = (Index('ix_job_opportunities_email_id', 'email_id'), Index('ix_job_opportunities_company', 'company'), Index('ix_job_opportunities_role', 'role'), Index('ix_job_opportunities_deadline', 'deadline'))`

**Functions within the class:**

- **`__repr__`** — Return a debug representation of the JobOpportunity instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/database/models/oauth_token.py`

*Module purpose:* SQLAlchemy ORM model for the OAuthToken entity.

#### Class: `OAuthToken` (extends `UUIDPrimaryKeyMixin, TimestampMixin, Base`)

Stores encrypted OAuth2 tokens for a user's Google account.

**Attributes / fields:**

- `__tablename__ = 'oauth_tokens'`
- `user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)`
- `encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)`
- `encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)`
- `expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)`
- `user: Mapped[User] = relationship('User', back_populates='oauth_tokens', lazy='select')`
- `__table_args__ = (Index('ix_oauth_tokens_user_id', 'user_id'),)`

**Functions within the class:**

- **`__repr__`** — Return a debug representation of the OAuthToken instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/database/models/processing_job.py`

*Module purpose:* SQLAlchemy ORM model for the ProcessingJob entity.

#### Class: `ProcessingJob` (extends `UUIDPrimaryKeyMixin, TimestampMixin, Base`)

Tracks the execution state of a single pipeline stage for an email.

**Attributes / fields:**

- `__tablename__ = 'processing_jobs'`
- `email_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('emails.id', ondelete='CASCADE'), nullable=False, index=True)`
- `pipeline_stage: Mapped[str] = mapped_column(String(100), nullable=False)`
- `status: Mapped[str] = mapped_column(String(50), nullable=False, default=JOB_STATUS_PENDING, server_default=JOB_STATUS_PENDING)`
- `error_message: Mapped[str | None] = mapped_column(Text, nullable=True)`
- `completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`
- `email: Mapped[Email] = relationship('Email', back_populates='processing_jobs', lazy='select')`
- `__table_args__ = (Index('ix_processing_jobs_email_id', 'email_id'), Index('ix_processing_jobs_status', 'status'), Index('ix_processing_jobs_pipeline_stage', 'pipeline_stage'))`

**Functions within the class:**

- **`__repr__`** — Return a debug representation of the ProcessingJob instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/database/models/task.py`

*Module purpose:* SQLAlchemy ORM model for the Task entity.

#### Class: `Task` (extends `UUIDPrimaryKeyMixin, TimestampMixin, Base`)

Represents an actionable task extracted from an email.

**Attributes / fields:**

- `__tablename__ = 'tasks'`
- `email_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('emails.id', ondelete='CASCADE'), nullable=False, index=True)`
- `title: Mapped[str | None] = mapped_column(String(500), nullable=True)`
- `description: Mapped[str | None] = mapped_column(Text, nullable=True)`
- `priority: Mapped[int | None] = mapped_column(Integer, nullable=True)`
- `status: Mapped[str] = mapped_column(String(50), nullable=False, default=TASK_STATUS_PENDING, server_default=TASK_STATUS_PENDING)`
- `due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`
- `email: Mapped[Email] = relationship('Email', back_populates='tasks', lazy='select')`
- `__table_args__ = (Index('ix_tasks_email_id', 'email_id'), Index('ix_tasks_status', 'status'), Index('ix_tasks_due_date', 'due_date'))`

**Functions within the class:**

- **`__repr__`** — Return a debug representation of the Task instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/database/models/user.py`

*Module purpose:* SQLAlchemy ORM model for the User entity.

#### Class: `User` (extends `UUIDPrimaryKeyMixin, TimestampMixin, Base`)

Represents an authenticated user of the platform.

**Attributes / fields:**

- `__tablename__ = 'users'`
- `email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)`
- `name: Mapped[str] = mapped_column(String(255), nullable=False)`
- `google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)`
- `oauth_tokens: Mapped[list[OAuthToken]] = relationship('OAuthToken', back_populates='user', cascade='all, delete-orphan', lazy='select')`
- `emails: Mapped[list[Email]] = relationship('Email', back_populates='user', cascade='all, delete-orphan', lazy='select')`
- `email_sync_states: Mapped[list[EmailSyncState]] = relationship('EmailSyncState', back_populates='user', cascade='all, delete-orphan', lazy='select')`
- `__table_args__ = (Index('ix_users_email', 'email'), Index('ix_users_google_id', 'google_id'))`

**Functions within the class:**

- **`__repr__`** — Return a debug representation of the User instance.
  - *Inputs:* None
  - *Output:* `str`


---

### `backend/app/infrastructure/database/repositories/__init__.py`

*Module purpose:* Concrete repository implementations.

_No classes or functions defined (configuration/wiring module)._


---

### `backend/app/infrastructure/database/repositories/base.py`

*Module purpose:* Generic async base repository providing common CRUD operations.

#### Class: `BaseRepository` (extends `Generic[ModelT]`)

Generic repository that wraps an :class:`AsyncSession`.

**Functions within the class:**

- **`__init__`** — Initialise the repository with an active session and model class.
  - *Inputs:* `session`, `model`
  - *Output:* `None`
- **`get_by_id`** — Fetch a single record by primary key.
  - *Inputs:* `record_id`
  - *Output:* `ModelT | None`
- **`get_all`** — Fetch a paginated list of records with optional filtering and ordering.
  - *Inputs:* `*`, `offset=0`, `limit=20`, `filters=None`, `order_by=None`
  - *Output:* `list[ModelT]`
- **`count`** — Return the total count of records matching optional filters.
  - *Inputs:* `filters=None`
  - *Output:* `int`
- **`create`** — Persist a new model instance.
  - *Inputs:* `instance`
  - *Output:* `ModelT`
- **`update`** — Apply a dictionary of field updates to an existing model instance.
  - *Inputs:* `instance`, `data`
  - *Output:* `ModelT`
- **`delete`** — Delete an existing model instance.
  - *Inputs:* `instance`
  - *Output:* `None`
- **`exists`** — Return True if at least one record matches the given filters.
  - *Inputs:* `filters`
  - *Output:* `bool`


---

### `backend/app/infrastructure/database/repositories/email_repository.py`

*Module purpose:* Repository for Email entity persistence operations.

#### Class: `EmailRepository` (extends `BaseRepository[Email]`)

Provides Email-specific database query operations.

**Functions within the class:**

- **`__init__`** — Initialise the repository with an active async session.
  - *Inputs:* `session`
  - *Output:* `None`
- **`get_by_gmail_message_id`** — Fetch an email by its unique Gmail message identifier.
  - *Inputs:* `gmail_message_id`
  - *Output:* `Email | None`
- **`gmail_message_exists`** — Return True if an email with the given Gmail message ID already exists.
  - *Inputs:* `gmail_message_id`
  - *Output:* `bool`
- **`get_by_user_id`** — Fetch a paginated list of emails belonging to a user.
  - *Inputs:* `user_id`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Email]`
- **`get_by_user_and_classification`** — Fetch emails for a user filtered by classification category.
  - *Inputs:* `user_id`, `classification`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Email]`
- **`get_high_priority`** — Fetch emails for a user whose priority score meets or exceeds a threshold.
  - *Inputs:* `user_id`, `min_priority`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Email]`
- **`get_action_required`** — Fetch emails for a user that require action.
  - *Inputs:* `user_id`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Email]`
- **`get_unclassified`** — Fetch emails that have not yet been classified.
  - *Inputs:* `*`, `offset=0`, `limit=20`
  - *Output:* `list[Email]`
- **`get_by_classification`** — Fetch emails filtered by classification category.
  - *Inputs:* `classification`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Email]`
- **`update_classification`** — Update an email's classification and confidence score.
  - *Inputs:* `gmail_message_id`, `classification`, `confidence_score`
  - *Output:* `Email`
- **`update_confidence_score`** — Update only an email's confidence score.
  - *Inputs:* `gmail_message_id`, `confidence_score`
  - *Output:* `Email`
- **`update_priority_score`** — Update only an email's priority score.
  - *Inputs:* `gmail_message_id`, `priority_score`
  - *Output:* `Email`
- **`update_summary`** — Update only an email's summary text.
  - *Inputs:* `gmail_message_id`, `summary`
  - *Output:* `Email`
- **`get_without_embedding`** — Fetch emails that have no stored pgvector embedding.
  - *Inputs:* `*`, `offset=0`, `limit=20`
  - *Output:* `list[Email]`
- **`get_without_summary`** — Fetch emails that have not yet had a summary generated.
  - *Inputs:* `*`, `offset=0`, `limit=20`
  - *Output:* `list[Email]`
- **`count_by_user`** — Return the total number of emails belonging to a user.
  - *Inputs:* `user_id`
  - *Output:* `int`
- **`count_high_priority_by_user`** — Return the count of high-priority emails for a user.
  - *Inputs:* `user_id`, `min_priority`
  - *Output:* `int`
- **`count_for_user`** — Return the count of emails for a user, optionally filtered by minimum priority score.
  - *Inputs:* `user_id`, `*`, `priority_min=None`
  - *Output:* `int`
- **`list_for_user`** — Fetch paginated emails for a user with optional filters.
  - *Inputs:* `user_id`, `*`, `classification=None`, `priority_min=None`, `offset=0`, `limit=20`
  - *Output:* `tuple[list[Email], int]`
- **`get_for_user`** — See signature.
  - *Inputs:* `email_id`, `user_id`
  - *Output:* `Email | None`


---

### `backend/app/infrastructure/database/repositories/email_sync_state_repository.py`

*Module purpose:* Repository for EmailSyncState entity persistence operations.

#### Class: `EmailSyncStateRepository` (extends `BaseRepository[EmailSyncState]`)

Provides EmailSyncState-specific database query operations.

**Functions within the class:**

- **`__init__`** — Initialise the repository with an active async session.
  - *Inputs:* `session`
  - *Output:* `None`
- **`get_by_user_id`** — Fetch the sync state record for a given user.
  - *Inputs:* `user_id`
  - *Output:* `EmailSyncState | None`
- **`get_or_create_for_user`** — Return the existing sync state for a user, creating one if absent.
  - *Inputs:* `user_id`
  - *Output:* `EmailSyncState`
- **`update_history_id`** — Persist a new Gmail History API cursor for a user.
  - *Inputs:* `user_id`, `history_id`
  - *Output:* `EmailSyncState`
- **`update_last_synced_at`** — Record the wall-clock time of the most recent completed sync.
  - *Inputs:* `user_id`, `synced_at=None`
  - *Output:* `EmailSyncState`


---

### `backend/app/infrastructure/database/repositories/interview_repository.py`

*Module purpose:* Repository for Interview entity persistence operations.

#### Class: `InterviewRepository` (extends `BaseRepository[Interview]`)

Provides Interview-specific database query operations.

**Functions within the class:**

- **`__init__`** — Initialise the repository with an active async session.
  - *Inputs:* `session`
  - *Output:* `None`
- **`get_by_email_id`** — Fetch all interviews linked to a specific email.
  - *Inputs:* `email_id`
  - *Output:* `list[Interview]`
- **`get_upcoming_by_user_emails`** — Fetch upcoming interviews whose date is in the future.
  - *Inputs:* `email_ids`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Interview]`
- **`count_upcoming_by_email_ids`** — Return the count of upcoming interviews across a set of email IDs.
  - *Inputs:* `email_ids`
  - *Output:* `int`
- **`email_has_interview`** — Return True if at least one interview is linked to the given email.
  - *Inputs:* `email_id`
  - *Output:* `bool`
- **`bulk_create`** — Persist multiple Interview records in a single transaction.
  - *Inputs:* `interviews`
  - *Output:* `list[Interview]`
- **`get_upcoming_interviews`** — Fetch upcoming interviews whose date is in the future or unset.
  - *Inputs:* `email_ids`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Interview]`
- **`get_next_interview`** — Return the single nearest upcoming interview across a set of email IDs.
  - *Inputs:* `email_ids`
  - *Output:* `Interview | None`
- **`get_by_user_emails`** — Fetch interviews belonging to a set of email IDs owned by a user.
  - *Inputs:* `email_ids`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Interview]`
- **`list_for_user`** — Fetch all interviews belonging to a user via their emails.
  - *Inputs:* `user_id`, `*`, `offset=0`, `limit=50`
  - *Output:* `list[Interview]`
- **`count_upcoming_for_user`** — Return the count of upcoming interviews for a user via their emails.
  - *Inputs:* `user_id`
  - *Output:* `int`


---

### `backend/app/infrastructure/database/repositories/job_opportunity_repository.py`

*Module purpose:* Repository for JobOpportunity entity persistence operations.

#### Class: `JobOpportunityRepository` (extends `BaseRepository[JobOpportunity]`)

Provides JobOpportunity-specific database query operations.

**Functions within the class:**

- **`__init__`** — Initialise the repository with an active async session.
  - *Inputs:* `session`
  - *Output:* `None`
- **`get_by_email_id`** — Fetch all job opportunities linked to a specific email.
  - *Inputs:* `email_id`
  - *Output:* `list[JobOpportunity]`
- **`get_by_user_emails`** — Fetch job opportunities belonging to a set of email IDs owned by a user.
  - *Inputs:* `email_ids`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[JobOpportunity]`
- **`get_active_by_user_emails`** — Fetch job opportunities whose deadline has not yet passed.
  - *Inputs:* `email_ids`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[JobOpportunity]`
- **`count_active_by_email_ids`** — Return the count of active job opportunities across a set of email IDs.
  - *Inputs:* `email_ids`
  - *Output:* `int`
- **`bulk_create`** — Persist multiple JobOpportunity instances efficiently.
  - *Inputs:* `instances`
  - *Output:* `list[JobOpportunity]`
- **`get_active_opportunities`** — Fetch job opportunities whose deadline has not yet passed.
  - *Inputs:* `*`, `email_ids`, `offset=0`, `limit=20`
  - *Output:* `list[JobOpportunity]`
- **`get_upcoming_deadlines`** — Fetch job opportunities with deadlines upcoming within a time window.
  - *Inputs:* `*`, `email_ids`, `days=14`, `offset=0`, `limit=20`
  - *Output:* `list[JobOpportunity]`
- **`email_has_job_opportunity`** — Return True if at least one job opportunity is linked to the given email.
  - *Inputs:* `email_id`
  - *Output:* `bool`
- **`list_for_user`** — Fetch all job opportunities belonging to a user via their emails.
  - *Inputs:* `user_id`, `*`, `offset=0`, `limit=50`
  - *Output:* `list[JobOpportunity]`
- **`count_active_for_user`** — Return the count of active job opportunities for a user via their emails.
  - *Inputs:* `user_id`
  - *Output:* `int`


---

### `backend/app/infrastructure/database/repositories/oauth_token_repository.py`

*Module purpose:* Repository for OAuthToken entity persistence operations.

#### Class: `OAuthTokenRepository` (extends `BaseRepository[OAuthToken]`)

Provides OAuthToken-specific database query operations.

**Functions within the class:**

- **`__init__`** — Initialise the repository with an active async session.
  - *Inputs:* `session`
  - *Output:* `None`
- **`get_by_user_id`** — Fetch the most recently created OAuth token for a given user.
  - *Inputs:* `user_id`
  - *Output:* `OAuthToken | None`
- **`get_valid_token`** — Fetch an unexpired OAuth token for a given user.
  - *Inputs:* `user_id`
  - *Output:* `OAuthToken | None`
- **`delete_all_for_user`** — Delete all OAuth token records belonging to a user.
  - *Inputs:* `user_id`
  - *Output:* `None`


---

### `backend/app/infrastructure/database/repositories/processing_job_repository.py`

*Module purpose:* Repository for ProcessingJob entity persistence operations.

#### Class: `ProcessingJobRepository` (extends `BaseRepository[ProcessingJob]`)

Provides ProcessingJob-specific database query operations.

**Functions within the class:**

- **`__init__`** — Initialise the repository with an active async session.
  - *Inputs:* `session`
  - *Output:* `None`
- **`get_by_email_id`** — Fetch all processing job records linked to a specific email.
  - *Inputs:* `email_id`
  - *Output:* `list[ProcessingJob]`
- **`get_by_email_and_stage`** — Fetch the processing job for a specific email and pipeline stage.
  - *Inputs:* `email_id`, `pipeline_stage`
  - *Output:* `ProcessingJob | None`
- **`get_by_status`** — Fetch a paginated list of processing jobs filtered by status.
  - *Inputs:* `status`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[ProcessingJob]`
- **`get_failed`** — Fetch a paginated list of processing jobs in a failed state.
  - *Inputs:* `*`, `offset=0`, `limit=20`
  - *Output:* `list[ProcessingJob]`
- **`stage_completed`** — Return True if a pipeline stage has completed successfully for an email.
  - *Inputs:* `email_id`, `pipeline_stage`
  - *Output:* `bool`
- **`mark_completed`** — Set the status of a pipeline stage job to completed.
  - *Inputs:* `email_id`, `pipeline_stage`
  - *Output:* `ProcessingJob | None`
- **`mark_failed`** — Set the status of a pipeline stage job to failed.
  - *Inputs:* `email_id`, `pipeline_stage`, `error_message`
  - *Output:* `ProcessingJob | None`


---

### `backend/app/infrastructure/database/repositories/task_repository.py`

*Module purpose:* Repository for Task entity persistence operations.

#### Class: `TaskRepository` (extends `BaseRepository[Task]`)

Provides Task-specific database query operations.

**Functions within the class:**

- **`__init__`** — Initialise the repository with an active async session.
  - *Inputs:* `session`
  - *Output:* `None`
- **`get_by_email_id`** — Fetch all tasks linked to a specific email.
  - *Inputs:* `email_id`
  - *Output:* `list[Task]`
- **`get_by_status`** — Fetch a paginated list of tasks filtered by status.
  - *Inputs:* `status`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Task]`
- **`get_by_user_emails`** — Fetch tasks belonging to a set of email IDs owned by a user.
  - *Inputs:* `email_ids`, `*`, `offset=0`, `limit=20`
  - *Output:* `list[Task]`
- **`count_pending_by_email_ids`** — Return the count of pending tasks across a set of email IDs.
  - *Inputs:* `email_ids`
  - *Output:* `int`
- **`bulk_create_tasks`** — Bulk insert tasks.
  - *Inputs:* `tasks`
  - *Output:* `None`
- **`get_pending_tasks`** — Fetch pending tasks.
  - *Inputs:* `*`, `offset=0`, `limit=20`
  - *Output:* `list[Task]`
- **`get_high_priority_tasks`** — Fetch high-priority tasks.
  - *Inputs:* `*`, `min_priority`, `offset=0`, `limit=20`
  - *Output:* `list[Task]`
- **`get_due_tasks`** — Fetch due tasks.
  - *Inputs:* `*`, `now`, `offset=0`, `limit=20`
  - *Output:* `list[Task]`
- **`email_has_tasks`** — Return True if at least one task is linked to the given email.
  - *Inputs:* `email_id`
  - *Output:* `bool`
- **`count_for_user`** — Return the count of tasks belonging to a user, optionally filtered by status.
  - *Inputs:* `user_id`, `*`, `status=None`
  - *Output:* `int`
- **`list_for_user`** — Fetch all tasks belonging to a user via their emails.
  - *Inputs:* `user_id`, `*`, `offset=0`, `limit=50`
  - *Output:* `list[Task]`
- **`get_for_user`** — Fetch a single task by ID, verifying ownership through the parent email.
  - *Inputs:* `task_id`, `user_id`
  - *Output:* `Task | None`


---

### `backend/app/infrastructure/database/repositories/user_repository.py`

*Module purpose:* Repository for User entity persistence operations.

#### Class: `UserRepository` (extends `BaseRepository[User]`)

Provides User-specific database query operations.

**Functions within the class:**

- **`__init__`** — Initialise the repository with an active async session.
  - *Inputs:* `session`
  - *Output:* `None`
- **`get_by_email`** — Fetch a user by their unique email address.
  - *Inputs:* `email`
  - *Output:* `User | None`
- **`get_by_google_id`** — Fetch a user by their unique Google OAuth subject identifier.
  - *Inputs:* `google_id`
  - *Output:* `User | None`
- **`email_exists`** — Return True if a user record with the given email already exists.
  - *Inputs:* `email`
  - *Output:* `bool`
- **`google_id_exists`** — Return True if a user record with the given Google ID already exists.
  - *Inputs:* `google_id`
  - *Output:* `bool`


---

### `backend/app/infrastructure/database/session.py`

*Module purpose:* Async SQLAlchemy engine and session factory.

#### Module-level functions

- **`_build_engine_kwargs`** — Build SQLAlchemy engine keyword arguments from settings.
  - *Inputs:* `settings`
  - *Output:* `dict[str, Any]`
- **`get_engine`** — Return the application-wide async SQLAlchemy engine.
  - *Inputs:* None
  - *Output:* `AsyncEngine`
- **`get_session_factory`** — Return the application-wide async session factory.
  - *Inputs:* None
  - *Output:* `async_sessionmaker[AsyncSession]`
- **`get_session`** — Yield a transactional database session.
  - *Inputs:* None
  - *Output:* `AsyncGenerator[AsyncSession, None]`
- **`dispose_engine`** — Dispose the engine connection pool.
  - *Inputs:* None
  - *Output:* `None`


---

## Infrastructure — Gmail (`infrastructure/gmail/`)

### `backend/app/infrastructure/gmail/__init__.py`

*Module purpose:* Gmail infrastructure package.

_No classes or functions defined (configuration/wiring module)._


---

### `backend/app/infrastructure/gmail/client.py`

*Module purpose:* Async Gmail REST API client.

#### Class: `GmailHeader`

A single RFC-2822 header from a Gmail message part.

**Attributes / fields:**

- `name: str`
- `value: str`


#### Class: `GmailMessagePart`

A MIME part of a Gmail message body.

**Attributes / fields:**

- `part_id: str`
- `mime_type: str`
- `filename: str`
- `headers: list[GmailHeader]`
- `body_data: str`
- `body_size: int`
- `parts: list[GmailMessagePart]`


#### Class: `GmailMessage`

A Gmail message resource returned by the Messages API.

**Attributes / fields:**

- `message_id: str`
- `thread_id: str`
- `label_ids: list[str]`
- `snippet: str`
- `history_id: str`
- `internal_date: int`
- `size_estimate: int`
- `payload: GmailMessagePart | None`
- `raw: str`


#### Class: `GmailMessageRef`

A lightweight message reference from list and history responses.

**Attributes / fields:**

- `message_id: str`
- `thread_id: str`


#### Class: `GmailThread`

A Gmail thread resource returned by the Threads API.

**Attributes / fields:**

- `thread_id: str`
- `snippet: str`
- `history_id: str`
- `messages: list[GmailMessage]`


#### Class: `GmailHistoryRecord`

One record in the mailbox history stream.

**Attributes / fields:**

- `history_id: str`
- `messages_added: list[GmailMessageRef]`
- `messages_deleted: list[GmailMessageRef]`
- `labels_added: list[GmailMessageRef]`
- `labels_removed: list[GmailMessageRef]`


#### Class: `GmailHistoryPage`

A page of history records from the History API.

**Attributes / fields:**

- `history: list[GmailHistoryRecord]`
- `next_page_token: str | None`
- `history_id: str`


#### Class: `GmailMessagesPage`

A single page from a messages.list response.

**Attributes / fields:**

- `messages: list[GmailMessageRef]`
- `next_page_token: str | None`
- `result_size_estimate: int`


#### Class: `GmailProfile`

Mailbox profile for the authenticated Gmail user.

**Attributes / fields:**

- `email_address: str`
- `messages_total: int`
- `threads_total: int`
- `history_id: str`


#### Class: `GmailClient`

Async client for the Gmail REST API v1.

**Functions within the class:**

- **`__init__`** — Initialise the client without opening the HTTP transport.
  - *Inputs:* `user_id`, `auth_service`
  - *Output:* `None`
- **`__aenter__`** — Open the underlying HTTP transport.
  - *Inputs:* None
  - *Output:* `GmailClient`
- **`__aexit__`** — Close the underlying HTTP transport.
  - *Inputs:* `*_`
  - *Output:* `None`
- **`fetch_profile`** — Fetch the authenticated user's Gmail mailbox profile.
  - *Inputs:* None
  - *Output:* `GmailProfile`
- **`fetch_message`** — Fetch a single Gmail message by its ID.
  - *Inputs:* `message_id`, `fmt=_DEFAULT_MESSAGE_FORMAT`
  - *Output:* `GmailMessage`
- **`fetch_messages`** — Fetch one page of message references from the user's mailbox.
  - *Inputs:* `*`, `label_ids=None`, `query=None`, `page_token=None`, `max_results=None`, `include_spam_trash=False`
  - *Output:* `GmailMessagesPage`
- **`fetch_thread`** — Fetch a complete Gmail thread including all its messages.
  - *Inputs:* `thread_id`
  - *Output:* `GmailThread`
- **`fetch_history`** — Fetch incremental history records since a given history ID.
  - *Inputs:* `start_history_id`, `*`, `label_id=None`, `history_types=None`, `page_token=None`, `max_results=500`
  - *Output:* `GmailHistoryPage`
- **`_request`** — Execute an authenticated request with retry and refresh logic.
  - *Inputs:* `method`, `path`, `params=None`, `*`, `_retry_count=0`, `_refreshed_token=False`
  - *Output:* `dict[str, Any]`

#### Module-level functions

- **`_parse_header`** — Parse a raw header dict into a :class:`GmailHeader`.
  - *Inputs:* `raw`
  - *Output:* `GmailHeader`
- **`_parse_part`** — Recursively parse a raw MIME part dict into a :class:`GmailMessagePart`.
  - *Inputs:* `raw`
  - *Output:* `GmailMessagePart`
- **`_parse_message`** — Parse a raw message dict into a :class:`GmailMessage`.
  - *Inputs:* `raw`
  - *Output:* `GmailMessage`
- **`_parse_message_ref`** — Parse a lightweight message reference dict.
  - *Inputs:* `raw`
  - *Output:* `GmailMessageRef`
- **`_parse_history_record`** — Parse a raw history record dict into a :class:`GmailHistoryRecord`.
  - *Inputs:* `raw`
  - *Output:* `GmailHistoryRecord`


---

### `backend/app/infrastructure/gmail/sync_service.py`

*Module purpose:* Gmail incremental email synchronisation service.

#### Class: `SyncResult`

Summary of a completed sync run for a single user.

**Attributes / fields:**

- `user_id: uuid.UUID`
- `synced: int`
- `skipped: int`
- `failed: int`
- `history_id: str`
- `full_sync: bool`


#### Class: `EmailSyncService`

Synchronises Gmail messages for a user into the local database.

**Functions within the class:**

- **`__init__`** — Initialise the service with injected collaborators.
  - *Inputs:* `session`, `gmail_client`, `email_repository`, `sync_state_repository`, `email_processing_service`
  - *Output:* `None`
- **`sync`** — Run a full or incremental sync for the given user.
  - *Inputs:* `user_id`
  - *Output:* `SyncResult`
- **`_full_sync`** — Backfill the inbox by paging through ``messages.list``.
  - *Inputs:* `user_id`
  - *Output:* `SyncResult`
- **`_incremental_sync`** — Fetch only new messages since ``start_history_id``.
  - *Inputs:* `user_id`, `start_history_id`
  - *Output:* `SyncResult`
- **`_process_message_refs`** — Hydrate, persist, and AI-process a batch of message references.
  - *Inputs:* `user_id`, `refs`
  - *Output:* `tuple[int, int, int]`

#### Module-level functions

- **`_normalize_message`** — Convert a :class:`GmailMessage` into a persistable :class:`Email` record.
  - *Inputs:* `user_id`, `message`
  - *Output:* `Email`
- **`_collect_headers`** — Build a case-normalised header lookup dict from the message payload.
  - *Inputs:* `message`
  - *Output:* `dict[str, str]`
- **`_parse_from_header`** — Split a raw ``From`` header value into display name and email address.
  - *Inputs:* `raw_from`
  - *Output:* `tuple[str, str]`
- **`_extract_body`** — Recursively decode plain-text and HTML body content from MIME parts.
  - *Inputs:* `part`
  - *Output:* `tuple[str | None, str | None]`
- **`_decode_base64url`** — Decode a base64url-encoded string to UTF-8 text.
  - *Inputs:* `data`
  - *Output:* `str | None`


---

## Application Entrypoint

### `backend/app/main.py`

*Module purpose:* FastAPI application factory and ASGI entrypoint.

#### Module-level functions

- **`lifespan`** — Manage application startup and shutdown lifecycle.
  - *Inputs:* `app`
  - *Output:* `AsyncGenerator[None, None]`
- **`create_app`** — Construct and configure the FastAPI application.
  - *Inputs:* None
  - *Output:* `FastAPI`


---

## Database Migrations (`backend/app/alembic/`)

### `backend/app/alembic/env.py`
*Module purpose:* Alembic migration environment. Loads app settings, rewrites the async DB URL (`postgresql+asyncpg://` → `postgresql://`) for migration use, and points Alembic at `Base.metadata` (importing all ORM models so autogenerate sees every table).

#### Module-level functions
- **`run_migrations_offline`** — Runs migrations in "offline" mode (emits SQL from just a URL, no live DB engine).
  - *Inputs:* None. *Output:* `None`.
- **`run_migrations_online`** — Runs migrations in "online" mode (creates an engine, opens a connection, and applies migrations transactionally).
  - *Inputs:* None. *Output:* `None`.
- *Module dispatch:* calls `run_migrations_offline()` or `run_migrations_online()` based on `context.is_offline_mode()`.

### `backend/app/alembic/versions/ef050afc22bd_initial_migration.py`
*Module purpose:* Initial schema migration (revision `ef050afc22bd`, no down-revision).
- **`upgrade`** — Enables the `vector` extension and creates all tables: `users`, `email_sync_states`, `emails` (incl. `embedding Vector(384)`), `oauth_tokens`, `email_classification_audits`, `interviews`, `job_opportunities`, `tasks`, `processing_jobs`, with their indexes.
  - *Inputs:* None. *Output:* `None`.
- **`downgrade`** — Drops every table and index created by `upgrade` (reverse order).
  - *Inputs:* None. *Output:* `None`.

### `backend/app/alembic/versions/104c85135682_change_in_oauth_token_model.py`
*Module purpose:* Schema change migration (revision `104c85135682`, down-revision `ef050afc22bd`).
- **`upgrade`** — Alters `oauth_tokens.expires_at` from timezone-aware to naive `DateTime`, and changes the `users.google_id` index from unique to non-unique.
  - *Inputs:* None. *Output:* `None`.
- **`downgrade`** — Reverts both changes (restores unique `google_id` index and timezone-aware `expires_at`).
  - *Inputs:* None. *Output:* `None`.

---

# Frontend (`frontend/src/`)

The frontend is a **React 18 + TypeScript** single-page app built with **Vite**. It uses **Material UI (MUI)** for components, **TanStack Query** for server-state/data-fetching, **Zustand** for client auth state, **React Router** for routing, **Axios** for HTTP, and **Framer Motion** for animations. There are no Python-style classes; the equivalent units are **React components**, **custom hooks**, **service functions**, **TypeScript interfaces/types**, and the **Zustand store**. Each is documented below with its inputs (props/params) and outputs (rendered UI / return values).

---

## Application Bootstrap & Routing

### `frontend/src/main.tsx`

*Module purpose:* ASGI-equivalent entrypoint — mounts the React app into the DOM.

#### Module-level code
- Renders the root React tree into `#root`, wrapping `<RouterProvider>` (router) inside `<QueryProvider>` (TanStack Query client) inside `<React.StrictMode>`.
  - *Inputs:* None (reads the `#root` DOM node).
  - *Output:* Mounts the live React application; no return value.

---

### `frontend/src/App.tsx`

*Module purpose:* Root layout component that applies page-transition animations around the routed content.

#### Component: `App`
The root route element. Wraps the active route's `<Outlet />` in a Framer Motion `motion.div` keyed by the current pathname so each route change animates (fade + slide).
- **`App`** — Renders animated wrapper around the current route's outlet.
  - *Inputs:* None (reads `useLocation()` internally).
  - *Output:* JSX — an `<AnimatePresence>` wrapping the routed page.
- *Module constant* `pageVariants` — Framer Motion variant object defining `initial` / `animate` / `exit` opacity+translateY keyframes.

---

### `frontend/src/router/index.tsx`

*Module purpose:* Declares the application's route tree (React Router `createBrowserRouter`) and the authentication guard.

#### Component: `RequireAuth`
Guards a route subtree behind authentication; redirects unauthenticated users to `/login`.
- **`RequireAuth`** — Returns its children only when the user is authenticated.
  - *Inputs:* `{ children: React.ReactNode }`.
  - *Output:* JSX — either the children or a `<Navigate to="/login" replace />`.

#### Module-level exports
- **`router`** — The configured `createBrowserRouter` instance. Public routes: `/login`, `/auth/callback`. Protected routes (wrapped in `RequireAuth` + `AppLayout`): `/` (Dashboard), `/emails`, `/emails/:id`, `/tasks`, `/jobs`, `/interviews`, `/search`. All page components are lazy-loaded via `lazy: () => import(...)`.
  - *Inputs:* None.
  - *Output:* A router object consumed by `<RouterProvider>`.

---

### `frontend/src/layouts/AppLayout.tsx`

*Module purpose:* The persistent authenticated shell — responsive sidebar/drawer navigation, top app bar (mobile), user avatar, and logout.

#### Component: `AppLayout`
Renders the navigation drawer (permanent on desktop, temporary on mobile), the nav links, the signed-in user footer, and a `<main>` region containing the route `<Outlet />`.
- **`AppLayout`** — Renders the app chrome and routed page content.
  - *Inputs:* None (reads auth user from the Zustand store, theme/breakpoints from MUI).
  - *Output:* JSX — full layout with sidebar + main content area.
- **`handleLogout`** (inner) — Calls `POST /auth/logout`, clears local auth state, and navigates to `/login`.
  - *Inputs:* None.
  - *Output:* `Promise<void>`.
- *Module constants:* `DRAWER_WIDTH` (220px), `NAV_ITEMS` (array of `{ label, path, icon }`).
- *Interface* `NavItem` — `{ label: string; path: string; icon: React.ReactNode }`.

---

### `frontend/src/providers/QueryProvider.tsx`

*Module purpose:* Provides the TanStack Query `QueryClient` to the component tree.

#### Component: `QueryProvider`
Creates a single `QueryClient` (memoised via `useState`) with sensible defaults (2-minute stale time, no refetch on focus, retry up to 2× except on 401/403/404) and wraps children in `<QueryClientProvider>`.
- **`QueryProvider`** — Supplies the query client to descendants.
  - *Inputs:* `{ children: ReactNode }` (interface `QueryProviderProps`).
  - *Output:* JSX — `<QueryClientProvider>` wrapping children.

---

## Client State

### `frontend/src/store/authStore.tsx`

*Module purpose:* Zustand store holding the authenticated user, persisted to `sessionStorage`.

#### Interface: `AuthUser`
The authenticated user shape. Fields: `id: string`, `email: string`, `name: string | null`.

#### Interface: `AuthState`
Store contract: `user: AuthUser | null`, `isAuthenticated: boolean`, `setUser(user)`, `clearAuth()`.

#### Store: `useAuthStore`
A persisted Zustand hook (key `"auth-store"`, `sessionStorage`). Exposes the auth state and its mutators.
- **`setUser`** — Stores the user and sets `isAuthenticated = true`.
  - *Inputs:* `user: AuthUser`. *Output:* `void`.
- **`clearAuth`** — Resets user to `null` and `isAuthenticated` to `false`.
  - *Inputs:* None. *Output:* `void`.

---

### `frontend/src/hooks/useAuth.ts`

*Module purpose:* Custom hooks encapsulating the OAuth login, callback, and logout flows.

#### Hook: `useLogin`
Provides login initiation: fetches the Google OAuth2 authorization URL and redirects the browser to it.
- **`useLogin`** — Returns `{ initiateLogin, isLoading, error }` (interface `UseLoginResult`).
  - *Inputs:* None.
  - *Output:* `UseLoginResult`. `initiateLogin(): Promise<void>` performs the redirect.

#### Hook: `useAuthCallback`
Handles post-OAuth-callback session hydration — calls `GET /auth/me` and persists the user into the Zustand store.
- **`useAuthCallback`** — Returns `{ resolveCallback, isLoading, error }` (interface `UseCallbackResult`).
  - *Inputs:* None.
  - *Output:* `UseCallbackResult`. `resolveCallback(): Promise<void>` hydrates the store.

#### Hook: `useLogout`
Clears the server session cookie and wipes local auth state, then redirects to `/login`.
- **`useLogout`** — Returns `{ logout, isLoading }` (interface `UseLogoutResult`).
  - *Inputs:* None.
  - *Output:* `UseLogoutResult`. `logout(): Promise<void>`.

---

## API Service Layer

### `frontend/src/services/api/client.ts`

*Module purpose:* Configures the shared Axios instance and centralised error handling.

#### Module-level functions
- **`createApiClient`** — Builds an Axios instance (base URL from `VITE_API_BASE_URL`, `withCredentials: true`, 30s timeout, JSON headers). A response interceptor redirects to `/login` and clears auth on HTTP 401, and normalises all errors.
  - *Inputs:* None. *Output:* `AxiosInstance`.
- **`normalizeError`** — Converts an `AxiosError` into a uniform `ApiError`.
  - *Inputs:* `error: AxiosError`. *Output:* `ApiError`.
- **`apiClient`** — The singleton Axios instance used by every API module.

#### Interface: `ApiError`
`{ status: number; message: string }`.

---

### `frontend/src/services/api/types.ts`

*Module purpose:* Central TypeScript type definitions mirroring the backend's Pydantic response/request schemas. Contains no executable code — only interfaces consumed across the app.

#### Interfaces (inputs/outputs of the API functions)
- **`LoginResponse`** — `{ authorization_url: string }`.
- **`CallbackResponse`** — `{ success: boolean }`.
- **`DashboardResponse`** — `{ total_emails, important_emails, pending_tasks, upcoming_interviews, active_jobs: number }`.
- **`EmailSummary`** — Lightweight email row: `id, subject, sender_name, sender_email, received_at, classification, confidence_score, priority_score, summary, is_action_required, snippet` (nullable where applicable).
- **`EmailDetail`** — Extends `EmailSummary` with `body_text, body_html, gmail_message_id, gmail_thread_id`.
- **`EmailListResponse`** — `{ items: EmailSummary[]; total; page; page_size }`.
- **`EmailListParams`** — Optional query filters `{ classification?, priority_min?, page?, page_size? }`.
- **`Task`** — `{ id, email_id, title, description, priority, status, due_date }`.
- **`TaskListResponse`** — `{ items: Task[] }`.
- **`TaskUpdateRequest`** — Optional `{ status?, priority?, due_date? }`.
- **`TaskUpdateResponse`** — `{ success: boolean }`.
- **`JobOpportunity`** — `{ id, email_id, company, role, location, salary, apply_link, deadline }`.
- **`JobListResponse`** — `{ items: JobOpportunity[] }`.
- **`Interview`** — `{ id, email_id, company, role, interview_date, meeting_link }`.
- **`InterviewListResponse`** — `{ items: Interview[] }`.
- **`SearchResult`** / **`SearchResponse`** / **`SearchParams`** — Semantic search result shapes (`email_id, subject, sender_email, received_at, summary, score`; `{ items, query }`; `{ q, limit? }`).
- **`SyncResponse`** — `{ synced: number; skipped: number }`.
- **`PaginationMeta`** — `{ total, page, page_size }`.

---

### `frontend/src/services/api/authApi.ts`
*Module purpose:* Auth-related HTTP calls.
- **`fetchLoginUrl`** — `GET /auth/login`; returns the Google OAuth2 authorization URL.
  - *Inputs:* None. *Output:* `Promise<string>`.
- **`fetchCurrentUser`** — `GET /auth/me`; returns the authenticated user (relies on the session cookie; throws 401 if absent).
  - *Inputs:* None. *Output:* `Promise<AuthUser>`.
- **`postLogout`** — `POST /auth/logout`; clears the server session.
  - *Inputs:* None. *Output:* `Promise<void>`.

### `frontend/src/services/api/dashboardApi.ts`
- **`fetchDashboard`** — `GET /dashboard`; returns aggregated counts.
  - *Inputs:* None. *Output:* `Promise<DashboardResponse>`.

### `frontend/src/services/api/emailApi.ts`
- **`fetchEmails`** — `GET /emails`; paginated, optionally filtered list.
  - *Inputs:* `params: EmailListParams = {}`. *Output:* `Promise<EmailListResponse>`.
- **`fetchEmailById`** — `GET /emails/{id}`; full email detail.
  - *Inputs:* `emailId: string`. *Output:* `Promise<EmailDetail>`.

### `frontend/src/services/api/interviewApi.ts`
- **`fetchInterviews`** — `GET /interviews`; all extracted interviews.
  - *Inputs:* None. *Output:* `Promise<InterviewListResponse>`.

### `frontend/src/services/api/jobApi.ts`
- **`fetchJobs`** — `GET /jobs`; all extracted job opportunities.
  - *Inputs:* None. *Output:* `Promise<JobListResponse>`.

### `frontend/src/services/api/taskApi.ts`
- **`fetchTasks`** — `GET /tasks`; all extracted tasks.
  - *Inputs:* None. *Output:* `Promise<TaskListResponse>`.
- **`updateTask`** — `PATCH /tasks/{id}`; partial update of status/priority/due date.
  - *Inputs:* `taskId: string`, `payload: TaskUpdateRequest`. *Output:* `Promise<TaskUpdateResponse>`.

---

## Pages (route components)

> Each page exports a `Component` (and a default export) consumed by React Router's lazy loader.

### `frontend/src/pages/Auth/CallbackPage.tsx`
#### Component: `Component` (OAuth callback landing)
After Google redirects back (cookie already set by backend), calls `useAuthCallback().resolveCallback()` exactly once (guarded by a `useRef`) to hydrate the user, then navigates to `/`. Shows a spinner, or an error alert with a "Try again" link.
- *Inputs:* None (route component). *Output:* JSX.

### `frontend/src/pages/Auth/LoginPage.tsx`
#### Component: `Component` (login screen)
Full-page login card with the `LoginButton`. Redirects already-authenticated users to `/`.
- *Inputs:* None. *Output:* JSX.

### `frontend/src/pages/Dashboard/DashboardPage.tsx`
#### Component: `Component` (dashboard overview)
Fetches `GET /dashboard` via TanStack Query and composes `<StatsCards>` + `<ImportantEmailsWidget>`. Owns heading + layout only.
- *Inputs:* None. *Output:* JSX.

### `frontend/src/pages/Emails/EmailsPage.tsx`
#### Component: `Component` (paginated email list)
Table of emails with classification and minimum-priority filters and pagination. Clicking a row navigates to the detail page.
- *Inputs:* None. *Output:* JSX.
- **`formatDate`** (helper) — Formats an ISO date to a short locale string.
  - *Inputs:* `iso: string`. *Output:* `string`.
- *Constants:* `PAGE_SIZE = 20`, `CLASSIFICATIONS` (label list).

### `frontend/src/pages/Emails/EmailDetailPage.tsx`
#### Component: `Component` (email detail)
Fetches one email by UUID (`GET /emails/{id}`) and composes `<EmailHeader>`, `<EmailSummaryCard>`, `<EmailBodyViewer>`. Owns data-fetching/loading/error only.
- *Inputs:* None (reads `:id` route param). *Output:* JSX.

### `frontend/src/pages/Interviews/InterviewsPage.tsx`
#### Component: `Component` — heading + `<InterviewList>`. *Inputs:* None. *Output:* JSX.

### `frontend/src/pages/Jobs/JobsPage.tsx`
#### Component: `Component` — heading + `<JobList>`. *Inputs:* None. *Output:* JSX.

### `frontend/src/pages/Tasks/TasksPage.tsx`
#### Component: `Component` — heading + `<TaskList>`. *Inputs:* None. *Output:* JSX.

### `frontend/src/pages/Search/SearchPage.tsx`
> **Empty file / unimplemented stub.** The `/search` route is declared and a backend `routes/search.py` stub exists, but no UI is implemented yet.

---

## Components

### `frontend/src/components/auth/LoginButton.tsx`
#### Component: `LoginButton`
Google sign-in button; on click triggers `useLogin().initiateLogin()` (redirect to consent screen). Shows a spinner while redirecting.
- *Inputs:* None. *Output:* JSX (MUI `<Button>`).

### `frontend/src/components/dashboard/StatCard.tsx`
#### Component: `StatCard`
A single dashboard metric card with a label, numeric value, icon, optional accent border, and skeleton loading state.
- *Inputs:* `StatCardProps` — `{ label: string; value: number | undefined; icon: React.ReactNode; isLoading: boolean; accentColor?: string; sx?: SxProps<Theme> }`.
- *Output:* JSX (MUI `<Card>`).

### `frontend/src/components/dashboard/StatsCards.tsx`
#### Component: `StatsCards`
Renders the five-card metrics grid (total emails, important, pending tasks, upcoming interviews, active jobs) from a `DashboardResponse`.
- *Inputs:* `StatsCardsProps` — `{ data: DashboardResponse | undefined; isLoading: boolean; isError: boolean }`.
- *Output:* JSX (grid of `StatCard`s, error alert when `isError`).

### `frontend/src/components/dashboard/ImportantEmailsWidget.tsx`
#### Component: `ImportantEmailsWidget`
Fetches up to 10 emails with `priority_min = 70` and renders them as a list of clickable rows linking to detail pages.
- *Inputs:* None. *Output:* JSX (MUI `<Card>` list).
- **`truncate`** — Truncates text to a max length with an ellipsis. *Inputs:* `text: string, max: number`. *Output:* `string`.
- **`EmailRowSkeleton`** — Loading placeholder row. *Inputs:* None. *Output:* JSX.
- **`EmailRow`** — Single email row (subject, sender, classification + priority chips, summary). *Inputs:* `{ email: EmailSummary }` (`EmailRowProps`). *Output:* JSX.
- *Constants:* `DISPLAY_LIMIT = 10`, `PRIORITY_MIN = 70`.

### `frontend/src/components/emails/EmailHeader.tsx`
#### Component: `EmailHeader`
Renders an email's subject, sender, received date/time, and a back button; skeletons while loading.
- *Inputs:* `EmailHeaderProps` — `{ email: EmailDetail | undefined; isLoading: boolean }`.
- *Output:* JSX.
- **`formatDateTime`** — ISO → full locale date/time string. *Inputs:* `iso: string`. *Output:* `string`.

### `frontend/src/components/emails/EmailSummaryCard.tsx`
#### Component: `EmailSummaryCard`
Displays the AI-derived metadata for an email: classification, confidence bar, priority, action-required flag, and the AI summary.
- *Inputs:* `EmailSummaryCardProps` — `{ email: EmailDetail | undefined; isLoading: boolean }`.
- *Output:* JSX.
- **`MetaRow`** — Labelled metadata row. *Inputs:* `MetaRowProps` `{ label: string; children: React.ReactNode }`. *Output:* JSX.
- **`ConfidenceBar`** — Renders a 0–1 confidence score as a progress bar. *Inputs:* `{ score: number | null }`. *Output:* JSX.

### `frontend/src/components/emails/EmailBodyViewer.tsx`
#### Component: `EmailBodyViewer`
Renders the email body — sandboxed HTML inside an iframe (`srcDoc`) when available, otherwise a plain-text fallback; supports toggling between HTML and text view modes.
- *Inputs:* `EmailBodyViewerProps` — `{ email: EmailDetail | undefined; isLoading: boolean }`.
- *Output:* JSX.
- **`buildSrcDoc`** — Wraps raw HTML in a safe document shell (preserves full documents as-is). *Inputs:* `html: string`. *Output:* `string` (iframe srcDoc).
- **`HtmlBodyFrame`** — Sandboxed iframe renderer. *Inputs:* `{ html: string }`. *Output:* JSX.
- **`TextBody`** — Plain-text renderer. *Inputs:* `{ text: string }`. *Output:* JSX.
- *Type:* `ViewMode = "html" | "text"`.

### `frontend/src/components/emails/EmailClassificationChip.tsx`
#### Component: `EmailClassificationChip`
A coloured MUI `<Chip>` for a classification label (colour keyed per category).
- *Inputs:* `EmailClassificationChipProps` — `{ classification: string | null; size?: ChipProps["size"] }`.
- *Output:* JSX (or `null` when no classification).
- *Constant:* `CLASSIFICATION_COLOUR` — `Record<string, ChipColor>` mapping labels → colours.

### `frontend/src/components/emails/EmailPriorityChip.tsx`
#### Component: `EmailPriorityChip`
A `<Chip>` showing the numeric priority score plus its tier (Critical ≥80 / High ≥60 / Medium ≥40 / Low). Null → neutral "—".
- *Inputs:* `EmailPriorityChipProps` — `{ priorityScore: number | null; size?: ChipProps["size"] }`.
- *Output:* JSX.
- **`resolveTier`** — Maps a score to `{ label, color }`. *Inputs:* `score: number`. *Output:* `PriorityTier`.
- *Interface:* `PriorityTier` — `{ label: string; color: ChipProps["color"] }`.

### `frontend/src/components/interviews/InterviewCard.tsx`
#### Component: `InterviewCard`
Compact card for one interview: company, role, date/time, countdown chip, and a Join button (disabled for past interviews).
- *Inputs:* `InterviewCardProps` — `{ interview: Interview }`.
- *Output:* JSX.
- **`formatDateTime`** — ISO → locale date/time or "—". *Inputs:* `iso: string | null`. *Output:* `string`.
- **`daysUntil`** — Whole days until a future date, else `null`. *Inputs:* `iso: string | null`. *Output:* `number | null`.
- **`countdownAppearance`** — Maps days-remaining to `{ label, color }`. *Inputs:* `days: number | null`. *Output:* `{ label; color }`.

### `frontend/src/components/interviews/InterviewList.tsx`
#### Component: `InterviewList`
Fetches `GET /interviews`, sorts by nearest date, and renders a grid of `InterviewCard`s with loading skeletons / empty / error states.
- *Inputs:* None. *Output:* JSX.
- **`sortInterviews`** — Sorts by `interview_date` ascending (nulls last). *Inputs:* `Interview[]`. *Output:* `Interview[]`.
- **`InterviewCardSkeleton`** — Loading placeholder. *Inputs:* None. *Output:* JSX.

### `frontend/src/components/jobs/JobCard.tsx`
#### Component: `JobCard`
Compact card for one job opportunity: company, role, location, salary, deadline, and an apply link (opens new tab). Past deadlines render in an error colour.
- *Inputs:* `JobCardProps` — `{ job: JobOpportunity }`.
- *Output:* JSX.
- **`formatDate`** — ISO → short locale date or "—". *Inputs:* `iso: string | null`. *Output:* `string`.
- **`isPastDeadline`** — True when the deadline is in the past. *Inputs:* `iso: string | null`. *Output:* `boolean`.

### `frontend/src/components/jobs/JobList.tsx`
#### Component: `JobList`
Fetches `GET /jobs`, sorts by nearest deadline, renders a grid of `JobCard`s with skeleton/empty/error states.
- *Inputs:* None. *Output:* JSX.
- **`sortJobs`** — Sorts by `deadline` ascending (nulls last). *Inputs:* `JobOpportunity[]`. *Output:* `JobOpportunity[]`.
- **`JobCardSkeleton`** — Loading placeholder. *Inputs:* None. *Output:* JSX.

### `frontend/src/components/tasks/TaskCard.tsx`
#### Component: `TaskCard`
Compact card for one task: title, description, due date, priority badge, status chip, and an inline `TaskStatusSelect`. Overdue, non-done tasks get a warning border.
- *Inputs:* `TaskCardProps` — `{ task: Task }`.
- *Output:* JSX.
- **`formatDate`** — ISO → short locale date or "—". *Inputs:* `iso: string | null`. *Output:* `string`.
- **`resolvePriority`** — Maps a numeric priority to `{ label, color }` (Critical/High/Medium/Low). *Inputs:* `priority: number | null`. *Output:* `{ label; color }`.

### `frontend/src/components/tasks/TaskList.tsx`
#### Component: `TaskList`
Fetches `GET /tasks`, sorts by priority desc then due date asc, renders a grid of `TaskCard`s with skeleton/empty/error states.
- *Inputs:* None. *Output:* JSX.
- **`sortTasks`** — Priority desc, due-date asc tiebreak (nulls last). *Inputs:* `Task[]`. *Output:* `Task[]`.
- **`TaskCardSkeleton`** — Loading placeholder. *Inputs:* None. *Output:* JSX.

### `frontend/src/components/tasks/TaskStatusSelect.tsx`
#### Component: `TaskStatusSelect`
Inline status dropdown for a task. On change, fires `PATCH /tasks/{id}` (TanStack mutation) and invalidates the `"tasks"` query; shows a spinner and disables during the update.
- *Inputs:* `TaskStatusSelectProps` — `{ task: Task }`.
- *Output:* JSX.
- **`statusChipColor`** — Maps a status string to a MUI chip colour. *Inputs:* `status: string | null`. *Output:* `"default" | "primary" | "success" | "error"`.
- *Exports:* `TASK_STATUS_OPTIONS` (`["pending","in_progress","done","cancelled"]`), type `TaskStatus`.

### `frontend/src/components/ui/EmptyState.tsx`
*Module purpose:* Reusable empty-state placeholders.
- **`EmptyState`** — Base empty state with icon, title, description, optional action. *Inputs:* `EmptyStateProps` `{ icon: LucideIcon; title; description; action?; className?; size? }`. *Output:* JSX.
- **`EmptyEmails` / `EmptyTasks` / `EmptyJobs` / `EmptyInterviews` / `EmptyDocuments` / `EmptyNotifications` / `EmptyGeneric`** — Domain-specific presets. *Inputs:* `{ action?: React.ReactNode }` (varies). *Output:* JSX.
- **`EmptySearch`** — Search empty state. *Inputs:* `{ query?: string }`. *Output:* JSX.

### `frontend/src/components/ui/Skeleton.tsx`
*Module purpose:* Skeleton-loading primitives and composed skeletons.
- **`Skeleton`** — Base skeleton block. *Inputs:* `{ className?; style? }`. *Output:* JSX.
- **`SkeletonText` / `SkeletonTextSm` / `SkeletonTitle`** — Text-line skeletons. *Inputs:* `{ width?; className? }`. *Output:* JSX.
- **`SkeletonAvatar` / `SkeletonBadge` / `SkeletonBtn` / `SkeletonIcon`** — Shape skeletons. *Inputs:* size/none. *Output:* JSX.
- **`SkeletonEmailRow` / `SkeletonEmailList` / `SkeletonTaskRow` / `SkeletonTaskList` / `SkeletonJobCard` / `SkeletonJobGrid` / `SkeletonInterviewCard` / `SkeletonInterviewGrid` / `SkeletonStatCard` / `SkeletonStatsGrid` / `SkeletonSearchResult` / `SkeletonSearchResults` / `SkeletonPage`** — Composed skeletons matching specific layouts. *Inputs:* optional `{ rows?/count? }`. *Output:* JSX.

### `frontend/src/components/ui/Motion.tsx`
*Module purpose:* Framer-Motion animation variants and wrapper components.
- *Exports (variant objects):* `listContainerVariants`, `listItemVariants`, `fadeInVariants`, `cardHoverProps`.
- **`PageTransition`** — Wraps a page root for enter/exit transition. *Inputs:* `{ children }`. *Output:* JSX.
- **`AnimatedList`** — Staggered-children container. *Inputs:* `{ children; className?; style? }`. *Output:* JSX.
- **`AnimatedItem`** — Single animated list item. *Inputs:* `{ children; className?; style? }`. *Output:* JSX.
- **`FadeIn`** — Simple fade-in wrapper. *Inputs:* `{ children; delay?; className?; style? }`. *Output:* JSX.
- **`RouteTransitions`** — `AnimatePresence` wrapper keyed by route. *Inputs:* `{ children }`. *Output:* JSX.

---

## Utilities & Config

### `frontend/src/lib/utils.ts`
- **`cn`** — Merges class names via `clsx` + `tailwind-merge`. *Inputs:* `...inputs: ClassValue[]`. *Output:* `string`.

### `frontend/vite.config.ts`
*Module purpose:* Vite build/dev config. Proxies `/api` → `http://localhost:8000` in dev. No exported functions.

### `frontend/src/App.css`, `frontend/src/index.css`
Global stylesheets (no executable code).
