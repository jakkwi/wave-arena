"""Wave Arena backend stack.

Empty until M4. Planned resources (see docs/ROADMAP.md, M4):
- HTTP API with POST /runs and GET /leaderboard, stage throttling
- Two Python Lambdas with least-privilege grants
- DynamoDB table (on-demand) for the leaderboard
- S3 bucket for raw run events (no public access, TLS only, encryption, lifecycle)
- AWS Budget with a 5 USD alert
"""

from typing import Any

import aws_cdk as cdk
from constructs import Construct


class WaveArenaStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        cdk.Tags.of(self).add("project", "wave-arena")
