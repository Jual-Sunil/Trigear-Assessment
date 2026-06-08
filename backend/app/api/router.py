"""
Central API router.

Aggregates all route modules and registers them under versioned prefixes.
Each sub-router is mounted with its own tag and prefix for OpenAPI grouping.
"""

from fastapi import APIRouter

from api.routes.auth import router as auth_router
from api.routes.sync import router as sync_router
from api.routes.email import router as email_router
from api.routes.task import router as task_router
from api.routes.job import router as job_router
from api.routes.interview import router as interview_router
from api.routes.dashboard import router as dashboard_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(sync_router, prefix="/sync", tags=["Sync"])
api_router.include_router(email_router, prefix="/emails", tags=["Emails"])
api_router.include_router(task_router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(job_router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(interview_router, prefix="/interviews", tags=["Interviews"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])