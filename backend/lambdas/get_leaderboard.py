"""GET /leaderboard: the best runs, ranked by the domain.

Environment: TABLE_NAME (DynamoDB leaderboard).
"""

import functools
import os
from datetime import UTC
from typing import Any

import boto3

from backend.adapters.dynamodb_runs import DynamoDbRunRepository
from backend.domain.errors import ValidationError
from backend.domain.models import LeaderboardEntry
from backend.domain.ports import RunRepository
from backend.domain.use_cases import get_top
from backend.domain.validation import parse_limit
from backend.lambdas.http import internal_error, invalid_request, json_response, query_parameter


@functools.cache
def dependencies() -> RunRepository:
    """Built once per Lambda container and reused by warm invocations."""
    table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return DynamoDbRunRepository(table)


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    try:
        repository = dependencies()
    except Exception:
        return internal_error()
    return handle(event, repository)


def handle(event: dict[str, Any], repository: RunRepository) -> dict[str, Any]:
    try:
        entries = get_top(repository, parse_limit(query_parameter(event, "limit")))
    except ValidationError as exc:
        return invalid_request(exc)
    except Exception:
        return internal_error()
    return json_response(200, {"entries": [_entry_json(e) for e in entries]})


def _entry_json(entry: LeaderboardEntry) -> dict[str, Any]:
    return {
        "rank": entry.rank,
        "player_name": entry.player_name,
        "score": entry.score,
        "waves_survived": entry.waves_survived,
        "submitted_at": entry.submitted_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
