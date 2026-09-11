# STATUS.md - Netie Control

**Last updated:** 2026-09-11
**Remote:** public https://github.com/Netie-AI/netie-control
**Plane:** 4 - operator shell

## Direct interact

```powershell
python -m uvicorn netie_control.app:app --port 8040   # then http://127.0.0.1:8040
python -m pytest D:\NetieControl\tests -q
```

## Shipped / verified

| ID | Result |
|----|--------|
| First slice | Gate, RUNTIME, CLAIMS, gh board. 405s. No keys. R-0015. Unknown never green |
| Cortex first page | GET loopback `/health` + activity + features in one pool (1.5s). Hero with OpenVault. Hung unread named |
| OpenVault liveness | GET `/api/healthz` + `/api/usage` in parallel (1.5s). Display only. `priced=false` |
| Crew conveyor | Display-only `/v1/belt`. Converse stays Crew. Hung `:8020` falls through to `:8023` |
| CI | `ci.yml` ruff+pytest. `board.yml` regex tests + hourly GitHub Pages census |
| Fleet / YOU | CLAIMS kanban + pads + RUNTIME. YOU HITL. HT1/HT2 HUMAN_STOP. `GET /v1/you` |
| Pickup | Unseated CLAIMS first. Org board overlay 1.5s. No silent 40-cap. Display only |
| Coordinate | Invoke map. `crew-bind` never green. Talk = `/crew/wakes`. Sidecar `:8023` |
| Display GETs | `/v1/plans` `/v1/prompts` `/v1/fetch` `/v1/sidecar` `/v1/launchers` `/v1/ops` (15s poll) |
| Gh board | Owner-wide `gh search` + regex. Slices: open/completed/PRs/Actions. Pages hourly |
| Contract | `AGENTS.md` + `GET /v1/contract`. before_seating includes `/v1/board`. No assign POST |
| Estate gate | Desk paints first. Live verdict `GET /v1/gate`. UNKNOWN until then |

## Open next

| ID | Work |
|----|------|
| **NEEDS-YOU** | Lift `dms#61` in `FLEET.md`. PR MERGED. Gate still HOLD_MISSING |
| **NEEDS-YOU** | Bind live `:8020` to `python -m CortexOS.crew` from `D:\Cortex` (R-0015) |
| **NEEDS-YOU** | Point **work.netie.ai** at this box, then `/healthz` |
| **NEEDS-YOU** | Answer **F36** and **F45**. YOU steps 2 and 3 link them |
| Not built | Launchers unwired (P-CTL-2). Issue #5 stays OPEN |
| Charter | Crew converse inside Control still needs NETIE.md display-launch-converse |

## What this does NOT claim

Not an engine, vault, router, or third orchestrator. Four routes still 405.
not Paperclip React. Not a Crew composer copy. Goal stays open.
