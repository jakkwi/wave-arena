"""Repository text check, run in CI.

Fails if any tracked text file contains a long dash (em dash or en dash) or an
AI attribution trailer. With --commits RANGE it also checks commit messages.

Usage:
    python tools/check_text.py
    python tools/check_text.py --commits origin/main..HEAD
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DASHES = (chr(0x2014), chr(0x2013))  # em dash, en dash
ATTRIBUTION = re.compile(r"^\s*Co-Authored-By:|Generated with \[?Claude", re.IGNORECASE)
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".dds", ".tif", ".tga",
    ".fbx", ".glb", ".gltf", ".bin", ".wav", ".ogg", ".mp3", ".ttf", ".otf",
    ".zip", ".pak", ".exe", ".dll", ".lock",
}  # fmt: skip


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, text=True, check=True, encoding="utf-8"
    ).stdout
    return [Path(p) for p in out.split("\0") if p]


def scan_text(name: str, text: str) -> list[str]:
    problems = []
    for i, line in enumerate(text.splitlines(), start=1):
        if any(d in line for d in DASHES):
            problems.append(f"{name}:{i}: long dash")
        if ATTRIBUTION.search(line):
            problems.append(f"{name}:{i}: AI attribution")
    return problems


def scan_files(paths: list[Path]) -> list[str]:
    problems: list[str] = []
    for path in paths:
        if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        problems.extend(scan_text(path.as_posix(), text))
    return problems


def scan_commits(rev_range: str) -> list[str]:
    out = subprocess.run(
        ["git", "log", "--format=%H%n%B%x00", rev_range],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout
    problems: list[str] = []
    for entry in out.split("\0"):
        entry = entry.strip()
        if not entry:
            continue
        sha, _, body = entry.partition("\n")
        problems.extend(scan_text(f"commit {sha[:10]}", body))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commits", help="git revision range whose messages to check")
    args = parser.parse_args(argv)

    problems = scan_files(tracked_files())
    if args.commits:
        problems.extend(scan_commits(args.commits))

    for problem in problems:
        print(problem)
    if problems:
        print(f"{len(problems)} problem(s). Use a comma, colon, parentheses or a plain hyphen.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
