from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from backend.adapters.dynamodb_runs import DynamoDbRunRepository, rank_key
from backend.domain.limits import MAX_SCORE, MAX_WAVES
from backend.domain.models import Position, Run
from backend.domain.ports import RunRepository
from backend.domain.use_cases import get_top, ranking_key

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def make_run(
    run_id: str,
    score: int = 100,
    waves: int = 5,
    at: datetime = T0,
    killer: str | None = "grunt",
) -> Run:
    return Run(
        run_id=run_id,
        received_at=at,
        player_name="Kuba",
        arena="arena_01",
        score=score,
        waves_survived=waves,
        duration_s=312.5,
        death_position=Position(x=-3.25, y=12.0),
        killer_type=killer,
    )


def test_adapter_implements_the_port(runs_table: "Table") -> None:
    repo: RunRepository = DynamoDbRunRepository(runs_table)
    assert repo is not None


def test_saved_run_round_trips(runs_table: "Table") -> None:
    repo = DynamoDbRunRepository(runs_table)
    run = make_run("r1", at=T0.replace(microsecond=123456))
    repo.save(run)
    assert repo.top(10) == [run]


def test_null_killer_type_round_trips(runs_table: "Table") -> None:
    repo = DynamoDbRunRepository(runs_table)
    run = make_run("r1", killer=None)
    repo.save(run)
    assert repo.top(10) == [run]
    (item,) = runs_table.scan()["Items"]
    assert "killer_type" not in item


def test_item_uses_adr_0004_keys(runs_table: "Table") -> None:
    DynamoDbRunRepository(runs_table).save(make_run("r1", score=4200, waves=7))
    (item,) = runs_table.scan()["Items"]
    assert item["board"] == "global"
    assert item["rank_key"] == "09995800#0993#2026-11-14T12:00:00.000000Z#r1"


def test_top_returns_best_first(runs_table: "Table") -> None:
    repo = DynamoDbRunRepository(runs_table)
    for run in [
        make_run("low", score=10),
        make_run("high", score=900),
        make_run("mid", score=500),
    ]:
        repo.save(run)
    assert [r.run_id for r in repo.top(10)] == ["high", "mid", "low"]


def test_ties_break_by_waves_then_earlier_time(runs_table: "Table") -> None:
    repo = DynamoDbRunRepository(runs_table)
    for run in [
        make_run("fewer_waves", score=100, waves=3),
        make_run("later", score=100, waves=4, at=T0 + timedelta(seconds=1)),
        make_run("earlier", score=100, waves=4, at=T0),
    ]:
        repo.save(run)
    assert [r.run_id for r in repo.top(10)] == ["earlier", "later", "fewer_waves"]


def test_top_respects_limit(runs_table: "Table") -> None:
    repo = DynamoDbRunRepository(runs_table)
    for i in range(15):
        repo.save(make_run(f"r{i:02d}", score=i * 10))
    assert [r.score for r in repo.top(10)] == [140, 130, 120, 110, 100, 90, 80, 70, 60, 50]
    assert len(repo.top(3)) == 3


def test_fewer_runs_than_limit(runs_table: "Table") -> None:
    repo = DynamoDbRunRepository(runs_table)
    repo.save(make_run("only"))
    assert len(repo.top(10)) == 1


def test_empty_table(runs_table: "Table") -> None:
    assert DynamoDbRunRepository(runs_table).top(10) == []


def test_boards_are_separate(runs_table: "Table") -> None:
    DynamoDbRunRepository(runs_table, board="arena_01").save(make_run("a"))
    assert DynamoDbRunRepository(runs_table).top(10) == []


def test_works_with_the_domain_use_case(runs_table: "Table") -> None:
    repo = DynamoDbRunRepository(runs_table)
    repo.save(make_run("a", score=5))
    repo.save(make_run("b", score=50))
    assert [(e.rank, e.score) for e in get_top(repo, limit=10)] == [(1, 50), (2, 5)]


def test_rank_key_order_matches_domain_ranking() -> None:
    runs = [
        make_run(run_id, score=score, waves=waves, at=T0 + timedelta(microseconds=us))
        for run_id, score, waves, us in [
            ("a", 0, 0, 0),
            ("b", MAX_SCORE, MAX_WAVES, 0),
            ("c", 100, 4, 5),
            ("d", 100, 4, 1),
            ("e", 100, 9, 0),
            ("f", 99, 1000, 0),
            ("g", 100, 4, 1),
            ("h", 1_000_000, 0, 0),
        ]
    ]
    assert sorted(runs, key=rank_key) == sorted(runs, key=ranking_key)


@pytest.mark.parametrize(
    ("score", "waves"), [(0, 0), (MAX_SCORE, MAX_WAVES), (1, 1), (MAX_SCORE - 1, 999)]
)
def test_rank_key_has_fixed_width(score: int, waves: int) -> None:
    key = rank_key(make_run("x", score=score, waves=waves))
    assert len(key) == len(rank_key(make_run("x")))


def test_rank_key_converts_to_utc() -> None:
    local = datetime(2026, 11, 14, 13, 0, tzinfo=UTC).astimezone(
        tz=datetime.now().astimezone().tzinfo
    )
    assert rank_key(make_run("x", at=local)) == rank_key(make_run("x", at=T0 + timedelta(hours=1)))
