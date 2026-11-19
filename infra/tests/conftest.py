"""Shared fixtures: the stack is built and synthesized once for all infra test modules."""

import json
from pathlib import Path

import aws_cdk as cdk
import aws_cdk.cx_api as cxapi
import pytest
from aws_cdk.assertions import Template

from infra.wave_arena_infra.stack import WaveArenaStack

CDK_JSON = Path(__file__).resolve().parents[1] / "cdk.json"


@pytest.fixture(scope="session")
def stack(tmp_path_factory: pytest.TempPathFactory) -> WaveArenaStack:
    # Same feature flags as `cdk synth`, so policies are rendered the same way.
    context = json.loads(CDK_JSON.read_text(encoding="utf-8"))["context"]
    outdir = tmp_path_factory.mktemp("cdk.out")
    app = cdk.App(context=context, outdir=str(outdir))
    return WaveArenaStack(app, "TestStack")


@pytest.fixture(scope="session")
def assembly(stack: WaveArenaStack) -> cxapi.CloudAssembly:
    """The app is synthesized once; template and asset tests read the same output."""
    app = stack.node.root
    assert isinstance(app, cdk.App)
    return app.synth()


@pytest.fixture(scope="session")
def template(stack: WaveArenaStack, assembly: cxapi.CloudAssembly) -> Template:
    return Template.from_json(assembly.get_stack_by_name(stack.stack_name).template)
