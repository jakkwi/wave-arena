"""Domain errors. Handlers map them to HTTP status codes."""


class ValidationError(ValueError):
    """Input breaks the API contract. Safe to show to the client."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message
