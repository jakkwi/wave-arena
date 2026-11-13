# analytics/ (M6)

Reads raw run events (S3 or a local export), produces:
- a death heatmap over the arena layout,
- deaths per wave, average run length, top killer types.

The conclusion and the resulting wave config change are written up in `docs/learning/M6.md`. Install the extra with `uv sync --extra analytics`. Tests use a small fixture dataset, never real S3.
