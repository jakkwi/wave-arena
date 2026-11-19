"""Assertion tests for WaveArenaStack: table, bucket, Lambdas and their exact IAM policies."""

import json
import re
from pathlib import Path
from typing import Any

import aws_cdk as cdk
import aws_cdk.cx_api as cxapi
import pytest
from aws_cdk.assertions import Match, Template

from infra.wave_arena_infra.stack import WaveArenaStack

REPO_ROOT = Path(__file__).resolve().parents[2]
CDK_JSON = REPO_ROOT / "infra" / "cdk.json"
HANDLERS = REPO_ROOT / "backend" / "lambdas"
ENV_READ = re.compile(r"""os\.environ\[["']([A-Z_]+)["']\]""")


@pytest.fixture(scope="module")
def stack(tmp_path_factory: pytest.TempPathFactory) -> WaveArenaStack:
    # Same feature flags as `cdk synth`, so policies are rendered the same way.
    context = json.loads(CDK_JSON.read_text(encoding="utf-8"))["context"]
    outdir = tmp_path_factory.mktemp("cdk.out")
    app = cdk.App(context=context, outdir=str(outdir))
    return WaveArenaStack(app, "TestStack")


@pytest.fixture(scope="module")
def assembly(stack: WaveArenaStack) -> cxapi.CloudAssembly:
    """The app is synthesized once; template and asset tests read the same output."""
    app = stack.node.root
    assert isinstance(app, cdk.App)
    return app.synth()


@pytest.fixture(scope="module")
def template(stack: WaveArenaStack, assembly: cxapi.CloudAssembly) -> Template:
    return Template.from_json(assembly.get_stack_by_name(stack.stack_name).template)


def logical_id(stack: WaveArenaStack, construct: Any) -> str:
    return stack.resolve(construct.node.default_child.logical_id)  # type: ignore[no-any-return]


def get_att(resource_id: str) -> dict[str, Any]:
    return {"Fn::GetAtt": [resource_id, "Arn"]}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def role_statements(template: Template, role_id: str) -> list[dict[str, Any]]:
    """All statements of every IAM policy attached to one role, actions normalised to lists."""
    statements = []
    for policy in template.find_resources("AWS::IAM::Policy").values():
        props = policy["Properties"]
        if {"Ref": role_id} not in props["Roles"]:
            continue
        for statement in props["PolicyDocument"]["Statement"]:
            statements.append(
                {
                    "Effect": statement["Effect"],
                    "Action": sorted(as_list(statement["Action"])),
                    "Resource": as_list(statement["Resource"]),
                }
            )
    return statements


def sort_statements(statements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(statements, key=lambda s: json.dumps(s, sort_keys=True))


# --- DynamoDB ---------------------------------------------------------------------------


def test_one_on_demand_table_with_adr_0004_keys(template: Template) -> None:
    template.resource_count_is("AWS::DynamoDB::Table", 1)
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "BillingMode": "PAY_PER_REQUEST",
            "KeySchema": [
                {"AttributeName": "board", "KeyType": "HASH"},
                {"AttributeName": "rank_key", "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": Match.array_equals(
                [
                    {"AttributeName": "board", "AttributeType": "S"},
                    {"AttributeName": "rank_key", "AttributeType": "S"},
                ]
            ),
        },
    )


def test_table_has_no_secondary_indexes(template: Template) -> None:
    table = next(iter(template.find_resources("AWS::DynamoDB::Table").values()))
    assert "GlobalSecondaryIndexes" not in table["Properties"]
    assert "LocalSecondaryIndexes" not in table["Properties"]


def test_table_pitr_is_off_by_decision(template: Template) -> None:
    # ADR 0004: the leaderboard can be rebuilt from the S3 raw events.
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "PointInTimeRecoverySpecification": {"PointInTimeRecoveryEnabled": False},
        },
    )


def test_table_is_deleted_with_the_stack(template: Template) -> None:
    # ADR 0005: the table is a rebuildable index of the S3 events.
    template.has_resource("AWS::DynamoDB::Table", {"DeletionPolicy": "Delete"})


# --- S3 ---------------------------------------------------------------------------------


def test_bucket_blocks_all_public_access(template: Template) -> None:
    template.resource_count_is("AWS::S3::Bucket", 1)
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
        },
    )


def test_bucket_is_encrypted_with_s3_managed_keys(template: Template) -> None:
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
        },
    )


def test_bucket_disables_acls(template: Template) -> None:
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {"OwnershipControls": {"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]}},
    )


def test_bucket_policy_denies_requests_without_tls(
    stack: WaveArenaStack, template: Template
) -> None:
    bucket_id = logical_id(stack, stack.bucket)
    template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "Bucket": {"Ref": bucket_id},
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Effect": "Deny",
                                "Action": "s3:*",
                                "Principal": {"AWS": "*"},
                                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                            }
                        )
                    ]
                )
            },
        },
    )


def test_bucket_policy_denies_tls_below_1_2(template: Template) -> None:
    template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Effect": "Deny",
                                "Action": "s3:*",
                                "Condition": {"NumericLessThan": {"s3:TlsVersion": 1.2}},
                            }
                        )
                    ]
                )
            },
        },
    )


def test_bucket_lifecycle_expires_old_events_and_aborts_uploads(template: Template) -> None:
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "LifecycleConfiguration": {
                "Rules": [
                    {
                        "Id": "expire-old-run-events",
                        "Status": "Enabled",
                        "Prefix": "runs/",
                        "ExpirationInDays": 730,
                    },
                    {
                        "Id": "abort-incomplete-uploads",
                        "Status": "Enabled",
                        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                    },
                ]
            }
        },
    )


def test_bucket_is_kept_when_the_stack_is_deleted(template: Template) -> None:
    # ADR 0005: the raw events are the source of truth.
    template.has_resource("AWS::S3::Bucket", {"DeletionPolicy": "Retain"})


def test_no_custom_resource_lambdas(template: Template) -> None:
    # Only our two functions: no auto-delete or log-retention helper Lambdas with broad roles.
    template.resource_count_is("AWS::Lambda::Function", 2)


# --- Lambda -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("attr", "handler", "env"),
    [
        ("post_run_function", "backend.lambdas.post_run.handler", {"TABLE_NAME", "BUCKET_NAME"}),
        ("get_leaderboard_function", "backend.lambdas.get_leaderboard.handler", {"TABLE_NAME"}),
    ],
)
def test_function_settings(
    stack: WaveArenaStack, template: Template, attr: str, handler: str, env: set[str]
) -> None:
    function = getattr(stack, attr)
    resource = template.find_resources("AWS::Lambda::Function")[logical_id(stack, function)]
    props = resource["Properties"]
    assert props["Runtime"] == "python3.12"
    assert props["Handler"] == handler
    assert props["Architectures"] == ["arm64"]
    assert props["Timeout"] == 10
    assert props["MemorySize"] == 256
    assert set(props["Environment"]["Variables"]) == env


def test_environment_points_at_the_stack_resources(
    stack: WaveArenaStack, template: Template
) -> None:
    table_ref = {"Ref": logical_id(stack, stack.table)}
    bucket_ref = {"Ref": logical_id(stack, stack.bucket)}
    functions = template.find_resources("AWS::Lambda::Function")
    post_run = functions[logical_id(stack, stack.post_run_function)]["Properties"]
    get_top = functions[logical_id(stack, stack.get_leaderboard_function)]["Properties"]
    assert post_run["Environment"]["Variables"] == {
        "TABLE_NAME": table_ref,
        "BUCKET_NAME": bucket_ref,
    }
    assert get_top["Environment"]["Variables"] == {"TABLE_NAME": table_ref}


def test_each_function_logs_to_its_own_log_group_with_retention(
    stack: WaveArenaStack, template: Template
) -> None:
    template.resource_count_is("AWS::Logs::LogGroup", 2)
    template.all_resources_properties("AWS::Logs::LogGroup", {"RetentionInDays": 30})
    functions = template.find_resources("AWS::Lambda::Function")
    for function, log_group in (
        (stack.post_run_function, stack.post_run_log_group),
        (stack.get_leaderboard_function, stack.get_leaderboard_log_group),
    ):
        props = functions[logical_id(stack, function)]["Properties"]
        assert props["LoggingConfig"]["LogGroup"] == {"Ref": logical_id(stack, log_group)}


def test_environment_matches_what_the_handlers_read(
    stack: WaveArenaStack, template: Template
) -> None:
    # A renamed variable in a handler would otherwise only fail at runtime with KeyError.
    functions = template.find_resources("AWS::Lambda::Function")
    for function, module in (
        (stack.post_run_function, "post_run.py"),
        (stack.get_leaderboard_function, "get_leaderboard.py"),
    ):
        read = set(ENV_READ.findall((HANDLERS / module).read_text(encoding="utf-8")))
        props = functions[logical_id(stack, function)]["Properties"]
        assert read == set(props["Environment"]["Variables"]), module


def test_code_asset_contains_only_runtime_backend_code(assembly: cxapi.CloudAssembly) -> None:
    asset_dirs = [p for p in Path(assembly.directory).glob("asset.*") if p.is_dir()]
    assert len(asset_dirs) == 1, "both functions share one code asset"
    files = {p.relative_to(asset_dirs[0]).as_posix() for p in asset_dirs[0].rglob("*")}
    assert "backend/lambdas/post_run.py" in files
    assert "backend/lambdas/get_leaderboard.py" in files
    assert "backend/domain/use_cases.py" in files
    assert "backend/adapters/dynamodb_runs.py" in files
    assert not any(f.startswith("backend/tests") for f in files)
    assert not any("__pycache__" in f for f in files)
    assert not any(not f.startswith("backend") for f in files)
    assert all(f.endswith(".py") for f in files if (asset_dirs[0] / f).is_file())


# --- IAM --------------------------------------------------------------------------------


def test_roles_trust_only_lambda_and_have_no_managed_policies(template: Template) -> None:
    roles = template.find_resources("AWS::IAM::Role")
    assert len(roles) == 2
    for role in roles.values():
        props = role["Properties"]
        assert "ManagedPolicyArns" not in props
        assert props["AssumeRolePolicyDocument"]["Statement"] == [
            {
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
            }
        ]


def test_post_run_policy_is_exactly_put_item_put_object_and_logs(
    stack: WaveArenaStack, template: Template
) -> None:
    role_id = logical_id(stack, stack.post_run_function.role)
    bucket_arn = get_att(logical_id(stack, stack.bucket))
    expected = [
        {
            "Effect": "Allow",
            "Action": ["dynamodb:PutItem"],
            "Resource": [get_att(logical_id(stack, stack.table))],
        },
        {
            "Effect": "Allow",
            "Action": ["s3:PutObject"],
            "Resource": [{"Fn::Join": ["", [bucket_arn, "/runs/*"]]}],
        },
        {
            "Effect": "Allow",
            "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
            "Resource": [get_att(logical_id(stack, stack.post_run_log_group))],
        },
    ]
    assert sort_statements(role_statements(template, role_id)) == sort_statements(expected)


def test_get_leaderboard_policy_is_exactly_query_and_logs(
    stack: WaveArenaStack, template: Template
) -> None:
    role_id = logical_id(stack, stack.get_leaderboard_function.role)
    expected = [
        {
            "Effect": "Allow",
            "Action": ["dynamodb:Query"],
            "Resource": [get_att(logical_id(stack, stack.table))],
        },
        {
            "Effect": "Allow",
            "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
            "Resource": [get_att(logical_id(stack, stack.get_leaderboard_log_group))],
        },
    ]
    assert sort_statements(role_statements(template, role_id)) == sort_statements(expected)


def test_no_wildcard_actions_or_resources_in_identity_policies(template: Template) -> None:
    for policy in template.find_resources("AWS::IAM::Policy").values():
        for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
            assert statement["Effect"] == "Allow"
            for action in as_list(statement["Action"]):
                assert "*" not in action
            # Prefix wildcards such as <bucket>/runs/* are Fn::Join dicts, not "*", and intended.
            for resource in as_list(statement["Resource"]):
                assert resource != "*"


def test_stack_is_tagged(template: Template) -> None:
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {"Tags": Match.array_with([{"Key": "project", "Value": "wave-arena"}])},
    )
