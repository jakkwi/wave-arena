"""Builders for API Gateway HTTP API (payload format 2.0) events."""

import base64
import json
from typing import Any


def http_event(
    method: str,
    path: str,
    *,
    body: str | None = None,
    query: dict[str, str] | None = None,
    base64_encoded: bool = False,
) -> dict[str, Any]:
    if body is not None and base64_encoded:
        body = base64.b64encode(body.encode("utf-8")).decode("ascii")
    event: dict[str, Any] = {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "headers": {"content-type": "application/json"},
        "requestContext": {"http": {"method": method, "path": path}},
        "isBase64Encoded": base64_encoded,
    }
    if body is not None:
        event["body"] = body
    if query is not None:
        event["queryStringParameters"] = query
    return event


def response_json(response: dict[str, Any]) -> dict[str, Any]:
    assert response["headers"]["content-type"] == "application/json"
    data = json.loads(response["body"])
    assert isinstance(data, dict)
    return data
