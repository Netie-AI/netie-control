"""Load: forty tabs hitting the desk at once must cost bounded upstream work.

End to end through the real app. Every upstream is stubbed and made slow (0.2s) so
the requests overlap; the stubs count what reaches gh and the loopback peers.
"""

from __future__ import annotations

import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from netie_control import imprint, sources
from netie_control.app import app

SLOW_S = 0.2
ROUTES = ("/v1/ops", "/v1/board", "/v1/coordinate", "/")
TABS = 40


def _stub_upstreams(monkeypatch, tmp_path) -> dict[str, int]:
    # imprint.read() is process-cached and shells out to git through the same
    # subprocess module; warm it for real first so the stub cannot poison it.
    imprint.read()
    counts = {"gh": 0, "loopback": 0}
    lock = threading.Lock()

    def bump(key: str) -> None:
        with lock:
            counts[key] += 1

    def fake_run(argv, *a, **k):
        if argv and argv[0] == "gh":
            bump("gh")
        time.sleep(SLOW_S)
        return subprocess.CompletedProcess(argv, 0, stdout="[]", stderr="")

    def fake_probe(url, *a, **k):
        bump("loopback")
        time.sleep(SLOW_S)
        return sources.Reading.unreachable(url, "stubbed: peer down")

    monkeypatch.setattr(sources.subprocess, "run", fake_run)
    monkeypatch.setattr(sources, "loopback_get_json", fake_probe)
    monkeypatch.setattr(sources, "loopback_get_status", fake_probe)
    monkeypatch.setattr(sources, "AGENTS", tmp_path)
    return counts


def _burst(client: TestClient) -> list:
    barrier = threading.Barrier(TABS)

    def tab(i: int):
        barrier.wait(5)
        path = ROUTES[i % len(ROUTES)]
        return path, client.get(path)

    with ThreadPoolExecutor(max_workers=TABS) as pool:
        return list(pool.map(tab, range(TABS)))


def test_forty_tabs_cost_one_board_fanout(monkeypatch, tmp_path) -> None:
    counts = _stub_upstreams(monkeypatch, tmp_path)
    client = TestClient(app)

    # Baselines, each taken alone on a cold cache.
    sources.clear_shared_reads()
    alone = sources.board()
    one_board_gh = counts["gh"]
    assert one_board_gh > 0

    # Empty-but-successful gh: board says ok with empty rows and nothing unreachable.
    # That is honest (gh answered, there is nothing open), not a painted green.
    assert alone.ok is True
    assert alone.data["unreachable"] == []
    assert alone.data["open"] == [] and alone.data["prs"] == [] and alone.data["actions"] == []

    sources.clear_shared_reads()
    counts["loopback"] = 0
    sources.cortex_view()
    one_cortex = counts["loopback"]
    assert one_cortex > 0

    # One sequential pass over every route: what a single tab costs in probes.
    sources.clear_shared_reads()
    counts["loopback"] = 0
    for path in ROUTES:
        assert client.get(path).status_code == 200
    one_pass_loopback = counts["loopback"]

    sources.clear_shared_reads()
    counts["gh"] = 0
    counts["loopback"] = 0
    started = time.monotonic()
    results = _burst(client)
    elapsed = time.monotonic() - started

    assert all(r.status_code == 200 for _, r in results), [
        (p, r.status_code) for p, r in results if r.status_code != 200
    ]
    assert counts["gh"] <= one_board_gh, (
        f"{counts['gh']} gh calls for {TABS} tabs; one board fan-out is {one_board_gh}"
    )
    # Every probe is shared_read(0) and every stubbed peer is down, so an unread
    # result is never kept: a tab arriving after a leader finished reads again.
    # With the barrier all tabs overlap one 0.2s window, so the ideal is one pass.
    # Allow two passes' worth for stragglers (thread start / portal setup can land
    # a tab just after a leader finishes). Uncoalesced, 40 tabs cost ~20 passes.
    assert counts["loopback"] <= 2 * one_pass_loopback, (
        f"{counts['loopback']} probes; one pass is {one_pass_loopback}, "
        f"one cortex_view is {one_cortex}"
    )

    for path, r in results:
        if path == "/":
            continue  # HTML; its status is asserted above, its JSON twins below.
        body = r.json()
        if path == "/v1/board":
            assert body["ok"] is True and body["data"]["unreachable"] == []
            assert body["data"]["open"] == []
        elif path == "/v1/ops":
            fleet = body["data"]["fleet"]
            assert fleet["ok"] is False and fleet["detail"], "missing CLAIMS must read unread"
        elif path == "/v1/coordinate":
            lanes = {lane["id"]: lane for lane in body["data"]["lanes"]}
            for peer in ("run", "talk", "sidecar", "skills", "keys"):
                assert lanes[peer]["live"] is False, f"{peer} is down but painted live"
    print(
        f"gh={counts['gh']} (one board={one_board_gh}) loopback={counts['loopback']} "
        f"(one pass={one_pass_loopback}, one cortex_view={one_cortex}) burst={elapsed:.2f}s"
    )

