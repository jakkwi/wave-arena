"""Ports: what the domain needs from the outside world. Adapters implement them."""

from typing import Protocol

from backend.domain.models import Run


class RunRepository(Protocol):
    """Leaderboard storage (DynamoDB in production)."""

    def save(self, run: Run) -> None: ...

    def top(self, limit: int) -> list[Run]:
        """Return up to `limit` of the best runs. Order is not guaranteed; the domain ranks them."""
        ...


class EventArchive(Protocol):
    """Raw run events for analytics (S3 in production)."""

    def store(self, run: Run) -> None: ...
