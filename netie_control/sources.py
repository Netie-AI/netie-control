"""Read-only readers for the estate's real state.

Every function here returns either real data or an explicit unreachable marker. None
of them invents a value, and none of them substitutes a plausible default for a source
it could not read - a page whose whole job is "what is actually true" is the worst
possible place to fake (R-0011).

Nothing in this module writes. Control is plane 4: it displays and it launches, and it
holds no keys and owns no route decision (NETIE.md section 3).
"""

from __future__ import annotations

import ctypes
import http.client
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from ctypes import wintypes
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
CREW_BELT_WAIT_S = 1.5
OPENVAULT_USAGE_WAIT_S = 1.5
PICKUP_BOARD_WAIT_S = 1.5
BOARD_WAIT_S = 4.0
KB_WAIT_S = 1.5
CORTEX_WAIT_S = 1.5
SIDECAR_WAIT_S = 1.5
PLAN_ROW_KEYS = ("id", "title", "status", "owner", "kind")
PROMPT_ROW_KEYS = ("id", "title", "kind", "source")
FETCH_ROW_KEYS = ("id", "title", "kind", "source", "status")
USAGE_SUMMARY_KEYS = (
    "requests",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "billable_tokens",
    "estimated_tokens",
    "cache_hits",
    "failed_requests",
    "priced",
)


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


def loopback_get_status(url: str, timeout: float = 2.0, read: int = 512) -> Reading:
    """Loopback GET for liveness. Discards the body. Not an open proxy.

    urllib.urlopen waits for the full payload; Crew `/` is ~48KB and that
    timed out. http.client + Connection: close is enough to know the host answers.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host not in LOOPBACK_HOSTS:
        return Reading.unreachable(url, "Control only probes loopback (not an open proxy)")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    conn: http.client.HTTPConnection | None = None
    try:
        if parsed.scheme == "https":
            conn = http.client.HTTPSConnection(host, port, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", path, headers={"Connection": "close", "Accept": "*/*"})
        resp = conn.getresponse()
        status = resp.status
        try:
            resp.read(read)
        except http.client.IncompleteRead:
            pass
    except (TimeoutError, OSError, ValueError, http.client.HTTPException) as exc:
        return Reading.unreachable(url, f"unreachable: {exc}")
    finally:
        if conn is not None:
            conn.close()
    if status != 200:
        return Reading.unreachable(url, f"HTTP {status}")
    return Reading(ok=True, data={"up": True}, source=url)


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
            "coordinate": f"{base}/v1/coordinate",
            "claim": "GitHub Issues + CLAIMS.json",
            "run": "Cortex",
            "converse": crew_base(),
        },
        "before_seating": [
            f"{base}/v1/pickup",
            f"{base}/v1/fleet",
            f"{base}/v1/you",
            f"{base}/v1/coordinate",
        ],
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "run_owner": "Cortex",
        "forbidden": ["/v1/secrets", "/v1/route", "/v1/goal", "/v1/run"],
        "human_stop": ["HT1", "HT2", "work.netie.ai"],
        "desk": {
            "talk_probe": "/crew/wakes",
            "you_steps": len(HITL_STEPS),
            "usage_probe": "/api/usage",
            "board_wait_s": BOARD_WAIT_S,
            "pickup_board_wait_s": PICKUP_BOARD_WAIT_S,
            "kb_wait_s": KB_WAIT_S,
            "cortex_wait_s": CORTEX_WAIT_S,
            "crew_belt_wait_s": CREW_BELT_WAIT_S,
            "openvault_usage_wait_s": OPENVAULT_USAGE_WAIT_S,
            "sidecar_wait_s": SIDECAR_WAIT_S,
            "sidecar_probe": "/health",
            "display_gets": [
                "/v1/plans",
                "/v1/prompts",
                "/v1/fetch",
                "/v1/sidecar",
                "/v1/launchers",
            ],
        },
        "rule": (
            "Every lane (Cursor, Claude Code, Grok Bot) reads Control before seating. "
            "Control does not assign and does not run. Claim on GitHub first (F-0025). "
            "F-0030: a scale request is not a third orchestrator."
        ),
    }


def kb_base() -> str:
    return os.environ.get("NETIE_KB_URL", "http://127.0.0.1:8030").rstrip("/")


def sidecar_base() -> str:
    """Engine sidecar host. Not Crew HTML :8020. Not paperclip :3100."""
    return os.environ.get("NETIE_SIDECAR_URL", "http://127.0.0.1:8023").rstrip("/")


def cortex_view() -> Reading:
    """Read-only Cortex probes. Does not touch the ledger; one ledger, via Cortex HTTP.

    Unlock for P-CTL-1: GET /health + GET /api/engine/activity including
    activity.governance (ledger tip, bound session ids, refusals; no payloads).
    Health, activity, and features share one pool at CORTEX_WAIT_S so a hung
    /health cannot stack a second wait. A dedicated refusal-history GET is
    still absent; Control will not scrape the chain for more than Cortex
    already returns.
    """
    base = cortex_base()
    with ThreadPoolExecutor(max_workers=3) as pool:
        health_f = pool.submit(
            loopback_get_json, f"{base}/health", CORTEX_WAIT_S
        )
        act_f = pool.submit(
            loopback_get_json, f"{base}/api/engine/activity", CORTEX_WAIT_S
        )
        feat_f = pool.submit(
            loopback_get_json, f"{base}/health/features", CORTEX_WAIT_S
        )
        health = health_f.result()
        activity = act_f.result()
        features = feat_f.result()
    if not health.ok:
        return health
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
            "features_detail": None if features.ok else features.detail,
            "governance": gov if gov_ok else None,
            "refusal_view": refusal_view,
            "refusal_why": refusal_why,
        },
        source=base,
        detail="" if activity.ok else f"activity: {activity.detail}",
    )


def slim_openvault_usage(payload: dict[str, Any]) -> dict[str, Any]:
    """Spend counts only. Drops the per-row ledger (those rows name vault holders).

    OpenVault labels estimated tokens separately and keeps priced=false.
    Control never invents a rate (HT1/HT2 HUMAN_STOP).
    """
    summary_in = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    summary = {key: summary_in[key] for key in USAGE_SUMMARY_KEYS if key in summary_in}
    return {
        "count": payload.get("count"),
        "summary": summary,
    }


def openvault_view() -> Reading:
    """Display FreeRoute/vault liveness and spend counts. Does not choose a route.

    Healthz and usage run in parallel at OPENVAULT_USAGE_WAIT_S so a hung
    peer cannot stack 2s + 1.5s on GET /.
    """
    base = openvault_base()
    health_url = f"{base}/api/healthz"
    usage_url = f"{base}/api/usage?limit=1"
    with ThreadPoolExecutor(max_workers=2) as pool:
        health_f = pool.submit(
            loopback_get_json, health_url, OPENVAULT_USAGE_WAIT_S
        )
        usage_f = pool.submit(
            loopback_get_json, usage_url, OPENVAULT_USAGE_WAIT_S
        )
        healthz = health_f.result()
        usage = usage_f.result()
    if not healthz.ok:
        return healthz
    status = (healthz.data or {}).get("status")
    usage_data = None
    usage_detail = ""
    if usage.ok and isinstance(usage.data, dict):
        usage_data = slim_openvault_usage(usage.data)
    else:
        usage_detail = usage.detail or "usage unread"
    return Reading(
        ok=True,
        data={
            "up": status == "ok",
            "healthz": healthz.data,
            "usage": usage_data,
            "usage_detail": usage_detail,
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
    """Display-only GET of Crew conveyor JSON. Control does not converse.

    Live :8020 is still the Cortex-crew fork: /v1/belt can hang and /crew/belt
    can 404. Probe both with a short timeout. Prefer /v1/belt when it answers.
    Named absence if neither does. No POST handoff.
    """
    base = crew_base()
    v1 = f"{base}/v1/belt"
    alt = f"{base}/crew/belt"
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="crew-belt") as pool:
        first = pool.submit(loopback_get_json, v1, CREW_BELT_WAIT_S)
        second = pool.submit(loopback_get_json, alt, CREW_BELT_WAIT_S)
        primary = first.result()
        fallback = second.result()
    if primary.ok:
        return primary
    if fallback.ok:
        return fallback
    why = (
        f"{primary.detail or 'unread'}; "
        f"tried {alt}: {fallback.detail or 'unread'}"
    )
    return Reading.unreachable(v1, why)


def crew_talk_view() -> Reading:
    """Engine converse host. Does not copy Crew HTML (F-0026).

    The hung Cortex-crew fork still answers GET / in tens of ms and hangs
    `/crew/health`. `/crew/wakes` 404s on that fork and 200s on engine Crew.
    Talk must not go green on HTML-only (R-0011).
    """
    wakes = f"{crew_base()}/crew/wakes"
    raw = loopback_get_json(wakes, timeout=CREW_BELT_WAIT_S)
    if not raw.ok:
        why = raw.detail or "wakes unread"
        return Reading.unreachable(wakes, why)
    return Reading(ok=True, data={"up": True, "wakes": True}, source=wakes)


def _slim_rows(payload: Any, keys: tuple[str, ...], *list_keys: str) -> list[dict[str, Any]]:
    """Ids/titles only. Prompt, skill_body, html, and transcript never travel."""
    items: Any = payload
    if isinstance(payload, dict):
        items = []
        for key in list_keys:
            cand = payload.get(key)
            if isinstance(cand, list):
                items = cand
                break
    if not isinstance(items, list):
        return []
    slim: list[dict[str, Any]] = []
    for row in items[:40]:
        if not isinstance(row, dict):
            continue
        slim.append({key: row.get(key) for key in keys if key in row})
    return slim


def slim_sidecar_health(payload: dict[str, Any]) -> dict[str, Any]:
    """Liveness only. Drop HTML, tool catalogs, and any token-shaped fields."""
    status = payload.get("status")
    ok = payload.get("ok")
    up = status in ("ok", "healthy") or ok is True
    return {
        "up": up,
        "status": status,
        "ok": ok,
        "service": payload.get("service"),
    }


def sidecar_view() -> Reading:
    """Engine sidecar :8023 health. JSON only. HTML GET / is not enough (R-0011).

    Hung Crew :8020 still serves HTML. Sidecar is the engine host. Control
    does not start or bind it. Agents do not rebind :8020 (R-0015).
    """
    base = sidecar_base()
    health = f"{base}/health"
    healthz = f"{base}/healthz"
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="sidecar") as pool:
        first = pool.submit(loopback_get_json, health, SIDECAR_WAIT_S)
        second = pool.submit(loopback_get_json, healthz, SIDECAR_WAIT_S)
        primary = first.result()
        fallback = second.result()
    raw = primary if primary.ok else fallback
    if not raw.ok:
        why = (
            f"{primary.detail or 'unread'}; "
            f"tried {healthz}: {fallback.detail or 'unread'}"
        )
        return Reading.unreachable(health, why)
    payload = raw.data if isinstance(raw.data, dict) else {}
    return Reading(ok=True, data=slim_sidecar_health(payload), source=raw.source)


def sidecar_plans_view() -> Reading:
    """Display sidecar GET /v1/plans. Control does not run a plan."""
    url = f"{sidecar_base()}/v1/plans"
    raw = loopback_get_json(url, timeout=SIDECAR_WAIT_S)
    if not raw.ok:
        return raw
    items = _slim_rows(raw.data, PLAN_ROW_KEYS, "items", "plans")
    return Reading(
        ok=True,
        data={"items": items, "count": len(items)},
        source=url,
    )


def sidecar_prompts_view() -> Reading:
    """Display sidecar GET /v1/prompts. Ids/titles only. Bodies refuse (TAS-CONTROL)."""
    url = f"{sidecar_base()}/v1/prompts"
    raw = loopback_get_json(url, timeout=SIDECAR_WAIT_S)
    if not raw.ok:
        return raw
    items = _slim_rows(raw.data, PROMPT_ROW_KEYS, "items", "prompts")
    return Reading(
        ok=True,
        data={"items": items, "count": len(items)},
        source=url,
    )


def sidecar_fetch_view(q: str = "") -> Reading:
    """Display sidecar GET /v1/fetch. Loopback only. Not an open proxy."""
    needle = (q or "").strip()
    url = f"{sidecar_base()}/v1/fetch"
    if not needle:
        return Reading.unreachable(url, "empty query")
    url = f"{url}?q={quote(needle)}"
    raw = loopback_get_json(url, timeout=SIDECAR_WAIT_S)
    if not raw.ok:
        return raw
    items = _slim_rows(raw.data, FETCH_ROW_KEYS, "items", "hits")
    return Reading(
        ok=True,
        data={"q": needle, "items": items, "count": len(items)},
        source=url,
    )


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
    engine = payload.get("engine") if isinstance(payload.get("engine"), dict) else {}
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
        "engine_ok": engine.get("ok"),
        "engine_url": engine.get("url"),
        "engine_detail": engine.get("detail"),
    }


def crew_health_view(timeout: float = CREW_BELT_WAIT_S) -> Reading:
    """Display Crew laptop-tool arming. Control does not arm, start, or kill MCPs.

    S-0001 step 3: GET /crew/health names which computer-control MCPs are armed.
    UACC is the OS mouse. Playwright is the Chrome DOM. Control never POSTs
    an arming route and never copies vault material from Crew's payload.
    Caps at CREW_BELT_WAIT_S so a hung fork cannot stall GET /. Talk liveness
    is crew_talk_view. Coordinate skips this probe.
    """
    raw = loopback_get_json(f"{crew_base()}/crew/health", timeout=timeout)
    if not raw.ok:
        return raw
    payload = raw.data if isinstance(raw.data, dict) else {}
    return Reading(ok=True, data=slim_crew_health(payload), source=raw.source)


def kb_view() -> Reading:
    """Liveness of the one skill registry. Counts only. No artifact bodies."""
    return loopback_get_json(f"{kb_base()}/healthz", timeout=KB_WAIT_S)


def kb_search(q: str, limit: int = 8) -> Reading:
    """Display-only search of the one registry. No bodies. Control does not run skills."""
    needle = (q or "").strip()
    if not needle:
        return Reading.unreachable(f"{kb_base()}/search", "empty query")
    cap = max(1, min(int(limit or 8), 20))
    url = f"{kb_base()}/search?q={quote(needle)}&limit={cap}"
    raw = loopback_get_json(url, timeout=KB_WAIT_S)
    if not raw.ok:
        return raw
    hits = raw.data
    if isinstance(hits, dict):
        hits = hits.get("hits") or hits.get("items") or []
    if not isinstance(hits, list):
        return Reading.unreachable(url, "search did not return a list")
    slim: list[dict[str, Any]] = []
    for row in hits[:cap]:
        if not isinstance(row, dict):
            continue
        slim.append(
            {
                "id": row.get("id"),
                "kind": row.get("kind"),
                "title": row.get("title"),
                "score": row.get("score"),
            }
        )
    return Reading(ok=True, data={"q": needle, "hits": slim}, source=url)


_SKILL_ID = re.compile(r"^[A-Za-z]-\d{4}$")


def loopback_get_text(url: str, timeout: float = 8.0, limit: int = 8000) -> Reading:
    """GET text from loopback only. Caps the body. Not a second registry."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host not in LOOPBACK_HOSTS:
        return Reading.unreachable(url, "Control only probes loopback (not an open proxy)")
    req = urllib.request.Request(url, method="GET", headers={"Accept": "text/markdown, text/plain"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(limit)
            status = getattr(resp, "status", 200)
            if status != 200:
                return Reading.unreachable(url, f"HTTP {status}")
    except urllib.error.HTTPError as exc:
        return Reading.unreachable(url, f"HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return Reading.unreachable(url, f"unreachable: {exc}")
    text = raw.decode("utf-8", errors="replace")
    return Reading(ok=True, data={"text": text, "capped": len(raw) >= limit}, source=url)


def kb_show(sid: str) -> Reading:
    """Display one registry artifact. Truncated. Control does not run it."""
    name = (sid or "").strip()
    if not _SKILL_ID.match(name):
        return Reading.unreachable(f"{kb_base()}/item", "id must look like S-0001")
    return loopback_get_text(f"{kb_base()}/item/{name}", timeout=KB_WAIT_S)


def _probe_failed(reading: dict[str, Any]) -> bool:
    """True when a probe failed. Deferred skips stay quiet so the 15s poll does not lie."""
    if reading.get("ok"):
        return False
    why = str(reading.get("detail") or "")
    return not why.startswith("deferred")


def workers_from(cortex: dict[str, Any], crew_health: dict[str, Any]) -> list[dict[str, Any]]:
    """Deep-agent-shaped live workers. Display only. Control does not start them.

    Unread Cortex, unread Cortex activity, or unread Crew health is a named
    chip, never an idle empty row (R-0011). Health-ok with activity None is
    unread, not quiet. Coordinate's deferred /crew/health skip is not unread.
    """
    rows: list[dict[str, Any]] = []
    cdata = cortex.get("data") if isinstance(cortex.get("data"), dict) else {}
    activity = cdata.get("activity")
    activity_unread = bool(cortex.get("ok")) and not isinstance(activity, dict)
    if _probe_failed(cortex) or activity_unread:
        rows.append(
            {
                "kind": "workflow",
                "name": "unread",
                "live": False,
                "unread": True,
                "href": cortex_base(),
                "do_not": "POST /v1/run stays 405",
            }
        )
    else:
        activity = activity if isinstance(activity, dict) else {}
        wf = activity.get("workflows") if isinstance(activity.get("workflows"), dict) else {}
        for run in (wf.get("active") or [])[:8]:
            if not isinstance(run, dict):
                continue
            rows.append(
                {
                    "kind": "workflow",
                    "name": str(run.get("title") or run.get("id") or "workflow"),
                    "live": True,
                    "status": run.get("status"),
                    "href": cortex_base(),
                    "do_not": "POST /v1/run stays 405",
                }
            )
        rt = activity.get("routines") if isinstance(activity.get("routines"), dict) else {}
        for rid in (rt.get("running") or [])[:8]:
            rows.append(
                {
                    "kind": "routine",
                    "name": str(rid),
                    "live": True,
                    "href": cortex_base(),
                    "do_not": "POST /v1/run stays 405",
                }
            )
    if _probe_failed(crew_health):
        rows.append(
            {
                "kind": "mcp",
                "name": "unread",
                "live": False,
                "unread": True,
                "href": crew_base(),
                "do_not": "Control does not arm MCPs",
            }
        )
    else:
        hdata = crew_health.get("data") if isinstance(crew_health.get("data"), dict) else {}
        for mcp in hdata.get("mcp") or []:
            if not isinstance(mcp, dict):
                continue
            running = bool(mcp.get("running"))
            armed = bool(mcp.get("armed"))
            if not running and not armed:
                continue
            rows.append(
                {
                    "kind": "mcp",
                    "name": str(mcp.get("name") or "mcp"),
                    "live": running,
                    "status": mcp.get("status"),
                    "href": crew_base(),
                    "do_not": "Control does not arm MCPs",
                }
            )
    return rows


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
    {
        "n": "8",
        "id": "crew-engine-bind",
        "title": "Bind live :8020 to engine Crew",
        "do": "Live converse is still the Cortex-crew fork. Belt /v1/belt hangs; "
             "/crew/belt 404s. Stop that hung process yourself, then start "
             "python -m CortexOS.crew from E:\\Cortex (scripts\\start_crew.ps1). "
             "Agents must not start or kill it (R-0015). Control stays display-only.",
        "url": "http://127.0.0.1:8020",
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


def pickup_from_readings(fleet: dict[str, Any], board: dict[str, Any]) -> Reading:
    """CLAIMS unseated tray. Board is optional. Control does not assign."""
    fleet = fleet if isinstance(fleet, dict) else {}
    board = board if isinstance(board, dict) else {}
    fleet_ok = bool(fleet.get("ok"))
    board_ok = bool(board.get("ok"))
    if not fleet_ok and not board_ok:
        why = "pickup needs fleet or board; both unread"
        fleet_why = fleet.get("detail") or ""
        board_why = board.get("detail") or ""
        if fleet_why or board_why:
            why = f"{why}. fleet: {fleet_why or 'unread'}. board: {board_why or 'unread'}"
        return Reading.unreachable("fleet+board", why)
    tray = pickup_tray(
        fleet.get("data") if fleet_ok else {},
        board.get("data") if board_ok else {},
    )
    tray["board_deferred"] = not board_ok
    tray["board_detail"] = "" if board_ok else (board.get("detail") or "board unread")
    tray["board_source"] = "GET /v1/board"
    source = str(fleet.get("source") or "") if fleet_ok else "fleet+board"
    detail = ""
    if not board_ok:
        detail = f"board deferred ({tray['board_source']}): {tray['board_detail']}"
    return Reading(ok=True, data=tray, source=source or "fleet+board", detail=detail)


def board_if_quick(wait_s: float | None = None) -> Reading:
    """Include gh board only if it finishes quickly. Pickup must not wait on gh."""
    timeout = PICKUP_BOARD_WAIT_S if wait_s is None else float(wait_s)

    def _call() -> Reading:
        try:
            return board(timeout=timeout)
        except TypeError:
            return board()

    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pickup-board")
    fut = pool.submit(_call)
    try:
        return fut.result(timeout=timeout)
    except TimeoutError:
        return Reading.unreachable(
            "GET /v1/board",
            f"deferred so pickup stays fast (gh did not finish within {timeout}s)",
        )
    except Exception as exc:  # noqa: BLE001 - a board fetch must never crash pickup
        # Deferring the board is the whole point of this call. Anything gh, the
        # network, or json can raise renders as a stated absence, which rule 5
        # already requires: unknown must never paint as green, and it must never
        # take the tray down with it either.
        return Reading.unreachable("GET /v1/board", f"deferred: {exc}")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def pickup_view(*, board_wait: float | None = None) -> Reading:
    """CLAIMS unseated tray. Board only if gh answers in time. Does not seat."""
    fleet = fleet_view().to_dict()
    board = board_if_quick(board_wait).to_dict()
    return pickup_from_readings(fleet, board)


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


def _claude_argv() -> list[str] | None:
    """Locate the Claude CLI. Does not start Claude (R-0015)."""
    found = shutil.which("claude")
    if found:
        return [found]
    home = Path.home()
    appdata = os.environ.get("APPDATA", "")
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(appdata) / "npm" / "claude.cmd" if appdata else None,
        Path(local) / "npm" / "claude.cmd" if local else None,
        home / "AppData" / "Roaming" / "npm" / "claude.cmd",
        home / ".local" / "bin" / "claude.exe",
    ]
    for path in candidates:
        if path is not None and path.is_file():
            return [str(path)]
    return None


def claude_pads_view() -> Reading:
    """Live Claude Code pads on this PC. List only. Does not start Claude (R-0015)."""
    argv = _claude_argv()
    if not argv:
        return Reading.unreachable(
            "claude agents --json",
            "claude not on PATH (unread, not down-and-quiet)",
        )
    try:
        proc = subprocess.run(
            [*argv, "agents", "--json"],
            capture_output=True,
            text=True,
            timeout=4,
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

_TH32CS_SNAPPROCESS = 0x00000002
_MAX_PATH = 260


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * _MAX_PATH),
    ]


def _win_running_images(wanted: set[str]) -> set[str]:
    """Lowercase exe names from wanted that are running. Never starts them."""
    if not wanted:
        return set()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_PROCESSENTRY32W),
    ]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_PROCESSENTRY32W),
    ]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    snap = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if snap == wintypes.HANDLE(-1).value:
        raise OSError("CreateToolhelp32Snapshot failed")
    pe = _PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
    found: set[str] = set()
    try:
        more = kernel32.Process32FirstW(snap, ctypes.byref(pe))
        while more:
            name = pe.szExeFile.lower()
            if name in wanted:
                found.add(name)
                if found == wanted:
                    break
            more = kernel32.Process32NextW(snap, ctypes.byref(pe))
        return found
    finally:
        kernel32.CloseHandle(snap)


def desktop_surfaces_view() -> Reading:
    """Which founder apps are running. Present/absent only. Never start or kill."""
    wanted = {image.lower() for image, _ in _SURFACE_IMAGES}
    try:
        running = _win_running_images(wanted)
    except OSError as exc:
        return Reading.unreachable("process snapshot", f"unreachable: {exc}")
    rows = [
        {
            "name": label,
            "image": image,
            "present": image.lower() in running,
        }
        for image, label in _SURFACE_IMAGES
    ]
    return Reading(
        ok=True,
        data={
            "rows": rows,
            "note": "present/absent only. Control did not start or kill them (R-0015).",
        },
        source="process snapshot",
    )


def _reading_live(reading: dict[str, Any], key: str = "up") -> bool:
    """A peer is live only if we read it and it said so. Unread is not green."""
    if not isinstance(reading, dict) or not reading.get("ok"):
        return False
    data = reading.get("data")
    if not isinstance(data, dict):
        return True
    if key in data:
        return bool(data.get(key))
    status = data.get("status")
    if status is not None:
        return status in ("ok", "healthy")
    if "ok" in data:
        return bool(data.get("ok"))
    if data.get("service"):
        return True
    return True


def _surface_present(surfaces: dict[str, Any], label: str) -> bool:
    if not isinstance(surfaces, dict) or not surfaces.get("ok"):
        return False
    data = surfaces.get("data") if isinstance(surfaces.get("data"), dict) else {}
    for row in data.get("rows") or []:
        if isinstance(row, dict) and row.get("name") == label:
            return bool(row.get("present"))
    return False


def _pad_count(claude_pads: dict[str, Any]) -> int | None:
    if not isinstance(claude_pads, dict) or not claude_pads.get("ok"):
        return None
    data = claude_pads.get("data") if isinstance(claude_pads.get("data"), dict) else {}
    pads = data.get("pads")
    if isinstance(pads, list):
        return len(pads)
    return None


def coordinate_teammates(
    *,
    surfaces: dict[str, Any],
    claude_pads: dict[str, Any],
    fleet: dict[str, Any],
    crew_health: dict[str, Any],
    crew_talk: dict[str, Any],
    cortex: dict[str, Any],
    sidecar: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Named workers the operator can actually invoke. Control does not spawn them."""
    crew = crew_base()
    mates: list[dict[str, Any]] = []
    for label, tid, href in (
        ("Cursor", "cursor", "#pc"),
        ("Claude Code", "claude", "#pads"),
        ("Grok Bot", "grok", crew),
    ):
        mates.append(
            {
                "id": tid,
                "name": label,
                "kind": "surface",
                "live": _surface_present(surfaces, label),
                "invoke": "present/absent only",
                "href": href if tid != "grok" else crew,
                "do_not": f"Control will not start {label}",
            }
        )
    if claude_pads.get("ok"):
        data = claude_pads.get("data") if isinstance(claude_pads.get("data"), dict) else {}
        for i, pad in enumerate((data.get("pads") or [])[:12]):
            if not isinstance(pad, dict):
                continue
            mates.append(
                {
                    "id": f"pad-{i}",
                    "name": str(pad.get("name") or f"pad-{i}"),
                    "kind": "pad",
                    "live": True,
                    "pid": pad.get("pid"),
                    "cwd": pad.get("cwd"),
                    "invoke": "list only",
                    "href": "#pads",
                    "do_not": "Control will not start Claude",
                }
            )
    fleet_data = fleet.get("data") if isinstance(fleet.get("data"), dict) else {}
    unseated = 0
    if fleet.get("ok"):
        for row in fleet_data.get("rows") or []:
            if not isinstance(row, dict):
                continue
            if row.get("role") == "UNSEATED":
                unseated += 1
                continue
            if row.get("role") != "SEATED":
                continue
            mates.append(
                {
                    "id": f"seat-{row.get('ticket')}",
                    "name": str(row.get("ticket") or "seated"),
                    "kind": "writer",
                    "live": True,
                    "lane": row.get("lane"),
                    "invoke": "already claimed on GitHub",
                    "href": str(row.get("href") or "#fleet"),
                    "do_not": "Do not dual-write this branch",
                }
            )
    mates.append(
        {
            "id": "ticket-runner",
            "name": "Ticket Runner",
            "kind": "seater",
            "live": False,
            "pickup": unseated,
            "invoke": "/ticket-runner in Claude Code, then claim GitHub",
            "href": "#pickup",
            "do_not": "F-0030 Control does not spawn Ticket Runner",
        }
    )
    mates.append(
        {
            "id": "cursor-task",
            "name": "Cursor cloud task",
            "kind": "task",
            "live": False,
            "invoke": "Cortex#51 kind=task on the matching workspace",
            "href": "https://github.com/Netie-AI/Cortex/issues/51",
            "do_not": "One writer per branch. Not one cloud agent per issue.",
        }
    )
    mates.append(
        {
            "id": "crew",
            "name": "Crew talk",
            "kind": "talk",
            "live": _reading_live(crew_talk),
            "invoke": crew,
            "href": crew,
            "do_not": "Do not copy Crew composer into Control",
        }
    )
    mates.append(
        {
            "id": "cortex",
            "name": "Cortex run",
            "kind": "run",
            "live": _reading_live(cortex),
            "invoke": cortex_base(),
            "href": cortex_base(),
            "do_not": "POST /v1/run stays 405",
        }
    )
    sidecar = sidecar or {}
    mates.append(
        {
            "id": "sidecar",
            "name": "Sidecar :8023",
            "kind": "sidecar",
            "live": _reading_live(sidecar),
            "invoke": sidecar_base(),
            "href": "/v1/sidecar",
            "do_not": "Control does not start :8023. Agents do not rebind :8020",
        }
    )
    return mates


def coordinate_payload(
    *,
    cortex: dict[str, Any],
    openvault: dict[str, Any],
    crew_health: dict[str, Any],
    crew_talk: dict[str, Any],
    kb: dict[str, Any],
    surfaces: dict[str, Any],
    claude_pads: dict[str, Any],
    fleet: dict[str, Any] | None = None,
    sidecar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Grok-class job -> owner invoke map. Display only. Control does not invoke."""
    fleet = fleet or {}
    sidecar = sidecar or {}
    crew = crew_base()
    cortex_url = cortex_base()
    kb_url = kb_base()
    vault_url = openvault_base()
    crew_data = crew_health.get("data") if isinstance(crew_health.get("data"), dict) else {}
    grok_offloaded = bool(crew_data.get("grok_offloaded")) if crew_health.get("ok") else False
    kb_data = kb.get("data") if isinstance(kb.get("data"), dict) else {}
    counts = kb_data.get("counts") if isinstance(kb_data.get("counts"), dict) else {}
    pad_n = _pad_count(claude_pads)
    cursor_on = _surface_present(surfaces, "Cursor")
    claude_on = _surface_present(surfaces, "Claude Code")
    grok_on = _surface_present(surfaces, "Grok Bot")
    lanes = [
        {
            "id": "fleet",
            "job": "See who holds what",
            "owner": "Control",
            "invoke": "GET /v1/fleet",
            "href": "/v1/fleet",
            "live": True,
            "do_not": "Control does not assign",
        },
        {
            "id": "claim",
            "job": "Claim / comment",
            "owner": "GitHub Issues + CLAIMS.json",
            "invoke": "comment on the GitHub issue",
            "href": "https://github.com/Netie-AI/netie-control/issues",
            "live": True,
            "do_not": "Do not invent a second bus",
        },
        {
            "id": "run",
            "job": "Run work",
            "owner": "Cortex",
            "invoke": cortex_url,
            "href": cortex_url,
            "live": _reading_live(cortex),
            "do_not": "POST /v1/run stays 405",
        },
        {
            "id": "talk",
            "job": "Talk / A2A",
            "owner": "Crew",
            "invoke": crew,
            "href": crew,
            "live": _reading_live(crew_talk),
            "do_not": "Do not copy Crew composer into Control",
        },
        {
            "id": "sidecar",
            "job": "Sidecar engine host",
            "owner": "Crew sidecar :8023",
            "invoke": sidecar_base(),
            "href": "/v1/sidecar",
            "live": _reading_live(sidecar),
            "do_not": "Control does not start :8023. Agents do not rebind :8020",
        },
        {
            "id": "crew-bind",
            "job": "Bind live :8020 to engine Crew",
            "owner": "founder hand (R-0015)",
            "invoke": "YOU step 8. scripts\\start_crew.ps1 from E:\\Cortex",
            "href": "/v1/you",
            "live": False,
            "do_not": "Agents must not start or kill :8020",
        },
        {
            "id": "cursor",
            "job": "Cursor (this PC)",
            "owner": "founder hand (R-0015)",
            "invoke": "present/absent only",
            "href": "#pc",
            "live": cursor_on,
            "do_not": "Control will not start Cursor.exe",
        },
        {
            "id": "claude",
            "job": "Claude pads",
            "owner": "Claude Code",
            "invoke": "claude agents --json (list only)",
            "href": "#pads",
            "live": claude_on or pad_n is not None,
            "count": pad_n,
            "do_not": "Control will not start Claude",
        },
        {
            "id": "grok",
            "job": "Grok Bot",
            "owner": "Crew offload when capped",
            "invoke": crew,
            "href": crew,
            "live": grok_on or grok_offloaded,
            "do_not": "Do not start Grok Bot.exe",
        },
        {
            "id": "skills",
            "job": "Skills chest",
            "owner": "Netie-KB",
            "invoke": f"{kb_url}/healthz",
            "href": f"{kb_url}/healthz",
            "live": _reading_live(kb),
            "counts": counts,
            "do_not": "Do not keep a private skills folder (R-0016)",
        },
        {
            "id": "keys",
            "job": "Keys",
            "owner": "OpenVault",
            "invoke": f"{vault_url}/api/healthz",
            "href": f"{vault_url}/api/healthz",
            "live": _reading_live(openvault),
            "do_not": "POST /v1/secrets stays 405",
        },
        {
            "id": "spawn",
            "job": "PRD / Epic / Ticket spawn",
            "owner": "AGENT_SYSTEM.md + Claude Code agents",
            "invoke": r"~/.claude/agents/{prd-agent,epic-agent,ticket-runner}.md",
            "href": "#pickup",
            "live": False,
            "do_not": "F-0030 Control does not spawn",
        },
    ]
    live_n = sum(1 for lane in lanes if lane.get("live"))
    teammates = coordinate_teammates(
        surfaces=surfaces,
        claude_pads=claude_pads,
        fleet=fleet,
        crew_health=crew_health,
        crew_talk=crew_talk,
        cortex=cortex,
        sidecar=sidecar,
    )
    workers = workers_from(cortex, crew_health)
    health_why = str(crew_health.get("detail") or "")
    health_deferred = (not crew_health.get("ok")) and health_why.startswith("deferred")
    return {
        "lanes": lanes,
        "teammates": teammates,
        "workers": workers,
        "health_deferred": health_deferred,
        "live": live_n,
        "router": {
            "owner": "OpenVault FreeRoute",
            "note": (
                "Grok Bot reconstructed routes Cursor / Claude / Codex. "
                "Control displays who is present. It does not pick a route."
            ),
            "surfaces": {
                "cursor": cursor_on,
                "claude": claude_on,
                "grok": grok_on,
                "cortex": _reading_live(cortex),
                "crew": _reading_live(crew_talk),
                "sidecar": _reading_live(sidecar),
            },
        },
        "note": (
            "Grok-class coordination is this map. Control displays who to invoke. "
            "Owners invoke. Control does not."
        ),
    }


def coordinate_from_readings(blob: dict[str, Any]) -> Reading:
    """Build the invoke map from desk readings already taken. Does not re-probe."""
    return Reading(
        ok=True,
        data=coordinate_payload(
            cortex=blob.get("cortex") or {},
            openvault=blob.get("openvault") or {},
            crew_health=blob.get("crew_health") or {},
            crew_talk=blob.get("crew_talk") or {},
            kb=blob.get("kb") or {},
            surfaces=blob.get("surfaces") or {},
            claude_pads=blob.get("claude_pads") or {},
            fleet=blob.get("fleet") or {},
            sidecar=blob.get("sidecar") or {},
        ),
        source="peers+surfaces",
    )


def coordinate_view() -> Reading:
    """Live invoke map. Probes peers and this-PC surfaces. Writes nothing.

    Talk shares the peer pool. /crew/health stays deferred: the 15s chip
    poll starved Talk when health ran ~8s. Hung wakes must not stack a
    second Cortex wait.
    """
    jobs = {
        "crew_talk": crew_talk_view,
        "cortex": cortex_view,
        "openvault": openvault_view,
        "kb": kb_view,
        "surfaces": desktop_surfaces_view,
        "fleet": fleet_view,
        "sidecar": sidecar_view,
    }
    blob: dict[str, Any] = {
        "crew_health": Reading.unreachable(
            f"{crew_base()}/crew/health",
            "deferred so Talk poll is not starved",
        ).to_dict(),
        "claude_pads": Reading.unreachable(
            "claude agents --json",
            "deferred so the poll stays fast",
        ).to_dict(),
    }
    with ThreadPoolExecutor(max_workers=max(len(jobs), 1)) as pool:
        futs = {key: pool.submit(fn) for key, fn in jobs.items()}
        for key, fut in futs.items():
            blob[key] = fut.result().to_dict()
    return coordinate_from_readings(blob)


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


def _gh_open_issues(repo: str, timeout: float = BOARD_WAIT_S) -> tuple[list[dict[str, Any]], str]:
    """One repo's open issues. Empty rows + reason when gh cannot answer."""
    try:
        proc = subprocess.run(
            ["gh", "issue", "list", "--repo", repo, "--state", "open",
             "--limit", "50", "--json", "number,title,labels,url"],
            capture_output=True, text=True, timeout=timeout,
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


def board(repos: tuple[str, ...] = BOARD_REPOS, *, timeout: float = BOARD_WAIT_S) -> Reading:
    """Open epics and tickets per repo, straight from gh. Display only.

    GET /v1/board uses BOARD_WAIT_S (4s). Pickup passes PICKUP_BOARD_WAIT_S
    (1.5s) so a hung gh cannot stall unseated CLAIMS.
    """
    rows: list[dict[str, Any]] = []
    unreachable: list[str] = []
    with ThreadPoolExecutor(max_workers=max(len(repos), 1)) as pool:
        for repo_rows, why in pool.map(partial(_gh_open_issues, timeout=timeout), repos):
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


def launchers_view() -> Reading:
    """Declared local CLI lanes. Display only. P-CTL-2 does not execute them."""
    items = [
        {
            "name": launcher.name,
            "blurb": launcher.blurb,
            "cwd": launcher.cwd,
            "argv": list(launcher.argv),
            "executes": False,
        }
        for launcher in LAUNCHERS
    ]
    return Reading(
        ok=True,
        data={
            "items": items,
            "count": len(items),
            "parked": "P-CTL-2",
            "executes": False,
        },
        source="LAUNCHERS",
        detail="Declared only. Control does not execute. P-CTL-2 has no principal.",
    )
