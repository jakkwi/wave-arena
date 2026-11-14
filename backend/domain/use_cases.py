"""Use cases called by the Lambda handlers."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from backend.domain.models import LeaderboardEntry, Run
from backend.domain.ports import EventArchive, RunRepository
from backend.domain.validation import check_limit, parse_run


def _new_id() -> str:
    return str(uuid.uuid4())


def _utc_now() -> datetime:
    return datetime.now(UTC)


def submit_run(
    payload: object,
    repository: RunRepository,
    archive: EventArchive,
    *,
    new_id: Callable[[], str] = _new_id,
    clock: Callable[[], datetime] = _utc_now,
) -> Run:
    """Validate a run, archive the raw event, then save it to the leaderboard.

    Archive first: analytics should see every valid run even if the leaderboard write fails.
    """
    run = parse_run(payload, run_id=new_id(), received_at=clock())
    archive.store(run)
    repository.save(run)
    return run


def ranking_key(run: Run) -> tuple[int, int, datetime, str]:
    """Higher score, then more waves, then earlier submission, then run_id for stability."""
    return (-run.score, -run.waves_survived, run.received_at, run.run_id)


def get_top(repository: RunRepository, limit: int) -> list[LeaderboardEntry]:
    check_limit(limit)
    runs = sorted(repository.top(limit), key=ranking_key)[:limit]
    return [
        LeaderboardEntry(
            rank=position,
            player_name=run.player_name,
            score=run.score,
            waves_survived=run.waves_survived,
            submitted_at=run.received_at,
        )
        for position, run in enumerate(runs, start=1)
    ]
