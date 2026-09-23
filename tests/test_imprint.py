"""The shell says which code it is serving, and never invents it."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from netie_control import imprint
from netie_control.app import app


@pytest.fixture(autouse=True)
def _fresh_imprint():
    imprint.read.cache_clear()
    yield
    imprint.read.cache_clear()


def test_wheel_imprint_wins(monkeypatch, tmp_path) -> None:
    path = tmp_path / "_imprint.json"
    monkeypatch.setattr(imprint, "IMPRINT_PATH", path)
    imprint.write("a" * 40)
    blob = json.loads(path.read_text())
    assert blob["commit"] == "a" * 40 and blob["built"]
    got = imprint.read()
    assert got["commit"] == "a" * 40
    assert got["source"] == "wheel imprint"
    assert got["dirty"] is False


def test_write_refuses_a_non_sha(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(imprint, "IMPRINT_PATH", tmp_path / "_imprint.json")
    with pytest.raises(SystemExit):
        imprint.write("main")
    assert not (tmp_path / "_imprint.json").exists()


def test_git_checkout_fallback_names_itself(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(imprint, "IMPRINT_PATH", tmp_path / "missing.json")
    answers = {"rev-parse": "b" * 40, "status": " M app.py"}
    monkeypatch.setattr(imprint, "_git", lambda *argv: answers[argv[0]])
    got = imprint.read()
    assert got["commit"] == "b" * 40
    assert got["dirty"] is True
    assert "not a built wheel" in got["source"]


def test_unimprinted_is_stated_and_page_says_unknown(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(imprint, "IMPRINT_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(imprint, "_git", lambda *argv: None)
    client = TestClient(app)
    build = client.get("/healthz").json()["build"]
    assert build["commit"] is None
    assert build["source"].startswith("unimprinted")
    assert "Build unknown: unimprinted" in client.get("/").text


def test_page_footer_shows_short_commit(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(imprint, "IMPRINT_PATH", tmp_path / "_imprint.json")
    imprint.write("c" * 40)
    page = TestClient(app).get("/").text
    assert "Build <code>cccccccccccc</code> (wheel imprint, built " in page
