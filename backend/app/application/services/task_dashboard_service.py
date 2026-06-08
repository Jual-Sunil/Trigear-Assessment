"""Task dashboard application service.

This service prepares task data for presentation in the dashboard.
It does not depend on FastAPI routes or frontend code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from infrastructure.database.models.task import Task
from infrastructure.database.repositories.task_repository import (
    TaskRepository,
)


@dataclass(frozen=True, slots=True)
class DashboardTaskDTO:
    """Dashboard-ready task representation."""

    id: str
    title: str
    description: str | None
    priority: int | None
    due_date: datetime | None
    status: str


class TaskDashboardService:
    """Prepare dashboard task data from pending tasks."""

    def __init__(
        self,
        *,
        task_repository: TaskRepository,
        min_confidence_score: float = 0.0,
    ) -> None:
        """Initialise the service.

        Args:
            task_repository: Repository used to retrieve tasks.
            min_confidence_score: Minimum confidence score required. Since
                tasks currently do not store confidence in the DB model, this
                threshold is reserved for future schema alignment and is
                effectively ignored.
        """
        self._task_repository = task_repository
        self._min_confidence_score = min_confidence_score

    async def get_dashboard_tasks(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        high_priority_min: int = 0,
    ) -> dict[str, Any]:
        """Retrieve, sort, and format tasks for the dashboard.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            high_priority_min: Minimum priority to consider a task high
                priority.

        Returns:
            Dictionary containing formatted task lists.
        """
        pending = await self._task_repository.get_pending_tasks(
            offset=offset, limit=limit
        )

        filtered = [t for t in pending if self._passes_confidence_filter(t)]

        # Deterministic ordering:
        # 1) due_date ascending (nulls last)
        # 2) priority descending with stable tie-breaker: title
        def sort_key(t: Task) -> tuple[int, int, str]:
            due = t.due_date
            if due is None:
                due_ts = datetime.max.replace(tzinfo=timezone.utc)
            else:
                due_ts = due
            priority = t.priority if t.priority is not None else -1
            # Convert due to timestamp ordering
            due_cmp = int(due_ts.timestamp())
            return (due_cmp, -priority, (t.title or ""))

        filtered_sorted = sorted(filtered, key=sort_key)

        high_priority = [t for t in filtered_sorted if (t.priority or 0) >= high_priority_min]

        return {
            "tasks": [self._to_dto(t) for t in filtered_sorted],
            "high_priority_tasks": [self._to_dto(t) for t in high_priority],
            "count": len(filtered_sorted),
            "high_priority_count": len(high_priority),
        }

    def _passes_confidence_filter(self, task: Task) -> bool:
        """Apply a confidence filter.

        Notes:
            The current Task ORM model does not include a confidence score.
            Therefore, this filter is conservatively implemented as a pass-all.
        """
        _ = self._min_confidence_score
        return True

    def _to_dto(self, task: Task) -> DashboardTaskDTO:
        """Convert a Task model into a dashboard DTO."""
        return DashboardTaskDTO(
            id=str(task.id),
            title=(task.title or "").strip(),
            description=task.description,
            priority=task.priority,
            due_date=task.due_date,
            status=task.status,
        )

