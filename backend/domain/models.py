"""Domain models. Immutable, already validated: build them through validation.parse_run."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Position:
    """A point in arena space, meters."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Run:
    """One finished run as stored by the backend."""

    run_id: str
    received_at: datetime
    player_name: str
    arena: str
    score: int
    waves_survived: int
    duration_s: float
    death_position: Position
    killer_type: str | None


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    """The public view of a run on the leaderboard. No ids, no telemetry."""

    rank: int
    player_name: str
    score: int
    waves_survived: int
    submitted_at: datetime
