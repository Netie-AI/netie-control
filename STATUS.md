# STATUS.md - Netie Control

**Last updated:** 2026-08-25
**Remote:** not yet pushed
**Plane:** 4 - operator shell

## Direct interact

```powershell
python -m uvicorn netie_control.app:app --port 8040   # then http://127.0.0.1:8040
python -m pytest D:\NetieControl\tests -q
```

## Shipped / verified

| ID | Result |
|----|--------|
| First slice | Operator page reading FOUR real sources: the estate gate (run live, not cached), the watchdog RUNTIME view, the CLAIMS board, and the open epic/ticket board via `gh`. **25 tests pass** |
| Plane guardrails | `/v1/secrets`, `/v1/route`, `/v1/goal`, `/v1/run` answer **405 with the owner named**, on every verb. 405 not 404 - 404 says "no such thing" and invites someone to build it |
| No key material | Asserted on the **source**, not at runtime: a key behind a config branch would pass a runtime probe |
| R-0015 | A test fails if any launcher targets Grok Bot, Cursor, or any desktop app |
| Honest absence | An unreachable source renders its reason and its path. Two tests assert an unreadable gate never renders as a pass (R-0011) |
| Live proof | On first run the page showed `GATE FAIL - HOLD_MISSING Netie-AI/dms#61`, which is real and current |

## Open next

| ID | Work |
|----|------|
| **NEEDS-YOU** | **Lift or update the `dms#61` hold in `FLEET.md`.** The estate gate FAILS on it, and under FLEET.md no writer may be seated while it does. It reads HOLD_MISSING because that PR was merged while held - see CHANGELOG |
| Not built | Cortex internals are named as the first page in NETIE.md section 3 but are **not** rendered yet: no live runs, no ledger view, no manifest or refusal view, no degradation banner. Today's first page is the gate and the board |
| Not built | OpenVault/FreeRoute route and budget status. Control may **display** these; the reader does not exist |
| Not built | Launchers are **declared and rendered, not wired**. Clicking one does nothing - there is no execution path yet, deliberately, because launching needs an auth story Control does not have |
| No CI | No workflow, no remote. Tests pass locally only |
| Not verified | Never run against a live Cortex. The gate and board readers are exercised against the real estate; the Cortex reader does not exist to be exercised |

## What this does NOT claim

It is not an engine, a key vault, a route picker, or a third orchestrator, and four
routes refuse in order to keep that true rather than merely stated.
