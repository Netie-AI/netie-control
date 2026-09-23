"""Scale: many tabs must share one slow read, and a shared read must say how old it is."""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from netie_control import sources
from netie_control.app import app


def test_concurrent_callers_share_one_read() -> None:
    calls = []
    gate = threading.Event()

    @sources.shared_read(0)
    def slow() -> sources.Reading:
        calls.append(1)
        gate.wait(2)
        return sources.Reading(ok=True, data={"n": 1}, source="slow")

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(slow) for _ in range(8)]
        time.sleep(0.2)
        gate.set()
        results = [f.result() for f in futs]

    assert len(calls) == 1
    assert all(r.ok and r.data == {"n": 1} for r in results)
    fresh = [r for r in results if r.age_s is None]
    assert len(fresh) == 1, "only the caller who ran the read gets it unaged"


def test_ttl_zero_does_not_reuse_a_finished_read() -> None:
    calls = []

    @sources.shared_read(0)
    def read() -> sources.Reading:
        calls.append(1)
        return sources.Reading(ok=True, data=len(calls), source="x")

    assert read().data == 1
    assert read().data == 2


def test_ttl_reuses_and_names_age_then_expires() -> None:
    calls = []

    @sources.shared_read(0.3)
    def read() -> sources.Reading:
        calls.append(1)
        return sources.Reading(ok=True, data=len(calls), source="x")

    first = read()
    second = read()
    assert first.age_s is None
    assert second.data == 1
    assert second.age_s is not None and second.to_dict()["age_s"] == second.age_s
    assert "age_s" not in first.to_dict()
    time.sleep(0.35)
    assert read().data == 2


def test_errors_reach_every_caller_and_are_not_kept() -> None:
    calls = []

    @sources.shared_read(60)
    def boom() -> sources.Reading:
        calls.append(1)
        raise RuntimeError("gh exploded")

    for _ in range(2):
        with pytest.raises(RuntimeError, match="gh exploded"):
            boom()
    assert len(calls) == 2


def test_arguments_are_separate_reads() -> None:
    @sources.shared_read(60)
    def read(x: int) -> sources.Reading:
        return sources.Reading(ok=True, data=x, source="x")

    assert read(1).data == 1
    assert read(2).data == 2


def test_board_route_and_panel_show_shared_age(monkeypatch) -> None:
    runs = []

    def fake_search(*, closed: bool, timeout: float):
        runs.append(closed)
        return [], "", False

    monkeypatch.setattr(sources, "_owner_search_issues", fake_search)
    monkeypatch.setattr(sources, "_owner_search_prs", lambda *, timeout: ([], ""))
    monkeypatch.setattr(sources, "list_board_repos", lambda *, timeout: ([], ""))
    client = TestClient(app)
    first = client.get("/v1/board").json()
    second = client.get("/v1/board").json()
    assert first["age_s"] is None
    assert second["age_s"] is not None
    assert second["ttl_s"] == sources.BOARD_TTL_S
    assert len(runs) == 2, "one open + one completed search, not repeated per request"
    # The panel is client-side JS; without a browser, assert the page ships the age line.
    page = client.get("/").text
    assert "b.age_s != null" in page and "Shared read, taken" in page


def test_estate_gate_is_never_served_from_a_finished_run(monkeypatch, tmp_path) -> None:
    (tmp_path / "estate_gate.py").write_text("")
    monkeypatch.setattr(sources, "AGENTS", tmp_path)
    runs = []

    class Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(*a, **k):
        runs.append(1)
        return Proc()

    monkeypatch.setattr(sources.subprocess, "run", fake_run)
    assert sources.estate_gate().age_s is None
    assert sources.estate_gate().age_s is None
    assert len(runs) == 2


def test_spaceship_host_view_has_no_password_on_fixture(monkeypatch, tmp_path) -> None:
    """CI has no D: drive. Run the no-password check on a fixture instead of skipping."""
    (tmp_path / "SHIP_SPACESHIP.md").write_text(
        "| host | 209.74.68.17 |\n| ftp user | ship@netie.ai |\nFTP_PASS=hunter2\n"
    )
    monkeypatch.setattr(sources, "AGENTS", tmp_path)
    reading = sources.spaceship_host_view()
    assert reading.ok
    blob = json.dumps(reading.data)
    assert "FTP_PASS" not in blob
    assert "hunter2" not in blob
    assert reading.data["ftp_user"] == "ship@netie.ai"
    assert "hosting-manager" in reading.data["hosting_manager"]


def test_unread_readings_are_not_kept() -> None:
    calls = []

    @sources.shared_read(60)
    def read() -> sources.Reading:
        calls.append(1)
        return sources.Reading.unreachable("gh", "gh not found")

    read()
    read()
    assert len(calls) == 2


def _js_function(page: str, name: str) -> str:
    """Cut one top-level JS function out of the rendered page by brace matching."""
    start = page.index(f"function {name}(")
    depth = 0
    for i in range(page.index("{", start), len(page)):
        depth += {"{": 1, "}": -1}.get(page[i], 0)
        if depth == 0:
            return page[start : i + 1]
    raise AssertionError(f"unbalanced function {name}")


def test_board_panel_keeps_truncated_and_unreachable_notes() -> None:
    """Both notices are real states. One must not erase the other (was `extra =`)."""
    import shutil
    import subprocess

    node = shutil.which("node")
    assert node, "node is required to run the page's own boardHtml; install it"
    page = TestClient(app).get("/").text
    script = "\n".join(
        [
            _js_function(page, "esc"),
            _js_function(page, "boardHtml"),
            "function ticketCardHtml(){return ''} function absentHtml(){return 'ABSENT'}",
            (
                "process.stdout.write(boardHtml({ok:true,data:{truncated:true,shown:100,cap:100,"
                "unreachable:['prs hung'],items:[]}}));"
            ),
        ]
    )
    out = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=20, check=False
    )
    assert out.returncode == 0, out.stderr
    assert "Truncated: showing 100" in out.stdout
    assert "Not shown, unreachable: prs hung" in out.stdout


def test_concurrent_page_loads_share_one_peer_probe(monkeypatch) -> None:
    calls = []
    lock = threading.Lock()

    def slow_probe(url: str, timeout: float = 2.0) -> sources.Reading:
        with lock:
            calls.append(url)
        time.sleep(0.3)
        return sources.Reading.unreachable(url, "test: nothing listening")

    monkeypatch.setattr(sources, "loopback_get_json", slow_probe)
    sources.cortex_view()
    single = len(calls)
    assert single > 0
    calls.clear()
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda _: sources.cortex_view(), range(5)))
    assert len(calls) == single, f"5 callers made {len(calls)} probes, one read makes {single}"
