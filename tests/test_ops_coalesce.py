"""Scale: every open tab polls /v1/ops. Concurrent polls must share one CLAIMS read."""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from netie_control import sources


def _setup(monkeypatch, tmp_path) -> list[str]:
    (tmp_path / "CLAIMS.json").write_text(json.dumps({"tickets": []}), encoding="utf-8")
    monkeypatch.setattr(sources, "AGENTS", tmp_path)
    monkeypatch.setattr(
        sources, "board", lambda *a, **k: sources.Reading.unreachable("gh", "test: no gh")
    )
    reads: list[str] = []
    lock = threading.Lock()
    real = sources._read_text

    def slow_read(p):
        with lock:
            reads.append(str(p))
        time.sleep(0.2)
        return real(p)

    monkeypatch.setattr(sources, "_read_text", slow_read)
    return reads


def test_concurrent_ops_polls_share_one_file_read(monkeypatch, tmp_path) -> None:
    reads = _setup(monkeypatch, tmp_path)
    assert sources.ops_view().data["fleet"]["ok"]
    single = len(reads)
    assert single > 0
    reads.clear()
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: sources.ops_view(), range(6)))
    assert len(reads) == single, f"6 polls made {len(reads)} reads, one poll makes {single}"
    assert all(r.data["fleet"]["ok"] for r in results)
    assert sum(r.age_s is None for r in results) == 1, "followers must carry age_s"


def test_ops_after_finished_poll_reads_fresh(monkeypatch, tmp_path) -> None:
    reads = _setup(monkeypatch, tmp_path)
    sources.ops_view()
    first = len(reads)
    again = sources.ops_view()
    assert len(reads) == 2 * first, "ttl 0 must never serve a finished read"
    assert again.age_s is None
