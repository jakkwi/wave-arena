"""Tests for .claude/hooks/check_edit.py, run as a subprocess like Claude Code does."""

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "check_edit.py"
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)


def run_hook(path: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(path)}})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        cwd=path.parent,
    )


def test_rejects_em_dash(tmp_path: Path) -> None:
    f = tmp_path / "note.md"
    f.write_text(f"one {EM_DASH} two\n", encoding="utf-8")
    result = run_hook(f)
    assert result.returncode == 2
    assert "long dash" in result.stderr


def test_rejects_en_dash(tmp_path: Path) -> None:
    f = tmp_path / "note.md"
    f.write_text(f"pages 1{EN_DASH}2\n", encoding="utf-8")
    assert run_hook(f).returncode == 2


def test_rejects_attribution_trailer(tmp_path: Path) -> None:
    f = tmp_path / "msg.txt"
    f.write_text("Fix bug\n\nCo-Authored-By: Claude <noreply@example.invalid>\n", encoding="utf-8")
    result = run_hook(f)
    assert result.returncode == 2
    assert "attribution" in result.stderr


def test_accepts_plain_text(tmp_path: Path) -> None:
    f = tmp_path / "note.md"
    f.write_text("one - two, three: four (five)\n", encoding="utf-8")
    assert run_hook(f).returncode == 0


def test_ignores_missing_file(tmp_path: Path) -> None:
    assert run_hook(tmp_path / "missing.md").returncode == 0
