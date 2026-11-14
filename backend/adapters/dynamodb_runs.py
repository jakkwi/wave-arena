"""DynamoDB implementation of RunRepository. Key design: docs/adr/0004-dynamodb-leaderboard-keys.md.

No business rules here: the adapter maps Run to an item and back, and runs one Query.
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import TYPE_CHECKING

from boto3.dynamodb.conditions import Key

from backend.domain import limits
from backend.domain.events import format_utc, parse_utc
from backend.domain.models import Position, Run

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

DEFAULT_BOARD = "global"
SCORE_DIGITS = len(str(limits.MAX_SCORE))
WAVES_DIGITS = len(str(limits.MAX_WAVES))


def rank_key(run: Run) -> str:
    """Sort key whose ascending string order is the leaderboard order (ADR 0004)."""
    inverted_score = limits.MAX_SCORE - run.score
    inverted_waves = limits.MAX_WAVES - run.waves_survived
    return (
        f"{inverted_score:0{SCORE_DIGITS}d}#{inverted_waves:0{WAVES_DIGITS}d}"
        f"#{format_utc(run.received_at)}#{run.run_id}"
    )


class DynamoDbRunRepository:
    def __init__(self, table: "Table", board: str = DEFAULT_BOARD) -> None:
        self._table = table
        self._board = board

    def save(self, run: Run) -> None:
        item: dict[str, str | int | Decimal] = {
            "board": self._board,
            "rank_key": rank_key(run),
            "run_id": run.run_id,
            "received_at": format_utc(run.received_at),
            "player_name": run.player_name,
            "arena": run.arena,
            "score": run.score,
            "waves_survived": run.waves_survived,
            # The DynamoDB resource API rejects float: numbers go in as Decimal.
            "duration_s": Decimal(str(run.duration_s)),
            "death_x": Decimal(str(run.death_position.x)),
            "death_y": Decimal(str(run.death_position.y)),
        }
        if run.killer_type is not None:
            item["killer_type"] = run.killer_type
        self._table.put_item(Item=item)

    def top(self, limit: int) -> list[Run]:
        response = self._table.query(
            KeyConditionExpression=Key("board").eq(self._board),
            ScanIndexForward=True,
            Limit=limit,
        )
        return [_to_run(item) for item in response.get("Items", [])]


def _to_run(item: Mapping[str, object]) -> Run:
    killer = item.get("killer_type")
    return Run(
        run_id=_text(item, "run_id"),
        received_at=parse_utc(_text(item, "received_at")),
        player_name=_text(item, "player_name"),
        arena=_text(item, "arena"),
        score=int(_number(item, "score")),
        waves_survived=int(_number(item, "waves_survived")),
        duration_s=float(_number(item, "duration_s")),
        death_position=Position(
            x=float(_number(item, "death_x")), y=float(_number(item, "death_y"))
        ),
        killer_type=killer if isinstance(killer, str) else None,
    )


def _text(item: Mapping[str, object], name: str) -> str:
    value = item[name]
    if not isinstance(value, str):
        raise TypeError(f"{name}: expected a string in the stored item")
    return value


def _number(item: Mapping[str, object], name: str) -> Decimal:
    value = item[name]
    if not isinstance(value, Decimal):
        raise TypeError(f"{name}: expected a number in the stored item")
    return value
