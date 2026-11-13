"""PreToolUse hook for Bash and PowerShell: blocks unsafe commands, secret reads,
destructive AWS calls and AI attribution.

Cross-platform: standard library only, runs with any Python 3.10+.
Exit code 2 blocks the call and sends stderr back to the agent.
"""

from __future__ import annotations

import json
import re
import sys

BLOCKED: list[tuple[str, str]] = [
    # destructive file and git operations
    (
        r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f|\brm\s+-[a-zA-Z]*f[a-zA-Z]*r",
        "Recursive force delete is blocked. Delete specific files instead.",
    ),
    (
        r"Remove-Item\b.*-Recurse\b.*-Force|Remove-Item\b.*-Force\b.*-Recurse",
        "Recursive force delete is blocked.",
    ),
    (r"\brd\s+/s\b|\brmdir\s+/s\b", "Recursive directory delete is blocked."),
    (r"\bgit\s+push\b.*(--force\b|--force-with-lease\b|\s-f\b)", "Force push is blocked."),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard is blocked. Ask the user first."),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f", "git clean -f is blocked. Ask the user first."),
    (
        r"--no-verify\b|--no-gpg-sign\b",
        "Skipping hooks or signing is blocked. Fix what failed instead.",
    ),
    # remote code execution and supply chain
    (
        r"\b(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^|]*\|\s*"
        r"(sh|bash|zsh|python\d*|pwsh|powershell|iex)\b",
        "Piping downloaded content into a shell is blocked.",
    ),
    (r"\b(iex|Invoke-Expression)\b", "Invoke-Expression is blocked."),
    (
        r"--index-url|--extra-index-url|--registry[= ]|UV_INDEX_URL|PIP_INDEX_URL",
        "Custom package indexes or registries are blocked.",
    ),
    # secrets
    (
        r"(cat|type|Get-Content|gc|less|more|head|tail|bat)\s+[^|;&>\n]*\.env(?![\w.]*example)\b",
        "Reading .env files is blocked.",
    ),
    (
        r"(cat|type|Get-Content|gc|less|more|head|tail|bat)\s+[^|;&>\n]*"
        r"(id_rsa|id_ed25519|\.pem\b|\.key\b|credentials|\.aws[/\\])",
        "Reading key or credential files is blocked.",
    ),
    (
        r"\$env:[A-Z_]*(KEY|TOKEN|SECRET)|echo\s+\$\{?[A-Z_]*(KEY|TOKEN|SECRET)",
        "Printing secrets from the environment is blocked.",
    ),
    (
        r"\baws\s+configure\s+(get|export-credentials)|\baws\s+sts\s+get-session-token",
        "Reading AWS credentials is blocked.",
    ),
    (r"\baws\s+iam\s+create-access-key\b", "Creating IAM access keys is blocked."),
    # destructive AWS operations (ask the user to run these themselves)
    (r"\bcdk\s+destroy\b", "cdk destroy is blocked. The user runs it themselves."),
    (
        r"\baws\s+s3\s+(rb|rm)\b|\baws\s+s3api\s+delete-|\baws\s+dynamodb\s+delete-"
        r"|\baws\s+cloudformation\s+delete-stack\b",
        "Deleting AWS resources is blocked. The user runs it themselves.",
    ),
    # attribution
    (r"Co-Authored-By", "Do not add Co-Authored-By trailers or any AI attribution."),
    (r"Generated with \[?Claude", "Do not add AI attribution to commits or PRs."),
]


def check(cmd: str) -> str | None:
    """Return the block message for a command, or None if it is allowed."""
    for pattern, msg in BLOCKED:
        if re.search(pattern, cmd, re.IGNORECASE):
            return msg
    return None


def main() -> int:
    data = json.load(sys.stdin)
    cmd = data.get("tool_input", {}).get("command", "")
    if not isinstance(cmd, str):
        cmd = " ".join(map(str, cmd))
    msg = check(cmd)
    if msg:
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
