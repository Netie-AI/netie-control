"""Scale: every open tab polls /v1/ops. Concurrent readers must share one file read.

Deterministic: the leader's read is held until every follower is provably parked on
the leader's flight, so no sleep decides who leads.
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from netie_control import sources
from netie_control.app import app

CALLERS = 5


class _CountingEvent(threading.Event):
    waiting = 0
    lock = threading.Lock()

    def wait(self, timeout=None):
        with _CountingEvent.lock:
            _CountingEvent.waiting += 1
        return super().wait(timeout)


class _CountingFlight(sources._Flight):
    def __init__(self) -> None:
        super().__init__()
        self.done = _CountingEvent()


def _setup(monkeypatch, tmp_path) -> tuple[list[str], threading.Event]:
    (tmp_path / "CLAIMS.json").write_text(json.dumps({"tickets": []}), encoding="utf-8")
    (tmp_path / "RUNTIME.md").write_text("# RUNTIME\n", encoding="utf-8")
    monkeypatch.setattr(sources, "AGENTS", tmp_path)
    monkeypatch.setattr(
        sources, "board", lambda *a, **k: sources.Reading.unreachable("gh", "test: no gh")
    )
    monkeypatch.setattr(sources, "_Flight", _CountingFlight)
    _CountingEvent.waiting = 0
    reads: list[str] = []
    lock = threading.Lock()
    release = threading.Event()
    release.set()
    real = sources._read_text

    def gated_read(p):
        with lock:
            reads.append(str(p))
        assert release.wait(5), "test gate never opened"
        return real(p)

    monkeypatch.setattr(sources, "_read_text", gated_read)
    return reads, release


def _burst(fn, release: threading.Event) -> list[sources.Reading]:
    release.clear()
    with ThreadPoolExecutor(max_workers=CALLERS) as pool:
        futs = [pool.submit(fn) for _ in range(CALLERS)]
        for _ in range(500):
            with _CountingEvent.lock:
                if _CountingEvent.waiting >= CALLERS - 1:
                    break
            threading.Event().wait(0.01)
        release.set()
        return [f.result(timeout=10) for f in futs]


@pytest.mark.parametrize(
    "name", ["ops_view", "fleet_view", "claims_board", "runtime_view", "pickup_view"]
)
def test_concurrent_callers_share_one_file_read(monkeypatch, tmp_path, name) -> None:
    reads, release = _setup(monkeypatch, tmp_path)
    fn = getattr(sources, name)
    fn()
    single = len(reads)
    assert single > 0, f"{name} read no files; the test would prove nothing"
    reads.clear()
    _CountingEvent.waiting = 0
    results = _burst(fn, release)
    assert len(reads) == single, f"{CALLERS} {name} calls made {len(reads)} reads, one makes {single}"
    assert sum(r.age_s is None for r in results) == 1, "followers must carry age_s"


def test_after_a_finished_read_the_next_call_reads_fresh(monkeypatch, tmp_path) -> None:
    reads, _ = _setup(monkeypatch, tmp_path)
    sources.ops_view()
    first = len(reads)
    again = sources.ops_view()
    assert len(reads) == 2 * first, "ttl 0 must never serve a finished read"
    assert again.age_s is None


@pytest.mark.parametrize("path", ["/v1/ops", "/v1/fleet", "/v1/pickup"])
def test_shared_routes_report_age_s(monkeypatch, tmp_path, path) -> None:
    _setup(monkeypatch, tmp_path)
    body = TestClient(app).get(path).json()
    assert "age_s" in body, f"{path} drops age_s; a shared read would look fresh"
    assert body["age_s"] is None


def test_fleet_lane_is_not_live_when_claims_unread(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sources, "AGENTS", tmp_path)
    lanes = sources.coordinate_payload(
        cortex={}, openvault={}, crew_health={}, crew_talk={}, kb={}, surfaces={},
        claude_pads={}, fleet=sources.fleet_view().to_dict(),
    )["lanes"]
    fleet = next(lane for lane in lanes if lane["id"] == "fleet")
    assert fleet["live"] is False
    assert fleet["unread"] is True
