"""Shared reads must not leak between tests. Each test mocks its own sources."""

from __future__ import annotations

import pytest

from netie_control import sources


@pytest.fixture(autouse=True)
def _fresh_shared_reads():
    sources.clear_shared_reads()
    yield
    sources.clear_shared_reads()
