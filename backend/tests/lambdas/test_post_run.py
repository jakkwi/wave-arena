import json
import logging
import uuid
from typing import TYPE_CHECKING

import pytest

from backend.domain.limits import MAX_BODY_BYTES
from backend.lambdas import post_run
from backend.tests.adapters.conftest import BUCKET_NAME, TABLE_NAME
from backend.tests.domain.test_validation import valid_payload
from backend.tests.fakes import FailingRunRepository, InMemoryEventArchive, InMemoryRunRepository
from backend.tests.lambdas.events import http_event, response_json

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table
    from mypy_boto3_s3.client import S3Client


def post(body: str | None, *, base64_encoded: bool = False) -> dict[str, object]:
    return http_event("POST", "/runs", body=body, base64_encoded=base64_encoded)


def handle(
    event: dict[str, object],
    repo: InMemoryRunRepository | None = None,
    archive: InMemoryEventArchive | None = None,
) -> dict[str, object]:
    return post_run.handle(
        event, repo or InMemoryRunRepository(), archive or InMemoryEventArchive()
    )


def assert_error(response: dict[str, object], status: int, code: str) -> str:
    assert response["statusCode"] == status
    body = response_json(response)
    assert body["v"] == 1
    assert body["error"] == code
    message = body["message"]
    assert isinstance(message, str)
    return message


def test_valid_run_returns_201_with_server_run_id() -> None:
    repo, archive = InMemoryRunRepository(), InMemoryEventArchive()
    response = handle(post(json.dumps(valid_payload())), repo, archive)
    assert response["statusCode"] == 201
    body = response_json(response)
    assert body["v"] == 1
    assert uuid.UUID(body["run_id"]).version == 4
    assert [r.run_id for r in repo.runs] == [body["run_id"]]
    assert [r.run_id for r in archive.events] == [body["run_id"]]


def test_base64_body_is_decoded() -> None:
    response = handle(post(json.dumps(valid_payload()), base64_encoded=True))
    assert response["statusCode"] == 201


@pytest.mark.parametrize("body", [None, "", "not json", "{", "[1, 2]", "null", '{"v": 1,}'])
def test_unusable_body_returns_400_and_stores_nothing(body: str | None) -> None:
    repo, archive = InMemoryRunRepository(), InMemoryEventArchive()
    assert_error(handle(post(body), repo, archive), 400, "invalid_request")
    assert repo.runs == []
    assert archive.events == []


def test_validation_error_names_the_field() -> None:
    message = assert_error(
        handle(post(json.dumps(valid_payload(score=-1)))), 400, "invalid_request"
    )
    assert message.startswith("score: ")


def test_nan_literal_is_rejected() -> None:
    body = json.dumps(valid_payload()).replace("312.5", "NaN")
    message = assert_error(handle(post(body)), 400, "invalid_request")
    assert message.startswith("duration_s: ")


def test_bad_base64_returns_400() -> None:
    event = post("%%% not base64 %%%")
    event["isBase64Encoded"] = True
    assert_error(handle(event), 400, "invalid_request")


def test_non_utf8_body_returns_400() -> None:
    event = post(None)
    event["body"] = "/w=="  # base64 of the single byte 0xff
    event["isBase64Encoded"] = True
    assert_error(handle(event), 400, "invalid_request")


def test_body_at_the_limit_is_accepted() -> None:
    body = json.dumps(valid_payload())
    padded = body + " " * (MAX_BODY_BYTES - len(body.encode("utf-8")))
    assert len(padded.encode("utf-8")) == MAX_BODY_BYTES
    assert handle(post(padded))["statusCode"] == 201


@pytest.mark.parametrize("base64_encoded", [False, True])
def test_body_over_the_limit_returns_413(base64_encoded: bool) -> None:
    body = json.dumps(valid_payload()) + " " * MAX_BODY_BYTES
    repo = InMemoryRunRepository()
    response = handle(post(body, base64_encoded=base64_encoded), repo)
    assert_error(response, 413, "payload_too_large")
    assert repo.runs == []


def test_unexpected_error_returns_500_without_details(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    response = post_run.handle(
        post(json.dumps(valid_payload(player_name="SecretName"))),
        FailingRunRepository(),
        InMemoryEventArchive(),
    )
    message = assert_error(response, 500, "internal_error")
    assert "table unavailable" not in message
    assert "table unavailable" in caplog.text
    assert "SecretName" not in caplog.text


def test_handler_wires_real_adapters(
    runs_table: "Table", events_bucket: "S3Client", monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)
    monkeypatch.setenv("BUCKET_NAME", BUCKET_NAME)
    post_run.dependencies.cache_clear()
    try:
        response = post_run.handler(post(json.dumps(valid_payload())), None)
    finally:
        post_run.dependencies.cache_clear()
    assert response["statusCode"] == 201
    assert runs_table.scan()["Count"] == 1
    assert events_bucket.list_objects_v2(Bucket=BUCKET_NAME)["KeyCount"] == 1
