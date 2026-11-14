"""moto fixtures. Fake credentials only: tests never reach a real AWS account."""

from collections.abc import Iterator
from typing import TYPE_CHECKING

import boto3
import pytest
from moto import mock_aws

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table
    from mypy_boto3_s3.client import S3Client

REGION = "eu-central-1"
TABLE_NAME = "wave-arena-test-runs"
BUCKET_NAME = "wave-arena-test-events"


@pytest.fixture(autouse=True)
def fake_aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.delenv("AWS_PROFILE", raising=False)


@pytest.fixture
def runs_table() -> Iterator["Table"]:
    """The leaderboard table with the keys from ADR 0004."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "board", "KeyType": "HASH"},
                {"AttributeName": "rank_key", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "board", "AttributeType": "S"},
                {"AttributeName": "rank_key", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def events_bucket() -> Iterator["S3Client"]:
    """An S3 client with the raw events bucket created."""
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": "eu-central-1"},
        )
        yield s3
