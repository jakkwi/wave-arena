"""In-memory fakes of the domain ports, for domain and use case tests."""

from backend.domain.models import Run


class InMemoryRunRepository:
    """Stores runs in a list. `top` returns them unsorted on purpose:
    ordering is a domain rule, so the use case must not rely on the adapter for it."""

    def __init__(self) -> None:
        self.runs: list[Run] = []

    def save(self, run: Run) -> None:
        self.runs.append(run)

    def top(self, limit: int) -> list[Run]:
        ranked = sorted(self.runs, key=lambda r: -r.score)[:limit]
        return list(reversed(ranked))


class InMemoryEventArchive:
    def __init__(self) -> None:
        self.events: list[Run] = []

    def store(self, run: Run) -> None:
        self.events.append(run)


class FailingRunRepository(InMemoryRunRepository):
    def save(self, run: Run) -> None:
        raise RuntimeError("table unavailable")
