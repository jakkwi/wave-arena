"""Public HTTP API in front of the two Lambda functions (issue #12, ADR 0006).

HTTP API (API Gateway v2), not REST API: cheaper per request, payload format 2.0 is what the
handlers parse, and nothing here needs REST-only features (API keys, usage plans, request
validation, WAF).
"""

from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

# Stage-wide limits. Real traffic is one GET when the menu opens and one POST per finished run
# (minutes apart), so a few requests per second is far above honest use. The numbers bound
# what an abusive client can cost; ADR 0006 has the worst-case monthly math.
STAGE_RATE_LIMIT = 2
STAGE_BURST_LIMIT = 5
# POST /runs writes to S3 and DynamoDB, the most expensive path, so it is throttled harder.
POST_RUNS_ROUTE = "POST /runs"
POST_RUNS_RATE_LIMIT = 1
POST_RUNS_BURST_LIMIT = 2


class PublicApi(Construct):
    """HTTP API with `POST /runs` and `GET /leaderboard` on a throttled `$default` stage."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        post_run: lambda_.IFunction,
        get_leaderboard: lambda_.IFunction,
    ) -> None:
        super().__init__(scope, construct_id)
        # No cors_preflight: the client is a native game, not a web page (ADR 0006).
        self.http_api = apigw.HttpApi(
            self, "HttpApi", api_name="wave-arena-api", create_default_stage=False
        )
        post_routes = self._route(apigw.HttpMethod.POST, "/runs", "PostRun", post_run)
        self._route(apigw.HttpMethod.GET, "/leaderboard", "GetLeaderboard", get_leaderboard)

        self.stage = apigw.HttpStage(
            self,
            "DefaultStage",
            http_api=self.http_api,
            stage_name="$default",
            auto_deploy=True,
            throttle=apigw.ThrottleSettings(
                rate_limit=STAGE_RATE_LIMIT, burst_limit=STAGE_BURST_LIMIT
            ),
        )
        # HttpStage has no per-route throttling option, so set it on the L1 resource.
        cfn_stage = self.stage.node.default_child
        if not isinstance(cfn_stage, apigw.CfnStage):
            raise TypeError("HttpStage is expected to wrap a CfnStage")
        # RouteSettings is a free-form JSON property: CDK does not rename the keys, so they are
        # written in CloudFormation's PascalCase (a RouteSettingsProperty would render camelCase).
        cfn_stage.route_settings = {
            POST_RUNS_ROUTE: {
                "ThrottlingRateLimit": POST_RUNS_RATE_LIMIT,
                "ThrottlingBurstLimit": POST_RUNS_BURST_LIMIT,
            }
        }
        # Route settings name a route key, so that route must exist before the stage.
        for route in post_routes:
            self.stage.node.add_dependency(route)

    def _route(
        self, method: apigw.HttpMethod, path: str, name: str, function: lambda_.IFunction
    ) -> list[apigw.HttpRoute]:
        integration = integrations.HttpLambdaIntegration(
            f"{name}Integration",
            function,
            payload_format_version=apigw.PayloadFormatVersion.VERSION_2_0,
            # Invoke permission for this method and path only, not for every route of the API.
            scope_permission_to_route=True,
        )
        return self.http_api.add_routes(path=path, methods=[method], integration=integration)
