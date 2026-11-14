from datetime import UTC, datetime
from typing import Any

import pytest

from backend.domain.errors import ValidationError
from backend.domain.limits import MAX_SCORE, MAX_SCORE_PER_WAVE
from backend.domain.models import Position, Run
from backend.domain.validation import parse_limit, parse_run

RUN_ID = "5f0c7d0e-2b1a-4c47-9a3e-1d2b8f6a9c10"
NOW = datetime(2026, 11, 14, 18, 3, 12, tzinfo=UTC)


def valid_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "v": 1,
        "player_name": "Kuba",
        "arena": "arena_01",
        "score": 4200,
        "waves_survived": 7,
        "duration_s": 312.5,
        "death_position": {"x": -3.5, "y": 12.0},
        "killer_type": "grunt",
    }
    payload.update(overrides)
    return payload


def parse(payload: Any) -> Run:
    return parse_run(payload, run_id=RUN_ID, received_at=NOW)


def assert_rejected(payload: Any, field: str) -> None:
    with pytest.raises(ValidationError) as exc:
        parse(payload)
    assert exc.value.field == field


def test_valid_payload_becomes_run() -> None:
    run = parse(valid_payload())
    assert run.run_id == RUN_ID
    assert run.received_at == NOW
    assert run.player_name == "Kuba"
    assert run.arena == "arena_01"
    assert run.score == 4200
    assert run.waves_survived == 7
    assert run.duration_s == 312.5
    assert run.death_position == Position(x=-3.5, y=12.0)
    assert run.killer_type == "grunt"


def test_run_is_immutable() -> None:
    run = parse(valid_payload())
    with pytest.raises(AttributeError):
        run.score = 1  # type: ignore[misc]


def test_player_name_is_trimmed() -> None:
    assert parse(valid_payload(player_name="  Kuba  ")).player_name == "Kuba"


def test_killer_type_may_be_null() -> None:
    assert parse(valid_payload(killer_type=None)).killer_type is None


def test_integer_coordinates_and_duration_are_accepted() -> None:
    run = parse(valid_payload(duration_s=300, death_position={"x": 1, "y": -2}))
    assert run.duration_s == 300.0
    assert run.death_position == Position(x=1.0, y=-2.0)


@pytest.mark.parametrize("body", [None, [], "run", 42])
def test_body_must_be_an_object(body: Any) -> None:
    assert_rejected(body, "body")


@pytest.mark.parametrize("version", [0, 2, "1", None, True])
def test_version_must_be_1(version: Any) -> None:
    assert_rejected(valid_payload(v=version), "v")


def test_unknown_field_is_rejected() -> None:
    assert_rejected(valid_payload(is_admin=True), "is_admin")


@pytest.mark.parametrize(
    "field",
    ["v", "player_name", "arena", "score", "waves_survived", "duration_s", "death_position"],
)
def test_missing_required_field_is_rejected(field: str) -> None:
    payload = valid_payload()
    del payload[field]
    assert_rejected(payload, field)


def test_killer_type_key_is_required_even_if_null() -> None:
    payload = valid_payload()
    del payload["killer_type"]
    assert_rejected(payload, "killer_type")


@pytest.mark.parametrize(
    "name",
    ["ab", "x" * 17, "   ", "Kuba!", "<script>", "Ku\nba", "Kuba\u0000", 7, None],
)
def test_bad_player_names_are_rejected(name: Any) -> None:
    assert_rejected(valid_payload(player_name=name), "player_name")


@pytest.mark.parametrize("name", ["abc", "x" * 16, "Jakub K", "pro_gamer-1"])
def test_good_player_names_are_accepted(name: str) -> None:
    assert parse(valid_payload(player_name=name)).player_name == name


@pytest.mark.parametrize("arena", ["", "a" * 33, "Arena01", "../etc", "arena 1", 3])
def test_bad_arena_is_rejected(arena: Any) -> None:
    assert_rejected(valid_payload(arena=arena), "arena")


@pytest.mark.parametrize("score", [-1, MAX_SCORE + 1, 1.5, "100", True, None])
def test_bad_score_is_rejected(score: Any) -> None:
    assert_rejected(valid_payload(score=score, waves_survived=1000), "score")


def test_score_above_per_wave_cap_is_rejected() -> None:
    cap = (7 + 1) * MAX_SCORE_PER_WAVE
    assert parse(valid_payload(score=cap)).score == cap
    assert_rejected(valid_payload(score=cap + 1), "score")


@pytest.mark.parametrize("waves", [-1, 1001, 2.0, False])
def test_bad_waves_are_rejected(waves: Any) -> None:
    assert_rejected(valid_payload(waves_survived=waves, score=0), "waves_survived")


@pytest.mark.parametrize(
    "duration", [0, -1.0, 7200.1, float("nan"), float("inf"), "300", True, None]
)
def test_bad_duration_is_rejected(duration: Any) -> None:
    assert_rejected(valid_payload(duration_s=duration), "duration_s")


@pytest.mark.parametrize(
    "position",
    [
        None,
        [1, 2],
        {"x": 1},
        {"x": 1, "y": 2, "z": 3},
        {"x": 500.1, "y": 0},
        {"x": 0, "y": -500.1},
        {"x": float("nan"), "y": 0},
        {"x": "1", "y": 0},
        {"x": True, "y": 0},
    ],
)
def test_bad_death_position_is_rejected(position: Any) -> None:
    assert_rejected(valid_payload(death_position=position), "death_position")


@pytest.mark.parametrize("killer", ["", "Grunt", "a" * 33, "big grunt", 5])
def test_bad_killer_type_is_rejected(killer: Any) -> None:
    assert_rejected(valid_payload(killer_type=killer), "killer_type")


def test_error_message_names_the_field() -> None:
    with pytest.raises(ValidationError) as exc:
        parse(valid_payload(score=-1))
    assert str(exc.value).startswith("score: ")


@pytest.mark.parametrize(("raw", "expected"), [(None, 10), ("1", 1), ("10", 10), ("5", 5)])
def test_parse_limit_accepts_valid_values(raw: str | None, expected: int) -> None:
    assert parse_limit(raw) == expected


@pytest.mark.parametrize("raw", ["0", "11", "-1", "abc", "", "1.5", " 5"])
def test_parse_limit_rejects_bad_values(raw: str) -> None:
    with pytest.raises(ValidationError) as exc:
        parse_limit(raw)
    assert exc.value.field == "limit"
