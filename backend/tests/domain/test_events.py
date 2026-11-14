import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

from backend.domain.events import EVENT_VERSION, run_to_event
from backend.domain.models import Position, Run

RUN = Run(
    run_id="5f0c7d0e-2b1a-4c47-9a3e-1d2b8f6a9c10",
    received_at=datetime(2026, 11, 14, 18, 3, 12, 5000, tzinfo=UTC),
    player_name="Kuba",
    arena="arena_01",
    score=4200,
    waves_survived=7,
    duration_s=312.5,
    death_position=Position(x=-3.5, y=12.0),
    killer_type="grunt",
)


def test_event_has_every_field_for_analytics() -> None:
    assert run_to_event(RUN) == {
        "v": EVENT_VERSION,
        "run_id": "5f0c7d0e-2b1a-4c47-9a3e-1d2b8f6a9c10",
        "received_at": "2026-11-14T18:03:12.005000Z",
        "player_name": "Kuba",
        "arena": "arena_01",
        "score": 4200,
        "waves_survived": 7,
        "duration_s": 312.5,
        "death_position": {"x": -3.5, "y": 12.0},
        "killer_type": "grunt",
    }


def test_null_killer_type_is_kept_as_null() -> None:
    assert run_to_event(replace(RUN, killer_type=None))["killer_type"] is None


def test_received_at_is_converted_to_utc() -> None:
    plus_two = timezone(timedelta(hours=2))
    run = replace(RUN, received_at=datetime(2026, 11, 14, 20, 3, 12, 5000, tzinfo=plus_two))
    assert run_to_event(run)["received_at"] == "2026-11-14T18:03:12.005000Z"


def test_event_is_json_serializable() -> None:
    assert json.loads(json.dumps(run_to_event(RUN)))["score"] == 4200
