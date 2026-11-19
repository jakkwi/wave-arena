"""Assertion tests for the public HTTP API, its throttling and invoke permissions, and the
5 USD budget alert (issue #12, ADR 0006)."""

import json
import re
from typing import Any

import pytest
from aws_cdk.assertions import Match, Template

from infra.tests.cdk_helpers import get_att, logical_id
from infra.wave_arena_infra.stack import WaveArenaStack

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def resource_props(template: Template, resource_type: str) -> dict[str, Any]:
    resources = template.find_resources(resource_type)
    assert len(resources) == 1, resource_type
    return next(iter(resources.values()))["Properties"]  # type: ignore[no-any-return]


# --- API --------------------------------------------------------------------------------


def test_one_http_api_without_cors(template: Template) -> None:
    # The game client is a native app, not a browser page: no CORS headers at all, so no
    # web page on another origin can read the API from a visitor's browser (ADR 0006).
    template.resource_count_is("AWS::ApiGatewayV2::Api", 1)
    props = resource_props(template, "AWS::ApiGatewayV2::Api")
    assert props["ProtocolType"] == "HTTP"
    assert "CorsConfiguration" not in props


@pytest.mark.parametrize(
    ("route_key", "function_attr"),
    [
        ("POST /runs", "post_run_function"),
        ("GET /leaderboard", "get_leaderboard_function"),
    ],
)
def test_route_integrates_its_lambda_with_payload_v2(
    stack: WaveArenaStack, template: Template, route_key: str, function_attr: str
) -> None:
    routes = template.find_resources(
        "AWS::ApiGatewayV2::Route", {"Properties": {"RouteKey": route_key}}
    )
    assert len(routes) == 1, route_key
    route = next(iter(routes.values()))["Properties"]
    assert route["AuthorizationType"] == "NONE"

    target = json.dumps(route["Target"])
    integrations = template.find_resources("AWS::ApiGatewayV2::Integration")
    matching = [props["Properties"] for iid, props in integrations.items() if f'"{iid}"' in target]
    assert len(matching) == 1
    integration = matching[0]
    assert integration["IntegrationType"] == "AWS_PROXY"
    assert integration["PayloadFormatVersion"] == "2.0"
    function_id = logical_id(stack, getattr(stack, function_attr))
    assert integration["IntegrationUri"] == get_att(function_id)


def test_only_the_two_documented_routes_exist(template: Template) -> None:
    routes = template.find_resources("AWS::ApiGatewayV2::Route")
    keys = sorted(r["Properties"]["RouteKey"] for r in routes.values())
    assert keys == ["GET /leaderboard", "POST /runs"]


def test_default_stage_auto_deploys_with_small_throttling(template: Template) -> None:
    template.resource_count_is("AWS::ApiGatewayV2::Stage", 1)
    props = resource_props(template, "AWS::ApiGatewayV2::Stage")
    assert props["StageName"] == "$default"
    assert props["AutoDeploy"] is True
    assert props["DefaultRouteSettings"]["ThrottlingRateLimit"] == 2
    assert props["DefaultRouteSettings"]["ThrottlingBurstLimit"] == 5


def test_post_runs_is_throttled_harder_than_the_stage(template: Template) -> None:
    # Every POST writes to S3 and DynamoDB, the most expensive path under abuse.
    props = resource_props(template, "AWS::ApiGatewayV2::Stage")
    assert props["RouteSettings"] == {
        "POST /runs": {"ThrottlingRateLimit": 1, "ThrottlingBurstLimit": 2}
    }


def test_stage_is_created_after_the_route_its_settings_name(template: Template) -> None:
    # API Gateway rejects RouteSettings for a route key that does not exist yet; synth would
    # not notice, only the deploy would.
    post_routes = template.find_resources(
        "AWS::ApiGatewayV2::Route", {"Properties": {"RouteKey": "POST /runs"}}
    )
    stage = next(iter(template.find_resources("AWS::ApiGatewayV2::Stage").values()))
    assert set(post_routes) <= set(stage.get("DependsOn", []))


def test_api_url_is_a_stack_output(stack: WaveArenaStack, template: Template) -> None:
    outputs = template.find_outputs("ApiUrl")
    assert len(outputs) == 1
    url = json.dumps(outputs["ApiUrl"]["Value"])
    assert logical_id(stack, stack.http_api) in url
    assert "execute-api" in url


# --- Invoke permissions -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("function_attr", "path"),
    [
        ("post_run_function", "/runs"),
        ("get_leaderboard_function", "/leaderboard"),
    ],
)
def test_invoke_permission_is_scoped_to_this_api_and_route(
    stack: WaveArenaStack, template: Template, function_attr: str, path: str
) -> None:
    # Source ARN <api-id>/<stage>/<method>/<path>: stage and method stay wildcards (one stage,
    # one method per path, ADR 0006), but never the whole API (`<api-id>/*/*`).
    function_id = logical_id(stack, getattr(stack, function_attr))
    permissions = [
        p["Properties"]
        for p in template.find_resources("AWS::Lambda::Permission").values()
        if p["Properties"]["FunctionName"] == get_att(function_id)
    ]
    assert len(permissions) == 1
    permission = permissions[0]
    assert permission["Action"] == "lambda:InvokeFunction"
    assert permission["Principal"] == "apigateway.amazonaws.com"
    parts = permission["SourceArn"]["Fn::Join"][1]
    assert {"Ref": logical_id(stack, stack.http_api)} in parts
    assert parts[-1] == f"/*/*{path}"


def test_no_other_invoke_permissions(template: Template) -> None:
    template.resource_count_is("AWS::Lambda::Permission", 2)


# --- Budget -----------------------------------------------------------------------------


def test_monthly_cost_budget_of_5_usd(template: Template) -> None:
    template.resource_count_is("AWS::Budgets::Budget", 1)
    template.has_resource_properties(
        "AWS::Budgets::Budget",
        {
            "Budget": {
                "BudgetType": "COST",
                "TimeUnit": "MONTHLY",
                "BudgetLimit": {"Amount": 5, "Unit": "USD"},
            }
        },
    )


def test_budget_emails_on_actual_and_forecasted_spend_over_the_limit(
    template: Template,
) -> None:
    props = resource_props(template, "AWS::Budgets::Budget")
    subscriber = [{"SubscriptionType": "EMAIL", "Address": {"Ref": "BudgetEmail"}}]
    notifications = sorted(
        props["NotificationsWithSubscribers"],
        key=lambda n: (n["Notification"]["NotificationType"], n["Notification"]["Threshold"]),
    )
    # ACTUAL 20 percent (1 USD) is the early warning: a new account has no cost history, so
    # the forecast alert may stay silent.
    assert notifications == [
        {
            "Notification": {
                "NotificationType": notification_type,
                "ComparisonOperator": "GREATER_THAN",
                "Threshold": threshold,
                "ThresholdType": "PERCENTAGE",
            },
            "Subscribers": subscriber,
        }
        for notification_type, threshold in (("ACTUAL", 20), ("ACTUAL", 100), ("FORECASTED", 100))
    ]


def test_budget_email_is_a_deploy_time_parameter_without_default(template: Template) -> None:
    template.has_parameter(
        "BudgetEmail",
        {"Type": "String", "AllowedPattern": Match.any_value(), "NoEcho": Match.absent()},
    )
    parameter = template.to_json()["Parameters"]["BudgetEmail"]
    assert "Default" not in parameter


def test_no_email_address_is_committed_in_the_template(template: Template) -> None:
    rendered = json.dumps(template.to_json())
    assert EMAIL.findall(rendered) == []
