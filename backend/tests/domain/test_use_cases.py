from datetime import UTC, datetime, timedelta

import pytest

from backend.domain.errors import ValidationError
from backend.domain.models import Position, Run
from backend.domain.use_cases import get_top, submit_run
from backend.tests.domain.test_validation import RUN_ID, valid_payload
from backend.tests.fakes import FailingRunRepository, InMemoryEventArchive, InMemoryRunRepository

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def make_run(run_id: str, score: int, waves: int = 5, at: datetime = T0, name: str = "Kuba") -> Run:
    return Run(
        run_id=run_id,
        received_at=at,
        player_name=name,
        arena="arena_01",
        score=score,
        waves_survived=waves,
        duration_s=100.0,
        death_position=Position(x=0.0, y=0.0),
        killer_type="grunt",
    )


def test_submit_run_archives_and_saves() -> None:
    repo, archive = InMemoryRunRepository(), InMemoryEventArchive()
    run = submit_run(valid_payload(), repo, archive, new_id=lambda: RUN_ID, clock=lambda: T0)
    assert run.run_id == RUN_ID
    assert run.received_at == T0
    assert repo.runs == [run]
    assert archive.events == [run]


def test_invalid_run_touches_nothing() -> None:
    repo, archive = InMemoryRunRepository(), InMemoryEventArchive()
    with pytest.raises(ValidationError):
        submit_run(valid_payload(score=-1), repo, archive, new_id=lambda: RUN_ID, clock=lambda: T0)
    assert repo.runs == []
    assert archive.events == []


def test_event_is_archived_even_if_saving_fails() -> None:
    archive = InMemoryEventArchive()
    with pytest.raises(RuntimeError):
        submit_run(
            valid_payload(),
            FailingRunRepository(),
            archive,
            new_id=lambda: RUN_ID,
            clock=lambda: T0,
        )
    assert len(archive.events) == 1


def test_default_id_and_clock_are_uuid_and_utc() -> None:
    repo, archive = InMemoryRunRepository(), InMemoryEventArchive()
    run = submit_run(valid_payload(), repo, archive)
    assert len(run.run_id) == 36
    assert run.received_at.tzinfo is UTC


def test_get_top_ranks_by_score_then_waves_then_time() -> None:
    repo = InMemoryRunRepository()
    repo.runs = [
        make_run("a", score=100, waves=3),
        make_run("b", score=300, waves=5),
        make_run("c", score=100, waves=4),
        make_run("d", score=100, waves=4, at=T0 - timedelta(minutes=1)),
    ]
    entries = get_top(repo, limit=10)
    assert [(e.rank, e.score, e.waves_survived) for e in entries] == [
        (1, 300, 5),
        (2, 100, 4),
        (3, 100, 4),
        (4, 100, 3),
    ]
    assert entries[1].submitted_at == T0 - timedelta(minutes=1)


def test_get_top_respects_limit() -> None:
    repo = InMemoryRunRepository()
    repo.runs = [make_run(str(i), score=i * 10) for i in range(15)]
    entries = get_top(repo, limit=3)
    assert [e.score for e in entries] == [140, 130, 120]
    assert [e.rank for e in entries] == [1, 2, 3]


def test_get_top_on_empty_leaderboard() -> None:
    assert get_top(InMemoryRunRepository(), limit=10) == []


def test_entry_exposes_only_public_fields() -> None:
    repo = InMemoryRunRepository()
    repo.runs = [make_run("a", score=1, name="Ala")]
    (entry,) = get_top(repo, limit=10)
    assert entry.player_name == "Ala"
    assert not hasattr(entry, "run_id")
    assert not hasattr(entry, "death_position")


@pytest.mark.parametrize("limit", [0, 11])
def test_get_top_rejects_out_of_range_limit(limit: int) -> None:
    with pytest.raises(ValidationError):
        get_top(InMemoryRunRepository(), limit=limit)
