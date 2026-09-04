"""The constitution, as tests.

NETIE.md section 3 says Netie Control is not an engine, a key vault, a route picker, or
a third orchestrator. Written down, that is a sentence somebody can disagree with in six
months. Written as a test, it is a thing that goes red.

A capability that is merely ABSENT gets added back by the next person who needs it and
does not know why it was left out. So each forbidden capability is a route that answers
405 with its owner named, and each has an assertion here.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from netie_control.app import FORBIDDEN, create_app
from netie_control.sources import (
    CREW_BELT_WAIT_S,
    Reading,
    loopback_get_json,
    loopback_get_status,
    spaceship_host_view,
)
from netie_control.sources import (
    board as _REAL_BOARD,
)
from netie_control.sources import (
    claude_pads_view as _REAL_CLAUDE_PADS,
)
from netie_control.sources import (
    cortex_view as _REAL_CORTEX,
)
from netie_control.sources import (
    crew_belt_view as _REAL_CREW_BELT,
)
from netie_control.sources import (
    crew_health_view as _REAL_CREW_HEALTH,
)
from netie_control.sources import (
    crew_talk_view as _REAL_CREW_TALK,
)
from netie_control.sources import (
    desktop_surfaces_view as _REAL_DESKTOP_SURFACES,
)
from netie_control.sources import (
    kb_search as _REAL_KB_SEARCH,
)
from netie_control.sources import (
    kb_show as _REAL_KB_SHOW,
)
from netie_control.sources import (
    kb_view as _REAL_KB_VIEW,
)
from netie_control.sources import (
    openvault_view as _REAL_OPENVAULT,
)


@pytest.fixture(autouse=True)
def _quiet_peer_probes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: no live peers and no live estate gate. A real gate run stalled the suite ~76s."""
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "cortex_view",
        lambda: Reading.unreachable("http://127.0.0.1:8010/health", "test: no live Cortex"),
    )
    monkeypatch.setattr(
        sources,
        "openvault_view",
        lambda: Reading.unreachable(
            "http://127.0.0.1:5000/api/healthz", "test: no live OpenVault"
        ),
    )
    monkeypatch.setattr(
        sources,
        "estate_gate",
        lambda: Reading.unreachable("estate_gate.py", "test: gate not run"),
    )
    monkeypatch.setattr(
        sources,
        "board",
        lambda *a, **k: Reading.unreachable("gh issue list", "test: gh not run"),
    )
    monkeypatch.setattr(
        sources,
        "crew_belt_view",
        lambda: Reading.unreachable("http://127.0.0.1:8020/v1/belt", "test: no live Crew"),
    )
    monkeypatch.setattr(
        sources,
        "crew_health_view",
        lambda timeout=CREW_BELT_WAIT_S: Reading.unreachable(
            "http://127.0.0.1:8020/crew/health", "test: no live Crew health"
        ),
    )
    monkeypatch.setattr(
        sources,
        "crew_talk_view",
        lambda: Reading.unreachable("http://127.0.0.1:8020/", "test: no live Crew talk"),
    )
    monkeypatch.setattr(
        sources,
        "kb_view",
        lambda: Reading.unreachable("http://127.0.0.1:8030/healthz", "test: no live KB"),
    )
    monkeypatch.setattr(
        sources,
        "kb_search",
        lambda q, limit=8: Reading.unreachable("kb search", "test: no live KB search"),
    )
    monkeypatch.setattr(
        sources,
        "fleet_view",
        lambda: Reading.unreachable("CLAIMS.json", "test: no live fleet"),
    )
    monkeypatch.setattr(
        sources,
        "claude_pads_view",
        lambda: Reading.unreachable("claude agents --json", "test: no live Claude pads"),
    )
    monkeypatch.setattr(
        sources,
        "desktop_surfaces_view",
        lambda: Reading.unreachable("tasklist", "test: no live surfaces"),
    )
    monkeypatch.setattr(
        sources,
        "runtime_view",
        lambda: Reading.unreachable("RUNTIME.md", "test: no live runtime"),
    )
    monkeypatch.setattr(
        sources,
        "spaceship_host_view",
        lambda: Reading(
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
                "domains": [{"host": "netie.ai", "site": "custom website"}],
                "rule": "Login once. Reopen Hosting Manager. Do not click New hosting.",
            },
            source="SHIP_SPACESHIP.md",
        ),
    )


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.mark.parametrize("path", sorted(FORBIDDEN))
def test_a_forbidden_capability_answers_405_with_its_owner(client: TestClient, path: str) -> None:
    """405, not 404. 404 says 'no such thing' and invites someone to build it."""
    resp = client.get(path)

    assert resp.status_code == 405, (
        f"{path} answered {resp.status_code}. This capability belongs to another plane "
        f"and must refuse, not silently not-exist."
    )
    body = resp.json()
    assert body["code"] == "not_this_plane"
    assert body["owner"], "a refusal that does not name the owner tells nobody where to go"
    assert len(body["message"]) > 40, "the refusal must carry the reason, not just a code"


@pytest.mark.parametrize("path", sorted(FORBIDDEN))
@pytest.mark.parametrize("verb", ["post", "put", "patch", "delete"])
def test_the_refusal_holds_for_every_verb(client: TestClient, path: str, verb: str) -> None:
    """A GET that 404s while a POST 405s reads as an oversight, not a decision."""
    resp = getattr(client, verb)(path)
    assert resp.status_code == 405, f"{verb.upper()} {path} -> {resp.status_code}"


def test_control_holds_no_key_material() -> None:
    """The one non-negotiable: exactly one key vault in this company.

    Asserted on the source rather than at runtime, because a key that only appears
    under a config branch would pass a runtime probe.
    """
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parents[1] / "netie_control"
    forbidden_names = ("api_key", "apikey", "secret_key", "private_key", "OPENAI_API_KEY",
                       "ANTHROPIC_API_KEY", "keyring", "vault_write")
    offenders: list[str] = []
    for py in pkg.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#") or '"""' in stripped:
                continue
            for name in forbidden_names:
                if name in line:
                    offenders.append(f"{py.name}:{line_no} {name}")
    assert not offenders, (
        "Control must hold no key material - custody is OpenVault's, and there is "
        "exactly one vault (NETIE.md section 3):\n" + "\n".join(offenders)
    )


def test_no_launcher_touches_the_founders_desktop_software() -> None:
    """R-0015. Grok Bot, Cursor and every user-facing app open by the founder's hand."""
    from netie_control.sources import LAUNCHERS

    banned = ("grok", "cursor", "chrome.exe", "code.exe", "explorer.exe", "taskkill")
    offenders = [
        f"{launcher.name}: {' '.join(launcher.argv)}"
        for launcher in LAUNCHERS
        if any(b in " ".join(launcher.argv).lower() for b in banned)
    ]
    assert not offenders, (
        "A launcher targets the founder's desktop software. Agents never start, "
        "restart or kill it (R-0015):\n" + "\n".join(offenders)
    )


def test_crew_chat_is_a_launch_not_an_iframe(client: TestClient) -> None:
    """F-0026 / P-CTL-3. Converse stays on Crew :8020. Control does not embed it."""
    page = client.get("/").text
    assert "Crew chat" in page
    assert 'id="openCrew"' in page
    assert 'href="http://127.0.0.1:8020"' in page
    assert 'target="_blank"' in page
    assert "<iframe" not in page.lower()
    assert "crewIframe" not in page
    assert "crew-frame" not in page
    assert "<form" not in page.lower()
    assert client.post("/v1/run", json={"chat": "hi"}).status_code == 405


def test_launcher_lanes_are_declared_not_executed(client: TestClient) -> None:
    """P-CTL-2. No principal, so the desk names cwd and does not run the CLI."""
    page = client.get("/").text
    assert "Local CLI lanes" in page
    assert "P-CTL-2" in page
    assert "does not execute" in page
    assert "estate-gate" in page
    assert "<form" not in page.lower()
    assert client.post("/v1/run", json={"launch": "estate-gate"}).status_code == 405


def test_an_unreachable_source_is_stated_not_blanked(client: TestClient, monkeypatch) -> None:
    """The page's whole job is 'what is actually true'. Silence is the worst answer.

    An empty panel and a healthy-but-quiet panel look identical, so the operator cannot
    tell which they are reading (R-0011). GET / defers the gate; GET /v1/gate is the
    live probe.
    """
    from netie_control import sources

    monkeypatch.setattr(
        sources, "estate_gate",
        lambda: sources.Reading.unreachable("estate_gate.py", "probe: pretend it is missing"),
    )
    page = client.get("/").text

    assert "Could not read this source" in page
    assert "deferred so the desk paints first" in page
    assert "UNKNOWN" in page, "an unreadable gate must not render as a pass"
    assert 'id="gateBanner">Estate gate PASSES' not in page
    assert 'class="banner ok" id="gateBanner"' not in page

    gate = client.get("/v1/gate").json()
    assert gate["ok"] is False
    assert "probe: pretend it is missing" in (gate.get("detail") or "")
    assert gate["display_only"] is True
    assert client.post("/v1/gate", json={"force": True}).status_code != 200


def test_index_does_not_run_estate_gate(client: TestClient, monkeypatch) -> None:
    """The desk must paint without waiting on a 120s gate subprocess."""
    from netie_control import sources

    def boom() -> None:
        raise AssertionError("GET / must not run estate_gate")

    monkeypatch.setattr(sources, "estate_gate", boom)
    page = client.get("/").text
    assert "GET /v1/gate not yet" in page
    assert "checking GET /v1/gate" not in page
    assert "searching Netie-KB" not in page
    assert "KB search unread. GET /v1/skills not yet." in page
    assert "signal: ctrl.signal" in page
    assert 'id="gateBody"' in page
    assert "fetch(\"/v1/gate\")" in page
    assert "GET /v1/gate unread" in page
    assert "gate unread" in page
    assert 'id="gateBanner">Estate gate PASSES' not in page
    assert 'class="banner ok" id="gateBanner"' not in page


def test_index_does_not_run_board(client: TestClient, monkeypatch) -> None:
    """The desk must paint without waiting on gh issue list."""
    from netie_control import sources

    def boom() -> None:
        raise AssertionError("GET / must not run board")

    monkeypatch.setattr(sources, "board", boom)
    page = client.get("/").text
    assert "GET /v1/board" in page
    assert 'id="boardBody"' in page
    assert "fetch(\"/v1/board\")" in page
    assert "fetch(\"/v1/pickup\")" in page
    assert "Board unread. GET /v1/board." in page
    assert "Pickup unread. GET /v1/pickup." in page
    assert 'id="pickupBody"' in page
    assert "deferred so the desk paints first" in page
    assert 'id="gateBanner">Estate gate PASSES' not in page
    assert 'class="banner ok" id="gateBanner"' not in page
    assert client.post("/v1/board", json={"assign": "me"}).status_code != 200


def test_index_does_not_run_claude_pads(client: TestClient, monkeypatch) -> None:
    """The desk must paint without waiting on claude agents --json."""
    from netie_control import sources

    def boom() -> None:
        raise AssertionError("GET / must not run claude_pads_view")

    monkeypatch.setattr(sources, "claude_pads_view", boom)
    page = client.get("/").text
    assert "GET /v1/pads" in page
    assert 'id="padsBody"' in page
    assert "fetch(\"/v1/pads\")" in page
    assert "function readingJson" in page
    assert 'if (!r.ok) throw new Error("unread " + r.status);' in page
    assert "Pads unread. GET /v1/pads." in page
    assert 'id="stripPads">unread</b>' in page
    assert client.post("/v1/pads", json={"start": True}).status_code != 200
    assert client.post("/v1/run").status_code == 405


def test_v1_state_is_display_only_and_skips_slow_probes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET /v1/state paints desk JSON. It must not wait on gate, gh, or pads."""
    from netie_control import sources

    def boom_gate() -> None:
        raise AssertionError("GET /v1/state must not run estate_gate")

    def boom_board(*_a: object, **_k: object) -> None:
        raise AssertionError("GET /v1/state must not run board")

    def boom_pads() -> None:
        raise AssertionError("GET /v1/state must not run claude_pads_view")

    monkeypatch.setattr(sources, "estate_gate", boom_gate)
    monkeypatch.setattr(sources, "board", boom_board)
    monkeypatch.setattr(sources, "claude_pads_view", boom_pads)
    body = client.get("/v1/state").json()
    assert body["display_only"] is True
    assert "claude_pads" in body
    assert body["claude_pads"]["ok"] is False
    assert "GET /v1/pads" in (body["claude_pads"].get("source") or "")
    assert client.post("/v1/state", json={"assign": "me"}).status_code != 200
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/goal").status_code == 405
    assert client.post("/v1/secrets").status_code == 405
    assert client.post("/v1/route").status_code == 405


def test_the_page_never_claims_a_pass_it_did_not_read(client: TestClient, monkeypatch) -> None:
    """The failure that matters: unknown rendering as green."""
    from netie_control import sources

    monkeypatch.setattr(
        sources, "estate_gate",
        lambda: sources.Reading.unreachable("estate_gate.py", "unreachable"),
    )
    page = client.get("/").text
    assert 'id="gateBanner">Estate gate PASSES' not in page
    assert 'class="banner ok" id="gateBanner"' not in page


def test_healthz_says_which_plane_it_is_on(client: TestClient) -> None:
    body = client.get("/healthz").json()
    assert body["plane"] == 4
    assert body["product"] == "netie-control"
    assert client.get("/favicon.ico").status_code == 204
    assert client.post("/v1/run").status_code == 405


def test_page_names_spaceship_host_to_reuse(client: TestClient) -> None:
    page = client.get("/").text
    assert "Hosting Manager" in page
    assert "ship@netie.ai" in page
    assert "Do not click New hosting" in page
    assert "FTP_PASS" not in page


def test_spaceship_host_view_has_no_password() -> None:
    reading = spaceship_host_view()
    if not reading.ok:
        pytest.skip(reading.detail)
    blob = json.dumps(reading.data)
    assert "FTP_PASS" not in blob
    assert reading.data["ftp_user"] == "ship@netie.ai"
    assert "hosting-manager" in reading.data["hosting_manager"]


def test_loopback_probe_refuses_off_box_urls() -> None:
    r = loopback_get_json("https://example.com/health")
    assert r.ok is False
    assert "loopback" in r.detail.lower()
    s = loopback_get_status("https://example.com/")
    assert s.ok is False
    assert "loopback" in s.detail.lower()
    assert s.data is None


def test_unreachable_cortex_never_renders_as_up(client: TestClient) -> None:
    page = client.get("/").text
    assert "Cortex is up" not in page
    assert "Could not read this source" in page
    assert "test: no live Cortex" in page


def test_cortex_and_vault_are_on_the_first_page_not_only_in_details(
    client: TestClient,
) -> None:
    """NETIE.md section 3: first page is Cortex internals. Second ring is FreeRoute."""
    page = client.get("/").text
    cortex_at = page.find('id="cortex"')
    vault_at = page.find('id="vault"')
    more_at = page.find("More estate")
    assert cortex_at != -1
    assert vault_at != -1
    assert more_at != -1
    assert cortex_at < more_at
    assert vault_at < more_at
    assert 'class="hero"' in page
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/route").status_code == 405


def test_cortex_up_renders_governance_without_payloads(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "cortex_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:8010",
            data={
                "up": True,
                "health": {"status": "ok", "pack": "dms"},
                "activity": {"workflows": {"active": []}, "routines": {"total": 0}},
                "activity_detail": None,
                "features": {"engine_version": "2.5.0"},
                "governance": {
                    "ledger": {
                        "registered": True,
                        "tip_seq": 12,
                        "recent": [{"seq": 12, "event_type": "ask", "actor": "dms"}],
                    },
                    "manifests": {"bound": 1, "sessions": []},
                    "refusals": {
                        "recent": [
                            {
                                "seq": 11,
                                "event_type": "action.tool_call_denied",
                                "actor": "engine",
                            }
                        ]
                    },
                },
                "refusal_view": "present",
                "refusal_why": "",
            },
        ),
    )
    page = client.get("/").text
    assert "Cortex is up" in page
    assert "ledger tip=12" in page
    assert "action.tool_call_denied" in page
    assert "Governance from Cortex" in page
    assert "will not scrape the ledger" not in page
    assert "payload" not in page


def test_openvault_up_does_not_claim_a_route_choice(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "openvault_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:5000/api/healthz",
            data={"up": True, "healthz": {"status": "ok", "service": "openvault"}},
        ),
    )
    page = client.get("/").text
    assert "OpenVault healthz ok" in page
    assert "did not pick a route" in page
    assert "OpenVault usage unread" in page
    assert client.post("/v1/route").status_code == 405


def test_openvault_usage_counts_are_display_not_a_price(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "openvault_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:5000/api/healthz",
            data={
                "up": True,
                "healthz": {"status": "ok"},
                "usage": {
                    "count": 3,
                    "summary": {
                        "requests": 3,
                        "total_tokens": 10,
                        "estimated_tokens": 2,
                        "priced": False,
                    },
                },
                "usage_detail": "",
            },
        ),
    )
    page = client.get("/").text
    assert "did not pick a route" in page
    assert "priced=False" in page
    assert "estimated_tokens=2" in page
    assert "total_tokens=10" in page
    assert "Do not invent prices" in page
    assert client.post("/v1/route").status_code == 405


def test_openvault_view_slims_usage_and_drops_ledger_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from netie_control import sources

    def fake(url: str, timeout: float = 2.0) -> Reading:
        if url.endswith("/api/healthz"):
            return Reading(ok=True, data={"status": "ok"}, source=url)
        if "/api/usage" in url:
            assert "limit=1" in url
            return Reading(
                ok=True,
                data={
                    "ok": True,
                    "events": [
                        {
                            "vault_key_id": "vk_secret",
                            "model_served": "auto",
                        }
                    ],
                    "count": 1,
                    "summary": {
                        "requests": 3,
                        "total_tokens": 10,
                        "estimated_tokens": 2,
                        "priced": False,
                    },
                },
                source=url,
            )
        return Reading.unreachable(url, "unexpected")

    monkeypatch.setattr(sources, "loopback_get_json", fake)
    reading = _REAL_OPENVAULT()
    assert reading.ok is True
    assert reading.data["up"] is True
    usage = reading.data["usage"]
    assert "events" not in usage
    blob = json.dumps(reading.data)
    assert "vk_secret" not in blob
    assert usage["summary"]["priced"] is False
    assert usage["summary"]["requests"] == 3


def test_openvault_view_names_unread_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    from netie_control import sources

    def fake(url: str, timeout: float = 2.0) -> Reading:
        if url.endswith("/api/healthz"):
            return Reading(ok=True, data={"status": "ok"}, source=url)
        if "/api/usage" in url:
            return Reading.unreachable(url, "HTTP 404")
        return Reading.unreachable(url, "unexpected")

    monkeypatch.setattr(sources, "loopback_get_json", fake)
    reading = _REAL_OPENVAULT()
    assert reading.ok is True
    assert reading.data["usage"] is None
    assert "404" in (reading.data.get("usage_detail") or "")


def test_openvault_view_healthz_and_usage_are_parallel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hung healthz + usage must not stack 2s + 1.5s on GET /."""
    from netie_control import sources

    seen: list[float] = []

    def fake(url: str, timeout: float = 2.0) -> Reading:
        seen.append(timeout)
        time.sleep(0.25)
        if url.endswith("/api/healthz"):
            return Reading(ok=True, data={"status": "ok"}, source=url)
        if "/api/usage" in url:
            return Reading.unreachable(url, "hung usage")
        return Reading.unreachable(url, "unexpected")

    monkeypatch.setattr(sources, "loopback_get_json", fake)
    t0 = time.perf_counter()
    reading = _REAL_OPENVAULT()
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.45
    assert seen
    assert all(t == sources.OPENVAULT_USAGE_WAIT_S for t in seen)
    assert sources.OPENVAULT_USAGE_WAIT_S <= 1.5
    assert reading.ok is True
    assert reading.data["usage"] is None
    assert "hung" in (reading.data.get("usage_detail") or "")


def test_v1_belt_is_display_proxy_not_a_second_engine(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "crew_belt_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:8020/v1/belt",
            data={
                "bus": "github-issues",
                "tickets": {
                    "items": [
                        {
                            "repo": "Netie-AI/dms",
                            "number": 2,
                            "title": "demo ticket",
                            "ready": True,
                        }
                    ],
                    "unreachable": [],
                },
                "handoffs": [{"ticket": "dms#2", "from": "a", "note": "go"}],
                "cortex": {"ok": True},
                "plan_for_next": {"decides_work_shape": False, "needs_human": True},
            },
        ),
    )
    body = client.get("/v1/belt").json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert body["converse_owner"] == "Netie Crew"
    assert body["data"]["bus"] == "github-issues"
    assert body["data"]["plan_for_next"]["decides_work_shape"] is False
    assert client.post("/v1/belt", json={"ticket": "x"}).status_code != 200


def test_crew_belt_view_uses_crew_belt_when_v1_hangs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from netie_control import sources

    def fake(url: str, timeout: float = 2.0) -> Reading:
        if url.endswith("/v1/belt"):
            return Reading.unreachable(url, "unreachable: timed out")
        if url.endswith("/crew/belt"):
            return Reading(
                ok=True,
                source=url,
                data={"bus": "github-issues", "wakes": [], "converse": True},
            )
        return Reading.unreachable(url, "unexpected")

    monkeypatch.setattr(sources, "loopback_get_json", fake)
    got = _REAL_CREW_BELT()
    assert got.ok is True
    assert str(got.source).endswith("/crew/belt")
    assert (got.data or {}).get("bus") == "github-issues"


def test_crew_belt_view_names_both_misses(monkeypatch: pytest.MonkeyPatch) -> None:
    from netie_control import sources

    def fake(url: str, timeout: float = 2.0) -> Reading:
        if url.endswith("/v1/belt"):
            return Reading.unreachable(url, "unreachable: timed out")
        if url.endswith("/crew/belt"):
            return Reading.unreachable(url, "HTTP 404")
        return Reading.unreachable(url, "unexpected")

    monkeypatch.setattr(sources, "loopback_get_json", fake)
    got = _REAL_CREW_BELT()
    assert got.ok is False
    assert "timed out" in (got.detail or "")
    assert "HTTP 404" in (got.detail or "")
    assert got.source.endswith("/v1/belt")


def test_crew_belt_panel_renders_json_display_only(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "crew_belt_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:8020/v1/belt",
            data={
                "bus": "github-issues",
                "tickets": {
                    "items": [
                        {
                            "repo": "Netie-AI/Cortex",
                            "number": 4,
                            "title": "chore ci",
                            "ready": True,
                        }
                    ],
                    "unreachable": [],
                },
                "handoffs": [],
                "cortex": {"ok": True},
                "plan_for_next": {"decides_work_shape": False, "needs_human": True},
                "wakes": [
                    {"kind": "timer", "state": "pending", "note": "morning brief"},
                ],
                "queue": {"pending": 1, "leased": 0, "done": 2, "dead": 0},
                "confirms": [{"id": "c1"}],
                "spaces": [{"id": "s1"}],
                "agents": [{"id": "a1", "name": "Scout"}],
                "assign_owner": (
                    "Crew /assign (local bind). CLAIMS seating is Ticket Runner. "
                    "Control does not assign."
                ),
                "assignments": [
                    {
                        "spec": "Netie-AI/Cortex#164",
                        "agent": "Scout",
                        "title": "fetch hud",
                    }
                ],
            },
        ),
    )
    page = client.get("/").text
    assert "Crew conveyor (display-only)" in page
    assert "chore ci" in page
    assert "morning brief" in page
    assert "does not POST wakes" in page
    assert "pending" in page
    assert "HITL pending=1" in page
    assert "Control does not approve" in page
    assert "Control does not spawn" in page
    assert "Crew owns leases" in page
    assert "crew talk" in page
    assert "does not converse" in page
    assert "dag_runner" not in page
    assert "<form" not in page.lower()
    assert "Crew surface" in page
    assert "http://127.0.0.1:8020" in page
    assert "Netie-AI/Cortex#164" in page
    assert "Scout" in page
    assert "Control does not assign" in page
    assert client.post("/v1/belt", json={"assign": "me"}).status_code != 200


def test_crew_belt_idle_is_named_not_silent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ok JSON with empty wakes/queue is idle, not unread (R-0011)."""
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "crew_belt_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:8020/v1/belt",
            data={
                "bus": "github-issues",
                "tickets": {"items": [], "unreachable": []},
                "wakes": [],
                "queue": {},
                "confirms": [],
                "plan_for_next": {"decides_work_shape": False, "needs_human": True},
            },
        ),
    )
    page = client.get("/").text
    assert "wakes none" in page
    assert "queue none" in page
    assert "assignments none" in page
    assert "Control does not assign" in page
    assert "HITL pending=0" in page
    assert "does not POST wakes" in page
    assert client.post("/v1/belt", json={"wake": "x"}).status_code != 200


def test_crew_belt_skipped_cortex_ping_is_not_a_failed_probe(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Engine Crew belt skips Cortex HTTP. That is not a hung ping (R-0011)."""
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "crew_belt_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:8020/v1/belt",
            data={
                "bus": "github-issues",
                "tickets": {"items": [], "unreachable": []},
                "wakes": [],
                "queue": {},
                "confirms": [],
                "cortex": {"ok": False, "detail": "not probed"},
            },
        ),
    )
    page = client.get("/").text
    assert "Crew belt does not ping Cortex" in page
    assert "Laptop-tools engine_ok is the live probe" in page
    assert "Crew Cortex ping: not probed" not in page
    assert client.post("/v1/run").status_code == 405


def test_unreachable_crew_belt_is_stated(client: TestClient) -> None:
    page = client.get("/").text
    assert "Crew conveyor (display-only)" in page
    assert "test: no live Crew" in page
    assert "http://127.0.0.1:8020/v1/belt" in page
    assert "Crew surface" in page
    assert "does not POST wakes" in page
    assert "YOU step 8" in page
    assert 'id="stripCrew"' in page
    assert "crew belt" in page
    assert 'id="stripCrew">unread</b>' in page
    assert 'id="stripTalk">unread</b>' in page
    assert "crew talk" in page
    assert "python -m CortexOS.crew" in page
    assert "R-0015" in page
    assert "dag_runner" not in page
    assert "<form" not in page.lower()


def test_unreachable_crew_health_is_stated(client: TestClient) -> None:
    page = client.get("/").text
    assert "Laptop tools (Crew health)" in page
    assert "test: no live Crew health" in page


def test_unreachable_kb_is_stated(client: TestClient) -> None:
    page = client.get("/").text
    assert "Skill chest (Netie-KB)" in page
    assert "test: no live KB" in page


def test_crew_health_renders_uacc_without_control_arming(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "crew_health_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:8020/crew/health",
            data={
                "ok": True,
                "computer_control": False,
                "grok_offloaded": True,
                "provider": {"label": "cursor", "model": "grok", "source": "env"},
                "mcp": [
                    {
                        "name": "uacc",
                        "status": "off (CORTEX_COMPUTER_CONTROL not set)",
                        "armed": False,
                        "enabled": False,
                        "running": False,
                    }
                ],
                "openvault_ok": True,
                "engine_ok": False,
                "engine_detail": "TimeoutError",
            },
        ),
    )
    page = client.get("/").text
    assert "uacc" in page
    assert "will not set the flag" in page
    assert "does not arm UACC" in page
    assert "does not bypass OS permission" in page
    assert "Crew engine ping" in page
    assert "does not start Cortex" in page
    assert "<form" not in page.lower()


def test_kb_chest_renders_counts_not_bodies(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "kb_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:8030/healthz",
            data={
                "ok": True,
                "service": "netie-kb",
                "counts": {"skill": 4, "finding": 20, "total": 40},
            },
        ),
    )
    page = client.get("/").text
    assert "Skill chest (Netie-KB)" in page
    assert "skill=4" in page
    assert "finding=20" in page
    assert "private SKILL.md" in page


def test_openvault_plugin_names_custody_and_keeps_405(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "openvault_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:5000/api/healthz",
            data={
                "up": True,
                "healthz": {"status": "ok", "service": "openvault"},
                "custody_owner": "OpenVault",
                "request_path": "OpenVault. Control /v1/secrets answers 405.",
            },
        ),
    )
    page = client.get("/").text
    assert "Custody plugin" in page
    assert "never stores them" in page
    body = client.get("/v1/secrets").json()
    assert client.get("/v1/secrets").status_code == 405
    assert body["owner"] == "OpenVault"


def test_crew_health_strips_mcp_tool_lists() -> None:
    """A Crew payload that grew a tool catalog must not be copied onto the page."""
    from netie_control.sources import slim_crew_health

    fat = {
        "ok": True,
        "computer_control": True,
        "mcp": [
            {
                "name": "uacc",
                "status": "ready",
                "armed": True,
                "enabled": True,
                "running": True,
                "tools": [{"name": "click", "description": "click the mouse"}],
            }
        ],
        "openvault": {"ok": True, "url": "http://127.0.0.1:5000"},
        "engine": {"ok": False, "url": "http://127.0.0.1:8011", "detail": "TimeoutError"},
        "provider": {"label": "x", "model": "y", "token": "must-not-copy"},
    }
    slim = slim_crew_health(fat)
    row = slim["mcp"][0]
    assert "tools" not in row
    assert "token" not in (slim.get("provider") or {})
    assert slim["openvault_ok"] is True
    assert slim["engine_ok"] is False
    assert slim["engine_detail"] == "TimeoutError"
    assert row["name"] == "uacc"


def test_crew_health_caps_at_belt_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """A hung fork /crew/health must not stall GET / longer than the belt probe."""
    from netie_control import sources

    seen: dict[str, float] = {}

    def fake(url: str, timeout: float = 2.0) -> Reading:
        seen["timeout"] = timeout
        seen["url"] = url
        return Reading.unreachable(url, "probe")

    monkeypatch.setattr(sources, "loopback_get_json", fake)
    reading = _REAL_CREW_HEALTH()
    assert seen["timeout"] == sources.CREW_BELT_WAIT_S
    assert seen["url"].endswith("/crew/health")
    assert reading.ok is False


def test_guess_lane_from_branch_prefix() -> None:
    from netie_control.sources import guess_lane

    assert guess_lane("cursor/sec01-dms-query-manifest-37b6") == "Cursor"
    assert guess_lane("claude/epic002-contract-wheel") == "Claude"
    assert guess_lane("worktree-dms-59-sqlgate-violations") == "Claude"
    assert guess_lane("chore/unblock-ci-and-estate-audit") == "mixed"
    assert guess_lane("") == "unknown"
    assert guess_lane("cursor/foo") != "Claude"


def test_fleet_from_claims_seated_first_and_does_not_invent_cloud() -> None:
    from netie_control.sources import fleet_from_claims

    payload = {
        "ts": "2026-08-27T00:00:00+00:00",
        "tickets": [
            {
                "ticket": "Netie-AI/Cortex#4",
                "repo": "Netie-AI/Cortex",
                "owner_pr": "Netie-AI/Cortex#4",
                "head": "chore/unblock",
                "role": "UNSEATED",
                "may_write": False,
            },
            {
                "ticket": "Netie-AI/Cortex#70",
                "repo": "Netie-AI/Cortex",
                "owner_pr": "Netie-AI/Cortex#70",
                "head": "claude/wip-onto-main",
                "role": "SEATED",
                "may_write": True,
            },
            {
                "ticket": "Netie-AI/dms#99",
                "repo": "Netie-AI/dms",
                "owner_pr": "Netie-AI/dms#99",
                "head": "cursor/e9-02-sql-scope-68a9",
                "role": "SEATED",
                "may_write": True,
            },
        ],
    }
    fleet = fleet_from_claims(payload, {"Netie-AI/dms#99": "scope the SQL"})
    assert fleet["seated"] == 2
    assert fleet["rows"][0]["role"] == "SEATED"
    dms = next(r for r in fleet["rows"] if r["ticket"] == "Netie-AI/dms#99")
    assert dms["lane"] == "Cursor"
    assert dms["title"] == "scope the SQL"
    assert "cloud vs this PC" in fleet["lane_rule"]
    mixed = next(r for r in fleet["rows"] if r["ticket"] == "Netie-AI/Cortex#4")
    assert mixed["lane"] == "mixed"


def test_parse_runtime_names_stale() -> None:
    from datetime import datetime

    from netie_control.sources import parse_runtime_md

    text = """# RUNTIME (generated 2026-08-25 22:30) -- not ticket law
## Alive
- Grok Bot: OFFLOADED -> http://127.0.0.1:8020/
## Live Claude pads (`claude agents --json`)
- shipping airgpt#35 pid= background cwd=D:\\AirGPT
## Open PRs (writer guess from branch name)
- Netie-AI/Cortex #70 [Claude-worktree] `claude/wip` title
## Who does what this tick
- Cursor: this laptop for Internal.
"""
    # Naive to match the naive wall-clock RUNTIME.md actually carries.
    parsed = parse_runtime_md(text, now=datetime(2026, 8, 27, 22, 0))  # noqa: DTZ001
    assert parsed["stale"] is True
    assert "STALE" in parsed["generated_note"]
    assert parsed["pads"][0].startswith("shipping airgpt#35")
    assert "Claude-worktree" in parsed["prs"][0]


def test_fleet_panel_shows_who_where_what(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "fleet_view",
        lambda: Reading(
            ok=True,
            source="CLAIMS.json",
            data={
                "ts": "2026-08-27T14:52:10+00:00",
                "seated": 1,
                "held": 0,
                "lane_rule": "Lane is a guess from branch prefix. cursor/* is not proof of cloud vs this PC.",
                "rows": [
                    {
                        "ticket": "Netie-AI/dms#99",
                        "repo": "dms",
                        "head": "cursor/e9-02-sql-scope-68a9",
                        "role": "SEATED",
                        "may_write": True,
                        "lane": "Cursor",
                        "title": "scope the SQL",
                    }
                ],
            },
        ),
    )
    page = client.get("/").text
    assert "Who is seated" in page
    assert "Netie-AI/dms#99" in page
    assert "scope the SQL" in page
    assert "cursor/e9-02-sql-scope-68a9" in page
    assert "not proof of cloud vs this PC" in page
    body = client.get("/v1/fleet").json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert client.post("/v1/fleet", json={"seat": "x"}).status_code != 200


def test_unreachable_fleet_and_pads_are_stated(client: TestClient) -> None:
    page = client.get("/").text
    assert "Who is seated" in page
    assert "test: no live fleet" in page
    assert "deferred so the desk paints first" in page
    assert "test: no live surfaces" in page
    assert "test: no live runtime" in page


def test_runtime_stale_snapshot_renders(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "runtime_view",
        lambda: Reading(
            ok=True,
            source="RUNTIME.md",
            data={
                "generated": "2026-08-25 22:30",
                "generated_note": "watchdog snapshot 2026-08-25 22:30 STALE (2880 min old)",
                "stale": True,
                "alive": ["Grok Bot: OFFLOADED -> http://127.0.0.1:8020/"],
                "pads": ["dms-fa pid=33236 interactive cwd=D:\\DMS"],
                "prs": ["Netie-AI/Cortex #70 [Claude-worktree] claude/wip"],
                "who": ["Cursor: this laptop for Internal."],
            },
        ),
    )
    page = client.get("/").text
    assert "STALE" in page
    assert "OFFLOADED" in page
    assert "Claude-worktree" in page


def test_surfaces_running_does_not_claim_control_started_them(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "desktop_surfaces_view",
        lambda: Reading(
            ok=True,
            source="tasklist",
            data={
                "note": "present/absent only. Control did not start or kill them (R-0015).",
                "rows": [
                    {"name": "Cursor", "image": "Cursor.exe", "present": True},
                    {"name": "Grok Bot", "image": "Grok Bot.exe", "present": False},
                ],
            },
        ),
    )
    page = client.get("/").text
    assert "This PC right now" in page
    assert "Cursor" in page
    assert "not running" in page
    assert "did not start or kill" in page


def test_ticket_github_url_parses_owner_repo_number() -> None:
    from netie_control.sources import ticket_github_url

    assert ticket_github_url("Netie-AI/dms#61") == "https://github.com/Netie-AI/dms/issues/61"
    assert ticket_github_url("not-a-ticket") == ""
    assert ticket_github_url("https://github.com/Netie-AI/OpenVault/issues/18").startswith(
        "https://github.com/"
    )


def test_you_desk_is_human_stop_with_github_urls(client: TestClient) -> None:
    page = client.get("/").text
    assert "YOU - founder actions" in page
    assert "HT1" in page
    assert "HT2" in page
    assert "HUMAN_STOP" in page
    assert "Do not invent a host URL" in page
    assert "Do not invent prices" in page
    assert "https://github.com/Netie-AI/dms/pull/61" in page
    assert "https://github.com/Netie-AI/OpenVault/issues/18" in page
    assert "http://127.0.0.1:8020" in page
    assert "vercel.app" not in page
    assert "$0" not in page
    assert "<form" not in page.lower()
    body = client.get("/v1/you").json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert client.post("/v1/you", json={"run": "ht1"}).status_code != 200


def test_you_desk_names_the_two_dms_decisions_that_park_finished_code(
    client: TestClient,
) -> None:
    """A hold that lives only in a PRD markdown file gets merged by the next person.

    Both branches are written, green, and blocked on a founder answer that has been
    open since 2026-08-07 (F36) and 2026-08-23 (F45). Control does not decide either
    - it shows that they are open, and links the branch that is waiting.
    """
    page = client.get("/").text
    for fragment in (
        "F36",
        "F45",
        "https://github.com/Netie-AI/dms/tree/park/epic-020-source-db-connector",
        "https://github.com/Netie-AI/dms/tree/park/f45-space-insights",
    ):
        assert fragment in page, fragment

    steps = {s["id"]: s for s in client.get("/v1/you").json()["data"]["steps"]}
    assert steps["f36-epic-020"]["kind"] == "you"
    assert steps["f45-insights"]["kind"] == "you"
    # Numbering stays contiguous, so "step 4" in conversation means one thing.
    numbers = [s["n"] for s in client.get("/v1/you").json()["data"]["steps"]]
    assert numbers == [str(i + 1) for i in range(len(numbers))]


def test_you_desk_names_crew_engine_bind(client: TestClient) -> None:
    """Live :8020 is the fork. Agents must not restart it. YOU starts the engine tree."""
    page = client.get("/").text
    assert "Bind live :8020 to engine Crew" in page
    assert "python -m CortexOS.crew" in page
    assert "R-0015" in page
    assert "http://127.0.0.1:8020" in page
    assert "<form" not in page.lower()
    steps = {s["id"]: s for s in client.get("/v1/you").json()["data"]["steps"]}
    bind = steps["crew-engine-bind"]
    assert bind["kind"] == "you"
    assert bind["n"] == "8"
    assert bind["url"] == "http://127.0.0.1:8020"
    assert client.post("/v1/you", json={"run": "crew-engine-bind"}).status_code != 200


def test_fleet_cards_can_carry_a_github_href() -> None:
    from netie_control.sources import fleet_from_claims

    fleet = fleet_from_claims(
        {
            "tickets": [
                {
                    "ticket": "Netie-AI/OpenVault#18",
                    "repo": "Netie-AI/OpenVault",
                    "owner_pr": "Netie-AI/OpenVault#18",
                    "head": "docs/ht1",
                    "role": "SEATED",
                    "may_write": True,
                }
            ]
        }
    )
    assert fleet["rows"][0]["href"] == "https://github.com/Netie-AI/OpenVault/issues/18"


def test_board_tickets_are_open_and_comment_cards(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "board",
        lambda *a, **k: Reading(
            ok=True,
            source="gh issue list",
            data={
                "items": [
                    {
                        "repo": "Netie-AI/dms",
                        "number": 61,
                        "title": "hold",
                        "url": "https://github.com/Netie-AI/dms/issues/61",
                        "is_epic": False,
                        "blocked": True,
                    }
                ],
                "unreachable": [],
            },
        ),
    )
    page = client.get("/").text
    assert "ticket-card" in page
    assert "fetch(\"/v1/board\")" in page
    assert 'id="boardBody"' in page
    assert "https://github.com/Netie-AI/dms/issues/61" not in page
    assert ">Open</a>" in page
    assert ">Comment</a>" in page
    assert "blocked" in page
    assert "<form" not in page.lower()
    board = client.get("/v1/board").json()
    assert board["ok"] is True
    assert board["display_only"] is True
    assert any(x.get("url") == "https://github.com/Netie-AI/dms/issues/61" for x in board["data"]["items"])
    assert any(x.get("repo") == "Netie-AI/dms" and x.get("number") == 61 for x in board["data"]["items"])
    assert client.post("/v1/board", json={"seat": True}).status_code != 200


def test_board_defaults_include_control_repo() -> None:
    from netie_control.sources import BOARD_REPOS, BOARD_WAIT_S, PICKUP_BOARD_WAIT_S

    assert "Netie-AI/netie-control" in BOARD_REPOS
    assert "Netie-AI/dms" in BOARD_REPOS
    assert BOARD_WAIT_S <= 4.0
    assert PICKUP_BOARD_WAIT_S <= 1.5


def test_v1_board_fail_closes_hung_gh(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hung gh is named unread. GET /v1/board must not wait 60s per repo."""
    import subprocess

    from netie_control import sources

    monkeypatch.setattr(sources, "board", _REAL_BOARD)

    def boom(*_a: object, **k: object) -> None:
        raise subprocess.TimeoutExpired(cmd="gh", timeout=k.get("timeout") or 4)

    monkeypatch.setattr(sources.subprocess, "run", boom)
    t0 = time.perf_counter()
    body = client.get("/v1/board").json()
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0
    assert body["ok"] is False
    assert body["display_only"] is True
    assert body["assign_owner"] == "GitHub Issues + CLAIMS.json"
    assert "gh" in (body.get("detail") or "").lower() or "issue" in (body.get("source") or "")
    assert client.post("/v1/board", json={"assign": "me"}).status_code != 200
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/secrets").status_code == 405
    assert client.post("/v1/route").status_code == 405
    assert client.post("/v1/goal").status_code == 405


def test_pickup_tray_lists_unseated_and_skips_seated() -> None:
    from netie_control.sources import pickup_tray

    tray = pickup_tray(
        {
            "rows": [
                {
                    "role": "SEATED",
                    "ticket": "Netie-AI/OpenVault#18",
                    "href": "https://github.com/Netie-AI/OpenVault/issues/18",
                    "title": "seated",
                },
                {
                    "role": "UNSEATED",
                    "ticket": "Netie-AI/dms#40",
                    "href": "https://github.com/Netie-AI/dms/issues/40",
                    "title": "open work",
                    "repo": "dms",
                },
            ]
        },
        {
            "items": [
                {
                    "repo": "Netie-AI/OpenVault",
                    "number": 18,
                    "title": "already seated",
                    "url": "https://github.com/Netie-AI/OpenVault/issues/18",
                },
                {
                    "repo": "Netie-AI/Cortex",
                    "number": 6,
                    "title": "SEC-01",
                    "url": "https://github.com/Netie-AI/Cortex/issues/6",
                },
            ]
        },
    )
    hrefs = [x["href"] for x in tray["items"]]
    assert "https://github.com/Netie-AI/dms/issues/40" in hrefs
    assert "https://github.com/Netie-AI/Cortex/issues/6" in hrefs
    assert "https://github.com/Netie-AI/OpenVault/issues/18" not in hrefs


def test_v1_pickup_is_display_only_and_does_not_assign(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "board",
        lambda *a, **k: Reading(
            ok=True,
            source="gh issue list",
            data={
                "items": [
                    {
                        "repo": "Netie-AI/Cortex",
                        "number": 6,
                        "title": "SEC-01",
                        "url": "https://github.com/Netie-AI/Cortex/issues/6",
                    }
                ],
                "unreachable": [],
            },
        ),
    )
    body = client.get("/v1/pickup").json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert body["run_owner"] == "Cortex"
    assert any(x.get("href") == "https://github.com/Netie-AI/Cortex/issues/6" for x in body["data"]["items"])
    page = client.get("/").text
    assert "Pickup - claim on GitHub" in page
    assert "Pick up" in page
    assert "fetch(\"/v1/pickup\")" in page
    assert 'id="pickupBody"' in page
    assert "https://github.com/Netie-AI/Cortex/issues/6" not in page
    assert "work-row" in page
    assert 'class="workbench"' in page
    assert 'id="pickup"' in page
    assert 'id="board"' in page
    assert 'id="fleet"' in page
    assert "workbench__pair" not in page
    assert 'id="more"' in page
    assert "<details class=\"more\" open" not in page
    assert "YOU - founder actions" in page
    assert 'class="strip"' in page
    assert 'id="focus"' in page
    assert "data-href=" in page
    assert "Space Grotesk" in page
    assert client.post("/v1/pickup", json={"assign": "me"}).status_code != 200
    assert client.post("/v1/run").status_code == 405


def test_v1_pickup_ok_without_live_gh(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAIMS unseated items must return even when gh is unread. Control does not assign."""
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "fleet_view",
        lambda: Reading(
            ok=True,
            source="CLAIMS.json",
            data={
                "rows": [
                    {
                        "role": "UNSEATED",
                        "ticket": "Netie-AI/dms#40",
                        "href": "https://github.com/Netie-AI/dms/issues/40",
                        "title": "open work",
                        "repo": "dms",
                    }
                ]
            },
        ),
    )
    t0 = time.perf_counter()
    resp = client.get("/v1/pickup")
    elapsed = time.perf_counter() - t0
    assert resp.status_code == 200
    assert elapsed < 2
    body = resp.json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert body["run_owner"] == "Cortex"
    hrefs = [x.get("href") for x in (body.get("data") or {}).get("items") or []]
    assert "https://github.com/Netie-AI/dms/issues/40" in hrefs
    assert (body.get("data") or {}).get("board_deferred") is True
    assert "GET /v1/board" in (body.get("detail") or "")
    assert client.post("/v1/pickup", json={"assign": "me"}).status_code != 200
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/secrets").status_code == 405
    assert client.post("/v1/route").status_code == 405
    assert client.post("/v1/goal").status_code == 405
    page = client.get("/").text
    assert "<form" not in page.lower()
    assert "Crew conveyor (display-only)" in page
    assert 'class="steps"' in page
    assert "Board deferred" in page
    assert "coord__n" in page


def test_v1_pickup_does_not_block_on_slow_board(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hung gh issue list must not stall pickup. Unseated CLAIMS still return."""
    from netie_control import sources

    monkeypatch.setattr(sources, "PICKUP_BOARD_WAIT_S", 0.25)

    def hang(*_a: object, **_k: object) -> Reading:
        time.sleep(2)
        return Reading.unreachable("gh issue list", "hung")

    monkeypatch.setattr(sources, "board", hang)
    monkeypatch.setattr(
        sources,
        "fleet_view",
        lambda: Reading(
            ok=True,
            source="CLAIMS.json",
            data={
                "rows": [
                    {
                        "role": "UNSEATED",
                        "ticket": "Netie-AI/dms#40",
                        "href": "https://github.com/Netie-AI/dms/issues/40",
                        "title": "open work",
                        "repo": "dms",
                    }
                ]
            },
        ),
    )
    t0 = time.perf_counter()
    body = client.get("/v1/pickup").json()
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.5
    assert body["ok"] is True
    assert body["display_only"] is True
    hrefs = [x.get("href") for x in (body.get("data") or {}).get("items") or []]
    assert "https://github.com/Netie-AI/dms/issues/40" in hrefs
    assert (body.get("data") or {}).get("board_deferred") is True
    assert "GET /v1/board" in (body.get("detail") or "")
    assert client.post("/v1/run").status_code == 405


def test_v1_pickup_skips_full_desk_state(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pickup used to call state(), which waited on gate, pads, and crew health."""
    from netie_control import sources

    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("GET /v1/pickup must not run full desk state")

    monkeypatch.setattr(sources, "estate_gate", boom)
    monkeypatch.setattr(sources, "claude_pads_view", boom)
    monkeypatch.setattr(sources, "crew_health_view", boom)
    monkeypatch.setattr(sources, "cortex_view", boom)
    monkeypatch.setattr(
        sources,
        "fleet_view",
        lambda: Reading(
            ok=True,
            source="CLAIMS.json",
            data={
                "rows": [
                    {
                        "role": "UNSEATED",
                        "ticket": "Netie-AI/dms#40",
                        "href": "https://github.com/Netie-AI/dms/issues/40",
                        "title": "open work",
                        "repo": "dms",
                    }
                ]
            },
        ),
    )
    body = client.get("/v1/pickup").json()
    assert body["ok"] is True
    assert client.post("/v1/run").status_code == 405


def test_dashboard_does_not_hide_panels() -> None:
    css = (Path(__file__).resolve().parents[1] / "netie_control" / "static" / "control.css").read_text(
        encoding="utf-8"
    )
    assert ".stage .grid .panel { display: none; }" not in css
    assert ".stage .grid .panel { display: block; }" in css
    assert "height: 100vh" in css
    assert "minmax(14rem, 1fr) minmax(15rem, 1.15fr) minmax(14rem, 1fr)" in css


def test_strip_and_rail_show_seated_writer(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "fleet_view",
        lambda: Reading(
            ok=True,
            source="CLAIMS.json",
            data={
                "seated": 1,
                "held": 0,
                "rows": [
                    {
                        "role": "SEATED",
                        "ticket": "Netie-AI/Cortex#6",
                        "href": "https://github.com/Netie-AI/Cortex/issues/6",
                        "lane": "Cursor",
                    }
                ],
            },
        ),
    )
    page = client.get("/").text
    assert 'class="strip"' in page
    assert ">1</b><span>seated</span>" in page
    assert "rail-agent" in page
    assert "Netie-AI/Cortex#6" in page
    assert client.post("/v1/run").status_code == 405


def test_constructor_sketch_is_a_launch_not_an_engine(
    client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Control launches Constructor HTML. It does not become the Cortex engine."""
    skin = tmp_path / "ctor"
    skin.mkdir()
    (skin / "index.html").write_text("<title>Constructor</title>", encoding="utf-8")
    (skin / "app.js").write_text("/* sketch, no Control engine */", encoding="utf-8")
    monkeypatch.setenv("NETIE_CONSTRUCTOR_DIR", str(skin))
    res = client.get("/constructor/")
    assert res.status_code == 200, res.text
    assert "Constructor" in res.text
    assert client.get("/constructor/app.js").status_code == 200
    assert client.post("/v1/run").status_code == 405
    home = client.get("/").text
    assert "/constructor/" in home


def test_constructor_missing_skin_is_503_unread(
    client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing Constructor files are unread, not an empty 200 (R-0011)."""
    missing = tmp_path / "no-ctor"
    missing.mkdir()
    monkeypatch.setenv("NETIE_CONSTRUCTOR_DIR", str(missing))
    res = client.get("/constructor/")
    assert res.status_code == 503
    assert 'class="absent"' in res.text
    assert "Constructor skin unread" in res.text
    assert "POST /v1/run stays 405" in res.text
    assert '"detail"' not in res.text
    missing_js = client.get("/constructor/app.js")
    assert missing_js.status_code == 503
    assert 'class="absent"' in missing_js.text
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/secrets").status_code == 405


def test_strip_unread_is_warn_not_quiet_question(client: TestClient) -> None:
    """Deferred/unread strip cells say unread in warn color, never a quiet '?' (R-0011)."""
    page = client.get("/").text
    assert 'class="strip__cell is-absent"' in page
    assert 'id="stripPickup">unread</b>' in page
    assert ">unread</b><span>seated</span>" in page
    assert 'id="stripPads">unread</b>' in page
    assert ">unread</b><span>claude pads</span>" in page
    assert ">unread</b><span>this PC live</span>" in page
    assert '<span class="count">unread</span>' in page
    assert '<span class="count">?</span>' not in page
    assert 'length : "unread"' in page
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/goal").status_code == 405
    assert client.post("/v1/secrets").status_code == 405


def test_v1_contract_is_display_only_and_does_not_assign(client: TestClient) -> None:
    body = client.get("/v1/contract").json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert body["run_owner"] == "Cortex"
    assert body["assign_owner"] == "GitHub Issues + CLAIMS.json"
    assert any(u.endswith("/v1/pickup") for u in body["before_seating"])
    assert any(u.endswith("/v1/coordinate") for u in body["before_seating"])
    assert "/v1/run" in body["forbidden"]
    assert body["desk"]["talk_probe"] == "/crew/wakes"
    assert body["desk"]["you_steps"] == 8
    assert body["desk"]["usage_probe"] == "/api/usage"
    assert body["desk"]["board_wait_s"] == 4.0
    assert body["desk"]["pickup_board_wait_s"] == 1.5
    assert body["desk"]["kb_wait_s"] == 1.5
    assert body["desk"]["cortex_wait_s"] == 1.5
    assert body["desk"]["crew_belt_wait_s"] == 1.5
    assert body["desk"]["openvault_usage_wait_s"] == 1.5
    page = client.get("/").text
    assert 'class="howto"' in page
    assert "Every agent" in page
    assert "GET /v1/contract" in page
    assert "YOU step 8 binds :8020" in page
    assert "talk_probe=/crew/wakes" in page
    assert "you_steps=8" in page
    assert "usage_probe=/api/usage" in page
    assert "board_wait_s=4.0" in page
    assert "pickup_board_wait_s=1.5" in page
    assert "kb_wait_s=1.5" in page
    assert "cortex_wait_s=1.5" in page
    assert "crew_belt_wait_s=1.5" in page
    assert "openvault_usage_wait_s=1.5" in page
    assert "<code>/v1/coordinate</code>" in page
    assert client.post("/v1/contract", json={"assign": "me"}).status_code != 200
    assert client.post("/v1/run").status_code == 405


def test_v1_coordinate_is_display_only_and_does_not_invoke(client: TestClient) -> None:
    """Grok-class map. Control names owners. It does not spawn or start apps."""
    body = client.get("/v1/coordinate").json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert body["run_owner"] == "Cortex"
    lanes = (body.get("data") or {}).get("lanes") or []
    by_id = {row["id"]: row for row in lanes if isinstance(row, dict)}
    assert "run" in by_id and by_id["run"]["owner"] == "Cortex"
    assert by_id["run"]["live"] is False
    assert "POST /v1/run stays 405" in by_id["run"]["do_not"]
    assert by_id["cursor"]["live"] is False
    assert "will not start Cursor.exe" in by_id["cursor"]["do_not"]
    assert by_id["spawn"]["live"] is False
    assert "does not spawn" in by_id["spawn"]["do_not"]
    assert by_id["talk"]["live"] is False
    assert by_id["talk"]["href"] == "http://127.0.0.1:8020"
    assert by_id["crew-bind"]["live"] is False
    assert "must not start or kill" in by_id["crew-bind"]["do_not"]
    assert by_id["crew-bind"]["href"] == "/v1/you"
    assert by_id["skills"]["live"] is False
    page = client.get("/").text
    assert 'id="coordinate"' in page
    assert "GET /v1/coordinate" in page
    assert "YOU step 8" in page
    assert "Bind live :8020 to engine Crew" in page
    assert "Agents must not start or kill :8020" in page
    assert 'class="coord-chips"' in page
    assert "Control will not start Cursor.exe" in page
    assert "F-0030 Control does not spawn" in page
    mates = (body.get("data") or {}).get("teammates") or []
    by_mate = {row["id"]: row for row in mates if isinstance(row, dict)}
    assert by_mate["ticket-runner"]["live"] is False
    assert "does not spawn Ticket Runner" in by_mate["ticket-runner"]["do_not"]
    assert "Cortex/issues/51" in str(by_mate["cursor-task"]["href"])
    assert by_mate["cursor-task"]["live"] is False
    router = (body.get("data") or {}).get("router") or {}
    assert router.get("owner") == "OpenVault FreeRoute"
    assert "does not pick a route" in (router.get("note") or "")
    assert "Ticket Runner" in page
    assert "Cortex#51" in page
    assert "/ticket-runner in Claude Code" in page
    assert "workers" in (body.get("data") or {})
    workers = (body.get("data") or {}).get("workers") or []
    assert any(row.get("unread") and row.get("kind") == "workflow" for row in workers)
    assert not any(row.get("kind") == "mcp" and row.get("unread") for row in workers)
    assert 'id="workers"' in page
    assert "workflow unread" in page
    assert "mcp unread" in page
    assert "Workers unread. GET /v1/coordinate." in page
    assert 'id="coordChips"' in page
    assert 'fetch("/v1/coordinate")' in page
    assert "coordinate unread" in page
    assert "function coordUnread" in page
    assert 'liveDot.className = "live is-unread"' in page
    assert ".live.is-unread { color: var(--warn); }" in page
    assert 'id="coordChips">Coordinate unread. GET /v1/coordinate.' in page
    assert (body.get("data") or {}).get("health_deferred") is True
    assert "if (workers && !d.health_deferred) workers.outerHTML = workersHtml(d)" in page
    assert client.post("/v1/coordinate", json={"spawn": "ticket-runner"}).status_code != 200
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/goal").status_code == 405


def test_workers_idle_when_cortex_and_crew_are_quiet(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ok quiet peers are idle, not unread (R-0011)."""
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "cortex_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:8010/health",
            data={"up": True, "activity": {"workflows": {"active": []}, "routines": {"running": []}}},
        ),
    )
    monkeypatch.setattr(
        sources,
        "crew_health_view",
        lambda timeout=CREW_BELT_WAIT_S: Reading(
            ok=True,
            source="http://127.0.0.1:8020/crew/health",
            data={"ok": True, "mcp": []},
        ),
    )
    page = client.get("/").text
    assert "No live Cortex workflows or armed Crew MCPs this tick" in page
    assert "workflow unread" not in page
    assert "mcp unread" not in page
    assert client.post("/v1/run").status_code == 405


def test_workers_unread_when_cortex_activity_hangs(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Health-ok with activity None is unread, not idle (R-0011)."""
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "cortex_view",
        lambda: Reading(
            ok=True,
            source="http://127.0.0.1:8010",
            data={
                "up": True,
                "health": {"status": "ok"},
                "activity": None,
                "activity_detail": "hung activity",
                "features": None,
                "features_detail": "hung features",
            },
        ),
    )
    monkeypatch.setattr(
        sources,
        "crew_health_view",
        lambda timeout=CREW_BELT_WAIT_S: Reading(
            ok=True,
            source="http://127.0.0.1:8020/crew/health",
            data={"ok": True, "mcp": []},
        ),
    )
    page = client.get("/").text
    assert "workflow unread" in page
    assert 'id="workers" aria-label="Live workers"' in page
    assert "Activity: hung activity" in page
    assert "Features: hung features" in page
    assert "Cortex is up" in page
    body = client.get("/v1/coordinate").json()
    workers = (body.get("data") or {}).get("workers") or []
    assert any(row.get("unread") and row.get("kind") == "workflow" for row in workers)
    assert not any(row.get("kind") == "mcp" and row.get("unread") for row in workers)
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/secrets").status_code == 405
    assert client.post("/v1/route").status_code == 405
    assert client.post("/v1/goal").status_code == 405


def test_v1_skills_is_display_only_and_does_not_run(client: TestClient, monkeypatch) -> None:
    """Skills menu is a registry search. Control does not execute the hit."""
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "kb_search",
        lambda q, limit=8: sources.Reading(
            ok=True,
            data={
                "q": q,
                "hits": [{"id": "S-0001", "kind": "skill", "title": "fleet", "score": 1}],
            },
            source="test",
        ),
    )
    body = client.get("/v1/skills", params={"q": "fleet"}).json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert body["owner"] == "Netie-KB"
    assert body["data"]["hits"][0]["id"] == "S-0001"
    empty = client.get("/v1/skills").json()
    assert empty["ok"] is False
    page = client.get("/").text
    assert 'id="skillQ"' in page
    assert "GET /v1/skills" in page
    assert 'id="skillFleet"' in page
    assert 'href="/v1/skills?q=fleet"' not in page
    assert "KB search unread" in page
    assert "function skillShow" in page
    assert "Skill unread. GET /v1/skill/" in page
    assert "data-skill=" in page
    assert 'href="/v1/skill/' not in page
    assert "Control does not run" in page
    assert "KB search failed" not in page
    assert client.post("/v1/skills", json={"run": "S-0001"}).status_code != 200
    assert client.post("/v1/run").status_code == 405


def test_cortex_view_followups_are_parallel_and_capped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hung Cortex activity+features must not stack 2s each on GET /."""
    from netie_control import sources

    def fake(url: str, timeout: float = 2.0) -> Reading:
        assert timeout == sources.CORTEX_WAIT_S
        if url.endswith("/health"):
            return Reading(ok=True, data={"status": "ok"}, source=url)
        time.sleep(0.3)
        return Reading.unreachable(url, "hung cortex")

    monkeypatch.setattr(sources, "loopback_get_json", fake)
    t0 = time.perf_counter()
    reading = _REAL_CORTEX()
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5
    assert reading.ok is True
    assert reading.data["activity"] is None
    assert reading.data["features"] is None
    assert "hung" in (reading.detail or "")
    assert "hung" in (reading.data.get("features_detail") or "")
    assert sources.CORTEX_WAIT_S <= 1.5


def test_cortex_view_health_and_followups_do_not_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hung /health must not add a second 1.5s wait before activity+features."""
    from netie_control import sources

    def fake(url: str, timeout: float = 2.0) -> Reading:
        assert timeout == sources.CORTEX_WAIT_S
        time.sleep(0.3)
        if url.endswith("/health"):
            return Reading(ok=True, data={"status": "ok"}, source=url)
        return Reading.unreachable(url, "hung cortex")

    monkeypatch.setattr(sources, "loopback_get_json", fake)
    t0 = time.perf_counter()
    reading = _REAL_CORTEX()
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5
    assert reading.ok is True
    assert reading.data["activity"] is None
    assert reading.data["features"] is None
    assert "hung" in (reading.detail or "")
    assert "hung" in (reading.data.get("features_detail") or "")


def test_kb_view_caps_at_kb_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    from netie_control import sources

    seen: dict[str, float] = {}

    def fake(url: str, timeout: float = 2.0) -> Reading:
        seen["timeout"] = timeout
        seen["url"] = url
        return Reading.unreachable(url, "hung kb healthz")

    monkeypatch.setattr(sources, "loopback_get_json", fake)
    reading = _REAL_KB_VIEW()
    assert seen["timeout"] == sources.KB_WAIT_S
    assert seen["url"].endswith("/healthz")
    assert reading.ok is False


def test_v1_skill_fail_closes_hung_kb(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hung GET /item must not wait the 8s text default."""
    from netie_control import sources

    monkeypatch.setattr(sources, "kb_show", _REAL_KB_SHOW)
    seen: dict[str, float] = {}

    def fake(url: str, timeout: float = 8.0, limit: int = 8000) -> Reading:
        seen["timeout"] = timeout
        return Reading.unreachable(url, "hung kb show")

    monkeypatch.setattr(sources, "loopback_get_text", fake)
    t0 = time.perf_counter()
    body = client.get("/v1/skill/S-0001").json()
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.5
    assert seen["timeout"] == sources.KB_WAIT_S
    assert body["ok"] is False
    assert body["display_only"] is True
    assert client.post("/v1/skill/S-0001", json={"run": True}).status_code != 200
    assert client.post("/v1/run").status_code == 405


def test_v1_skills_fail_closes_hung_kb(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hung Netie-KB search is named unread. Must not wait 8s."""
    from netie_control import sources

    monkeypatch.setattr(sources, "kb_search", _REAL_KB_SEARCH)
    seen: dict[str, float] = {}

    def fake(url: str, timeout: float = 2.0) -> Reading:
        seen["timeout"] = timeout
        return Reading.unreachable(url, "hung kb")

    monkeypatch.setattr(sources, "loopback_get_json", fake)
    t0 = time.perf_counter()
    body = client.get("/v1/skills", params={"q": "fleet"}).json()
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.5
    assert seen["timeout"] == sources.KB_WAIT_S
    assert sources.KB_WAIT_S <= 1.5
    assert body["ok"] is False
    assert body["display_only"] is True
    assert client.post("/v1/skills", json={"run": "S-0001"}).status_code != 200
    assert client.post("/v1/run").status_code == 405


def test_v1_skill_show_is_display_only_and_rejects_junk_ids(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "kb_show",
        lambda sid: sources.Reading(
            ok=True,
            data={"text": "# S-0001\nsteps", "capped": False},
            source="test",
        ),
    )
    body = client.get("/v1/skill/S-0001").json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert body["owner"] == "Netie-KB"
    assert "steps" in body["data"]["text"]
    page = client.get("/").text
    assert "function skillShow" in page
    assert "Skill unread. GET /v1/skill/" in page
    assert client.post("/v1/skill/S-0001", json={"run": True}).status_code != 200
    assert client.post("/v1/run").status_code == 405


def test_kb_show_rejects_path_shaped_ids() -> None:
    from netie_control.sources import kb_show

    junk = kb_show("../etc/passwd")
    assert junk.ok is False
    assert "id must look like" in (junk.detail or "")
    root = Path(__file__).resolve().parents[1]
    assert (root / "netie_control" / "app.py").is_file()
    assert not (root / "paperclip").exists()
    assert not (root / "server" / "src" / "index.ts").exists()
    app = (root / "netie_control" / "app.py").read_text(encoding="utf-8")
    assert "from fastapi" in app
    assert "plane: 4" in app or "plane 4" in app.lower()
    status = (root / "STATUS.md").read_text(encoding="utf-8")
    assert "not Paperclip React" in status
    assert "hard-fork" not in status.lower()


def test_agents_md_is_the_seating_contract_for_every_runtime() -> None:
    text = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_text(encoding="utf-8")
    assert "GET http://127.0.0.1:8040/v1/contract" in text
    assert "/v1/pickup" in text
    assert "Control does not assign" in text
    assert "405" in text
    assert "Grok Bot" in text
    assert "Claude" in text
    assert "/v1/coordinate" in text
    claude = (Path(__file__).resolve().parents[1] / "CLAUDE.md").read_text(encoding="utf-8")
    assert "public" in claude.lower()
    assert "AGENTS.md" in claude


def test_desktop_surfaces_snapshot_marks_present_without_tasklist(monkeypatch) -> None:
    """tasklist dumps of many Cursor.exe rows timed out and painted Cursor down."""
    from netie_control import sources

    monkeypatch.setattr(
        sources, "_win_running_images", lambda wanted: {"cursor.exe"}
    )
    reading = _REAL_DESKTOP_SURFACES()
    assert reading.ok is True
    by_name = {row["name"]: row for row in reading.data["rows"]}
    assert by_name["Cursor"]["present"] is True
    assert by_name["Grok Bot"]["present"] is False
    assert "unread" not in by_name["Grok Bot"]
    assert reading.source == "process snapshot"


def test_desktop_surfaces_snapshot_failure_is_unread_not_green(monkeypatch) -> None:
    from netie_control import sources

    def boom(_wanted: set[str]) -> set[str]:
        raise OSError("snapshot denied")

    monkeypatch.setattr(sources, "_win_running_images", boom)
    reading = _REAL_DESKTOP_SURFACES()
    assert reading.ok is False
    assert "unreachable" in (reading.detail or "")


def test_claude_pads_missing_cli_is_unread_not_invented(monkeypatch) -> None:
    from netie_control import sources

    monkeypatch.setattr(sources, "_claude_argv", lambda: None)
    reading = _REAL_CLAUDE_PADS()
    assert reading.ok is False
    assert "not on PATH" in (reading.detail or "")
    assert reading.data is None


def test_v1_pads_is_display_only_and_does_not_start_claude(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Live pads are GET /v1/pads. Control does not start Claude (R-0015)."""
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "claude_pads_view",
        lambda: Reading(
            ok=True,
            source="claude agents --json",
            data={
                "pads": [
                    {
                        "name": "dms-fa",
                        "pid": 33236,
                        "kind": "interactive",
                        "cwd": r"D:\DMS",
                    }
                ]
            },
        ),
    )
    body = client.get("/v1/pads").json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert body["data"]["pads"][0]["name"] == "dms-fa"
    page = client.get("/").text
    assert "fetch(\"/v1/pads\")" in page
    assert 'id="padsBody"' in page
    assert "Control did not start Claude" in page
    assert client.post("/v1/pads", json={"start": True}).status_code != 200
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/secrets").status_code == 405


def test_v1_pads_fail_closes_hung_cli(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hung claude agents --json is named unread. GET / still must not wait."""
    import subprocess

    from netie_control import sources

    monkeypatch.setattr(sources, "claude_pads_view", _REAL_CLAUDE_PADS)
    monkeypatch.setattr(sources, "_claude_argv", lambda: ["claude"])

    def boom(*_a: object, **k: object) -> None:
        raise subprocess.TimeoutExpired(cmd="claude", timeout=k.get("timeout") or 4)

    monkeypatch.setattr(sources.subprocess, "run", boom)
    t0 = time.perf_counter()
    body = client.get("/v1/pads").json()
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.5
    assert body["ok"] is False
    assert body["display_only"] is True
    assert "unreachable" in (body.get("detail") or "")
    assert client.post("/v1/pads", json={"start": True}).status_code != 200
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/goal").status_code == 405


def test_talk_live_is_crew_host_not_slow_health(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Talk chip follows engine converse, not a hung /crew/health probe."""
    from netie_control import sources

    monkeypatch.setattr(
        sources,
        "crew_talk_view",
        lambda: Reading(
            ok=True, data={"up": True, "wakes": True}, source="http://127.0.0.1:8020/"
        ),
    )
    monkeypatch.setattr(
        sources,
        "crew_health_view",
        lambda timeout=2.0: Reading.unreachable(
            "http://127.0.0.1:8020/crew/health", "timed out"
        ),
    )
    body = client.get("/v1/coordinate").json()
    lanes = {row["id"]: row for row in (body.get("data") or {}).get("lanes") or []}
    assert lanes["talk"]["live"] is True
    mates = {row["id"]: row for row in (body.get("data") or {}).get("teammates") or []}
    assert mates["crew"]["live"] is True
    assert (body.get("data") or {}).get("router", {}).get("surfaces", {}).get("crew") is True
    page = client.get("/").text
    assert "Talk / A2A" in page
    assert "coord-chip live" in page
    assert 'id="stripTalk">up</b>' in page
    assert 'id="stripCrew">unread</b>' in page


def test_coordinate_poll_does_not_call_crew_health(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    """Chip poll must not take the Crew thread for /crew/health."""
    from netie_control import sources

    called: list[str] = []

    def boom(timeout: float = 2.0):
        called.append("health")
        return Reading.unreachable("http://127.0.0.1:8020/crew/health", "should not run")

    monkeypatch.setattr(sources, "crew_health_view", boom)
    monkeypatch.setattr(
        sources,
        "crew_talk_view",
        lambda: Reading(ok=True, data={"up": True}, source="http://127.0.0.1:8020/"),
    )
    body = client.get("/v1/coordinate").json()
    assert called == []
    lanes = {row["id"]: row for row in (body.get("data") or {}).get("lanes") or []}
    assert lanes["talk"]["live"] is True

def test_crew_talk_view_needs_engine_wakes(monkeypatch: pytest.MonkeyPatch) -> None:
    """A hung fork that still serves GET / HTML must not paint Talk live."""
    from netie_control import sources

    def fake_json(url: str, timeout: float = 2.0) -> Reading:
        assert url.endswith("/crew/wakes")
        return Reading.unreachable(url, "HTTP 404")

    monkeypatch.setattr(sources, "loopback_get_json", fake_json)
    reading = _REAL_CREW_TALK()
    assert reading.ok is False
    assert "404" in (reading.detail or "")
    assert str(reading.source).endswith("/crew/wakes")


def test_crew_talk_view_discards_html(monkeypatch: pytest.MonkeyPatch) -> None:
    from netie_control import sources

    def fake_json(url: str, timeout: float = 2.0) -> Reading:
        assert url.endswith("/crew/wakes")
        return Reading(
            ok=True,
            data={"ok": True, "wakes": [], "html": "<html>crew composer secret</html>"},
            source=url,
        )

    monkeypatch.setattr(sources, "loopback_get_json", fake_json)
    reading = _REAL_CREW_TALK()
    assert reading.ok is True
    assert reading.data == {"up": True, "wakes": True}
    assert str(reading.source).endswith("/crew/wakes")
    # F-0026 class: Crew's HTML must not travel into Control and become a second
    # copy of the composer. Assert on the serialised payload, not on the keys we
    # happened to read - a nested string would pass a key check.
    blob = json.dumps(reading.data)
    assert "html" not in blob
    assert "composer" not in blob



def test_get_home_talk_and_health_do_not_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hung /crew/wakes must not add a second wait after /crew/health."""
    from netie_control import sources
    from netie_control.app import state

    def slow_talk() -> Reading:
        time.sleep(0.35)
        return Reading(ok=True, data={"up": True, "wakes": True}, source="talk")

    def slow_health(timeout: float = CREW_BELT_WAIT_S) -> Reading:
        time.sleep(0.35)
        return Reading.unreachable("health", "timed out")

    monkeypatch.setattr(sources, "crew_talk_view", slow_talk)
    monkeypatch.setattr(sources, "crew_health_view", slow_health)
    t0 = time.perf_counter()
    blob = state(include_gate=False, include_board=False, include_pads=False)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.6
    assert blob["crew_talk"]["ok"] is True
    assert blob["crew_health"]["ok"] is False


def test_v1_coordinate_talk_and_cortex_do_not_stack(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hung /crew/wakes must not stack a second Cortex wait on GET /v1/coordinate."""
    from netie_control import sources

    def slow_talk() -> Reading:
        time.sleep(0.35)
        return Reading(ok=True, data={"up": True, "wakes": True}, source="talk")

    def slow_cortex() -> Reading:
        time.sleep(0.35)
        return Reading.unreachable("http://127.0.0.1:8010/health", "hung cortex")

    monkeypatch.setattr(sources, "crew_talk_view", slow_talk)
    monkeypatch.setattr(sources, "cortex_view", slow_cortex)
    t0 = time.perf_counter()
    body = client.get("/v1/coordinate").json()
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.6
    assert body["ok"] is True
    assert body["display_only"] is True
    assert (body.get("data") or {}).get("health_deferred") is True
    lanes = {row["id"]: row for row in (body.get("data") or {}).get("lanes") or []}
    assert lanes["talk"]["live"] is True
    assert client.post("/v1/run").status_code == 405
    assert client.post("/v1/secrets").status_code == 405
    assert client.post("/v1/route").status_code == 405
    assert client.post("/v1/goal").status_code == 405

