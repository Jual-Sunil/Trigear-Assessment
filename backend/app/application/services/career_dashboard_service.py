"""Service for assembling career-related dashboard data."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from infrastructure.database.models.interview import Interview
from infrastructure.database.models.job_opportunity import JobOpportunity
from infrastructure.database.repositories.interview_repository import InterviewRepository
from infrastructure.database.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)


@dataclass(frozen=True, slots=True)
class CareerDashboardData:
    """Immutable snapshot of career-related data for the dashboard.

    Attributes:
        active_job_opportunities: Job opportunities whose deadline is unset or
            still in the future, ordered by deadline ascending (nulls last).
        upcoming_interviews: Interviews whose date is unset or still in the
            future, ordered by interview date ascending (nulls last).
        total_active_jobs: Total count of active job opportunities for the
            supplied email scope, independent of pagination.
        total_upcoming_interviews: Total count of upcoming interviews for the
            supplied email scope, independent of pagination.
    """

    active_job_opportunities: list[JobOpportunity] = field(default_factory=list)
    upcoming_interviews: list[Interview] = field(default_factory=list)
    total_active_jobs: int = 0
    total_upcoming_interviews: int = 0


@dataclass(frozen=True, slots=True)
class CareerDashboardRequest:
    """Parameters that scope a career dashboard data fetch.

    Attributes:
        email_ids: UUIDs of email records owned by the requesting user.
        job_offset: Zero-based offset for job opportunity pagination.
        job_limit: Maximum number of job opportunities to return.
        interview_offset: Zero-based offset for interview pagination.
        interview_limit: Maximum number of interviews to return.
    """

    email_ids: list[uuid.UUID]
    job_offset: int = 0
    job_limit: int = 20
    interview_offset: int = 0
    interview_limit: int = 20


class CareerDashboardService:
    """Assembles career-related data from the jobs and interviews repositories.

    All queries are scoped to the email IDs supplied by the caller, which acts
    as a proxy for user ownership when no direct ``user_id`` FK exists on the
    ``JobOpportunity`` or ``Interview`` models.

    Attributes:
        _job_repo: Repository responsible for :class:`JobOpportunity` queries.
        _interview_repo: Repository responsible for :class:`Interview` queries.
    """

    def __init__(
        self,
        job_repo: JobOpportunityRepository,
        interview_repo: InterviewRepository,
    ) -> None:
        """Initialise the service with pre-constructed repository instances.

        Args:
            job_repo: A :class:`JobOpportunityRepository` bound to the current
                async database session.
            interview_repo: An :class:`InterviewRepository` bound to the current
                async database session.
        """
        self._job_repo = job_repo
        self._interview_repo = interview_repo

    async def get_dashboard_data(
        self,
        request: CareerDashboardRequest,
    ) -> CareerDashboardData:
        """Fetch and assemble all career dashboard data for the given email scope.

        Executes four concurrent-friendly repository queries:

        1. Active job opportunities (deadline unset or future), paginated.
        2. Total count of active job opportunities.
        3. Upcoming interviews (date unset or future), paginated.
        4. Total count of upcoming interviews.

        Sorting is delegated entirely to the repositories, which apply
        ``ORDER BY deadline ASC NULLS LAST`` for jobs and
        ``ORDER BY interview_date ASC NULLS LAST`` for interviews.

        Args:
            request: A :class:`CareerDashboardRequest` carrying the email scope
                and pagination parameters.

        Returns:
            A :class:`CareerDashboardData` instance populated with the fetched
            records and total counts.
        """
        if not request.email_ids:
            return CareerDashboardData()

        active_jobs = await self._job_repo.get_active_opportunities(
            email_ids=request.email_ids,
            offset=request.job_offset,
            limit=request.job_limit,
        )
        total_active_jobs = await self._job_repo.count_active_by_email_ids(
            request.email_ids,
        )
        upcoming_interviews = await self._interview_repo.get_upcoming_interviews(
            request.email_ids,
            offset=request.interview_offset,
            limit=request.interview_limit,
        )
        total_upcoming_interviews = await self._interview_repo.count_upcoming_by_email_ids(
            request.email_ids,
        )

        return CareerDashboardData(
            active_job_opportunities=active_jobs,
            upcoming_interviews=upcoming_interviews,
            total_active_jobs=total_active_jobs,
            total_upcoming_interviews=total_upcoming_interviews,
        )

    async def get_active_job_opportunities(
        self,
        email_ids: list[uuid.UUID],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[JobOpportunity]:
        """Return active job opportunities for a set of email IDs.

        Delegates directly to :meth:`JobOpportunityRepository.get_active_opportunities`.
        A job opportunity is active when its deadline is ``NULL`` or in the future.

        Args:
            email_ids: UUIDs of email records scoping the query.
            offset: Number of records to skip for pagination.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`JobOpportunity` instances ordered by deadline
            ascending with nulls sorted last.
        """
        if not email_ids:
            return []
        return await self._job_repo.get_active_opportunities(
            email_ids=email_ids,
            offset=offset,
            limit=limit,
        )

    async def get_upcoming_interviews(
        self,
        email_ids: list[uuid.UUID],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Interview]:
        """Return upcoming interviews for a set of email IDs.

        Delegates directly to :meth:`InterviewRepository.get_upcoming_interviews`.
        An interview is upcoming when its date is ``NULL`` or in the future.

        Args:
            email_ids: UUIDs of email records scoping the query.
            offset: Number of records to skip for pagination.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`Interview` instances ordered by interview date
            ascending with nulls sorted last.
        """
        if not email_ids:
            return []
        return await self._interview_repo.get_upcoming_interviews(
            email_ids,
            offset=offset,
            limit=limit,
        )

    async def get_next_interview(
        self,
        email_ids: list[uuid.UUID],
    ) -> Interview | None:
        """Return the single nearest upcoming scheduled interview.

        Only interviews with a concrete ``interview_date`` in the future are
        considered; records with a ``NULL`` date are excluded.

        Args:
            email_ids: UUIDs of email records scoping the query.

        Returns:
            The nearest :class:`Interview` instance, or ``None`` when no
            scheduled future interview exists within the supplied email scope.
        """
        if not email_ids:
            return None
        return await self._interview_repo.get_next_interview(email_ids)

    async def get_upcoming_job_deadlines(
        self,
        email_ids: list[uuid.UUID],
        *,
        days: int = 14,
        offset: int = 0,
        limit: int = 20,
    ) -> list[JobOpportunity]:
        """Return job opportunities whose deadline falls within a future time window.

        Only opportunities with a concrete deadline are included; records with a
        ``NULL`` deadline are excluded because no concrete urgency can be derived.

        Args:
            email_ids: UUIDs of email records scoping the query.
            days: Number of calendar days ahead to treat as the upper bound.
            offset: Number of records to skip for pagination.
            limit: Maximum number of records to return.

        Returns:
            A list of :class:`JobOpportunity` instances with deadlines in
            ``[now, now + days]``, ordered by deadline ascending.
        """
        if not email_ids:
            return []
        return await self._job_repo.get_upcoming_deadlines(
            email_ids=email_ids,
            days=days,
            offset=offset,
            limit=limit,
        )