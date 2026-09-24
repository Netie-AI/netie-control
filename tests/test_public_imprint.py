"""The public Pages board says which commit built it, or says it cannot."""

from __future__ import annotations

from netie_control import imprint, publish_board
from netie_control.render import public_board_page
from netie_control.sources import Reading, issues_from_gh_search

SHA = "0123456789abcdef0123456789abcdef01234567"
BUILD = {"commit": SHA, "built": None, "dirty": False, "source": "git checkout, not a built wheel"}


def _reading() -> Reading:
    return Reading(
        ok=True,
        source="gh search issues",
        data=issues_from_gh_search(
            [
                {
                    "number": 11,
                    "title": "org board",
                    "url": "https://github.com/Netie-AI/netie-control/issues/11",
                    "labels": [],
                    "repository": {"nameWithOwner": "Netie-AI/netie-control"},
                }
            ]
        ),
    )


def test_public_board_page_shows_build_commit() -> None:
    html = public_board_page(_reading().to_dict(), built_at="2026-09-24 00:00 UTC", build=BUILD)
    assert f"Build <code>{SHA[:12]}</code>" in html
    assert SHA[12:] not in html


def test_public_board_page_without_build_states_absence() -> None:
    html = public_board_page(_reading().to_dict(), built_at="2026-09-24 00:00 UTC")
    assert "Build unknown: build imprint not given to this page." in html
    assert "Build <code>" not in html


def test_publish_board_main_writes_build_line(tmp_path, monkeypatch) -> None:
    imprint.read.cache_clear()
    monkeypatch.setattr(publish_board, "board", lambda *a, **k: _reading())
    monkeypatch.setattr(imprint, "read", lambda: dict(BUILD))
    dest = tmp_path / "index.html"
    assert publish_board.main([str(dest)]) == 0
    text = dest.read_text(encoding="utf-8")
    assert f"Build <code>{SHA[:12]}</code>" in text
    assert "git checkout, not a built wheel" in text
