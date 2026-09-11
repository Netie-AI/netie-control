"""sources.py must import on Ubuntu CI. wintypes is Windows-only."""

from __future__ import annotations

import os

from netie_control import sources


def test_sources_imports_without_wintypes_at_module_level() -> None:
    import inspect

    src = inspect.getsource(sources)
    assert "from ctypes import wintypes\n" not in src.split("if os.name == \"nt\":", 1)[0]


def test_win_running_images_empty_off_windows(monkeypatch) -> None:
    monkeypatch.setattr(sources.os, "name", "posix")
    assert sources._win_running_images({"cursor.exe"}) == set()


def test_desktop_surfaces_view_does_not_need_win32() -> None:
    if os.name == "nt":
        view = sources.desktop_surfaces_view()
        assert view.ok is True
        return
    view = sources.desktop_surfaces_view()
    assert view.ok is False
    assert "unreachable" in (view.detail or "")
    assert view.data is None
