"""
Pagination dependency.

Provides a standardized, validated pagination parameter object for use
across list endpoints. Enforces safe upper bounds on page size.
"""

from dataclasses import dataclass

from fastapi import Query


@dataclass(frozen=True)
class PaginationParams:
    """
    Immutable container for validated pagination parameters.

    Attributes:
        page: 1-based page number.
        page_size: Number of items per page.
        offset: Computed zero-based row offset for database queries.
    """

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        """
        Compute the zero-based row offset for the current page.

        Returns:
            int: Row offset for use in SQL OFFSET clauses.
        """
        return (self.page - 1) * self.page_size


_MAX_PAGE_SIZE = 100
_DEFAULT_PAGE_SIZE = 20


def get_pagination(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(
        default=_DEFAULT_PAGE_SIZE,
        ge=1,
        le=_MAX_PAGE_SIZE,
        description=f"Items per page (max {_MAX_PAGE_SIZE})",
    ),
) -> PaginationParams:
    """
    Parse and validate pagination query parameters.

    Args:
        page: Requested page number, must be >= 1.
        page_size: Items per page, clamped between 1 and MAX_PAGE_SIZE.

    Returns:
        PaginationParams: Validated, immutable pagination parameters.
    """
    return PaginationParams(page=page, page_size=page_size)
