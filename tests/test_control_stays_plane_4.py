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
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from netie_control.app import FORBIDDEN, create_app
from netie_control.sources import Reading, loopback_get_json, spaceship_host_view


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
        lambda: Reading.unreachable("gh issue list", "test: gh not run"),
    )
    monkeypatch.setattr(
        sources,
        "crew_belt_view",
        lambda: Reading.unreachable("http://127.0.0.1:8020/v1/belt", "test: no live Crew"),
    )
    monkeypatch.setattr(
        sources,
        "crew_health_view",
        lambda: Reading.unreachable(
            "http://127.0.0.1:8020/crew/health", "test: no live Crew health"
        ),
    )
    monkeypatch.setattr(
        sources,
        "kb_view",
        lambda: Reading.unreachable("http://127.0.0.1:8030/healthz", "test: no live KB"),
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
    assert "checking GET /v1/gate" in page
    assert 'id="gateBody"' in page
    assert "fetch(\"/v1/gate\")" in page
    assert 'id="gateBanner">Estate gate PASSES' not in page
    assert 'class="banner ok" id="gateBanner"' not in page


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


def test_unreachable_cortex_never_renders_as_up(client: TestClient) -> None:
    page = client.get("/").text
    assert "Cortex is up" not in page
    assert "Could not read this source" in page
    assert "test: no live Cortex" in page


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
            },
        ),
    )
    page = client.get("/").text
    assert "Crew conveyor (display-only)" in page
    assert "chore ci" in page
    assert "does not converse" in page
    assert "dag_runner" not in page
    assert "<form" not in page.lower()
    assert "Crew surface" in page
    assert "http://127.0.0.1:8020" in page


def test_unreachable_crew_belt_is_stated(client: TestClient) -> None:
    page = client.get("/").text
    assert "Crew conveyor (display-only)" in page
    assert "test: no live Crew" in page
    assert "Crew surface" in page


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
            },
        ),
    )
    page = client.get("/").text
    assert "uacc" in page
    assert "will not set the flag" in page
    assert "does not arm UACC" in page
    assert "does not bypass OS permission" in page
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
        "provider": {"label": "x", "model": "y", "token": "must-not-copy"},
    }
    slim = slim_crew_health(fat)
    row = slim["mcp"][0]
    assert "tools" not in row
    assert "token" not in (slim.get("provider") or {})
    assert slim["openvault_ok"] is True
    assert row["name"] == "uacc"


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
    assert "test: no live Claude pads" in page
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
        lambda: Reading(
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
    assert "https://github.com/Netie-AI/dms/issues/61" in page
    assert ">Open</a>" in page
    assert ">Comment</a>" in page
    assert "dms#61" in page
    assert "blocked" in page
    assert "<form" not in page.lower()


def test_board_defaults_include_control_repo() -> None:
    from netie_control.sources import BOARD_REPOS

    assert "Netie-AI/netie-control" in BOARD_REPOS
    assert "Netie-AI/dms" in BOARD_REPOS


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
        lambda: Reading(
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


def test_v1_contract_is_display_only_and_does_not_assign(client: TestClient) -> None:
    body = client.get("/v1/contract").json()
    assert body["ok"] is True
    assert body["display_only"] is True
    assert body["run_owner"] == "Cortex"
    assert body["assign_owner"] == "GitHub Issues + CLAIMS.json"
    assert any(u.endswith("/v1/pickup") for u in body["before_seating"])
    assert "/v1/run" in body["forbidden"]
    page = client.get("/").text
    assert 'class="howto"' in page
    assert "Every agent" in page
    assert "GET /v1/contract" in page
    assert client.post("/v1/contract", json={"assign": "me"}).status_code != 200
    assert client.post("/v1/run").status_code == 405


def test_agents_md_is_the_seating_contract_for_every_runtime() -> None:
    text = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_text(encoding="utf-8")
    assert "GET http://127.0.0.1:8040/v1/contract" in text
    assert "/v1/pickup" in text
    assert "Control does not assign" in text
    assert "405" in text
    assert "Grok Bot" in text
    assert "Claude" in text
    claude = (Path(__file__).resolve().parents[1] / "CLAUDE.md").read_text(encoding="utf-8")
    assert "public" in claude.lower()
    assert "AGENTS.md" in claude
