"""HTTP plumbing shared by the handlers: reading API Gateway HTTP API (v2) events and
building responses in the shape documented in docs/api.md."""

import base64
import binascii
import json
import logging
from typing import Any

from backend.domain import limits
from backend.domain.errors import ValidationError

LOGGER = logging.getLogger("wave_arena")
LOGGER.setLevel(logging.INFO)

# Base64 grows data by 4/3; anything longer than this cannot decode to an allowed body.
MAX_BASE64_CHARS = (limits.MAX_BODY_BYTES + 2) // 3 * 4


class PayloadTooLargeError(Exception):
    pass


def read_json_body(event: dict[str, Any]) -> object:
    """Decode the request body as JSON. Raises ValidationError or PayloadTooLargeError."""
    raw = event.get("body")
    if not isinstance(raw, str) or raw == "":
        raise ValidationError("body", "required")
    data = _decode_base64(raw) if event.get("isBase64Encoded") else raw.encode("utf-8")
    if len(data) > limits.MAX_BODY_BYTES:
        raise PayloadTooLargeError
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValidationError("body", "must be valid UTF-8 JSON") from None


def query_parameter(event: dict[str, Any], name: str) -> str | None:
    params = event.get("queryStringParameters") or {}
    value = params.get(name)
    return value if isinstance(value, str) else None


def json_response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"v": limits.API_VERSION, **body}, separators=(",", ":")),
    }


def error_response(status: int, error: str, message: str) -> dict[str, Any]:
    return json_response(status, {"error": error, "message": message})


def invalid_request(exc: ValidationError) -> dict[str, Any]:
    # Log the field only, never the submitted value.
    LOGGER.info("invalid request: field=%s", exc.field)
    return error_response(400, "invalid_request", str(exc))


def payload_too_large() -> dict[str, Any]:
    return error_response(413, "payload_too_large", f"body over {limits.MAX_BODY_BYTES} bytes")


def internal_error() -> dict[str, Any]:
    # Called from an except block: the traceback goes to the logs, not to the client.
    LOGGER.exception("unhandled error")
    return error_response(500, "internal_error", "internal error")


def _decode_base64(raw: str) -> bytes:
    if len(raw) > MAX_BASE64_CHARS:
        raise PayloadTooLargeError
    try:
        return base64.b64decode(raw, validate=True)
    except binascii.Error:
        raise ValidationError("body", "invalid base64") from None
