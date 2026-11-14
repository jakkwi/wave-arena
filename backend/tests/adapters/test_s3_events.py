import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

from backend.adapters.s3_events import S3EventArchive, event_key
from backend.domain.events import run_to_event
from backend.domain.ports import EventArchive
from backend.tests.adapters.conftest import BUCKET_NAME
from backend.tests.domain.test_events import RUN

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


def stored_keys(s3: "S3Client") -> list[str]:
    return [obj["Key"] for obj in s3.list_objects_v2(Bucket=BUCKET_NAME).get("Contents", [])]


def test_adapter_implements_the_port(events_bucket: "S3Client") -> None:
    archive: EventArchive = S3EventArchive(events_bucket, BUCKET_NAME)
    assert archive is not None


def test_store_writes_one_object_under_a_date_key(events_bucket: "S3Client") -> None:
    S3EventArchive(events_bucket, BUCKET_NAME).store(RUN)
    assert stored_keys(events_bucket) == [
        "runs/2026/11/14/5f0c7d0e-2b1a-4c47-9a3e-1d2b8f6a9c10.json"
    ]


def test_body_round_trips_as_the_domain_event(events_bucket: "S3Client") -> None:
    S3EventArchive(events_bucket, BUCKET_NAME).store(RUN)
    obj = events_bucket.get_object(Bucket=BUCKET_NAME, Key=event_key(RUN))
    assert obj["ContentType"] == "application/json"
    assert json.loads(obj["Body"].read()) == run_to_event(RUN)


def test_each_run_gets_its_own_object(events_bucket: "S3Client") -> None:
    archive = S3EventArchive(events_bucket, BUCKET_NAME)
    archive.store(RUN)
    archive.store(replace(RUN, run_id="0b1c2d3e-0000-4000-8000-000000000001"))
    assert len(stored_keys(events_bucket)) == 2


def test_date_in_key_is_utc() -> None:
    # 00:30 on the 15th at UTC+2 is still the 14th in UTC.
    late = datetime(2026, 11, 15, 0, 30, tzinfo=timezone(timedelta(hours=2)))
    assert event_key(replace(RUN, received_at=late)).startswith("runs/2026/11/14/")


def test_month_and_day_are_zero_padded() -> None:
    early = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    assert event_key(replace(RUN, received_at=early)).startswith("runs/2026/01/05/")


@pytest.mark.parametrize(
    "run_id", ["", "../../etc/passwd", "a/b", "id with space", "x" * 65, "id\n", "id.json"]
)
def test_unsafe_run_id_never_reaches_the_key(run_id: str) -> None:
    with pytest.raises(ValueError, match="run_id"):
        event_key(replace(RUN, run_id=run_id))


def test_unsafe_run_id_writes_nothing(events_bucket: "S3Client") -> None:
    with pytest.raises(ValueError):
        S3EventArchive(events_bucket, BUCKET_NAME).store(replace(RUN, run_id="../x"))
    assert stored_keys(events_bucket) == []
