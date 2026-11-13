"""PostToolUse hook for Edit/Write: no new long dashes, no AI attribution, formatted code.

Only lines that are new compared to the last commit are checked, so older text
does not block an edit. Exit 2 shows the problem to the agent so it fixes it.
Cross-platform: standard library only.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DASHES = (chr(0x2014), chr(0x2013))  # em dash, en dash
ATTRIBUTION = re.compile(r"^\s*Co-Authored-By:\s*Claude|Generated with \[Claude", re.IGNORECASE)
CPP_SUFFIXES = {".h", ".hpp", ".cpp", ".inl"}


def committed_lines(p: Path) -> set[str]:
    try:
        rel = p.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return set()
    old = subprocess.run(
        ["git", "show", f"HEAD:{rel}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return set(old.stdout.splitlines()) if old.returncode == 0 else set()


def find_problems(text: str, old: set[str]) -> list[str]:
    dash_lines: list[int] = []
    attr_lines: list[int] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if line in old:
            continue
        if any(d in line for d in DASHES):
            dash_lines.append(i)
        if ATTRIBUTION.search(line):
            attr_lines.append(i)
    problems = []
    if dash_lines:
        problems.append(
            f"long dash on new line(s) {dash_lines}. "
            "Use a comma, colon, parentheses or a plain hyphen."
        )
    if attr_lines:
        problems.append(f"AI attribution on line(s) {attr_lines}. Remove it.")
    return problems


def format_file(path: Path) -> None:
    if path.suffix == ".py":
        if shutil.which("ruff"):
            subprocess.run(["ruff", "format", "--quiet", str(path)], check=False)
        elif shutil.which("uv"):
            subprocess.run(["uv", "run", "--quiet", "ruff", "format", str(path)], check=False)
    elif path.suffix in CPP_SUFFIXES and shutil.which("clang-format"):
        subprocess.run(["clang-format", "-i", "--style=file", str(path)], check=False)


def main() -> int:
    data = json.load(sys.stdin)
    path = Path(data.get("tool_input", {}).get("file_path", ""))
    if not path.is_file():
        return 0
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return 0

    problems = find_problems(text, committed_lines(path))
    if problems:
        print(f"{path}: " + " ".join(problems), file=sys.stderr)
        return 2

    format_file(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
