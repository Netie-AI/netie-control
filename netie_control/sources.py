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
AIRGPT_WAIT_S = 1.5
CORTEX_WAIT_S = 1.5
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
CONTROL_ROOT = Path(__file__).resolve().parents[1]


def _cortex_root() -> Path:
    env = os.environ.get("CORTEX_ROOT", "").strip()
    if env:
        return Path(env)
    for candidate in (Path(r"D:\Cortex"), Path(r"E:\Cortex")):
        if (candidate / "PARKING_LOT.md").is_file():
            return candidate
    return Path(r"D:\Cortex")


# TAS analog map, measured 2026-09-03 on this laptop. Live trees are D:\ not E:\.
# Verdicts match TAS/README.md. Control displays them; it does not unpark or copy.
ANALOG_LANES: tuple[dict[str, str], ...] = (
    {"lane": "1", "path": r"D:\Netie\mygastown", "product": "Crew",
     "name": "Crew", "surface": "integrated", "home": r"D:\Cortex\CortexOS\crew",
     "verdict": "SHIPPED",
     "note": "stranded/claim/wakes on engine. Hung :8020 is founder rebind"},
    {"lane": "1b", "path": r"D:\myopenworker", "product": "Crew",
     "name": "Crew HITL", "surface": "part", "home": r"D:\Cortex\CortexOS\crew",
     "verdict": "SHIPPED",
     "note": "queue leases + HITL tighten-only on engine. SKIP ee/"},
    {"lane": "1c", "path": r"D:\mydeepagents", "product": "Crew",
     "name": "Crew harness", "surface": "part", "home": r"D:\Cortex\CortexOS\crew",
     "verdict": "ALREADY",
     "note": "harness patterns already original on engine"},
    {"lane": "2", "path": r"D:\Netie\myOmniRoute", "product": "OpenVault",
     "name": "OpenVault FreeRoute", "surface": "integrated", "home": r"D:\OpenVault",
     "verdict": "SHIPPED",
     "note": "FreeRoute KEEP. SKIP NVIDIA/executors. HT1-HT5 HUMAN_STOP"},
    {"lane": "3", "path": r"D:\Netie\mypaperclip", "product": "Control",
     "name": "Control hub", "surface": "integrated", "home": r"D:\NetieControl",
     "verdict": "SHIPPED",
     "note": "board GET /v1/board + heartbeat on /v1/plans /v1/fetch. REFUSE analog React/:3100"},
    {"lane": "4", "path": r"D:\Cortex\myactiveflow\myactivepieces", "product": "Constructor",
     "name": "Constructor", "surface": "frozen", "home": r"D:\Constructor",
     "verdict": "SKIP", "note": "BAN clone + 665 pieces. Cortex is the only engine"},
    {"lane": "5", "path": r"D:\Cortex\Windows-MCP", "product": "Pointer",
     "name": "Pointer catalog", "surface": "page", "home": r"D:\Pointer",
     "verdict": "ALREADY",
     "note": "catalog only. UACC is the OS mouse"},
    {"lane": "6a", "path": r"D:\mygraphiti", "product": "Cortex assemble",
     "name": "Cortex assemble", "surface": "part", "home": r"D:\Cortex",
     "verdict": "ALREADY",
     "note": "temporal/provenance. Ledger stays SoT"},
    {"lane": "6b", "path": r"D:\mygraphify", "product": "Cortex assemble",
     "name": "Cortex assemble", "surface": "part", "home": r"D:\Cortex",
     "verdict": "ALREADY",
     "note": "layer_confidence. SKIP as product"},
    {"lane": "6c", "path": r"D:\myzep", "product": "Cortex assemble",
     "name": "Cortex assemble", "surface": "frozen", "home": r"D:\Cortex",
     "verdict": "SKIP",
     "note": "Cloud memory vendor. COPY none"},
    {"lane": "6d", "path": r"D:\myzep-go", "product": "Cortex assemble",
     "name": "Cortex assemble", "surface": "frozen", "home": r"D:\Cortex",
     "verdict": "SKIP",
     "note": "Go SDK. COPY none"},
    {"lane": "7a", "path": r"D:\mycogitorium", "product": "Constructor+Cortex",
     "name": "Cortex ontology", "surface": "parked", "home": r"D:\Cortex",
     "verdict": "PARK",
     "note": "P1 second ontology product. COPY none"},
    {"lane": "7b", "path": r"D:\mysemantica", "product": "Constructor+Cortex",
     "name": "Constructor inspect", "surface": "parked", "home": r"D:\Constructor",
     "verdict": "PARK",
     "note": "PROV-O/decision into inspect. No hub product"},
    {"lane": "8a", "path": r"D:\Cortex\myguaca", "product": "Crew CSS",
     "name": "Crew CSS", "surface": "frozen", "home": r"D:\Cortex\CortexOS\crew",
     "verdict": "SKIP",
     "note": "AGPL. COPY none. GET /stolen.css 410"},
    {"lane": "8b", "path": r"D:\Cortex\myrakazo", "product": "Crew CSS",
     "name": "Crew CSS", "surface": "frozen", "home": r"D:\Cortex\CortexOS\crew",
     "verdict": "SKIP",
     "note": "memory contract only. Stop CSS paste"},
    {"lane": "9", "path": r"D:\myOpenManus", "product": "Cortex agent_task",
     "name": "Cortex agent_task", "surface": "part", "home": r"D:\Cortex",
     "verdict": "SHIPPED",
     "note": "F20b quality-terminated loop on agent_task. SKIP second agent product"},
    {"lane": "10", "path": r"D:\Cortex\myorca", "product": "AirGPT",
     "name": "AirGPT host", "surface": "page", "home": r"D:\AirGPT",
     "verdict": "DISTILL",
     "note": "mobile steer. SKIP second orchestrator"},
    {"lane": "11", "path": r"D:\mysemble", "product": "AirGPT OpenIDE",
     "name": "OpenIDE search", "surface": "part", "home": r"D:\AirGPT\OpenIDE",
     "verdict": "SHIPPED",
     "note": "token rank in search_files. SKIP second search product"},
    {"lane": "12", "path": r"D:\myletta", "product": "Cortex /api/memory",
     "name": "Cortex memory", "surface": "frozen", "home": r"D:\Cortex",
     "verdict": "SKIP",
     "note": "Do not vendor a second memory product"},
    {"lane": "13", "path": r"D:\myn8n", "product": "Constructor",
     "name": "Constructor", "surface": "frozen", "home": r"D:\Constructor",
     "verdict": "BAN",
     "note": "Not a Constructor engine. Cortex compiles"},
    {"lane": "14", "path": r"D:\mybot", "product": "Crew+OpenVault",
     "name": "Crew converse", "surface": "frozen", "home": r"D:\Cortex\CortexOS\crew",
     "verdict": "SKIP",
     "note": "COPY none of analog reconstruction. Router/usage already OpenVault FreeRoute"},
    {"lane": "15", "path": r"D:\myclaude-code-system-prompts", "product": "Crew prompts",
     "name": "Crew prompts", "surface": "part", "home": r"D:\Cortex\CortexOS\crew",
     "verdict": "DISTILL", "note": "Ideas only. Write original Netie text. Do not paste Anthropic prompts"},
    {"lane": "16", "path": r"D:\myclaude-code", "product": "none",
     "name": "none", "surface": "frozen", "home": "frozen",
     "verdict": "BAN",
     "note": "Leaked tree. Do not copy"},
    {"lane": "17", "path": r"D:\mymem0", "product": "Cortex /api/memory",
     "name": "Cortex memory", "surface": "part", "home": r"D:\Cortex",
     "verdict": "DISTILL",
     "note": "add/update/retrieve + scope. SKIP vendor SDK. upsert/query already exist"},
    {"lane": "18", "path": r"D:\mymempalace", "product": "Cortex /api/memory",
     "name": "Cortex memory", "surface": "part", "home": r"D:\Cortex",
     "verdict": "DISTILL",
     "note": "collection = wing/room/drawer. SKIP Chroma vendor. Verbatim store"},
    {"lane": "19", "path": r"D:\myopencode", "product": "AirGPT OpenIDE",
     "name": "OpenIDE leftover TUI", "surface": "page", "home": r"D:\AirGPT\OpenIDE",
     "verdict": "SHIPPED",
     "note": "token coalesce + OpenAI tool schema. Leftover TUI DISTILL. SKIP second IDE"},
    {"lane": "20", "path": r"D:\OpenWillow", "product": "Pointer",
     "name": "Pointer dictation", "surface": "part", "home": r"D:\Pointer",
     "verdict": "DISTILL",
     "note": "GPLv3. COPY none. Dictation/scribe/hotkey. Keys stay OpenVault"},
)

# Prompt/system-prompt surfaces. Control lists them. It does not edit them.
PROMPT_SURFACES: tuple[dict[str, str], ...] = (
    {
        "id": "crew-manager",
        "path": r"D:\Cortex\CortexOS\crew\runtime.py",
        "product": "Crew",
        "verdict": "ALREADY",
        "note": "MANAGER_CHARTER is original Netie text. Improve in CortexOS/crew.",
    },
    {
        "id": "crew-skills",
        "path": r"D:\Cortex\CortexOS\crew\skill_packs",
        "product": "Crew",
        "verdict": "ALREADY",
        "note": "skill_packs/*.md names only. Control does not run a skill.",
    },
    {
        "id": "lane-15",
        "path": r"D:\myclaude-code-system-prompts",
        "product": "Crew prompts",
        "verdict": "DISTILL",
        "note": "Ideas only. Do not paste Anthropic prompt strings into Netie files.",
    },
    {
        "id": "lane-16",
        "path": r"D:\myclaude-code",
        "product": "none",
        "verdict": "BAN",
        "note": "Leaked Claude Code tree. Do not copy.",
    },
)

# Paste-ready Crew lane briefs. Original Netie text. Control displays
# them. It does not spawn the agents (F-0030). WIP cap is 2.
GROK_LANE_PASTES: tuple[dict[str, str], ...] = (
    {
        "id": "grok-master",
        "product": "Crew coordinator",
        "wip": "coordinator",
        "paste": (
            "You are the Netie estate coordinator. Crew converse is the chat "
            "surface. You are not D:\\mybot. COPY none of that reconstruction.\n\n"
            "Seat first:\n"
            "1. GET http://127.0.0.1:8040/v1/contract\n"
            "2. GET /v1/pickup /v1/fleet /v1/you /v1/coordinate /v1/plans "
            "/v1/prompts /v1/fetch /v1/sidecar /v1/insights /v1/openide /v1/pointer\n"
            "3. Claim a GitHub issue. Then CLAIMS.json. Control does not assign.\n\n"
            "Law: Cortex runs. Crew talks. OpenVault routes. Control displays. "
            "Pointer confirms. Constructor compiles to Cortex. OpenIDE is "
            "D:\\AirGPT\\OpenIDE. Ontology stays Cortex. P1 parked.\n"
            "Control POST /v1/run /v1/goal /v1/route /v1/secrets is 405.\n"
            "WIP two epics. Paste prd-agent first from GET /v1/prompts, then "
            "asset-guide. Then spawn at most 2 specialist pastes from GET /v1/prompts "
            "data.pastes. Do not spawn from Control (F-0030).\n"
            "Reuse analog segments: name TAS lane + live files. If stuck, DISTILL "
            "the analog widget/schema/PRD slice into original Netie code. Do not "
            "redesign UI tokens or layout DNA. Analog clones stay frozen.\n"
            "Do not start or kill :8020, Grok Bot.exe, Cursor, or founder desktop "
            "(R-0015). Hung converse is :8020. Engine Crew is :8023. YOU step 8 "
            "is founder rebind.\n\n"
            "BAN copy: D:\\mybot, D:\\myclaude-code, D:\\myn8n, D:\\OpenWillow "
            "(GPLv3), Guaca AGPL, Activepieces 665 pieces. Do not paste Anthropic "
            "prompt strings from D:\\myclaude-code-system-prompts.\n\n"
            "Live products (power internally):\n"
            "Crew D:\\Cortex\\CortexOS\\crew converse :8020 + sidecar :8023\n"
            "OpenVault D:\\OpenVault :5000\n"
            "Control D:\\NetieControl :8040\n"
            "Constructor D:\\Constructor canvas. Cortex compiles.\n"
            "Pointer D:\\Pointer confirm. UACC is the OS mouse.\n"
            "Cortex memory/assemble D:\\Cortex /api/memory /api/context\n"
            "OpenIDE D:\\AirGPT\\OpenIDE. SKIP second IDE.\n"
            "Cortex agent_task F20b SHIPPED. SKIP second agent product.\n"
            "Ontology stays Cortex Constructor. Do not unpark P1.\n\n"
            "Next after seating: one Crew writer on D:\\Cortex and one Control "
            "writer on D:\\NetieControl, or OpenVault playground DISTILL. "
            "Verify: python -m pytest D:\\NetieControl\\tests -q\n"
            "D:\\Cortex\\.venv\\Scripts\\python.exe -m pytest tests/test_crew "
            "tests/dms/test_memory_provider.py -q"
        ),
    },
    {
        "id": "prd-agent",
        "product": "PRD Agent",
        "wip": "coordinator",
        "paste": (
            "You are the Netie PRD Agent. Read D:\\Netie\\Internal\\Agents\\"
            "AGENT_SYSTEM.md section 1, D:\\Netie\\TAS\\README.md analog map, "
            "and GET http://127.0.0.1:8040/v1/plans.\n\n"
            "Portfolio (ship in the live path, not a second clone):\n"
            "OpenVault D:\\OpenVault keys+FreeRoute+OpenShip.\n"
            "Cortex D:\\Cortex engine+ledger+constructor compile+memory+assemble.\n"
            "DMS D:\\DMS. Space D:\\Space. AirGPT+OpenIDE D:\\AirGPT.\n"
            "Pointer D:\\Pointer confirm. Control D:\\NetieControl display.\n"
            "Crew D:\\Cortex\\CortexOS\\crew converse :8020 + sidecar :8023.\n"
            "Constructor canvas D:\\Constructor; Cortex is the only engine.\n"
            "Ontology stays Cortex. P1 parked. Objects+links+actions stay Constructor+Cortex.\n"
            "Read WP-003 and D:\\Netie\\Internal\\Workflow\\FUTURE_BUILD_ASSET_GUIDE.md. "
            "Extra feature = button/tab/route on the live app. Swap semantic_layer.yaml "
            "before a new ontology product.\n\n"
            "Before slicing: name TAS analog lane + live files that already own "
            "this surface. Prefer extend-live. If stuck, DISTILL one analog "
            "segment (UI widget, DB shape, PRD slice) into original Netie code "
            "in that live product. Analog clones stay frozen. Do not vendor them.\n"
            "Do not redesign the UI system, tokens, or layout DNA.\n"
            "BAN: D:\\myn8n, D:\\mybot, D:\\myclaude-code, D:\\OpenWillow GPLv3, "
            "Guaca AGPL, Activepieces 665 pieces. Do not paste Anthropic prompts.\n"
            "WIP two epics. Control does not spawn (F-0030). POST /v1/run stays 405."
        ),
    },
    {
        "id": "asset-guide",
        "product": "PRD Agent",
        "wip": "coordinator",
        "paste": (
            "Read D:\\Netie\\White Paper - Why\\WP-003-reuse-the-estate-do-not-rebuild.md "
            "and D:\\Netie\\Internal\\Workflow\\FUTURE_BUILD_ASSET_GUIDE.md.\n"
            "Live portfolio first: Cortex constructor_graph + packs/dms semantic_layer "
            "and ontology YAML (parity), Constructor app.js/engine.js, DMS OntologyPage "
            "tabs objects/map/metrics/actions/functions.\n"
            "New warehouse = swap semantic_layer + logo/copy, not a new ontology product.\n"
            "Extra feature = button, tab, or route on the live app. Analog D:\\my* is "
            "frozen study. DISTILL one widget if stuck. Do not vendor clones.\n"
            "Ontology stays Cortex. P1 parked. BAN n8n grok-bot Guaca AGPL OpenWillow GPL "
            "leaked Claude Code Activepieces 665. Control POST /v1/run stays 405."
        ),
    },
    {
        "id": "crew-long-horizon",
        "product": "Crew",
        "wip": "writer",
        "paste": (
            "Seat Control GET /v1/contract then /v1/sidecar. Write-target is "
            "D:\\Cortex\\CortexOS\\crew. Not D:\\Cortex-crew. Not a second engine.\n"
            "queue.py and wakes.py are wired. Do not rebuild them. Mailbox cursors "
            "and stall.py are on this tree. Do not rewrite unless a test is red.\n"
            "Live hung converse is :8020. Do not kill it (R-0015). Engine Crew "
            ":8023 already serves belt/wakes. start_crew.ps1 refuses a second bind.\n"
            "SKIP Mayor/beads/LangGraph/ee/Guaca AGPL/grok-bot copy. Analog clones "
            "stay frozen. Control never POSTs wakes. 405s stay on Control /v1/run.\n"
            "Verify from D:\\Cortex with PYTHONPATH=D:\\Cortex:\n"
            "python -m pytest tests/test_crew/test_wakes.py tests/test_crew/test_queue.py "
            "tests/test_crew/test_store.py tests/test_crew/test_server.py -q"
        ),
    },
    {
        "id": "openvault-omniroute",
        "product": "OpenVault",
        "wip": "writer",
        "paste": (
            "Seat Control GET /v1/contract. Live is D:\\OpenVault :5000. Analog "
            "D:\\Netie\\myOmniRoute is frozen. KEEP proxy/fallback/meters. "
            "LIFT thin /playground and register help. priced=false. No invented "
            "dollars (DR-0009). HT1-HT5 HUMAN_STOP. Do not invent a host URL.\n"
            "SKIP NVIDIA classifier, Cursor/Copilot executors, 250-provider clone.\n"
            "Control /v1/route stays 405. Keys stay in the vault.\n"
            "Verify: GET http://127.0.0.1:5000/api/healthz"
        ),
    },
    {
        "id": "control-desk",
        "product": "Control",
        "wip": "writer",
        "paste": (
            "Live tree D:\\NetieControl :8040. Read D:\\Netie\\TAS\\TAS-CONTROL.md.\n"
            "Display only. GET /v1/plans /v1/prompts /v1/fetch /v1/sidecar /v1/insights /v1/pointer stay GET. "
            "POST /v1/run /v1/goal /v1/route /v1/secrets is 405. Do not boot "
            "paperclip :3100. Do not copy Crew composer. Analog D:\\Netie\\mypaperclip "
            "is distill-only -- do not edit it.\n"
            "Talk live follows Crew GET /crew/wakes. Hung :8020 still serves HTML /. "
            "Sidecar :8023 is the engine host. crew-bind never green. Agents do not "
            "rebind :8020.\n"
            "Verify: python -m pytest D:\\NetieControl\\tests\\test_control_stays_plane_4.py -q"
        ),
    },
    {
        "id": "constructor-skin",
        "product": "Constructor",
        "wip": "writer",
        "paste": (
            "Read D:\\Netie\\TAS\\TAS-CONSTRUCTOR.md. Cortex is the only engine. "
            "Do not clone D:\\Cortex\\myactiveflow\\myactivepieces or D:\\myn8n. "
            "Ghost writes nothing. Distill piece taxonomy only if a Cortex action "
            "type is missing. Ontology stays Cortex. P1 parked. Objects+links+actions live "
            "on Constructor inspect + Cortex ontology.\n"
            "Verify Constructor compiler tests. Do not import @xyflow as the IR."
        ),
    },
    {
        "id": "pointer-hands",
        "product": "Pointer",
        "wip": "writer",
        "paste": (
            "Read D:\\Netie\\TAS\\TAS-POINTER.md. Live is D:\\Pointer. UACC is the "
            "only OS mouse. Playwright is DOM. Windows-MCP is a catalog, not the "
            "click driver. OpenWillow is GPLv3: distill dictation/hotkey ideas only. "
            "COPY none. Mutating clicks stay Confirm. Keys stay OpenVault. "
            "GET http://127.0.0.1:8040/v1/pointer lists confirm_gated from disk. "
            "Do not start or kill founder desktop apps (R-0015)."
        ),
    },
    {
        "id": "context-memory",
        "product": "Cortex memory",
        "wip": "writer",
        "paste": (
            "Write on D:\\Cortex. LIFT Graphiti temporal/provenance into "
            "/api/context/assemble. mem0 DISTILL add/update/retrieve+scope into "
            "/api/memory. MemPalace DISTILL wing/room/drawer as collection. "
            "SKIP myzep-go, Zep Cloud, mem0 SDK, Chroma, Letta product. Ledger stays SoT.\n"
            "Verify: D:\\Cortex\\.venv\\Scripts\\python.exe -m pytest "
            "tests/dms/test_memory_provider.py tests/test_api/test_memory_assemble.py -q"
        ),
    },
    {
        "id": "openide-search",
        "product": "AirGPT OpenIDE",
        "wip": "writer",
        "paste": (
            "OpenIDE is D:\\AirGPT\\OpenIDE, not a new repo. DISTILL Semble "
            "query-not-grep and OpenCode session/TUI ideas. SKIP second IDE product "
            "and embeddings product. Token rank, GitHub paste, S5 coalesce, and "
            "OpenAI/Cursor tool JSON are the bar.\n"
            "Verify: python -m pytest D:\\AirGPT\\OpenIDE\\tests\\test_stream_coalesce.py "
            "D:\\AirGPT\\OpenIDE\\tests\\test_s5_tool_loop.py -q"
        ),
    },
)


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
    """Live laptop engine is :8011. Override with NETIE_CORTEX_URL."""
    return os.environ.get("NETIE_CORTEX_URL", "http://127.0.0.1:8011").rstrip("/")


def openvault_base() -> str:
    return os.environ.get("NETIE_OPENVAULT_URL", "http://127.0.0.1:5000").rstrip("/")


def openvault_app_base() -> str:
    """Local Ship/Route UI. Control lists it. It does not start :3010."""
    return os.environ.get("NETIE_OPENVAULT_APP_URL", "http://127.0.0.1:3010").rstrip("/")


def crew_base() -> str:
    return os.environ.get("NETIE_CREW_URL", "http://127.0.0.1:8020").rstrip("/")


def crew_sidecar_base() -> str:
    """Engine-tree converse that can bind while hung :8020 stays untouched."""
    return os.environ.get("NETIE_CREW_SIDECAR_URL", "http://127.0.0.1:8023").rstrip("/")


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
            f"{base}/v1/plans",
            f"{base}/v1/prompts",
            f"{base}/v1/fetch",
            f"{base}/v1/sidecar",
            f"{base}/v1/openide",
            f"{base}/v1/insights",
            f"{base}/v1/pointer",
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
            "airgpt_wait_s": AIRGPT_WAIT_S,
            "cortex_wait_s": CORTEX_WAIT_S,
            "crew_belt_wait_s": CREW_BELT_WAIT_S,
            "openvault_usage_wait_s": OPENVAULT_USAGE_WAIT_S,
        },
        "rule": (
            "Every lane (Cursor, Claude Code, Grok Bot) reads Control before seating. "
            "Control does not assign and does not run. Claim on GitHub first (F-0025). "
            "F-0030: a scale request is not a third orchestrator."
        ),
    }


def kb_base() -> str:
    return os.environ.get("NETIE_KB_URL", "http://127.0.0.1:8030").rstrip("/")


def airgpt_base() -> str:
    return os.environ.get("NETIE_AIRGPT_URL", "http://127.0.0.1:8765").rstrip("/")


def slim_constructor_ontology(payload: dict[str, Any]) -> dict[str, Any]:
    """Counts only. Drops object/property maps so Control never holds warehouse rows."""
    objects = payload.get("objects")
    places = payload.get("fetch_places")
    actions = payload.get("actions")
    return {
        "object_count": len(objects) if isinstance(objects, dict) else 0,
        "action_count": len(actions) if isinstance(actions, list) else 0,
        "fetch_place_count": len(places) if isinstance(places, list) else 0,
        "p1": "parked",
    }


def cortex_view() -> Reading:
    """Read-only Cortex probes. Does not touch the ledger; one ledger, via Cortex HTTP.

    Unlock for P-CTL-1: GET /health + GET /api/engine/activity including
    activity.governance (ledger tip, bound session ids, refusals; no payloads).
    Health, activity, and features share one pool at CORTEX_WAIT_S so a hung
    /health cannot stack a second wait. Control does not GET constructor
    ontology: that 401 queues behind activity on a single uvicorn worker and
    reads as unread. Engine up + no Control key is gated. P1 stays
    parked.
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
    feat_data = features.data if features.ok and isinstance(features.data, dict) else {}
    extras = feat_data.get("extras") if isinstance(feat_data.get("extras"), dict) else {}
    health_data = health.data if isinstance(health.data, dict) else {}
    insights = {
        "pack": health_data.get("pack"),
        "agentic": extras.get("agentic") if extras else None,
        "constructor_view": "gated",
        "constructor_detail": "Control holds no viewer key. Ontology GET is not probed.",
        "ontology": None,
        "p1": "parked",
        "palantir_lite": constructor_seeds(),
        "constructor_seeds": constructor_seeds(),
        "ontology_owner": "Ontology stays Cortex Constructor. P1 parked.",
    }
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
            "constructor_live": constructor_live_url(),
            "insights": insights,
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


def slim_free_register(payload: dict[str, Any]) -> dict[str, Any]:
    """Register help only. No vault rows. priced stays false."""
    steps = payload.get("next_steps")
    if not isinstance(steps, list):
        steps = []
    slim_steps: list[dict[str, Any]] = []
    for row in steps[:8]:
        if isinstance(row, dict):
            slim_steps.append(
                {
                    "do": row.get("do") or row.get("step") or row.get("text"),
                    "href": row.get("href") or row.get("register_url") or row.get("url"),
                }
            )
        elif isinstance(row, str):
            slim_steps.append({"do": row, "href": None})
    ladder_in = payload.get("ladder")
    slim_ladder: list[dict[str, Any]] = []
    if isinstance(ladder_in, list):
        for row in ladder_in[:12]:
            if not isinstance(row, dict):
                continue
            slim_ladder.append(
                {
                    "id": row.get("id"),
                    "kind": row.get("kind"),
                }
            )
    return {
        "priced": False if payload.get("priced") is False else payload.get("priced"),
        "count": payload.get("count"),
        "help": payload.get("help") if isinstance(payload.get("help"), str) else None,
        "next_steps": slim_steps,
        "ladder": slim_ladder,
    }


def slim_ship(payload: dict[str, Any]) -> dict[str, Any]:
    """Publish/maintain liveness only. Drops repo lists, tokens, and adapter paths.

    Control probes GET /api/ship/targets (local cards + OpenShip adapter), not
    /api/ship/library (gh repo list, often slower than OPENVAULT_USAGE_WAIT_S).
    Library-shaped payloads still slim if a test or older probe sends one.
    """
    conn = payload.get("connection") if isinstance(payload.get("connection"), dict) else {}
    repos = payload.get("repos") if isinstance(payload.get("repos"), list) else []
    openship = payload.get("openship") if isinstance(payload.get("openship"), dict) else {}
    targets = payload.get("targets") if isinstance(payload.get("targets"), list) else []
    connected = conn.get("connected") if conn else None
    return {
        "connected": connected,
        "mode": conn.get("mode") or openship.get("effective"),
        "login": conn.get("login"),
        "repo_count": len(repos) if repos else None,
        "tabs": ["folder", "github", "url", "upload"],
        "target_count": len(targets) if targets else None,
        "openship_effective": openship.get("effective"),
        "human_test_gate": payload.get("human_test_gate"),
        "live_url_observed": payload.get("live_url_observed"),
        "publish_owner": "OpenVault OpenShip",
        "rule": "Control does not publish. POST /v1/run stays 405. Do not start :3010. HT1 stays human.",
    }


def openvault_view() -> Reading:
    """Display FreeRoute/vault liveness and spend counts. Does not choose a route.

    Healthz, usage, free-register help, ship targets, and :3010 playground
    run in parallel at OPENVAULT_USAGE_WAIT_S so a hung peer cannot stack
    waits on GET /. Control does not start :3010.
    """
    base = openvault_base()
    app_base = openvault_app_base()
    health_url = f"{base}/api/healthz"
    usage_url = f"{base}/api/usage?limit=1"
    free_url = f"{base}/api/providers/free"
    ship_url = f"{base}/api/ship/targets"
    play_url = f"{app_base}/"
    with ThreadPoolExecutor(max_workers=5) as pool:
        health_f = pool.submit(
            loopback_get_json, health_url, OPENVAULT_USAGE_WAIT_S
        )
        usage_f = pool.submit(
            loopback_get_json, usage_url, OPENVAULT_USAGE_WAIT_S
        )
        free_f = pool.submit(
            loopback_get_json, free_url, OPENVAULT_USAGE_WAIT_S
        )
        ship_f = pool.submit(
            loopback_get_json, ship_url, OPENVAULT_USAGE_WAIT_S
        )
        play_f = pool.submit(
            loopback_get_status, play_url, OPENVAULT_USAGE_WAIT_S
        )
        healthz = health_f.result()
        usage = usage_f.result()
        free = free_f.result()
        ship = ship_f.result()
        play = play_f.result()
    if not healthz.ok:
        return healthz
    status = (healthz.data or {}).get("status")
    usage_data = None
    usage_detail = ""
    if usage.ok and isinstance(usage.data, dict):
        usage_data = slim_openvault_usage(usage.data)
    else:
        usage_detail = usage.detail or "usage unread"
    register = None
    register_detail = ""
    if free.ok and isinstance(free.data, dict):
        register = slim_free_register(free.data)
    else:
        register_detail = free.detail or "register help unread"
    ship_data = None
    ship_detail = ""
    if ship.ok and isinstance(ship.data, dict):
        ship_data = slim_ship(ship.data)
    else:
        ship_detail = ship.detail or "ship unread"
    playground = {
        "up": play.ok,
        "href": play_url,
        "vault": f"{app_base}/vault",
        "playground": f"{app_base}/playground",
        "detail": "" if play.ok else (play.detail or "OpenVault app unread"),
        "rule": "Control does not start :3010. npm run dev in D:\\OpenVault\\apps\\web.",
    }
    return Reading(
        ok=True,
        data={
            "up": status == "ok",
            "healthz": healthz.data,
            "usage": usage_data,
            "usage_detail": usage_detail,
            "register": register,
            "register_detail": register_detail,
            "ship": ship_data,
            "ship_detail": ship_detail,
            "playground": playground,
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
    can 404. Probe fork and engine sidecar in one pool. Prefer :8020 when it
    answers. Named absence if none do. No POST handoff. Does not kill :8020.
    """
    base = crew_base()
    side = crew_sidecar_base()
    urls = [f"{base}/v1/belt", f"{base}/crew/belt"]
    if side != base:
        urls.extend([f"{side}/v1/belt", f"{side}/crew/belt"])
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="crew-belt") as pool:
        futs = [pool.submit(loopback_get_json, url, CREW_BELT_WAIT_S) for url in urls]
        readings = [fut.result() for fut in futs]
    for reading in readings:
        if reading.ok:
            return reading
    bits = [readings[0].detail or "unread"]
    for url, reading in zip(urls[1:], readings[1:], strict=True):
        bits.append(f"tried {url}: {reading.detail or 'unread'}")
    return Reading.unreachable(urls[0], "; ".join(bits))


def crew_talk_view() -> Reading:
    """Engine converse host. Does not copy Crew HTML (F-0026).

    The hung Cortex-crew fork still answers GET / in tens of ms and hangs
    `/crew/health`. `/crew/wakes` 404s on that fork and 200s on engine Crew
    :8023. Talk must not go green on HTML-only (R-0011). Sidecar fallback
    does not kill :8020 (R-0015).
    """
    base = crew_base()
    side = crew_sidecar_base()
    urls = [f"{base}/crew/wakes"]
    if side != base:
        urls.append(f"{side}/crew/wakes")
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="crew-talk") as pool:
        futs = [pool.submit(loopback_get_json, url, CREW_BELT_WAIT_S) for url in urls]
        readings = [fut.result() for fut in futs]
    for reading in readings:
        if reading.ok:
            return Reading(ok=True, data={"up": True, "wakes": True}, source=reading.source)
    why = readings[0].detail or "wakes unread"
    if len(readings) > 1:
        why = f"{why}; tried {urls[1]}: {readings[1].detail or 'unread'}"
    return Reading.unreachable(urls[0], why)


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
        "wake_tick_at": payload.get("wake_tick_at"),
    }


def constructor_live_url() -> str:
    """Cortex Constructor mount. Control serves the sketch; Cortex is the engine."""
    env = (os.environ.get("NETIE_CONSTRUCTOR_URL") or "").strip()
    if env:
        return env.rstrip("/") + "/"
    return f"{cortex_base()}/cortex/constructor/"


def constructor_root() -> Path:
    """Constructor sketch dir. Control serves files from here. Cortex compiles."""
    env = (os.environ.get("NETIE_CONSTRUCTOR_DIR") or "").strip()
    if env:
        return Path(env)
    for candidate in (Path(r"D:\Constructor"), Path(r"E:\Constructor")):
        if (candidate / "index.html").is_file():
            return candidate
    return Path(r"D:\Constructor")


def crew_health_view(timeout: float = CREW_BELT_WAIT_S) -> Reading:
    """Display Crew laptop-tool arming. Control does not arm, start, or kill MCPs.

    S-0001 step 3: GET /crew/health names which computer-control MCPs are armed.
    UACC is the OS mouse. Playwright is the Chrome DOM. Control never POSTs
    an arming route and never copies vault material from Crew's payload.
    Caps at CREW_BELT_WAIT_S so a hung fork cannot stall GET /. Talk liveness
    is crew_talk_view. Coordinate skips this probe. Sidecar :8023 is probed
    in the same pool. Does not kill :8020 (R-0015).
    """
    base = crew_base()
    side = crew_sidecar_base()
    urls = [f"{base}/crew/health"]
    if side != base:
        urls.append(f"{side}/crew/health")
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="crew-health") as pool:
        futs = [pool.submit(loopback_get_json, url, timeout) for url in urls]
        readings = [fut.result() for fut in futs]
    for reading in readings:
        if reading.ok and isinstance(reading.data, dict):
            return Reading(
                ok=True,
                data=slim_crew_health(reading.data),
                source=reading.source,
            )
    why = readings[0].detail or "unread"
    if len(readings) > 1:
        why = f"{why}; tried {urls[1]}: {readings[1].detail or 'unread'}"
    return Reading.unreachable(urls[0], why)


def crew_sidecar_view(timeout: float = CREW_BELT_WAIT_S) -> Reading:
    """Engine Crew on :8023. Does not start, stop, or rebind hung :8020.

    Health and wakes share one pool. Empty wakes is none, not unread. Control
    never POSTs /crew/wakes. The sidecar tick owns 24/7 fire.
    """
    base = crew_sidecar_base()
    health_url = f"{base}/crew/health"
    wakes_url = f"{base}/crew/wakes"
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="crew-sidecar") as pool:
        health_f = pool.submit(loopback_get_json, health_url, timeout)
        wakes_f = pool.submit(loopback_get_json, wakes_url, timeout)
        raw = health_f.result()
        wakes = wakes_f.result()
    if not raw.ok:
        return raw
    payload = raw.data if isinstance(raw.data, dict) else {}
    data = slim_crew_health(payload)
    data["converse"] = base
    data["fork"] = crew_base()
    rows = []
    if wakes.ok and isinstance(wakes.data, dict):
        raw_wakes = wakes.data.get("wakes")
        if isinstance(raw_wakes, list):
            rows = raw_wakes
        data["wakes_n"] = len(rows)
        data["wakes_view"] = "none" if not rows else "present"
        data["wakes_detail"] = ""
    else:
        data["wakes_n"] = None
        data["wakes_view"] = "unread"
        data["wakes_detail"] = wakes.detail or "wakes unread"
    data["rule"] = (
        "Sidecar is engine Crew. Hung converse stays :8020 until YOU step 8. "
        "Agents must not kill :8020 (R-0015). Control does not POST wakes."
    )
    return Reading(ok=True, data=data, source=raw.source)


def kb_view() -> Reading:
    """Liveness of the one skill registry. Counts only. No artifact bodies."""
    return loopback_get_json(f"{kb_base()}/healthz", timeout=KB_WAIT_S)


def slim_openide_ready(payload: dict[str, Any]) -> dict[str, Any]:
    """Flags only. Drop vault/token fields if a ready payload carries them."""
    missing = payload.get("missing")
    if not isinstance(missing, list):
        missing = []
    return {
        "ok": payload.get("ok"),
        "backend": payload.get("backend"),
        "need": payload.get("need") if isinstance(payload.get("need"), str) else None,
        "usable_count": payload.get("usable_count"),
        "missing": [str(x) for x in missing[:12]],
    }


def openide_view() -> Reading:
    """AirGPT OpenIDE liveness. Display only. Control does not run the IDE.

    Health and /api/openide/ready share one pool at AIRGPT_WAIT_S. Unreachable
    host is unread, not a quiet empty IDE. Does not start clipdrop (R-0015 for
    founder desktop still holds; this probe is GET only).
    """
    base = airgpt_base()
    health_url = f"{base}/api/health"
    ready_url = f"{base}/api/openide/ready"
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="openide") as pool:
        health_f = pool.submit(loopback_get_json, health_url, AIRGPT_WAIT_S)
        ready_f = pool.submit(loopback_get_json, ready_url, AIRGPT_WAIT_S)
        health = health_f.result()
        ready = ready_f.result()
    if not health.ok:
        return health
    payload = health.data if isinstance(health.data, dict) else {}
    up = payload.get("ok") is True or payload.get("service") == "airgpt"
    if not up:
        return Reading.unreachable(health_url, "AirGPT health did not report ok")
    ready_data = None
    ready_detail = ""
    if ready.ok and isinstance(ready.data, dict):
        ready_data = slim_openide_ready(ready.data)
    else:
        ready_detail = ready.detail or "ready unread"
    return Reading(
        ok=True,
        data={
            "up": True,
            "service": payload.get("service") or "airgpt",
            "href": f"{base}/OpenIDE/ui/",
            "host": base,
            "ready": ready_data,
            "ready_detail": ready_detail,
            "rule": (
                "OpenIDE is D:\\AirGPT\\OpenIDE. Control lists it. "
                "It does not run the IDE. POST /v1/run stays 405."
            ),
            "leftover": "OpenIDE leftover TUI. SKIP second IDE.",
        },
        source=health_url,
    )


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
        "title": "dms#61 hold is lifted",
        "do": "Named hold dms#61 is LIFTED (E11 on main 2026-08-24). "
             "MERGEABLE is still not permission for any other hold.",
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
        "do": "Live converse is still the hung fork on :8020. Belt may 404. "
             "Stop that hung process yourself, then start "
             "python -m CortexOS.crew from D:\\Cortex (scripts\\start_crew.ps1). "
             "Night keep-alive is D:\\Cortex\\scripts\\night_watch.ps1 for sidecar :8023. "
             "Agents must not start or kill :8020 (R-0015). Control stays display-only.",
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


_PARK_HEAD = re.compile(
    r"^## (P(?:-CTL)?-?\d+[a-z]?)\s*[—–-]\s*(.+)$",
    re.MULTILINE,
)


def prompt_catalog() -> Reading:
    """Where prompts live. Display only. Control does not rewrite a charter."""
    rows: list[dict[str, Any]] = []
    for surf in PROMPT_SURFACES:
        path = Path(surf["path"])
        files: list[str] = []
        if surf["id"] == "crew-skills" and path.is_dir():
            files = sorted(p.name for p in path.glob("*.md"))[:40]
        rows.append(
            {
                "kind": "prompt",
                "id": surf["id"],
                "path": surf["path"],
                "product": surf["product"],
                "verdict": surf["verdict"],
                "note": surf["note"],
                "tree": "present" if path.exists() else "absent",
                "files": files,
            }
        )
    distill = [row for row in rows if row["verdict"] == "DISTILL"]
    banned = [row for row in rows if row["verdict"] == "BAN"]
    pastes = [
        {
            "kind": "paste",
            "id": item["id"],
            "product": item["product"],
            "wip": item["wip"],
            "paste": item["paste"],
        }
        for item in GROK_LANE_PASTES
    ]
    return Reading(
        ok=True,
        data={
            "items": rows,
            "count": len(rows),
            "open": len(distill),
            "distill": distill,
            "banned": banned,
            "pastes": pastes,
            "wip_cap": 2,
            "spawn_owner": "Crew chat. Control does not spawn (F-0030).",
            "rule": (
                "Prompts is display. Paste grok-master, then prd-agent, then at most "
                "2 writer pastes. Reuse analog segments in the live product. "
                "Do not redesign UI tokens/layout. Improve Crew charters and "
                "skill_packs in Cortex. Do not paste Anthropic text. Control does "
                "not edit prompts. POST /v1/run stays 405."
            ),
        },
        source="TAS prompt surfaces",
        detail=f"{len(distill)} DISTILL, {len(banned)} BAN, {len(pastes)} pastes",
    )


def constructor_seeds() -> dict[str, str]:
    """Constructor rail seeds: define data, govern agents, insights. No HTTP."""
    return {
        "p1": "parked",
        "define_data": (
            "POST /cortex/constructor/generate prompt define data -> ontology+insight"
        ),
        "govern_agents": (
            "generate govern agents -> action=agent.checked "
            "kinds connector,ontology,agent,audit"
        ),
        "business_insights": (
            "generate business insights -> Constructor compile + insight"
        ),
        "engine": "Cortex Constructor. Control does not POST generate.",
        "dms_canvas": (
            "DMS Ontology header Constructor canvas -> "
            "http://127.0.0.1:8040/constructor/"
        ),
        "guide": r"D:\Netie\Internal\Workflow\FUTURE_BUILD_ASSET_GUIDE.md",
    }


def palantir_lite() -> dict[str, str]:
    """Alias for constructor_seeds. Live name is Constructor seeds."""
    return constructor_seeds()


def heartbeat_labels() -> list[dict[str, str]]:
    """Name live probes. No extra HTTP. Control does not start peers."""
    return [
        {"product": "Cortex", "href": f"{cortex_base()}/health", "role": "engine"},
        {"product": "Control", "href": "/healthz", "role": "hub"},
        {
            "product": "Crew converse",
            "href": f"{crew_base()}/crew/health",
            "role": "founder rebind",
        },
        {
            "product": "Crew sidecar",
            "href": f"{crew_sidecar_base()}/crew/health",
            "role": "tick",
        },
        {
            "product": "OpenVault",
            "href": f"{openvault_base()}/api/healthz",
            "role": "keys",
        },
        {
            "product": "Constructor",
            "href": constructor_live_url(),
            "role": "canvas",
        },
        {"product": "Pointer", "href": "/v1/pointer", "role": "confirm gated"},
    ]


def analog_work_next(
    analog: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """First leftover DISTILL lift. PARK/BAN are not next. Control does not seat."""
    rows = analog if analog is not None else analog_catalog()
    distill = [r for r in rows if isinstance(r, dict) and r.get("verdict") == "DISTILL"]
    present = [r for r in distill if r.get("tree") == "present"]
    pick = (present or distill or [None])[0]
    if not isinstance(pick, dict):
        return None
    return {
        "kind": "analog",
        "lane": pick.get("lane"),
        "path": pick.get("path"),
        "product": pick.get("product"),
        "verdict": "DISTILL",
        "note": pick.get("note"),
        "tree": pick.get("tree"),
        "name": pick.get("name") or pick.get("product"),
        "surface": pick.get("surface") or "part",
        "home": pick.get("home"),
        "href": "/v1/plans",
        "rule": (
            "Control displays leftover DISTILL. Ticket Runner seats GitHub. "
            "Analog clones stay frozen. Ontology stays Cortex. P1 parked."
        ),
    }


def _peer_stamp(
    *,
    product: str,
    href: str,
    role: str,
    reading: Reading,
    up_key: str = "up",
) -> dict[str, Any]:
    """Unread is not green. Control does not start the peer."""
    row: dict[str, Any] = {
        "product": product,
        "href": href,
        "role": role,
        "up": False,
        "state": "unread",
        "detail": reading.detail or "unread",
    }
    if not reading.ok:
        return row
    data = reading.data if isinstance(reading.data, dict) else {}
    live = bool(data[up_key]) if up_key in data else True
    row["up"] = live
    row["state"] = "live" if live else "down"
    row["detail"] = str(data.get("detail") or "")
    if "confirm_gated" in data:
        row["confirm_gated"] = bool(data["confirm_gated"])
    return row


def working_tray() -> list[dict[str, Any]]:
    """Laptop fetch peers. Display only. Does not start OpenIDE, Pointer, or :3010."""
    sketch = constructor_root() / "index.html"
    with ThreadPoolExecutor(max_workers=5, thread_name_prefix="fetch-work") as pool:
        cx = pool.submit(cortex_view)
        sc = pool.submit(crew_sidecar_view)
        ov = pool.submit(openvault_view)
        ide = pool.submit(openide_view)
        ptr = pool.submit(pointer_view)
        cortex = cx.result()
        sidecar = sc.result()
        vault = ov.result()
        openide = ide.result()
        pointer = ptr.result()
    ov_data = vault.data if vault.ok and isinstance(vault.data, dict) else {}
    register = ov_data.get("register") if isinstance(ov_data.get("register"), dict) else {}
    ov_row = _peer_stamp(
        product="OpenVault free",
        href=f"{openvault_base()}/api/providers/free",
        role="priced=false",
        reading=vault,
    )
    if register:
        ov_row["priced"] = register.get("priced")
        if ov_row["state"] == "live":
            ov_row["detail"] = f"priced={register.get('priced')}"
    ctor_up = sketch.is_file()
    sidecar_row = _peer_stamp(
        product="Crew sidecar",
        href=crew_sidecar_base(),
        role="tick",
        reading=sidecar,
    )
    if sidecar.ok and isinstance(sidecar.data, dict):
        sidecar_row["wakes_n"] = sidecar.data.get("wakes_n")
        sidecar_row["wakes_view"] = sidecar.data.get("wakes_view")
        sidecar_row["detail"] = (
            f"wakes {sidecar.data.get('wakes_view') or 'unread'} "
            f"n={sidecar.data.get('wakes_n')}"
        )
    return [
        _peer_stamp(
            product="Cortex",
            href=f"{cortex_base()}/health",
            role="engine",
            reading=cortex,
        ),
        {
            "product": "Constructor",
            "href": "http://127.0.0.1:8040/constructor/",
            "role": "canvas",
            "up": ctor_up,
            "state": "live" if ctor_up else "unread",
            "detail": (
                f"sketch. Cortex compiles {constructor_live_url()}"
                if ctor_up
                else "Constructor skin unread"
            ),
        },
        sidecar_row,
        ov_row,
        _peer_stamp(
            product="OpenIDE",
            href=f"{airgpt_base()}/OpenIDE/ui/",
            role="live",
            reading=openide,
        ),
        _peer_stamp(
            product="Pointer",
            href="/v1/pointer",
            role="confirm_gated",
            reading=pointer,
        ),
    ]


def analog_catalog() -> list[dict[str, Any]]:
    """Every analog tree TAS names, plus whether it is on this disk."""
    rows: list[dict[str, Any]] = []
    for lane in ANALOG_LANES:
        path = Path(lane["path"])
        rows.append(
            {
                "kind": "analog",
                "lane": lane["lane"],
                "path": lane["path"],
                "product": lane["product"],
                "name": lane.get("name") or lane["product"],
                "surface": lane.get("surface") or "part",
                "home": lane.get("home") or "",
                "verdict": lane["verdict"],
                "note": lane["note"],
                "tree": "present" if path.exists() else "absent",
            }
        )
    return rows


def _parking_open(path: Path, product: str) -> tuple[list[dict[str, Any]], str]:
    """Parked headings that still have remaining work. Missing file is unread."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], "absent"
    except OSError as exc:
        return [], f"unreadable: {exc}"
    items: list[dict[str, Any]] = []
    parts = re.split(r"(?m)^(?=## P)", text)
    for part in parts:
        match = _PARK_HEAD.match(part)
        if not match:
            continue
        pid, title = match.group(1), match.group(2).strip()
        body = part.lower()
        remaining = any(
            token in body
            for token in ("still parked", "still open", "remaining:", "**remaining**")
        )
        condition = "condition:" in body
        shipped = "shipped" in body
        if shipped and not remaining and not condition:
            continue
        items.append(
            {
                "kind": "parking",
                "id": pid,
                "title": title[:160],
                "product": product,
                "state": "parked" if (remaining or condition) else "open",
                "source": str(path),
            }
        )
    return items[:40], "ok"


def incomplete_plans() -> Reading:
    """Unfinished analog lifts + parked lots across repos. Display only. No HTTP.

    Pickup is GitHub/CLAIMS seats. This tray is TAS analog remaining plus
    PARKING_LOT headings that still have a condition or remaining work.
    Control does not unpark P1 and does not clone analog workflow engines.
    """
    analog = analog_catalog()
    cortex_lot = _cortex_root() / "PARKING_LOT.md"
    control_lot = CONTROL_ROOT / "PARKING_LOT.md"
    parking: list[dict[str, Any]] = []
    unread: list[str] = []
    for path, product in ((cortex_lot, "Cortex"), (control_lot, "Control")):
        rows, status = _parking_open(path, product)
        if status != "ok":
            unread.append(f"{path}: {status}")
            continue
        parking.extend(rows)
    open_analog = [
        row
        for row in analog
        if row["verdict"] in {"DISTILL", "PARK"} or row["tree"] == "absent"
    ]
    items: list[dict[str, Any]] = []
    items.extend(open_analog)
    items.extend(parking)
    open_n = len(items)
    analog_absent = sum(1 for row in analog if row["tree"] == "absent")
    analog_present = sum(1 for row in analog if row["tree"] == "present")
    detail_bits: list[str] = []
    if analog_absent:
        detail_bits.append(f"{analog_absent} analog trees absent")
    if unread:
        detail_bits.append("parking unread: " + "; ".join(unread))
    if open_n == 0:
        detail_bits.append("none")
    return Reading(
        ok=True,
        data={
            "items": items[:80],
            "count": min(open_n, 80),
            "open": min(open_n, 80),
            "none": open_n == 0,
            "analog": analog,
            "analog_present": analog_present,
            "analog_absent": analog_absent,
            "heartbeat": heartbeat_labels(),
            "parking": parking,
            "parking_unread": unread,
            "rule": (
                "Plans is display. Analog clones stay frozen. Control does not "
                "unpark P1, does not copy analog reconstructions/AGPL/GPL/leaked "
                "trees, and does not clone analog workflow engines. Claim on "
                "GitHub. POST /v1/run stays 405."
            ),
        },
        source="TAS analog + PARKING_LOT",
        detail="; ".join(detail_bits),
    )


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
    ("Pointer.exe", "Pointer"),
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


def pointer_root() -> Path:
    env = os.environ.get("POINTER_ROOT", "").strip()
    if env:
        return Path(env)
    for candidate in (Path(r"D:\Pointer"), Path(r"E:\Pointer")):
        if (candidate / "electron" / "netie" / "plan-guard.js").is_file():
            return candidate
    return Path(r"D:\Pointer")


def pointer_view() -> Reading:
    """Pointer confirm-gate from disk + process present/absent. Does not start Electron."""
    root = pointer_root()
    guard = root / "electron" / "netie" / "plan-guard.js"
    if not guard.is_file():
        return Reading.unreachable(str(guard), "Pointer plan-guard unread")
    try:
        text = guard.read_text(encoding="utf-8")
    except OSError as exc:
        return Reading.unreachable(str(guard), f"unreachable: {exc}")
    confirm_gated = "_requireConfirm: true" in text
    modes = root / "docs" / "MODES.md"
    nod_confirm = False
    if modes.is_file():
        try:
            nod_confirm = "Nod confirm" in modes.read_text(encoding="utf-8")
        except OSError:
            nod_confirm = False
    live = False
    live_detail = ""
    try:
        live = bool(_win_running_images({"pointer.exe", "netie-pointer.exe"}))
    except OSError as exc:
        live_detail = f"process unread: {exc}"
    detail = ""
    if not confirm_gated:
        detail = "plan-guard.js missing _requireConfirm"
    elif live_detail:
        detail = live_detail
    return Reading(
        ok=True,
        data={
            "up": live,
            "confirm_gated": confirm_gated,
            "nod_confirm": nod_confirm,
            "tree": str(root),
            "rule": (
                "Pointer is HUD + Cortex POST /dms/secure. UACC is the only OS mouse. "
                "Control does not start Pointer (R-0015). POST /v1/run stays 405."
            ),
            "detail": detail,
        },
        source=str(guard),
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
) -> list[dict[str, Any]]:
    """Named workers the operator can actually invoke. Control does not spawn them."""
    crew = crew_base()
    mates: list[dict[str, Any]] = []
    for label, tid, href in (
        ("Cursor", "cursor", "#pc"),
        ("Claude Code", "claude", "#pads"),
        ("Grok Bot", "grok", crew),
        ("Pointer", "pointer", "#pointer"),
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
) -> dict[str, Any]:
    """Grok-class job -> owner invoke map. Display only. Control does not invoke."""
    fleet = fleet or {}
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
