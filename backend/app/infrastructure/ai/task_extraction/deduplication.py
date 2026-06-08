"""Task deduplication utilities for the task extraction subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from rapidfuzz import fuzz

from infrastructure.ai.task_extraction.schemas import ExtractedTask


@dataclass(frozen=True, slots=True)
class TaskDeduplicationService:
    """Remove duplicate and near-duplicate extracted tasks.

    Responsibilities:
    - Remove duplicate tasks (exact and near-duplicate)
    - Preserve the highest confidence version
    - Preserve earliest due date

    Duplicate detection considers title similarity and description
    similarity. Similarity threshold is configurable.

    Notes:
        This service does not access repositories and does not implement
        extraction logic.
    """

    similarity_threshold: int = 90

    def deduplicate(self, tasks: Iterable[ExtractedTask]) -> list[ExtractedTask]:
        """Deduplicate tasks based on title and description similarity.

        Args:
            tasks: Iterable of :class:`ExtractedTask` items.

        Returns:
            A list of deduplicated tasks.
        """
        unique: list[ExtractedTask] = []

        for candidate in tasks:
            matched_index = self._find_match_index(candidate, unique)
            if matched_index is None:
                unique.append(candidate)
                continue

            existing = unique[matched_index]
            unique[matched_index] = self._merge_preferred(existing, candidate)

        return unique

    def _find_match_index(
        self, candidate: ExtractedTask, existing_tasks: list[ExtractedTask]
    ) -> int | None:
        """Find the index of the best matching existing task.

        Args:
            candidate: Task to match.
            existing_tasks: Current deduplicated set.

        Returns:
            Index of best match if similarity meets threshold; otherwise None.
        """
        best_score: int = -1
        best_index: int | None = None

        for idx, existing in enumerate(existing_tasks):
            score = self._similarity_score(candidate, existing)
            if score >= self.similarity_threshold and score > best_score:
                best_score = score
                best_index = idx

        return best_index

    def _merge_preferred(
        self, existing: ExtractedTask, incoming: ExtractedTask
    ) -> ExtractedTask:
        """Merge two tasks preserving highest confidence and earliest due date.

        Args:
            existing: Previously stored task.
            incoming: Newly encountered task.

        Returns:
            The preferred :class:`ExtractedTask` instance.
        """
        if incoming.confidence_score > existing.confidence_score:
            preferred = incoming
        elif incoming.confidence_score < existing.confidence_score:
            preferred = existing
        else:
            # Same confidence: preserve earliest due date.
            preferred = self._earliest_due_date(existing, incoming)

        # If the preferred task had lower confidence originally but incoming had
        # earlier due date with same confidence, it is already handled above.
        # Otherwise, keep the preferred representation.
        return preferred

    def _earliest_due_date(
        self, a: ExtractedTask, b: ExtractedTask
    ) -> ExtractedTask:
        """Select the task with the earliest due date.

        If one task has due_date=None, prefer the other task with a due date.
        If both have due_date=None, default to `a`.
        If both have due_date set, return the task with the earlier date.
        """
        if a.due_date is None and b.due_date is None:
            return a
        if a.due_date is None and b.due_date is not None:
            return b
        if b.due_date is None and a.due_date is not None:
            return a

        assert a.due_date is not None and b.due_date is not None
        return a if a.due_date <= b.due_date else b

    def _similarity_score(self, a: ExtractedTask, b: ExtractedTask) -> int:
        """Compute a combined similarity score for two tasks.

        Args:
            a: First task.
            b: Second task.

        Returns:
            Integer similarity score in [0, 100].
        """
        title_score = fuzz.token_set_ratio(a.title, b.title)
        description_a = a.description or ""
        description_b = b.description or ""
        description_score = (
            fuzz.token_set_ratio(description_a, description_b)
            if (description_a or description_b)
            else 0
        )

        # Weighted combination: title is more important than description.
        # If both descriptions are empty, rely mostly on title.
        if not description_a and not description_b:
            return int(title_score)

        return int((0.7 * title_score) + (0.3 * description_score))

