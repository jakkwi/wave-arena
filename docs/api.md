# Wave Arena API (v1)

The contract between the game client (C++, M5) and the backend (Python, M4). The game client is untrusted: the backend validates every field and rejects anything it does not expect.

All bodies are JSON, UTF-8. Every body carries `"v": 1`. A breaking change bumps the version and is done in the backend and the game in the same milestone.

Limits live in one place in code: `backend/domain/limits.py`. This document and that file must agree.

## POST /runs

Stores one finished run: the leaderboard entry in DynamoDB and the raw event in S3.

### Request

```json
{
  "v": 1,
  "player_name": "Kuba",
  "arena": "arena_01",
  "score": 4200,
  "waves_survived": 7,
  "duration_s": 312.5,
  "death_position": { "x": -3.5, "y": 12.0 },
  "killer_type": "grunt"
}
```

| Field | Type | Rule |
|---|---|---|
| `v` | int | Must be `1` |
| `player_name` | string | 3 to 16 characters after trimming spaces. Letters, digits, space, `_`, `-` |
| `arena` | string | 1 to 32 characters: lowercase letters, digits, `_` |
| `score` | int | 0 to 10 000 000, and at most 10 000 points per wave reached (`waves_survived + 1`) |
| `waves_survived` | int | 0 to 1000 |
| `duration_s` | number | Greater than 0, at most 7200 (two hours), finite |
| `death_position` | object | `x` and `y` numbers, finite, each between -500 and 500 (meters, arena space) |
| `killer_type` | string or null | 1 to 32 characters: lowercase letters, digits, `_`. `null` when the run did not end by death (quit) |

Rules for every field:
- Unknown fields are rejected (fail closed). New fields mean a new version.
- Booleans are not numbers: `true` is not a valid `score`.
- The request body is at most 4096 bytes.

The score per wave cap is a rough plausibility check against edited clients, not real anti-cheat. Tune `MAX_SCORE_PER_WAVE` when the game's scoring is known (M2).

### Response 201

```json
{ "v": 1, "run_id": "5f0c7d0e-2b1a-4c47-9a3e-1d2b8f6a9c10" }
```

The server sets `run_id` (UUID4) and the time the run was received (UTC). The client never sends either.

## GET /leaderboard

Returns the best runs.

| Query parameter | Rule |
|---|---|
| `limit` | Optional integer, 1 to 10. Default 10 |

### Response 200

```json
{
  "v": 1,
  "entries": [
    {
      "rank": 1,
      "player_name": "Kuba",
      "score": 4200,
      "waves_survived": 7,
      "submitted_at": "2026-11-14T18:03:12Z"
    }
  ]
}
```

Order: higher `score` first, then more `waves_survived`, then the earlier submission. Ties are broken this way, so every entry has a unique `rank` (1, 2, 3, ...). An empty leaderboard returns `"entries": []`.

## Errors

Every error has the same shape and never includes stack traces or internal details.

```json
{ "v": 1, "error": "invalid_request", "message": "score: must be at most 10000000" }
```

| Status | `error` | When |
|---|---|---|
| 400 | `invalid_request` | Body is not JSON, or a field breaks a rule above. `message` names the first bad field |
| 413 | `payload_too_large` | Body over 4096 bytes |
| 429 | (API Gateway) | Throttled by the stage limits |
| 500 | `internal_error` | Anything unexpected. Details only in the logs |

## Raw run event (S3)

Not part of the HTTP API: the record `POST /runs` archives for analytics (M6). Built by `backend/domain/events.py`.

- Key: `runs/YYYY/MM/DD/<run_id>.json`, date in UTC. Only `[A-Za-z0-9-]` is allowed in `run_id` before it goes into a key.
- Content type `application/json`, compact JSON, UTF-8.

```json
{
  "v": 1,
  "run_id": "5f0c7d0e-2b1a-4c47-9a3e-1d2b8f6a9c10",
  "received_at": "2026-11-14T18:03:12.005000Z",
  "player_name": "Kuba",
  "arena": "arena_01",
  "score": 4200,
  "waves_survived": 7,
  "duration_s": 312.5,
  "death_position": { "x": -3.5, "y": 12.0 },
  "killer_type": "grunt"
}
```

`received_at` always has microseconds and a `Z`, so string order equals time order. `killer_type` is `null` when the run did not end by death.

## Order of writes in POST /runs

1. Validate the body.
2. Store the raw event in S3.
3. Save the leaderboard entry in DynamoDB.

If step 3 fails, the raw event still exists. That is acceptable: analytics (M6) should see every run, and the client gets a 500 and may retry once (M5).
