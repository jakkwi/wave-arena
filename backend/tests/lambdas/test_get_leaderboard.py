import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from backend.adapters.dynamodb_runs import DynamoDbRunRepository
from backend.domain.models import Run
from backend.lambdas import get_leaderboard
from backend.tests.adapters.conftest import TABLE_NAME
from backend.tests.domain.test_use_cases import make_run
from backend.tests.fakes import FailingRunRepository, InMemoryRunRepository
from backend.tests.lambdas.events import http_event, response_json

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table


def get(query: dict[str, str] | None = None) -> dict[str, object]:
    return http_event("GET", "/leaderboard", query=query)


class BrokenTopRepository(FailingRunRepository):
    def top(self, limit: int) -> list[Run]:
        raise RuntimeError("query failed")


def test_empty_leaderboard() -> None:
    response = get_leaderboard.handle(get(), InMemoryRunRepository())
    assert response["statusCode"] == 200
    assert response_json(response) == {"v": 1, "entries": []}


def test_entries_are_ranked_and_public_only() -> None:
    repo = InMemoryRunRepository()
    repo.runs = [
        make_run("a", score=10, name="Ala"),
        make_run("b", score=90, waves=7, at=datetime(2026, 11, 14, 18, 3, 12, 999, tzinfo=UTC)),
    ]
    body = response_json(get_leaderboard.handle(get(), repo))
    assert body["entries"] == [
        {
            "rank": 1,
            "player_name": "Kuba",
            "score": 90,
            "waves_survived": 7,
            "submitted_at": "2026-11-14T18:03:12Z",
        },
        {
            "rank": 2,
            "player_name": "Ala",
            "score": 10,
            "waves_survived": 5,
            "submitted_at": "2026-11-14T12:00:00Z",
        },
    ]


def test_limit_parameter() -> None:
    repo = InMemoryRunRepository()
    repo.runs = [make_run(str(i), score=i) for i in range(10)]
    body = response_json(get_leaderboard.handle(get({"limit": "3"}), repo))
    assert [e["score"] for e in body["entries"]] == [9, 8, 7]


@pytest.mark.parametrize("limit", ["0", "11", "abc", ""])
def test_bad_limit_returns_400(limit: str) -> None:
    response = get_leaderboard.handle(get({"limit": limit}), InMemoryRunRepository())
    assert response["statusCode"] == 400
    body = response_json(response)
    assert body["error"] == "invalid_request"
    assert body["message"].startswith("limit: ")


def test_unexpected_error_returns_500(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    response = get_leaderboard.handle(get(), BrokenTopRepository())
    assert response["statusCode"] == 500
    body = response_json(response)
    assert body == {"v": 1, "error": "internal_error", "message": "internal error"}
    assert "query failed" in caplog.text


def test_handler_wires_real_adapter(runs_table: "Table", monkeypatch: pytest.MonkeyPatch) -> None:
    DynamoDbRunRepository(runs_table).save(make_run("a", score=42))
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)
    get_leaderboard.dependencies.cache_clear()
    try:
        response = get_leaderboard.handler(get(), None)
    finally:
        get_leaderboard.dependencies.cache_clear()
    assert response["statusCode"] == 200
    body = response_json(response)
    assert [e["score"] for e in body["entries"]] == [42]
