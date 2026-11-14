"""Turns untrusted JSON from the game client into a valid Run. Fails closed.

Rules are documented in docs/api.md. Each check raises ValidationError naming the field.
"""

import math
import re
from collections.abc import Mapping
from datetime import datetime

from backend.domain import limits
from backend.domain.errors import ValidationError
from backend.domain.models import Position, Run

FIELDS = frozenset(
    {
        "v",
        "player_name",
        "arena",
        "score",
        "waves_survived",
        "duration_s",
        "death_position",
        "killer_type",
    }
)
PLAYER_NAME = re.compile(rf"[A-Za-z0-9 _-]{{{limits.PLAYER_NAME_MIN},{limits.PLAYER_NAME_MAX}}}")
IDENTIFIER = re.compile(rf"[a-z0-9_]{{1,{limits.ID_MAX}}}")
LIMIT = re.compile(r"[0-9]{1,2}")


def parse_run(payload: object, *, run_id: str, received_at: datetime) -> Run:
    body = _require_object(payload)
    _require_fields(body)
    if _int(body["v"], "v", 0, 1_000) != limits.API_VERSION:
        raise ValidationError("v", f"unsupported version, expected {limits.API_VERSION}")

    waves = _int(body["waves_survived"], "waves_survived", 0, limits.MAX_WAVES)
    score = _int(body["score"], "score", 0, limits.MAX_SCORE)
    if score > (waves + 1) * limits.MAX_SCORE_PER_WAVE:
        raise ValidationError("score", "too high for the number of waves")

    return Run(
        run_id=run_id,
        received_at=received_at,
        player_name=_player_name(body["player_name"]),
        arena=_identifier(body["arena"], "arena"),
        score=score,
        waves_survived=waves,
        duration_s=_duration(body["duration_s"]),
        death_position=_position(body["death_position"]),
        killer_type=None
        if body["killer_type"] is None
        else _identifier(body["killer_type"], "killer_type"),
    )


def parse_limit(raw: str | None) -> int:
    """Parse the `limit` query parameter of GET /leaderboard."""
    if raw is None:
        return limits.LEADERBOARD_DEFAULT_LIMIT
    if not LIMIT.fullmatch(raw):
        raise ValidationError("limit", "must be an integer")
    return check_limit(int(raw))


def check_limit(limit: int) -> int:
    if not 1 <= limit <= limits.LEADERBOARD_MAX_LIMIT:
        raise ValidationError("limit", f"must be between 1 and {limits.LEADERBOARD_MAX_LIMIT}")
    return limit


def _require_object(payload: object) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise ValidationError("body", "must be a JSON object")
    return payload


def _require_fields(body: Mapping[str, object]) -> None:
    unknown = sorted(set(body) - FIELDS)
    if unknown:
        raise ValidationError(str(unknown[0]), "unknown field")
    missing = sorted(FIELDS - set(body))
    if missing:
        raise ValidationError(missing[0], "required")


def _int(value: object, field: str, low: int, high: int) -> int:
    # bool is a subclass of int in Python: reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(field, "must be an integer")
    if not low <= value <= high:
        raise ValidationError(field, f"must be between {low} and {high}")
    return value


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValidationError(field, "must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError(field, "must be finite")
    return number


def _duration(value: object) -> float:
    duration = _number(value, "duration_s")
    if not 0 < duration <= limits.MAX_DURATION_S:
        raise ValidationError("duration_s", f"must be above 0 and at most {limits.MAX_DURATION_S}")
    return duration


def _position(value: object) -> Position:
    if not isinstance(value, Mapping) or set(value) != {"x", "y"}:
        raise ValidationError("death_position", "must be an object with x and y only")
    coords = []
    for axis in ("x", "y"):
        try:
            coord = _number(value[axis], "death_position")
        except ValidationError as exc:
            raise ValidationError("death_position", f"{axis} {exc.message}") from None
        if abs(coord) > limits.MAX_COORDINATE:
            raise ValidationError(
                "death_position", f"{axis} must be within {limits.MAX_COORDINATE} of the center"
            )
        coords.append(coord)
    return Position(x=coords[0], y=coords[1])


def _player_name(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("player_name", "must be a string")
    name = value.strip(" ")
    if not PLAYER_NAME.fullmatch(name):
        raise ValidationError(
            "player_name",
            f"{limits.PLAYER_NAME_MIN} to {limits.PLAYER_NAME_MAX} letters, digits, spaces, _ or -",
        )
    return name


def _identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValidationError(field, f"1 to {limits.ID_MAX} lowercase letters, digits or _")
    return value
