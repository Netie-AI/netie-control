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
import os
import re
import subprocess
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _estate_root() -> Path:
    env = os.environ.get("NETIE_ROOT", "").strip()
    if env:
        return Path(env)
    for candidate in (Path(r"D:\Netie"), Path(r"E:\Netie")):
        if (candidate / "Internal" / "Agents").is_dir():
            return candidate
    return Path(r"D:\Netie")


NETIE = _estate_root()
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


def loopback_get_json(url: str, timeout: float = 2.0) -> Reading:
    """GET JSON from loopback only. Off-box URLs are a refusal, not a fetch."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host not in LOOPBACK_HOSTS:
        return Reading.unreachable(url, "Control only probes loopback (not an open proxy)")
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(65536)
            status = getattr(resp, "status", 200)
            if status != 200:
                return Reading.unreachable(url, f"HTTP {status}")
    except urllib.error.HTTPError as exc:
        return Reading.unreachable(url, f"HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return Reading.unreachable(url, f"unreachable: {exc}")
    try:
        return Reading(ok=True, data=json.loads(raw.decode("utf-8")), source=url)
    except json.JSONDecodeError as exc:
        return Reading.unreachable(url, f"not JSON: {exc}")


def cortex_base() -> str:
    return os.environ.get("NETIE_CORTEX_URL", "http://127.0.0.1:8010").rstrip("/")


def openvault_base() -> str:
    return os.environ.get("NETIE_OPENVAULT_URL", "http://127.0.0.1:5000").rstrip("/")


def crew_base() -> str:
    return os.environ.get("NETIE_CREW_URL", "http://127.0.0.1:8020").rstrip("/")


def control_base() -> str:
    return os.environ.get("NETIE_CONTROL_URL", "http://127.0.0.1:8040").rstrip("/")


def agent_contract() -> dict[str, Any]:
    """What every lane must read before seating. Display only. Control does not assign."""
    base = control_base()
    return {
        "ok": True,
        "display_only": True,
        "plane": 4,
        "product": "netie-control",
        "repo": "https://github.com/Netie-AI/netie-control",
        "communication_layer": {
            "read": "Netie Control :8040",
            "claim": "GitHub Issues + CLAIMS.json",
            "run": "Cortex",
            "converse": crew_base(),
        },
        "before_seating": [
            f"{base}/v1/pickup",
            f"{base}/v1/fleet",
            f"{base}/v1/you",
        ],
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "run_owner": "Cortex",
        "forbidden": ["/v1/secrets", "/v1/route", "/v1/goal", "/v1/run"],
        "human_stop": ["HT1", "HT2", "work.netie.ai"],
        "rule": (
            "Every lane (Cursor, Claude Code, Grok Bot) reads Control before seating. "
            "Control does not assign and does not run. Claim on GitHub first (F-0025). "
            "F-0030: a scale request is not a third orchestrator."
        ),
    }


def kb_base() -> str:
    return os.environ.get("NETIE_KB_URL", "http://127.0.0.1:8030").rstrip("/")


def cortex_view() -> Reading:
    """Read-only Cortex probes. Does not touch the ledger; one ledger, via Cortex HTTP.

    Unlock for P-CTL-1: GET /health + GET /api/engine/activity including
    activity.governance (ledger tip, bound session ids, refusals; no payloads).
    A dedicated refusal-history GET is still absent; Control will not scrape
    the chain for more than Cortex already returns.
    """
    base = cortex_base()
    health = loopback_get_json(f"{base}/health")
    if not health.ok:
        return health
    activity = loopback_get_json(f"{base}/api/engine/activity")
    features = loopback_get_json(f"{base}/health/features")
    up = (health.data or {}).get("status") == "ok"
    gov = None
    if activity.ok and isinstance(activity.data, dict):
        gov = activity.data.get("governance")
    gov_ok = isinstance(gov, dict) and "error" not in gov
    if gov_ok:
        refusal_view, refusal_why = "present", ""
    else:
        refusal_view, refusal_why = (
            "absent",
            "Cortex activity had no governance section; Control will not scrape the ledger.",
        )
    return Reading(
        ok=True,
        data={
            "up": up,
            "health": health.data,
            "activity": activity.data if activity.ok else None,
            "activity_detail": None if activity.ok else activity.detail,
            "features": features.data if features.ok else None,
            "governance": gov if gov_ok else None,
            "refusal_view": refusal_view,
            "refusal_why": refusal_why,
        },
        source=base,
        detail="" if activity.ok else f"activity: {activity.detail}",
    )


def openvault_view() -> Reading:
    """Display FreeRoute/vault liveness. Does not choose a route."""
    base = openvault_base()
    healthz = loopback_get_json(f"{base}/api/healthz")
    if not healthz.ok:
        return healthz
    status = (healthz.data or {}).get("status")
    return Reading(
        ok=True,
        data={
            "up": status == "ok",
            "healthz": healthz.data,
            "custody_owner": "OpenVault",
            "request_path": "OpenVault. Control /v1/secrets answers 405.",
        },
        source=healthz.source,
    )


def spaceship_host_view() -> Reading:
    """Public Spaceship host facts. Passwords stay in OpenVault / spaceship-ftp.env.

    Control does not scrape spaceship.com (loopback-only probes). Agents reopen
    Hosting Manager in the persistent Playwright profile. Do not buy New hosting.
    """
    path = AGENTS / "SHIP_SPACESHIP.md"
    reading = _read_text(path)
    if not reading.ok:
        return reading
    text = reading.data if isinstance(reading.data, str) else ""
    if "209.74.68.17" not in text or "ship@netie.ai" not in text:
        return Reading.unreachable(str(path), "SHIP_SPACESHIP.md missing live host table")
    return Reading(
        ok=True,
        data={
            "package": "Web Hosting Essential",
            "apex": "netie.ai",
            "host": "209.74.68.17",
            "server": "server901.shared.spaceship.host",
            "docroot": "/home/ffvtfuqcxb/netie.ai",
            "ftp_user": "ship@netie.ai",
            "hosting_manager": "https://www.spaceship.com/application/hosting-manager/",
            "cpanel_access": "https://www.spaceship.com/hosting/tools/cpanel-access/",
            "launchpad": "https://www.spaceship.com/launchpad/",
            "playwright_profile": r"C:\Users\oojia\.netie\chrome-playwright",
            "domains": [
                {"host": "netie.ai", "site": "custom website"},
                {"host": "crash.netie.ai", "site": "custom website"},
                {"host": "mail.netie.ai", "site": "empty"},
                {"host": "api.netie.ai", "site": "empty"},
                {"host": "app.netie.ai", "site": "empty"},
            ],
            "rule": (
                "Login once. Reopen Hosting Manager. Do not click New hosting. "
                "Do not invent Cloudflare for netie.ai. Passwords are not on this page."
            ),
        },
        source=str(path),
    )


def crew_belt_view() -> Reading:
    """Display-only GET of Crew's conveyor JSON. Control does not converse.

    NETIE.md section 3 is still display-and-launch. Converse stays on Crew
    at :8020 until a charter amendment merges. This reader copies no HTML
    and posts no handoff.
    """
    return loopback_get_json(f"{crew_base()}/v1/belt")


def slim_crew_health(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep arming flags. Drop tool catalogs and any extra provider fields."""
    mcp_rows: list[dict[str, Any]] = []
    for row in payload.get("mcp") or []:
        if not isinstance(row, dict):
            continue
        mcp_rows.append(
            {
                "name": row.get("name"),
                "status": row.get("status"),
                "armed": row.get("armed"),
                "enabled": row.get("enabled"),
                "running": row.get("running"),
            }
        )
    provider = payload.get("provider") if isinstance(payload.get("provider"), dict) else {}
    vault = payload.get("openvault") if isinstance(payload.get("openvault"), dict) else {}
    return {
        "ok": bool(payload.get("ok")),
        "computer_control": payload.get("computer_control"),
        "grok_offloaded": payload.get("grok_offloaded"),
        "provider": {
            "label": provider.get("label"),
            "model": provider.get("model"),
            "source": provider.get("source"),
            "configured": provider.get("configured"),
            "active": provider.get("active"),
        },
        "mcp": mcp_rows,
        "openvault_ok": vault.get("ok"),
    }


def crew_health_view() -> Reading:
    """Display Crew laptop-tool arming. Control does not arm, start, or kill MCPs.

    S-0001 step 3: GET /crew/health names which computer-control MCPs are armed.
    UACC is the OS mouse. Playwright is the Chrome DOM. Control never POSTs
    an arming route and never copies vault material from Crew's payload.
    """
    raw = loopback_get_json(f"{crew_base()}/crew/health")
    if not raw.ok:
        return raw
    payload = raw.data if isinstance(raw.data, dict) else {}
    return Reading(ok=True, data=slim_crew_health(payload), source=raw.source)


def kb_view() -> Reading:
    """Liveness of the one skill registry. Counts only. No artifact bodies."""
    return loopback_get_json(f"{kb_base()}/healthz")


def _read_text(p: Path) -> Reading:
    try:
        return Reading(ok=True, data=p.read_text(encoding="utf-8"), source=str(p))
    except FileNotFoundError:
        return Reading.unreachable(str(p), "file does not exist")
    except OSError as exc:
        return Reading.unreachable(str(p), f"unreadable: {exc}")


def guess_lane(head: str) -> str:
    """Guess the writer family from a branch name. Same family as estate-watchdog.ps1.

    This is a guess, not a live Cursor/Claude API. cursor/* does not prove cloud
    vs this PC. Empty or unmatched prefixes stay unknown/mixed, never Cursor.
    """
    h = (head or "").strip().lower()
    if h.startswith("cursor/"):
        return "Cursor"
    if h.startswith(("claude/", "worktree-")):
        return "Claude"
    if not h:
        return "unknown"
    return "mixed"


def parse_runtime_md(text: str, now: datetime | None = None) -> dict[str, Any]:
    """Split RUNTIME.md into the sections an operator can scan. Stale is named."""
    # Naive local on purpose: estate-watchdog.ps1 stamps RUNTIME.md with
    # `Get-Date -Format "yyyy-MM-dd HH:mm"`, which carries no zone. Comparing an
    # aware now() against that would need an assumed zone, and a wrong assumption
    # renders a stale snapshot as fresh - which is the one thing Control must not do.
    now = now or datetime.now()  # noqa: DTZ005
    generated = ""
    match = re.search(r"generated\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", text or "")
    if match:
        generated = match.group(1)
    stale = False
    generated_note = "could not parse generated time"
    if generated:
        try:
            ts = datetime.strptime(generated, "%Y-%m-%d %H:%M")  # noqa: DTZ007
            age_min = int((now - ts).total_seconds() / 60)
            stale = age_min > 30
            generated_note = f"watchdog snapshot {generated}"
            if stale:
                generated_note += f" STALE ({age_min} min old)"
        except ValueError:
            generated_note = f"unreadable generated value {generated}"
    sections: dict[str, list[str]] = {"alive": [], "pads": [], "prs": [], "who": []}
    heading_map = (
        ("## Alive", "alive"),
        ("## Live Claude pads", "pads"),
        ("## Open PRs", "prs"),
        ("## Who does what this tick", "who"),
    )
    current: str | None = None
    for line in (text or "").splitlines():
        hit = next((key for title, key in heading_map if line.startswith(title)), None)
        if hit:
            current = hit
            continue
        if line.startswith("## "):
            current = None
            continue
        if current and line.startswith("- "):
            sections[current].append(line[2:].strip())
    return {
        "generated": generated,
        "generated_note": generated_note,
        "stale": stale,
        **sections,
    }


def ticket_github_url(ticket: str) -> str:
    """GitHub issue/PR URL from `owner/repo#N`. Empty if the handle is not parseable."""
    raw = str(ticket or "").strip()
    if raw.startswith("https://github.com/"):
        return raw
    if "#" not in raw:
        return ""
    repo, num = raw.rsplit("#", 1)
    if "/" not in repo or not num.isdigit():
        return ""
    return f"https://github.com/{repo}/issues/{num}"


HITL_STEPS: tuple[dict[str, str], ...] = (
    {
        "n": "1",
        "id": "hold-dms-61",
        "title": "Lift estate hold in FLEET.md",
        "do": "Named hold dms#61. The PR is MERGED. Control did not invent this. "
             "Edit FLEET.md yourself. MERGEABLE is not permission.",
        "url": "https://github.com/Netie-AI/dms/pull/61",
        "kind": "you",
    },
    {
        "n": "2",
        "id": "f36-epic-020",
        "title": "Answer F36 - extract, or live federation",
        "do": "EPIC-020 has been blocked on this since 2026-08-07. A read-only SQL Server / "
             "MySQL connector is written and green on dms `park/epic-020-source-db-connector` "
             "and must not merge until you answer: is F27 reversed, and does 'query "
             "immediately' mean fast-to-first-answer over an extract, or live federation. "
             "PRD-001 holds the question; Control only shows that it is open.",
        "url": "https://github.com/Netie-AI/dms/tree/park/epic-020-source-db-connector",
        "kind": "you",
    },
    {
        "n": "3",
        "id": "f45-insights",
        "title": "Answer F45 - insights + brief epic",
        "do": "F45 is STOP in the feedback ledger, and option (B) is itself downstream of "
             "EPIC-021a, which is NEEDS-YOU under F41. Grain-guarded insights are written "
             "and green on dms `park/f45-space-insights` and must not merge until you pick "
             "(A) keep under EPIC-022's precision gate, (B) open a thin deterministic epic, "
             "or (C) decline.",
        "url": "https://github.com/Netie-AI/dms/tree/park/f45-space-insights",
        "kind": "you",
    },
    {
        "n": "4",
        "id": "ht1",
        "title": "HT1 live Ship host URL",
        "do": "HUMAN_STOP. A real openable CF/Coolify/Netlify/VPS URL under the leave-machine "
             "gate. Simulated deploy public_url stays empty. Do not invent a host URL. "
             "https://netie.ai on Spaceship is the landing, not HT1.",
        "url": "https://github.com/Netie-AI/OpenVault/issues/18",
        "kind": "human-stop",
    },
    {
        "n": "5",
        "id": "ht2",
        "title": "HT2 live FreeRoute with vaulted keys",
        "do": "HUMAN_STOP. Live chat with real vaulted provider keys. summary.priced stays "
             "false until DR-0009. Do not invent prices.",
        "url": "https://github.com/Netie-AI/OpenVault/issues/18",
        "kind": "human-stop",
    },
    {
        "n": "6",
        "id": "crew-talk",
        "title": "Talk to agents (Crew)",
        "do": "Converse is Crew, not Control. Control does not auto-route a comment to a "
             "Ticket Runner. That would be a third orchestrator.",
        "url": "http://127.0.0.1:8020",
        "kind": "you",
    },
    {
        "n": "7",
        "id": "feedback",
        "title": "Feedback on a ticket",
        "do": "Click a fleet/board card. Comment on that GitHub issue. GitHub is the bus "
             "(W-0005). There is no circle-chat on this page.",
        "url": "",
        "kind": "you",
    },
)


def you_desk() -> Reading:
    """Numbered founder actions. GitHub URLs only. No invented host URLs or prices."""
    return Reading(
        ok=True,
        data={"steps": [dict(s) for s in HITL_STEPS]},
        source="HITL_STEPS",
    )


def snapshot_pr_titles() -> dict[str, str]:
    """PR titles from the gate snapshot. Missing file -> empty, not invented."""
    path = AGENTS / "snapshots" / "latest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    for row in data.get("prs") or []:
        if isinstance(row, dict) and row.get("id"):
            out[str(row["id"])] = str(row.get("title") or "")
    return out


def fleet_from_claims(
    payload: dict[str, Any], titles: dict[str, str] | None = None
) -> dict[str, Any]:
    """Who is seated, on which repo/branch, with a labeled lane guess."""
    titles = titles or {}
    rows: list[dict[str, Any]] = []
    for item in payload.get("tickets") or []:
        if not isinstance(item, dict):
            continue
        head = str(item.get("head") or "")
        key = str(item.get("owner_pr") or item.get("ticket") or "")
        rows.append(
            {
                "ticket": item.get("ticket"),
                "repo": str(item.get("repo") or "").split("/")[-1],
                "head": head,
                "role": item.get("role"),
                "may_write": bool(item.get("may_write")),
                "lane": guess_lane(head),
                "title": titles.get(key) or titles.get(str(item.get("ticket") or "")) or "",
                "href": ticket_github_url(str(item.get("ticket") or key)),
            }
        )
    rank = {"SEATED": 0, "HELD": 1, "EXTRA_STOP": 2, "UNSEATED": 3}
    rows.sort(
        key=lambda row: (rank.get(str(row["role"]), 9), str(row.get("repo")), str(row.get("ticket")))
    )
    return {
        "ts": payload.get("ts"),
        "seated": sum(1 for row in rows if row["role"] == "SEATED"),
        "held": sum(1 for row in rows if row["role"] in {"HELD", "EXTRA_STOP"}),
        "rows": rows,
        "lane_rule": (
            "Lane is a guess from branch prefix (estate-watchdog.ps1 family). "
            "cursor/* means Cursor, not proof of cloud vs this PC. "
            "claude/* or worktree-* means Claude. else mixed."
        ),
    }


def pickup_tray(
    fleet_data: dict[str, Any] | None,
    board_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Open work agents can pick up. Display only. Control does not assign or seat.

    Optio-shaped intake: a tray of GitHub tickets. Claim stays GitHub + CLAIMS.json.
    """
    items: list[dict[str, Any]] = []
    seated: set[str] = set()
    seen: set[str] = set()
    fleet_data = fleet_data if isinstance(fleet_data, dict) else {}
    board_data = board_data if isinstance(board_data, dict) else {}
    for row in fleet_data.get("rows") or []:
        if not isinstance(row, dict):
            continue
        href = str(row.get("href") or "")
        if row.get("role") == "SEATED" and href:
            seated.add(href)
        if row.get("role") != "UNSEATED" or not href or href in seen:
            continue
        seen.add(href)
        items.append(
            {
                "kind": "unseated",
                "ticket": row.get("ticket"),
                "title": row.get("title") or row.get("ticket"),
                "href": href,
                "repo": row.get("repo"),
                "lane": row.get("lane"),
            }
        )
    for row in board_data.get("items") or []:
        if not isinstance(row, dict):
            continue
        href = str(row.get("url") or "")
        if not href or href in seen or href in seated:
            continue
        seen.add(href)
        items.append(
            {
                "kind": "open",
                "ticket": f"{row.get('repo')}#{row.get('number')}",
                "title": row.get("title"),
                "href": href,
                "repo": str(row.get("repo") or "").split("/")[-1],
                "blocked": bool(row.get("blocked")),
                "is_epic": bool(row.get("is_epic")),
            }
        )
    return {
        "items": items[:40],
        "count": min(len(items), 40),
        "rule": (
            "Pickup is display. Claim on the GitHub issue, then CLAIMS.json. "
            "Control GET /v1/pickup does not seat. POST /v1/run stays 405."
        ),
    }


def fleet_view() -> Reading:
    """CLAIMS seats plus snapshot titles. Control does not write the board."""
    claims = claims_board()
    if not claims.ok:
        return claims
    payload = claims.data if isinstance(claims.data, dict) else {}
    return Reading(
        ok=True,
        data=fleet_from_claims(payload, snapshot_pr_titles()),
        source=claims.source,
    )


def claude_pads_view() -> Reading:
    """Live Claude Code pads on this PC. List only. Does not start Claude (R-0015)."""
    try:
        proc = subprocess.run(
            ["claude", "agents", "--json"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Reading.unreachable("claude agents --json", f"unreachable: {exc}")
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "exit non-zero").strip()[:200]
        return Reading.unreachable("claude agents --json", err or "exit non-zero")
    raw = (proc.stdout or "").strip()
    if not raw:
        return Reading(
            ok=True,
            data={"pads": [], "note": "no live Claude pads"},
            source="claude agents --json",
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return Reading.unreachable("claude agents --json", f"not JSON: {exc}")
    items = parsed if isinstance(parsed, list) else [parsed]
    pads: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pads.append(
            {
                "name": item.get("name"),
                "pid": item.get("pid"),
                "kind": item.get("kind"),
                "cwd": item.get("cwd"),
            }
        )
    return Reading(ok=True, data={"pads": pads}, source="claude agents --json")


_SURFACE_IMAGES = (
    ("Grok Bot.exe", "Grok Bot"),
    ("claude.exe", "Claude Code"),
    ("Cursor.exe", "Cursor"),
)


def desktop_surfaces_view() -> Reading:
    """Which founder apps are running. Present/absent only. Never start or kill."""
    try:
        proc = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Reading.unreachable("tasklist", f"unreachable: {exc}")
    if proc.returncode != 0:
        return Reading.unreachable("tasklist", (proc.stderr or "exit non-zero")[:160])
    blob = (proc.stdout or "").lower()
    rows = [
        {"name": label, "image": image, "present": image.lower() in blob}
        for image, label in _SURFACE_IMAGES
    ]
    return Reading(
        ok=True,
        data={
            "rows": rows,
            "note": "present/absent only. Control did not start or kill them (R-0015).",
        },
        source="tasklist",
    )


def runtime_view() -> Reading:
    """The watchdog's plane view. Stale is a real state and must be visible as one."""
    reading = _read_text(AGENTS / "RUNTIME.md")
    if not reading.ok:
        return reading
    text = reading.data if isinstance(reading.data, str) else ""
    return Reading(ok=True, data=parse_runtime_md(text), source=reading.source)


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


def _gh_open_issues(repo: str) -> tuple[list[dict[str, Any]], str]:
    """One repo's open issues. Empty rows + reason when gh cannot answer."""
    try:
        proc = subprocess.run(
            ["gh", "issue", "list", "--repo", repo, "--state", "open",
             "--limit", "50", "--json", "number,title,labels,url"],
            capture_output=True, text=True, timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], f"{repo}: {exc}"
    if proc.returncode != 0:
        return [], f"{repo}: {(proc.stderr or '').strip()[:120]}"
    try:
        items = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        return [], f"{repo}: {exc}"
    rows: list[dict[str, Any]] = []
    for it in items:
        labels = [x.get("name") for x in (it.get("labels") or [])]
        rows.append({
            "repo": repo,
            "number": it.get("number"),
            "title": it.get("title"),
            "url": it.get("url") or ticket_github_url(f"{repo}#{it.get('number')}"),
            "is_epic": "epic" in labels,
            "blocked": "blocked" in labels,
        })
    return rows, ""


BOARD_REPOS: tuple[str, ...] = (
    "Netie-AI/dms",
    "Netie-AI/Cortex",
    "Netie-AI/OpenVault",
    "Netie-AI/netie-control",
)


def board(repos: tuple[str, ...] = BOARD_REPOS) -> Reading:
    """Open epics and tickets per repo, straight from gh. Display only."""
    rows: list[dict[str, Any]] = []
    unreachable: list[str] = []
    with ThreadPoolExecutor(max_workers=len(repos)) as pool:
        for repo_rows, why in pool.map(_gh_open_issues, repos):
            rows.extend(repo_rows)
            if why:
                unreachable.append(why)

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
