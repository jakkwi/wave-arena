"""Raw run event: the record archived for analytics (M6). Format documented in docs/api.md.

Pure: builds plain JSON-ready data. Writing it somewhere is an adapter's job.
"""

from datetime import UTC, datetime

from backend.domain.models import Run

EVENT_VERSION = 1
# Fixed width (microseconds always present) so that string order equals time order.
UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def format_utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime(UTC_FORMAT)


def parse_utc(text: str) -> datetime:
    return datetime.strptime(text, UTC_FORMAT).replace(tzinfo=UTC)


def run_to_event(run: Run) -> dict[str, object]:
    return {
        "v": EVENT_VERSION,
        "run_id": run.run_id,
        "received_at": format_utc(run.received_at),
        "player_name": run.player_name,
        "arena": run.arena,
        "score": run.score,
        "waves_survived": run.waves_survived,
        "duration_s": run.duration_s,
        "death_position": {"x": run.death_position.x, "y": run.death_position.y},
        "killer_type": run.killer_type,
    }
