"""Small helpers shared by the infra assertion tests."""

from typing import Any

import aws_cdk as cdk


def logical_id(stack: cdk.Stack, construct: Any) -> str:
    return stack.resolve(construct.node.default_child.logical_id)  # type: ignore[no-any-return]


def get_att(resource_id: str) -> dict[str, Any]:
    return {"Fn::GetAtt": [resource_id, "Arn"]}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]
