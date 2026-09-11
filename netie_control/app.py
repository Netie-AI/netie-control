"""Netie Control - the operator shell. Plane 4.

What this is, per NETIE.md section 3: the estate shell operators use. First page is
Cortex internals; second ring is route and budget status, the repo/epic/ticket board,
and local CLI launchers.

What it is NOT, and the reason those refusals are routes rather than omissions: an
engine, a key vault, a route picker, or a third orchestrator. It holds no keys and owns
no route decision.

A capability that is merely absent gets added back by the next person who needs it and
does not know why it was left out. So the three forbidden ones answer **405 with the
reason and the owner**, and a test asserts each. That turns "we decided not to" into
something the codebase enforces.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

from netie_control import sources
from netie_control.render import render_page

CONSTRUCTOR_SKIN_NAMES = frozenset({"index.html", "app.js", "styles.css", "engine.js", "README.md"})

_CONSTRUCTOR_UNREAD_HTML = (
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    "<title>Constructor unread</title>"
    "<style>.absent{color:#c99a6a;font-style:italic}</style></head><body>"
    '<p class="absent">Constructor skin unread. This shell launches the sketch. '
    "Live run stays Cortex "
    '<a href="{live}">{live}</a>. '
    "Control is not the engine. POST /v1/run stays 405.</p>"
    "</body></html>"
)


def constructor_skin_dir() -> Path:
    return sources.constructor_root()


def _constructor_unread() -> HTMLResponse:
    """Missing skin is a stated absence, not FastAPI JSON that looks like a crash."""
    live = sources.constructor_live_url()
    html = _CONSTRUCTOR_UNREAD_HTML.replace("{live}", live)
    return HTMLResponse(html, status_code=503)


def _constructor_file(name: str) -> Path | None:
    if name not in CONSTRUCTOR_SKIN_NAMES:
        raise HTTPException(status_code=404, detail="not found")
    path = constructor_skin_dir() / name
    if not path.is_file():
        return None
    return path

router = APIRouter()

#: Each entry is a capability the constitution assigns to another plane, the owner it
#: belongs to, and the clause. Answering 405 rather than 404 is deliberate: 404 says
#: "no such thing", which invites someone to build it. 405 says "this exists as a
#: decision, and the decision was no".
FORBIDDEN: dict[str, dict[str, str]] = {
    "/v1/secrets": {
        "owner": "OpenVault",
        "why": "Control holds no keys. There is exactly one key vault in this company "
               "(NETIE.md section 3). A local secret store here would be the second one.",
    },
    "/v1/route": {
        "owner": "OpenVault FreeRoute",
        "why": "Control owns no route decision. It may display which route was chosen "
               "and what it cost; choosing is plane 2.",
    },
    "/v1/goal": {
        "owner": "Cortex",
        "why": "Goal alignment decides the shape of work, which is plane 3. A second "
               "place that decides work shape is a third orchestrator (NETIE.md section 6).",
    },
    "/v1/run": {
        "owner": "Cortex",
        "why": "No write reaches a customer system except through a Cortex action type. "
               "Control may launch a LOCAL CLI lane; it may not execute against a customer.",
    },
}


def _forbidden_response(path: str) -> JSONResponse:
    spec = FORBIDDEN[path]
    return JSONResponse(
        status_code=405,
        content={
            "code": "not_this_plane",
            "message": spec["why"],
            "owner": spec["owner"],
            "path": path,
        },
    )


@router.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"status": "ok", "product": "netie-control", "plane": 4}


@router.get("/favicon.ico")
def favicon() -> Response:
    """Browsers probe this. 204 is a stated empty, not a 404 that looks like a missing app."""
    return Response(status_code=204)


def _reading(fn: Any) -> dict[str, Any]:
    return fn().to_dict()


def state(*, include_gate: bool = True, include_board: bool = True, include_pads: bool = True, include_stage: bool = True) -> dict[str, Any]:
    """Desk payload. Gate, gh board, Claude pads, and backstage are optional so GET / can paint first.

    Talk, health, and belt share the pool so a hung /crew/health cannot stack
    a second wait after /crew/wakes.
    """
    jobs = {
        "crew_talk": sources.crew_talk_view,
        "cortex": sources.cortex_view,
        "openvault": sources.openvault_view,
        "spaceship": sources.spaceship_host_view,
        "crew": sources.crew_belt_view,
        "crew_health": sources.crew_health_view,
        "kb": sources.kb_view,
        "runtime": sources.runtime_view,
        "fleet": sources.fleet_view,
        "you": sources.you_desk,
        "surfaces": sources.desktop_surfaces_view,
        "claims": sources.claims_board,
        "plans": sources.incomplete_plans,
        "prompts": sources.prompt_catalog,
        "crew_sidecar": sources.crew_sidecar_view,
        "openide": sources.openide_view,
        "pointer": sources.pointer_view,
    }
    if include_board:
        jobs["board"] = sources.board
    if include_gate:
        jobs["gate"] = sources.estate_gate
    if include_pads:
        jobs["claude_pads"] = sources.claude_pads_view
    if include_stage:
        jobs["stage"] = sources.stage_backends_view
    out: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=max(len(jobs), 1)) as pool:
        futs = {key: pool.submit(_reading, fn) for key, fn in jobs.items()}
        for key, fut in futs.items():
            out[key] = fut.result()
    if not include_gate:
        out["gate"] = sources.Reading.unreachable(
            "GET /v1/gate",
            "deferred so the desk paints first",
        ).to_dict()
    if not include_board:
        out["board"] = sources.Reading.unreachable(
            "GET /v1/board",
            "deferred so the desk paints first",
        ).to_dict()
    if not include_pads:
        out["claude_pads"] = sources.Reading.unreachable(
            "GET /v1/pads",
            "deferred so the desk paints first",
        ).to_dict()
    if not include_stage:
        out["stage"] = sources.Reading.unreachable(
            "GET /v1/stage",
            "deferred so the desk paints first",
        ).to_dict()
    out["pickup"] = sources.pickup_from_readings(out["fleet"], out["board"]).to_dict()
    out["crew_converse"] = sources.crew_base()
    out["contract"] = sources.agent_contract()
    out["coordinate"] = sources.coordinate_from_readings(out).to_dict()
    out["launchers"] = [
        {"name": launcher.name, "blurb": launcher.blurb, "cwd": launcher.cwd}
        for launcher in sources.LAUNCHERS
    ]
    return out


@router.get("/v1/state")
def v1_state() -> dict[str, Any]:
    """Desk JSON without the estate gate or gh board. Those are GET /v1/gate and GET /v1/board."""
    blob = state(include_gate=False, include_board=False, include_pads=False, include_stage=False)
    blob["display_only"] = True
    return blob


@router.get("/v1/gate")
def v1_gate() -> dict[str, Any]:
    """Live estate gate. Display only. Slow on purpose; the desk does not wait."""
    reading = sources.estate_gate()
    return {
        "ok": reading.ok,
        "display_only": True,
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/board")
def v1_board() -> dict[str, Any]:
    """Open GitHub issues for the owner, regex-filtered. Display only. Hung gh is named unread."""
    reading = sources.board()
    return {
        "ok": reading.ok,
        "display_only": True,
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/belt")
def v1_belt() -> dict[str, Any]:
    """Proxy Crew GET /v1/belt. Display only. Control does not hand off."""
    reading = sources.crew_belt_view()
    return {
        "ok": reading.ok,
        "display_only": True,
        "converse_owner": "Netie Crew",
        "converse_url": sources.crew_base(),
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/fleet")
def v1_fleet() -> dict[str, Any]:
    """CLAIMS seats plus lane guess. Display only. Control does not seat."""
    reading = sources.fleet_view()
    return {
        "ok": reading.ok,
        "display_only": True,
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/pads")
def v1_pads() -> dict[str, Any]:
    """Live Claude pads on this PC. Display only. Does not start Claude (R-0015)."""
    reading = sources.claude_pads_view()
    return {
        "ok": reading.ok,
        "display_only": True,
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/stage")
def v1_stage() -> dict[str, Any]:
    """Backstage listeners and console-popup owners. Display only. Does not start or kill (R-0015)."""
    reading = sources.stage_backends_view()
    return {
        "ok": reading.ok,
        "display_only": True,
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/constructor", include_in_schema=False)
def constructor_redirect() -> RedirectResponse:
    return RedirectResponse(url="/constructor/", status_code=307)


@router.get("/constructor/", response_model=None)
def constructor_index() -> FileResponse | HTMLResponse:
    """Launch Constructor sketch. Chat compiles locally. Live run stays Cortex."""
    path = _constructor_file("index.html")
    if path is None:
        return _constructor_unread()
    return FileResponse(path)


@router.get("/constructor/{name}", response_model=None)
def constructor_asset(name: str) -> FileResponse | HTMLResponse:
    path = _constructor_file(name)
    if path is None:
        return _constructor_unread()
    return FileResponse(path)


@router.get("/v1/pickup")
def v1_pickup() -> dict[str, Any]:
    """CLAIMS unseated tray. Board only if gh is quick. Display only. Does not assign."""
    reading = sources.pickup_view()
    return {
        "ok": bool(reading.ok),
        "display_only": True,
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "run_owner": "Cortex",
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/fetch")
def v1_fetch() -> dict[str, Any]:
    """Laptop task fetch. GitHub next + analog leftover. Control does not seat or run."""
    reading = sources.pickup_view()
    plans = sources.incomplete_plans()
    data = dict(reading.data) if isinstance(reading.data, dict) else {}
    items = data.get("items") if isinstance(data.get("items"), list) else []
    nxt = items[0] if items and isinstance(items[0], dict) else None
    pdata = plans.data if isinstance(plans.data, dict) else {}
    analog = pdata.get("analog") if isinstance(pdata.get("analog"), list) else []
    data["next"] = nxt
    data["analog_next"] = sources.analog_work_next(analog)
    data["analog_open"] = sum(
        1 for row in analog if isinstance(row, dict) and row.get("verdict") == "DISTILL"
    )
    data["heartbeat"] = pdata.get("heartbeat") or sources.heartbeat_labels()
    data["p1"] = "parked"
    data["constructor_canvas"] = "http://127.0.0.1:8040/constructor/"
    data["dms_canvas"] = sources.constructor_seeds()["dms_canvas"]
    data["working"] = sources.working_tray()
    data["grok"] = "offloaded. COPY none of D:\\mybot."
    data["converse_founder"] = sources.crew_base()
    data["seat_owner"] = "Ticket Runner. Control does not seat."
    return {
        "ok": bool(reading.ok),
        "display_only": True,
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "run_owner": "Cortex",
        "source": reading.source,
        "detail": reading.detail,
        "data": data,
        "fetch_owner": "Ticket Runner + Crew. Control POST /v1/run stays 405.",
    }


@router.get("/v1/sidecar")
def v1_sidecar() -> dict[str, Any]:
    """Engine Crew :8023 health. Display only. Does not touch hung :8020."""
    reading = sources.crew_sidecar_view()
    return {
        "ok": reading.ok,
        "display_only": True,
        "run_owner": "Cortex",
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/you")
def v1_you() -> dict[str, Any]:
    """Numbered human steps. Display only. Control does not execute them."""
    reading = sources.you_desk()
    return {
        "ok": reading.ok,
        "display_only": True,
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/plans")
def v1_plans() -> dict[str, Any]:
    """Analog remaining + parked lots. Display only. Control does not unpark or copy."""
    reading = sources.incomplete_plans()
    return {
        "ok": reading.ok,
        "display_only": True,
        "run_owner": "Cortex",
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/openide")
def v1_openide() -> dict[str, Any]:
    """AirGPT OpenIDE liveness. Display only. Control does not run the IDE."""
    reading = sources.openide_view()
    return {
        "ok": reading.ok,
        "display_only": True,
        "run_owner": "Cortex",
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/pointer")
def v1_pointer() -> dict[str, Any]:
    """Pointer confirm-gate and process present/absent. Display only. Does not start Electron."""
    reading = sources.pointer_view()
    return {
        "ok": reading.ok,
        "display_only": True,
        "run_owner": "Cortex",
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/insights")
def v1_insights() -> dict[str, Any]:
    """Cortex pack/constructor ontology detection. Display only. Does not unpark P1."""
    reading = sources.cortex_view()
    blob = reading.data if isinstance(reading.data, dict) else {}
    insights = dict(blob.get("insights") or {}) if isinstance(blob.get("insights"), dict) else {}
    seeds = sources.constructor_seeds()
    insights["constructor_seeds"] = seeds
    insights["palantir_lite"] = seeds
    insights["p1"] = insights.get("p1") or "parked"
    return {
        "ok": reading.ok,
        "display_only": True,
        "run_owner": "Cortex",
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "source": reading.source,
        "detail": reading.detail,
        "data": {
            "insights": insights,
            "constructor_live": blob.get("constructor_live") or sources.constructor_live_url(),
            "ontology_owner": insights.get("ontology_owner")
            or "Ontology stays Cortex Constructor. P1 parked.",
            "rule": "Control displays. Cortex governs. POST /v1/run stays 405.",
        },
    }


@router.get("/v1/prompts")
def v1_prompts() -> dict[str, Any]:
    """Crew/Cortex prompt surfaces and Grok paste briefs. Display only. Does not spawn."""
    reading = sources.prompt_catalog()
    return {
        "ok": reading.ok,
        "display_only": True,
        "run_owner": "Cortex",
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/contract")
def v1_contract() -> dict[str, Any]:
    """Seating protocol for every lane. Display only. Control does not assign."""
    return sources.agent_contract()


@router.get("/v1/skills")
def v1_skills(q: str = Query("", max_length=120), limit: int = Query(8, ge=1, le=20)) -> dict[str, Any]:
    """Proxy Netie-KB search. Display only. Control does not run a skill."""
    if not (q or "").strip():
        return {
            "ok": False,
            "display_only": True,
            "owner": "Netie-KB",
            "source": sources.kb_base() + "/search",
            "detail": "empty query",
            "data": {},
        }
    reading = sources.kb_search(q, limit=limit)
    return {
        "ok": reading.ok,
        "display_only": True,
        "owner": "Netie-KB",
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/skill/{sid}")
def v1_skill(sid: str) -> dict[str, Any]:
    """One registry artifact, truncated. Display only. Control does not run it."""
    reading = sources.kb_show(sid)
    return {
        "ok": reading.ok,
        "display_only": True,
        "owner": "Netie-KB",
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/v1/coordinate")
def v1_coordinate() -> dict[str, Any]:
    """Grok-class invoke map. Display only. Control does not invoke or spawn."""
    reading = sources.coordinate_view()
    return {
        "ok": reading.ok,
        "display_only": True,
        "run_owner": "Cortex",
        "assign_owner": "GitHub Issues + CLAIMS.json",
        "source": reading.source,
        "detail": reading.detail,
        "data": reading.data,
    }


@router.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(render_page(state(include_gate=False, include_board=False, include_pads=False, include_stage=False)))


def create_app() -> FastAPI:
    app = FastAPI(
        title="Netie Control",
        description="Operator shell. Displays and launches. Holds no keys, decides no route.",
        version="0.1.0",
    )
    app.include_router(router)

    for path in FORBIDDEN:
        def _make(p: str):
            def _handler() -> JSONResponse:
                return _forbidden_response(p)
            return _handler

        # Registered for every verb so the refusal is the answer regardless of how it
        # is reached. A GET that 404s while a POST 405s reads as an oversight.
        app.add_api_route(
            path, _make(path),
            methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            include_in_schema=True,
        )

    return app


app = create_app()
