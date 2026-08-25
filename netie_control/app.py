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

from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from netie_control import sources
from netie_control.render import render_page

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


@router.get("/v1/state")
def state() -> dict[str, Any]:
    """Everything the first page shows, as data. Unreachable sources say so."""
    gate = sources.estate_gate()
    return {
        "gate": gate.to_dict(),
        "runtime": sources.runtime_view().to_dict(),
        "claims": sources.claims_board().to_dict(),
        "board": sources.board().to_dict(),
        "launchers": [
            {"name": launcher.name, "blurb": launcher.blurb, "cwd": launcher.cwd}
            for launcher in sources.LAUNCHERS
        ],
    }


@router.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(render_page(state()))


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
