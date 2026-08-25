"""The constitution, as tests.

NETIE.md section 3 says Netie Control is not an engine, a key vault, a route picker, or
a third orchestrator. Written down, that is a sentence somebody can disagree with in six
months. Written as a test, it is a thing that goes red.

A capability that is merely ABSENT gets added back by the next person who needs it and
does not know why it was left out. So each forbidden capability is a route that answers
405 with its owner named, and each has an assertion here.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from netie_control.app import FORBIDDEN, create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.mark.parametrize("path", sorted(FORBIDDEN))
def test_a_forbidden_capability_answers_405_with_its_owner(client: TestClient, path: str) -> None:
    """405, not 404. 404 says 'no such thing' and invites someone to build it."""
    resp = client.get(path)

    assert resp.status_code == 405, (
        f"{path} answered {resp.status_code}. This capability belongs to another plane "
        f"and must refuse, not silently not-exist."
    )
    body = resp.json()
    assert body["code"] == "not_this_plane"
    assert body["owner"], "a refusal that does not name the owner tells nobody where to go"
    assert len(body["message"]) > 40, "the refusal must carry the reason, not just a code"


@pytest.mark.parametrize("path", sorted(FORBIDDEN))
@pytest.mark.parametrize("verb", ["post", "put", "patch", "delete"])
def test_the_refusal_holds_for_every_verb(client: TestClient, path: str, verb: str) -> None:
    """A GET that 404s while a POST 405s reads as an oversight, not a decision."""
    resp = getattr(client, verb)(path)
    assert resp.status_code == 405, f"{verb.upper()} {path} -> {resp.status_code}"


def test_control_holds_no_key_material() -> None:
    """The one non-negotiable: exactly one key vault in this company.

    Asserted on the source rather than at runtime, because a key that only appears
    under a config branch would pass a runtime probe.
    """
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parents[1] / "netie_control"
    forbidden_names = ("api_key", "apikey", "secret_key", "private_key", "OPENAI_API_KEY",
                       "ANTHROPIC_API_KEY", "keyring", "vault_write")
    offenders: list[str] = []
    for py in pkg.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#") or '"""' in stripped:
                continue
            for name in forbidden_names:
                if name in line:
                    offenders.append(f"{py.name}:{line_no} {name}")
    assert not offenders, (
        "Control must hold no key material - custody is OpenVault's, and there is "
        "exactly one vault (NETIE.md section 3):\n" + "\n".join(offenders)
    )


def test_no_launcher_touches_the_founders_desktop_software() -> None:
    """R-0015. Grok Bot, Cursor and every user-facing app open by the founder's hand."""
    from netie_control.sources import LAUNCHERS

    banned = ("grok", "cursor", "chrome.exe", "code.exe", "explorer.exe", "taskkill")
    offenders = [
        f"{launcher.name}: {' '.join(launcher.argv)}"
        for launcher in LAUNCHERS
        if any(b in " ".join(launcher.argv).lower() for b in banned)
    ]
    assert not offenders, (
        "A launcher targets the founder's desktop software. Agents never start, "
        "restart or kill it (R-0015):\n" + "\n".join(offenders)
    )


def test_an_unreachable_source_is_stated_not_blanked(client: TestClient, monkeypatch) -> None:
    """The page's whole job is 'what is actually true'. Silence is the worst answer.

    An empty panel and a healthy-but-quiet panel look identical, so the operator cannot
    tell which they are reading (R-0011).
    """
    from netie_control import sources

    monkeypatch.setattr(
        sources, "estate_gate",
        lambda: sources.Reading.unreachable("estate_gate.py", "probe: pretend it is missing"),
    )
    page = client.get("/").text

    assert "Could not read this source" in page
    assert "probe: pretend it is missing" in page
    assert "UNKNOWN" in page, "an unreadable gate must not render as a pass"


def test_the_page_never_claims_a_pass_it_did_not_read(client: TestClient, monkeypatch) -> None:
    """The failure that matters: unknown rendering as green."""
    from netie_control import sources

    monkeypatch.setattr(
        sources, "estate_gate",
        lambda: sources.Reading.unreachable("estate_gate.py", "unreachable"),
    )
    page = client.get("/").text
    assert "Estate gate PASSES" not in page


def test_healthz_says_which_plane_it_is_on(client: TestClient) -> None:
    body = client.get("/healthz").json()
    assert body["plane"] == 4
    assert body["product"] == "netie-control"
