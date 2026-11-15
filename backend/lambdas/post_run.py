"""POST /runs: validate a finished run, archive the raw event, save it to the leaderboard.

Environment: TABLE_NAME (DynamoDB leaderboard), BUCKET_NAME (S3 raw events).
"""

import functools
import os
from typing import Any

import boto3

from backend.adapters.dynamodb_runs import DynamoDbRunRepository
from backend.adapters.s3_events import S3EventArchive
from backend.domain.errors import ValidationError
from backend.domain.ports import EventArchive, RunRepository
from backend.domain.use_cases import submit_run
from backend.lambdas.http import (
    LOGGER,
    PayloadTooLargeError,
    internal_error,
    invalid_request,
    json_response,
    payload_too_large,
    read_json_body,
)


@functools.cache
def dependencies() -> tuple[RunRepository, EventArchive]:
    """Built once per Lambda container and reused by warm invocations."""
    table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    s3 = boto3.client("s3")
    return DynamoDbRunRepository(table), S3EventArchive(s3, os.environ["BUCKET_NAME"])


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    try:
        repository, archive = dependencies()
    except Exception:
        return internal_error()
    return handle(event, repository, archive)


def handle(
    event: dict[str, Any], repository: RunRepository, archive: EventArchive
) -> dict[str, Any]:
    try:
        run = submit_run(read_json_body(event), repository, archive)
    except ValidationError as exc:
        return invalid_request(exc)
    except PayloadTooLargeError:
        return payload_too_large()
    except Exception:
        return internal_error()
    LOGGER.info("run stored: run_id=%s", run.run_id)
    return json_response(201, {"run_id": run.run_id})
