"""Application-wide constants used across multiple modules."""

from typing import Final

# ---------------------------------------------------------------------------
# Email Classification Categories
# ---------------------------------------------------------------------------

EMAIL_CATEGORIES: Final[list[str]] = [
    "Work",
    "Interview",
    "Job Opportunity",
    "Finance",
    "Personal",
    "Promotion",
    "Newsletter",
    "Spam",
    "Other",
]

EMAIL_CATEGORY_WORK: Final[str] = "Work"
EMAIL_CATEGORY_INTERVIEW: Final[str] = "Interview"
EMAIL_CATEGORY_JOB_OPPORTUNITY: Final[str] = "Job Opportunity"
EMAIL_CATEGORY_FINANCE: Final[str] = "Finance"
EMAIL_CATEGORY_PERSONAL: Final[str] = "Personal"
EMAIL_CATEGORY_PROMOTION: Final[str] = "Promotion"
EMAIL_CATEGORY_NEWSLETTER: Final[str] = "Newsletter"
EMAIL_CATEGORY_SPAM: Final[str] = "Spam"
EMAIL_CATEGORY_OTHER: Final[str] = "Other"

# ---------------------------------------------------------------------------
# Task Status Values
# ---------------------------------------------------------------------------

TASK_STATUS_PENDING: Final[str] = "pending"
TASK_STATUS_IN_PROGRESS: Final[str] = "in_progress"
TASK_STATUS_COMPLETED: Final[str] = "completed"
TASK_STATUS_CANCELLED: Final[str] = "cancelled"

TASK_STATUSES: Final[list[str]] = [
    TASK_STATUS_PENDING,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_CANCELLED,
]

# ---------------------------------------------------------------------------
# Processing Pipeline Stages
# ---------------------------------------------------------------------------

PIPELINE_STAGE_CLASSIFICATION: Final[str] = "classification"
PIPELINE_STAGE_PRIORITY: Final[str] = "priority"
PIPELINE_STAGE_SUMMARY: Final[str] = "summary"
PIPELINE_STAGE_TASK_EXTRACTION: Final[str] = "task_extraction"
PIPELINE_STAGE_JOB_EXTRACTION: Final[str] = "job_extraction"
PIPELINE_STAGE_INTERVIEW_EXTRACTION: Final[str] = "interview_extraction"
PIPELINE_STAGE_EMBEDDING: Final[str] = "embedding"

PIPELINE_STAGES: Final[list[str]] = [
    PIPELINE_STAGE_CLASSIFICATION,
    PIPELINE_STAGE_PRIORITY,
    PIPELINE_STAGE_SUMMARY,
    PIPELINE_STAGE_TASK_EXTRACTION,
    PIPELINE_STAGE_JOB_EXTRACTION,
    PIPELINE_STAGE_INTERVIEW_EXTRACTION,
    PIPELINE_STAGE_EMBEDDING,
]

# ---------------------------------------------------------------------------
# Processing Job Status Values
# ---------------------------------------------------------------------------

JOB_STATUS_PENDING: Final[str] = "pending"
JOB_STATUS_RUNNING: Final[str] = "running"
JOB_STATUS_COMPLETED: Final[str] = "completed"
JOB_STATUS_FAILED: Final[str] = "failed"

# ---------------------------------------------------------------------------
# Priority Score Boundaries
# ---------------------------------------------------------------------------

PRIORITY_SCORE_MIN: Final[int] = 0
PRIORITY_SCORE_MAX: Final[int] = 100
PRIORITY_SCORE_HIGH_THRESHOLD: Final[int] = 70
PRIORITY_SCORE_MEDIUM_THRESHOLD: Final[int] = 40

# ---------------------------------------------------------------------------
# Pagination Defaults
# ---------------------------------------------------------------------------

DEFAULT_PAGE: Final[int] = 1
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

SEARCH_MAX_RESULTS: Final[int] = 50
SEARCH_SIMILARITY_THRESHOLD: Final[float] = 0.3

# ---------------------------------------------------------------------------
# Classification Methods (used in audit log)
# ---------------------------------------------------------------------------

CLASSIFICATION_METHOD_EMBEDDING: Final[str] = "embedding_similarity"
CLASSIFICATION_METHOD_ZERO_SHOT: Final[str] = "zero_shot_bart"
CLASSIFICATION_METHOD_LLM: Final[str] = "llm_fallback"

# ---------------------------------------------------------------------------
# Gmail API
# ---------------------------------------------------------------------------

GMAIL_READONLY_SCOPE: Final[str] = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_MAX_BATCH_SIZE: Final[int] = 50
GMAIL_HISTORY_TYPES: Final[list[str]] = ["messageAdded"]
