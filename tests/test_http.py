"""HTTP transport: compress the page, and never let a browser or proxy cache display truth."""

from __future__ import annotations

import gzip

import pytest
from fastapi.testclient import TestClient

from netie_control import sources
from netie_control.app import create_app
from netie_control.sources import Reading
from tests.test_control_stays_plane_4 import _quiet_peer_probes  # noqa: F401  autouse fixture


@pytest.fixture(autouse=True)
def _quiet_ops(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "ops_view", lambda: Reading.unreachable("ops", "test: no live ops"))


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def _wire(client: TestClient, path: str) -> tuple[dict[str, str], bytes]:
    """Raw bytes as sent, before httpx transparently decodes gzip."""
    with client.stream("GET", path, headers={"Accept-Encoding": "gzip"}) as r:
        assert r.status_code == 200
        return dict(r.headers), b"".join(r.iter_raw())


def test_index_is_gzipped_and_decompresses_to_the_page(client: TestClient) -> None:
    headers, body = _wire(client, "/")
    assert headers.get("content-encoding") == "gzip"
    page = gzip.decompress(body)
    assert b"Holds no keys" in page
    assert len(body) < len(page) / 2


def test_small_response_is_not_gzipped(client: TestClient) -> None:
    headers, body = _wire(client, "/healthz")
    assert len(body) < 1024
    assert "content-encoding" not in headers
    assert b'"status":"ok"' in body


@pytest.mark.parametrize("path", ["/", "/v1/ops"])
def test_display_is_no_store(client: TestClient, path: str) -> None:
    r = client.get(path)
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-store"


def test_refusal_still_405(client: TestClient) -> None:
    r = client.post("/v1/run")
    assert r.status_code == 405
    assert r.json()["owner"]
    assert r.headers.get("cache-control") == "no-store"
