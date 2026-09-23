"""Build imprint: which commit this Control was built from. Display only.

A running shell that cannot say what code it is serving invites guessing, and this
page's job is "what is actually true". The wheel carries ``_imprint.json`` written at
build time. A source checkout falls back to git. Neither present is said out loud.

Write at build time (CI does this before ``pip wheel``)::

    python -m netie_control.imprint "$(git rev-parse HEAD)"
"""

from __future__ import annotations

import functools
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PKG_DIR = Path(__file__).resolve().parent
IMPRINT_PATH = PKG_DIR / "_imprint.json"


def _git(*argv: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *argv], cwd=PKG_DIR, capture_output=True, text=True, timeout=2, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


@functools.cache
def read() -> dict[str, Any]:
    """Read once per process. The code a process serves does not change under it."""
    try:
        blob = json.loads(IMPRINT_PATH.read_text(encoding="utf-8"))
        return {
            "commit": str(blob["commit"]),
            "built": blob.get("built"),
            "dirty": False,
            "source": "wheel imprint",
        }
    except (OSError, ValueError, KeyError, TypeError):
        pass
    commit = _git("rev-parse", "HEAD")
    if commit:
        return {
            "commit": commit,
            "built": None,
            "dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
            "source": "git checkout, not a built wheel",
        }
    return {
        "commit": None,
        "built": None,
        "dirty": None,
        "source": "unimprinted: no _imprint.json and no git checkout",
    }


def write(commit: str) -> Path:
    commit = commit.strip()
    if len(commit) < 7 or not all(c in "0123456789abcdef" for c in commit):
        raise SystemExit(f"imprint: not a git sha: {commit!r}")
    IMPRINT_PATH.write_text(
        json.dumps({"commit": commit, "built": datetime.now(UTC).isoformat(timespec="seconds")})
        + "\n",
        encoding="utf-8",
    )
    return IMPRINT_PATH


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m netie_control.imprint <git-sha>")
    print(write(sys.argv[1]))
