# AI Email Intelligence Platform

## Objective

Build a production-quality AI Email Intelligence Platform that:

- Connects to Gmail via OAuth2.
- Syncs and stores emails.
- Classifies emails.
- Scores email importance.
- Generates summaries.
- Extracts tasks.
- Extracts job and interview information.
- Provides semantic search.
- Exposes functionality through a React dashboard.

Tech Stack

Backend:
- Python 3.13+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- pgvector
- Redis
- Celery
- Pydantic v2

Frontend:
- React
- TypeScript
- Vite
- Material UI
- TanStack Query
- Zustand
- React Router

AI:
- sentence-transformers/all-MiniLM-L6-v2
- facebook/bart-large-mnli
- Provider abstraction for OpenAI, Claude, and Gemini

---

# Global Rules

## Architecture

- Use Clean Architecture.
- Use layered architecture.
- Use dependency injection wherever appropriate.
- Keep business logic isolated from API routes.
- Keep Gmail integration isolated from business logic.
- Keep AI services isolated from business logic.
- Every component must be modular and independently testable.
- Design for maintainability and extensibility.
- Favor composition over inheritance.
- Avoid tightly coupled modules.

---

## Code Quality

- Every function must contain a docstring.
- Use strong typing throughout the codebase.
- Keep files small.
- Keep classes small.
- Keep functions small.
- Follow single responsibility principles.
- Prefer interfaces, abstractions, and clear boundaries.
- Generate production-quality code only.

Never generate:

```python
pass
```

```python
# TODO
```

```python
raise NotImplementedError
```

unless explicitly requested.

Do not generate placeholder implementations.

Do not generate mock implementations unless explicitly requested.

Generate complete working implementations for the current phase.

---

## Security

OAuth:

- Use OAuth2 Authorization Code Flow.
- Implement token refresh support.
- Store tokens securely.
- Encrypt sensitive token data before persistence.
- Use least-privilege scopes.

Allowed Gmail Scope:

```text
gmail.readonly
```

Secrets:

- Read all secrets from `.env`.
- Never hardcode secrets.

Database:

- Use SQLAlchemy ORM.
- Use parameterized queries only.
- Prevent SQL injection.

Frontend:

- Prevent XSS.
- Never use unsafe HTML rendering.

API:

- Validate all inputs.
- Implement request size limits.
- Implement rate limiting.

Logging:

Never log:

- Access tokens
- Refresh tokens
- Email content
- Personally identifiable information

---

# Token Optimization Rules

These rules override all other instructions.

Generate only requested artifacts.

Do not generate:

- Diagrams
- Mermaid
- UML
- Flowcharts
- Architecture visualizations
- Data flow visualizations
- Component visualizations
- ASCII art
- Explanations
- Tutorials
- Walkthroughs
- Design discussions
- Tradeoff discussions
- Educational content
- Best-practice discussions
- Executive summaries
- Handoff documents
- Retrospectives
- Long-form documentation

Perform all reasoning internally.

Output final artifacts only.

---

# Output Format

## Architecture Phases

Generate only:

1. Database schema
2. Backend folder structure
3. Frontend folder structure
4. API contracts

Nothing else.

---

## Implementation Phases

Generate only:

1. Files created
2. File contents

Format:

```text
filepath

<complete file contents>
```

Do not include:

- Introductions
- Conclusions
- Explanations
- Notes
- Recommendations
- Future considerations

Stop immediately when the requested phase is complete.

---

# Refactoring Rules

Do not regenerate existing files unless:

- A dependency changes.
- A bug fix requires modification.
- Explicitly requested.

Generate only new or modified files.

Avoid regenerating unchanged code.

---

# Development Workflow

Complete one phase at a time.

Do not automatically continue.

Wait for:

```text
Start Phase X
```

before proceeding.

Before generating output:

- Consider security implications.
- Consider maintainability implications.
- Consider scalability implications.
- Consider testing implications.
- Consider failure scenarios.
- Consider future phase dependencies.

Perform this reasoning internally.

Do not output reasoning.

---

# Phase 1

Generate only:

## Database Schema

Include:

- Tables
- Fields
- Relationships
- Constraints
- Indexes

Minimum entities:

### User

- id
- email
- name
- google_id
- created_at
- updated_at

### OAuthToken

- id
- user_id
- access_token
- refresh_token
- expires_at

### Email

- id
- gmail_message_id
- thread_id
- sender_name
- sender_email
- subject
- body
- received_at
- classification
- confidence_score
- priority_score
- summary
- is_action_required
- created_at

### Task

- id
- email_id
- title
- description
- status
- due_date

### JobOpportunity

- id
- email_id
- company
- role
- location
- salary
- apply_link
- deadline

### Interview

- id
- email_id
- company
- role
- interview_date
- meeting_link

Generate:

- Database schema
- Backend folder structure
- Frontend folder structure
- API contracts

No implementation code.

Stop.

---

# Phase 2

Generate:

- FastAPI application setup
- Configuration management
- Environment handling
- Logging
- SQLAlchemy setup
- Database session management
- Dependency injection layer
- Base repository layer

No Gmail integration.

No AI implementation.

Generate working code only.

Stop.

---

# Phase 3

Generate:

- SQLAlchemy models
- Relationships
- Constraints
- Indexes
- Alembic migrations
- Repository implementations
- CRUD foundations

Architecture must be unit-test friendly.

Generate working code only.

Stop.

---

# Phase 4

Generate:

- Google OAuth login flow
- OAuth callback flow
- Token persistence
- Token refresh support
- GmailClient
- EmailSyncService

Requirements:

- Real Google OAuth implementation
- No simulated authentication
- No placeholders
- Incremental synchronization
- Duplicate prevention
- gmail_message_id uniqueness enforcement

Generate working code only.

Stop.

---

# Phase 5

Generate:

ClassificationService

Layer 1:

- all-MiniLM-L6-v2 embeddings

Layer 2:

- bart-large-mnli zero-shot classification

Layer 3:

- LLM fallback

Categories:

- Work
- Interview
- Job Opportunity
- Finance
- Personal
- Promotion
- Newsletter
- Spam
- Other

Persist:

- category
- confidence_score

Requirements:

- Real HuggingFace model integration
- No mocked classification logic
- Configurable confidence thresholds

Generate working code only.

Stop.

---

# Phase 6

Generate:

PriorityScoringService

Factors:

- Sender reputation
- Deadline detection
- Action-required detection
- Classification weighting

Output:

```python
priority_score: int
```

Range:

```text
0-100
```

Persist results.

Generate working code only.

Stop.

---

# Phase 7

Generate:

- BaseLLMProvider
- OpenAIProvider
- ClaudeProvider
- GeminiProvider
- Provider registry
- SummarizationService

Requirements:

- Structured prompts
- JSON outputs
- Retry handling
- Response validation
- Avoid regenerating existing summaries

Generate working provider implementations.

Do not generate stubs.

Generate working code only.

Stop.

---

# Phase 8

Generate:

TaskExtractionService

Extract:

- task
- deadline
- priority

Persist tasks.

Requirements:

- Validate extracted data
- Handle malformed model responses
- Prevent duplicate task creation

Generate working code only.

Stop.

---

# Phase 9

Generate:

JobExtractionService

Extract:

- company
- role
- location
- salary
- deadline
- apply_link

InterviewExtractionService

Extract:

- company
- role
- date
- meeting_link

Persist extracted data.

Generate working code only.

Stop.

---

# Phase 10

Generate:

- Redis integration
- Celery integration
- Background task architecture

Pipeline:

Email → Classification → Priority → Summary → Task → Job → Interview

Requirements:

- Retry handling
- Failure handling
- Working Celery implementation
- No placeholder queue logic

Generate working code only.

Stop.

---

# Phase 11

Generate:

- pgvector integration
- Embedding storage
- Similarity search
- Search APIs

Requirements:

- Store embeddings in PostgreSQL
- Query embeddings using pgvector
- Support semantic search

Examples:

```text
Show interview emails
```

```text
Find emails mentioning Amazon
```

Generate working code only.

Stop.

---

# Phase 12

Generate:

- React routing
- Layout architecture
- Authentication flow
- API client layer
- Zustand state management
- Reusable component structure

Generate working code only.

Stop.

---

# Phase 13

Generate production-ready dashboard pages and components.

Overview:

- Total emails
- Important emails
- Pending tasks
- Upcoming interviews
- Active job opportunities

Important Emails:

- Priority sorted
- Summary preview
- Sender
- Subject
- Open email action

Tasks:

- Task list
- Status tracking
- Deadline display

Interviews:

- Company
- Role
- Date
- Meeting link

Jobs:

- Company
- Role
- Deadline
- Apply link

Search:

- Semantic search UI
- Search results
- Filtering

Requirements:

- Real API integration
- No mock data
- No placeholders

Generate working code only.

Stop.

---

# Phase 14

Backend:

- Pytest
- Unit tests
- Integration tests

Frontend:

- Vitest
- React Testing Library

Focus on:

- Core business logic
- Gmail integration flows
- Classification pipeline
- Summarization pipeline
- Task extraction
- Job extraction
- Interview extraction
- Dashboard functionality

Generate working tests only.

Stop.

# Folder Architecture

# Backend Structure

```text
app/
├── api/
│   ├── deps/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── email.py
│   │   ├── task.py
│   │   ├── job.py
│   │   ├── interview.py
│   │   ├── search.py
│   │   └── sync.py
│   └── router.py
│
├── core/
│   ├── config.py
│   ├── security.py
│   ├── logging.py
│   └── constants.py
│
├── domain/
│   ├── entities/
│   ├── repositories/
│   └── services/
│
├── application/
│   ├── dto/
│   ├── use_cases/
│   └── interfaces/
│
├── infrastructure/
│   ├── database/
│   │   ├── models/
│   │   ├── repositories/
│   │   └── session.py
│   │
│   ├── gmail/
│   │   ├── client.py
│   │   └── sync_service.py
│   │
│   ├── ai/
│   │   ├── classification/
│   │   ├── summarization/
│   │   ├── extraction/
│   │   └── embeddings/
│   │
│   ├── providers/
│   │   ├── openai.py
│   │   ├── claude.py
│   │   └── gemini.py
│   │
│   ├── queue/
│   │   ├── celery_app.py
│   │   └── tasks/
│   │
│   └── search/
│       └── semantic_search.py
│
├── schemas/
│
├── dependencies/
│
├── tests/
│
├── main.py
└── alembic/
```

# Frontend Structure

```text
src/
├── api/
│
├── pages/
│   ├── Dashboard/
│   ├── Emails/
│   ├── Tasks/
│   ├── Jobs/
│   ├── Interviews/
│   └── Search/
│
├── layouts/
│
├── components/
│   ├── email/
│   ├── task/
│   ├── job/
│   ├── interview/
│   ├── dashboard/
│   └── common/
│
├── hooks/
│
├── store/
│
├── services/
│
├── routes/
│
├── types/
│
├── utils/
│
├── theme/
│
├── App.tsx
└── main.tsx
```
