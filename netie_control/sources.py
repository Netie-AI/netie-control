"""Read-only readers for the estate's real state.

Every function here returns either real data or an explicit unreachable marker. None
of them invents a value, and none of them substitutes a plausible default for a source
it could not read - a page whose whole job is "what is actually true" is the worst
possible place to fake (R-0011).

Nothing in this module writes. Control is plane 4: it displays and it launches, and it
holds no keys and owns no route decision (NETIE.md section 3).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NETIE = Path(r"D:\Netie")
AGENTS = NETIE / "Internal" / "Agents"


@dataclass
class Reading:
    """A value the operator can trust, or an honest statement that we could not get it.

    ``ok=False`` is not an error state to be hidden behind a spinner. It is the answer,
    and the UI renders ``detail`` rather than an empty panel.
    """

    ok: bool
    data: Any = None
    detail: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "data": self.data, "detail": self.detail, "source": self.source}

    @classmethod
    def unreachable(cls, source: str, why: str) -> Reading:
        return cls(ok=False, data=None, detail=why, source=source)


def _read_text(p: Path) -> Reading:
    try:
        return Reading(ok=True, data=p.read_text(encoding="utf-8"), source=str(p))
    except FileNotFoundError:
        return Reading.unreachable(str(p), "file does not exist")
    except OSError as exc:
        return Reading.unreachable(str(p), f"unreadable: {exc}")


def runtime_view() -> Reading:
    """The watchdog's plane view. Stale is a real state and must be visible as one."""
    return _read_text(AGENTS / "RUNTIME.md")


def claims_board() -> Reading:
    """Who holds what. The answer to 'may I seat here' before a branch exists."""
    p = AGENTS / "CLAIMS.json"
    r = _read_text(p)
    if not r.ok:
        return r
    try:
        return Reading(ok=True, data=json.loads(r.data), source=str(p))
    except json.JSONDecodeError as exc:
        return Reading.unreachable(str(p), f"claims board is not valid JSON: {exc}")


def estate_gate() -> Reading:
    """Run the estate gate and surface its fails verbatim.

    Deliberately runs the real gate rather than reading a cached verdict. A cached
    green is a claim about the past; the operator is asking about now.
    """
    script = AGENTS / "estate_gate.py"
    if not script.is_file():
        return Reading.unreachable(str(script), "estate_gate.py not found")
    try:
        proc = subprocess.run(
            ["python", str(script), "check"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(AGENTS),
            # check=False deliberately: a non-zero exit is the gate's ANSWER, not a
            # failure to run it. Raising here would turn "the estate is failing" into
            # "we could not tell", which is a different and much worse thing to show.
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Reading.unreachable(str(script), "gate did not finish within 120s")
    except OSError as exc:
        return Reading.unreachable(str(script), f"could not run gate: {exc}")

    out = (proc.stdout or "") + (proc.stderr or "")
    fails = [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.startswith(" ")]
    return Reading(
        ok=True,
        data={"exit_code": proc.returncode, "passing": proc.returncode == 0, "output": fails},
        source=str(script),
    )


def board(repos: tuple[str, ...] = ("Netie-AI/dms", "Netie-AI/Cortex")) -> Reading:
    """Open epics and tickets per repo, straight from gh. Display only."""
    rows: list[dict[str, Any]] = []
    unreachable: list[str] = []
    for repo in repos:
        try:
            proc = subprocess.run(
                ["gh", "issue", "list", "--repo", repo, "--state", "open",
                 "--limit", "50", "--json", "number,title,labels"],
                capture_output=True, text=True, timeout=60,
                # check=False: one unreachable repo must not blank the whole board.
                # The returncode is inspected below and that repo is named in
                # `unreachable` instead.
                check=False,
            )
            if proc.returncode != 0:
                unreachable.append(f"{repo}: {(proc.stderr or '').strip()[:120]}")
                continue
            for it in json.loads(proc.stdout or "[]"):
                labels = [x.get("name") for x in (it.get("labels") or [])]
                rows.append({
                    "repo": repo,
                    "number": it.get("number"),
                    "title": it.get("title"),
                    "is_epic": "epic" in labels,
                    "blocked": "blocked" in labels,
                })
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            unreachable.append(f"{repo}: {exc}")

    if unreachable and not rows:
        return Reading.unreachable("gh issue list", "; ".join(unreachable))
    return Reading(
        ok=True,
        data={"items": rows, "unreachable": unreachable},
        detail=("some repos unreachable: " + "; ".join(unreachable)) if unreachable else "",
        source="gh issue list",
    )


@dataclass
class Launcher:
    """A local CLI lane Control may start on the operator's behalf.

    Display-and-launch only. Note what is NOT here: nothing that starts, restarts or
    kills the founder's desktop software. Grok Bot, Cursor and every user-facing app
    open and close by the founder's own hand (R-0015), so they are not launchers and
    adding one would be a defect, not a feature.
    """

    name: str
    argv: tuple[str, ...]
    cwd: str
    blurb: str
    tags: tuple[str, ...] = field(default_factory=tuple)


LAUNCHERS: tuple[Launcher, ...] = (
    Launcher("estate-gate", ("python", "estate_gate.py", "all"), str(AGENTS),
             "Run the full estate gate and print its fails."),
    Launcher("kb-search", ("python", r"D:\Netie-KB\scripts\kb.py", "search"), r"D:\Netie-KB",
             "Search the one skill registry (R-0016). Takes keywords."),
    Launcher("dms-demo-verify", ("python", r"D:\DMS\scripts\verify_demo_live.py"), r"D:\DMS",
             "Verify the DMS demo against a live stack. Needs the stack up."),
)
