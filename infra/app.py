"""CDK app entry point. Run `npx cdk synth` from infra/."""

import sys
from pathlib import Path

# cdk runs this file from infra/; make the repo root importable so `infra.*` and
# `backend.*` resolve the same way as in tests and mypy.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aws_cdk as cdk

from infra.wave_arena_infra.stack import WaveArenaStack

app = cdk.App()
WaveArenaStack(app, "WaveArenaStack")
app.synth()
