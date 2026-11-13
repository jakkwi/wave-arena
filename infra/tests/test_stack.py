import aws_cdk as cdk
from aws_cdk.assertions import Template

from infra.wave_arena_infra.stack import WaveArenaStack


def test_stack_synthesizes() -> None:
    app = cdk.App()
    stack = WaveArenaStack(app, "TestStack")
    template = Template.from_stack(stack)
    assert isinstance(template.to_json(), dict)
