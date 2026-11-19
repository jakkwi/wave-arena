# 0006: Public HTTP API: throttling, no CORS, body size, 5 USD budget

**Status:** Accepted

## Context
Issue #12 puts the two Lambda functions from ADR 0005 on the internet. The API has no authentication (the game client is untrusted and anonymous, docs/api.md), so the only things standing between a script and the AWS bill are throttling, input validation in the handlers and a budget alert.

## Decision

**HTTP API, not REST API.** API Gateway HTTP API (v2) with payload format 2.0, which is what the handlers parse. It is cheaper per request and has every feature this backend uses. REST-only features (API keys and usage plans, request validation, WAF, caching) are not needed for a learning project with two routes.

| Route | Integration |
|---|---|
| `POST /runs` | `post_run` Lambda, payload 2.0 |
| `GET /leaderboard` | `get_leaderboard` Lambda, payload 2.0 |

One `$default` stage with auto deploy, so the base URL has no stage segment. It is the stack output `ApiUrl`.

**Throttling.**

| Scope | Rate (requests/s) | Burst |
|---|---|---|
| Every route (stage default) | 2 | 5 |
| `POST /runs` (route override) | 1 | 2 |

Honest use is one `GET /leaderboard` when the menu opens and one `POST /runs` per finished run, minutes apart. The limits sit far above that and far below the account default (10 000 rps). `POST /runs` is lower because each call writes to S3 and DynamoDB. Throttled requests get a 429 from API Gateway and never reach Lambda. API Gateway applies throttling on a best-effort basis, so short bursts can pass slightly above these numbers.

Worst case if a script keeps both routes at their limits (the stage default is counted per route, the safe upper bound) for a whole month (2.59 million seconds), at approximate us-east-1 list prices:

| Item | Volume | About |
|---|---|---|
| HTTP API requests | 7.8 M (2.6 M POST, 5.2 M GET) | 7.80 USD |
| Lambda requests and ARM compute (256 MB, about 50 ms) | 7.8 M | 2.90 USD |
| S3 PUT | 2.6 M | 13.00 USD |
| DynamoDB on-demand writes and reads | 2.6 M writes, 5.2 M queries | 2.30 USD |
| Total | | about 26 USD |

So throttling bounds abuse to tens of dollars a month, not thousands. The budget below alerts long before that: at about 0.85 USD a day the 1 USD early warning fires on the second day.

**Request body size.** HTTP API has a fixed 10 MB payload quota that cannot be lowered. The 4096 byte limit from docs/api.md is enforced in the handler (`backend/lambdas/http.py`), before any parsing, and answered with 413. A big body still costs one short Lambda invocation, which the throttling above bounds.

**No CORS.** The client is a native game (C++, M5), not a web page, and browsers are the only thing CORS affects. Without a CORS configuration the API sends no `Access-Control-Allow-Origin`, so no page on another origin can read responses in a visitor's browser. A web leaderboard would need an explicit origin, never `*`.

**Lambda invoke permissions.** `HttpLambdaIntegration` with `scope_permission_to_route`: each function may be invoked only by this API and only for its own path.

| Function | Principal | Source ARN |
|---|---|---|
| `post_run` | `apigateway.amazonaws.com` | `arn:aws:execute-api:<region>:<account>:<api-id>/*/*/runs` |
| `get_leaderboard` | `apigateway.amazonaws.com` | `arn:aws:execute-api:<region>:<account>:<api-id>/*/*/leaderboard` |

Stage and method stay wildcards: there is one stage and one method per path, and CDK has no option to pin them. Without the route scope the source ARN would be `<api-id>/*/*`, any route of the API.

**Budget.** An `AWS::Budgets::Budget` of 5 USD per month on actual cost, account-wide (not filtered by the `project` tag: an untagged resource would slip past a tag filter, and the account exists for this project). Three email notifications:

| Type | Threshold | Why |
|---|---|---|
| Actual | 20 percent (1 USD) | Early warning. Normal use stays near zero |
| Actual | 100 percent (5 USD) | The alert the milestone asks for |
| Forecasted | 100 percent | Warns before the month ends, once AWS has enough cost history to forecast (a new account may have none) |

The address is the CloudFormation parameter `BudgetEmail` with no default, so no real address is committed. It is supplied at deploy time, for example `npx cdk deploy --parameters BudgetEmail=$WAVE_ARENA_BUDGET_EMAIL`; later deploys keep the previous value. A parameter (not CDK context) keeps `cdk synth` in CI working without any address at all.

## Consequences
- A budget only alerts. It never stops resources. Stopping abuse is manual: set both throttle limits to 0 in `infra/wave_arena_infra/api.py` and deploy (every request then gets 429), or in the console open API Gateway, the `wave-arena-api` API, Protect, Throttling, and edit the `$default` stage.
- Throttling is one shared limit per route, not per client: HTTP API has no usage plans and no WAF. One script at the limit gets every honest player 429s and can post about 86 000 runs a day that pass validation. Accepted for a learning project; the fix if it ever matters is a REST API or CloudFront with WAF rate-based rules.
- No stage access logs or alarms yet: abuse shows only in the Lambda logs and default API metrics. Revisited in the pre-deploy audit (issue #13).
- The budget lives in this stack, so deleting the stack removes the alert too, while the retained bucket keeps a small cost. Move it to its own stack if the backend is ever torn down and rebuilt.
- The parameter value is visible in the CloudFormation console to anyone with read access to the stack. An email address is not a secret, so this is accepted.
- A new route needs its own throttle decision and gets its own scoped invoke permission from the integration. The infra tests pin the two routes, the limits and the permissions.
- Prices in the table are approximate and change; check the official pricing pages before trusting the total.
