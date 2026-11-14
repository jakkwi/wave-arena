"""Limits of the API contract. docs/api.md documents the same values; keep them in sync."""

API_VERSION = 1

MAX_BODY_BYTES = 4096

PLAYER_NAME_MIN = 3
PLAYER_NAME_MAX = 16
ID_MAX = 32  # arena and killer_type

MAX_SCORE = 10_000_000
# Rough plausibility cap against edited clients. Tune once the game's scoring exists (M2).
MAX_SCORE_PER_WAVE = 10_000
MAX_WAVES = 1000
MAX_DURATION_S = 7200.0
MAX_COORDINATE = 500.0

LEADERBOARD_DEFAULT_LIMIT = 10
LEADERBOARD_MAX_LIMIT = 10
