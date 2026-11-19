"""Wave Arena backend stack (M4).

This stack: DynamoDB leaderboard table, S3 bucket for raw run events and the two Lambda
functions with hand-written least-privilege policies. The HTTP API, stage throttling and the
budget alert are added on top in issue #12, using the public attributes below.

Decisions: docs/adr/0004-dynamodb-leaderboard-keys.md (keys, PITR) and
docs/adr/0005-cdk-stack-data-and-iam.md (removal policies, lifecycle, IAM).
"""

from pathlib import Path
from typing import Any

import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from constructs import Construct

REPO_ROOT = Path(__file__).resolve().parents[2]

# Matches backend/adapters/s3_events.py (event_key): every raw event lives under this prefix.
RUN_EVENTS_PREFIX = "runs/"
RUN_EVENTS_EXPIRE_AFTER = cdk.Duration.days(730)

LAMBDA_TIMEOUT = cdk.Duration.seconds(10)
LAMBDA_MEMORY_MB = 256
LOG_RETENTION = logs.RetentionDays.ONE_MONTH

# The asset is the repo root filtered down to backend/ runtime code, so the handlers import
# `backend.lambdas.*` the same way as in tests. boto3 comes from the Lambda runtime.
CODE_EXCLUDES = [
    "*",
    # Glob `*` skips dot names (.git, .venv, .claude), so exclude them explicitly.
    ".*",
    "!backend",
    "!backend/**",
    # Only Python files: a stray backend/notes.txt or data dump must never be deployed.
    "backend/**/*.*",
    "!backend/**/*.py",
    "backend/tests",
    "backend/tests/**",
    "**/__pycache__",
    "**/*.pyc",
]


class WaveArenaStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        cdk.Tags.of(self).add("project", "wave-arena")

        self.table = self._leaderboard_table()
        self.bucket = self._events_bucket()
        code = lambda_.Code.from_asset(
            str(REPO_ROOT), exclude=CODE_EXCLUDES, ignore_mode=cdk.IgnoreMode.GLOB
        )

        self.post_run_function, self.post_run_log_group = self._function(
            "PostRun",
            code,
            "backend.lambdas.post_run.handler",
            {"TABLE_NAME": self.table.table_name, "BUCKET_NAME": self.bucket.bucket_name},
        )
        self.get_leaderboard_function, self.get_leaderboard_log_group = self._function(
            "GetLeaderboard",
            code,
            "backend.lambdas.get_leaderboard.handler",
            {"TABLE_NAME": self.table.table_name},
        )
        self._grant_post_run()
        self._grant_get_leaderboard()

    def _leaderboard_table(self) -> dynamodb.Table:
        return dynamodb.Table(
            self,
            "Leaderboard",
            partition_key=dynamodb.Attribute(name="board", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="rank_key", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            # ADR 0004: off, the leaderboard can be rebuilt from the S3 raw events.
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=False
            ),
            # ADR 0005: a rebuildable index, so it goes away with the stack.
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

    def _events_bucket(self) -> s3.Bucket:
        return s3.Bucket(
            self,
            "RunEvents",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            minimum_tls_version=1.2,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="expire-old-run-events",
                    prefix=RUN_EVENTS_PREFIX,
                    expiration=RUN_EVENTS_EXPIRE_AFTER,
                ),
                s3.LifecycleRule(
                    id="abort-incomplete-uploads",
                    abort_incomplete_multipart_upload_after=cdk.Duration.days(1),
                ),
            ],
            # ADR 0005: the raw events are the source of truth, keep them.
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

    def _function(
        self, name: str, code: lambda_.Code, handler: str, environment: dict[str, str]
    ) -> tuple[lambda_.Function, logs.LogGroup]:
        # Own log group and role: no log-retention helper Lambda and no
        # AWSLambdaBasicExecutionRole, whose log permissions use Resource "*".
        log_group = logs.LogGroup(
            self,
            f"{name}Logs",
            retention=LOG_RETENTION,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        role = iam.Role(
            self,
            f"{name}Role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        function = lambda_.Function(
            self,
            name,
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            code=code,
            handler=handler,
            timeout=LAMBDA_TIMEOUT,
            memory_size=LAMBDA_MEMORY_MB,
            environment=environment,
            role=role,
            log_group=log_group,
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                resources=[log_group.log_group_arn],
            )
        )
        return function, log_group

    def _grant_post_run(self) -> None:
        # Hand-written instead of grant_write_data / grant_put: those add BatchWriteItem,
        # UpdateItem, DeleteItem, DescribeTable and s3:Abort*, PutObjectLegalHold etc.
        # The adapters call exactly table.put_item and s3.put_object under runs/.
        self.post_run_function.add_to_role_policy(
            iam.PolicyStatement(actions=["dynamodb:PutItem"], resources=[self.table.table_arn])
        )
        self.post_run_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject"],
                resources=[self.bucket.arn_for_objects(f"{RUN_EVENTS_PREFIX}*")],
            )
        )

    def _grant_get_leaderboard(self) -> None:
        # grant_read_data would add GetItem, BatchGetItem, Scan, DescribeTable and stream reads;
        # the adapter only runs table.query (ADR 0004).
        self.get_leaderboard_function.add_to_role_policy(
            iam.PolicyStatement(actions=["dynamodb:Query"], resources=[self.table.table_arn])
        )
