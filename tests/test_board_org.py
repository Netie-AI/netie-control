"""Org-wide board is regex + gh search, not a frozen four-repo list."""

from __future__ import annotations

import json
import subprocess

from netie_control.sources import (
    BOARD_OWNER,
    BOARD_SEARCH_LIMIT,
    board_repo_allowed,
    issues_from_gh_search,
    pickup_tray,
)


def test_board_repo_regex_allows_work_trees_and_denies_noise() -> None:
    for repo in (
        "Netie-AI/netie-control",
        "Netie-AI/dms",
        "Netie-AI/Cortex",
        "Netie-AI/OpenVault",
        "Netie-AI/Pointer",
        "Netie-AI/landing",
        "Netie-AI/Space",
        "Netie-AI/constructor",
        "Netie-AI/Netie-KB",
    ):
        assert board_repo_allowed(repo), repo
    assert not board_repo_allowed("Netie-AI/demo-repository")
    assert not board_repo_allowed("other/Cortex")
    assert not board_repo_allowed("Netie-AI/Cortex/extra")


def test_issues_from_gh_search_keeps_other_repos_and_names_deny() -> None:
    payload = [
        {
            "number": 66,
            "title": "EPIC-P10",
            "url": "https://github.com/Netie-AI/Pointer/issues/66",
            "labels": [{"name": "epic"}],
            "repository": {"nameWithOwner": "Netie-AI/Pointer"},
        },
        {
            "number": 6,
            "title": "contact 404",
            "url": "https://github.com/Netie-AI/landing/issues/6",
            "labels": [],
            "repository": {"nameWithOwner": "Netie-AI/landing"},
        },
        {
            "number": 1,
            "title": "noise",
            "url": "https://github.com/Netie-AI/demo-repository/issues/1",
            "labels": [],
            "repository": {"nameWithOwner": "Netie-AI/demo-repository"},
        },
    ]
    data = issues_from_gh_search(payload, limit=100)
    hrefs = [row["url"] for row in data["items"]]
    assert "https://github.com/Netie-AI/Pointer/issues/66" in hrefs
    assert "https://github.com/Netie-AI/landing/issues/6" in hrefs
    assert all("demo-repository" not in url for url in hrefs)
    assert "Netie-AI/demo-repository" in data["skipped"]
    assert data["truncated"] is False
    assert data["query"] == f"owner:{BOARD_OWNER} is:open"
    assert data["items"][0]["is_epic"] is True


def test_issues_from_gh_search_names_truncation_at_cap() -> None:
    payload = [
        {
            "number": i,
            "title": f"t{i}",
            "url": f"https://github.com/Netie-AI/Cortex/issues/{i}",
            "labels": [],
            "repository": {"nameWithOwner": "Netie-AI/Cortex"},
        }
        for i in range(1, BOARD_SEARCH_LIMIT + 1)
    ]
    data = issues_from_gh_search(payload, limit=BOARD_SEARCH_LIMIT)
    assert data["truncated"] is True
    assert data["shown"] == BOARD_SEARCH_LIMIT
    assert data["cap"] == BOARD_SEARCH_LIMIT


def test_pickup_tray_does_not_silent_cap_at_forty() -> None:
    board_items = [
        {
            "repo": "Netie-AI/Pointer",
            "number": n,
            "title": f"p{n}",
            "url": f"https://github.com/Netie-AI/Pointer/issues/{n}",
        }
        for n in range(1, 46)
    ]
    tray = pickup_tray({"rows": []}, {"items": board_items})
    assert tray["count"] == 45
    assert len(tray["items"]) == 45
    assert tray["truncated"] is False


def test_board_calls_gh_search_owner_not_four_repo_list(monkeypatch) -> None:
    from netie_control import sources

    seen: dict[str, object] = {}

    def fake_hidden(argv: object, **_k: object) -> subprocess.CompletedProcess[str]:
        seen["argv"] = argv
        body = json.dumps(
            [
                {
                    "number": 11,
                    "title": "org board",
                    "url": "https://github.com/Netie-AI/netie-control/issues/11",
                    "labels": [],
                    "repository": {"nameWithOwner": "Netie-AI/netie-control"},
                }
            ]
        )
        return subprocess.CompletedProcess(argv, 0, body, "")  # type: ignore[arg-type]

    monkeypatch.setattr(sources, "_run_hidden", fake_hidden)
    reading = sources.board(timeout=1)
    argv = list(seen.get("argv") or [])
    assert argv[:3] == ["gh", "search", "issues"]
    assert "--owner" in argv and "Netie-AI" in argv
    assert "--repo" not in argv
    assert reading.ok is True
    assert reading.source == "gh search issues"
    assert reading.data["items"][0]["number"] == 11


def test_public_board_page_is_display_only_and_lists_other_repos() -> None:
    from netie_control.render import public_board_page
    from netie_control.sources import issues_from_gh_search

    data = issues_from_gh_search(
        [
            {
                "number": 66,
                "title": "EPIC-P10",
                "url": "https://github.com/Netie-AI/Pointer/issues/66",
                "labels": [{"name": "epic"}],
                "repository": {"nameWithOwner": "Netie-AI/Pointer"},
            }
        ]
    )
    html = public_board_page(
        {"ok": True, "source": "gh search issues", "detail": "", "data": data},
        built_at="2026-09-11 06:00 UTC",
    )
    assert "Pointer#66" in html
    assert "EPIC-P10" in html
    assert "does not assign" in html
    assert "<form" not in html.lower()
    assert "F-0030" in html
    unread = public_board_page(
        {"ok": False, "source": "gh search issues", "detail": "hung", "data": None}
    )
    assert "Board unread" in unread
    assert "hung" in unread


def test_publish_board_writes_html(tmp_path, monkeypatch) -> None:
    from netie_control import publish_board, sources
    from netie_control.sources import Reading, issues_from_gh_search

    monkeypatch.setattr(
        sources,
        "board",
        lambda *a, **k: Reading(
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
        ),
    )
    dest = tmp_path / "index.html"
    assert publish_board.main([str(dest)]) == 0
    text = dest.read_text(encoding="utf-8")
    assert "netie-control#11" in text
    assert (tmp_path / ".nojekyll").is_file()
