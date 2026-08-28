# STATUS.md - Netie Control

**Last updated:** 2026-08-28
**Remote:** public https://github.com/Netie-AI/netie-control
**Plane:** 4 - operator shell

## Direct interact

```powershell
python -m uvicorn netie_control.app:app --port 8040   # then http://127.0.0.1:8040
python -m pytest E:\NetieControl\tests -q
```

## Shipped / verified

| ID | Result |
|----|--------|
| First slice | Gate, RUNTIME, CLAIMS, gh board. 405s. No keys. R-0015. Unknown never green |
| Cortex first page | GET loopback `/health` + `/api/engine/activity` including `governance` (ledger tip, bound sessions, refusals). Unreachable never renders "Cortex is up". No ledger scrape |
| OpenVault liveness | GET `/api/healthz`. Display only. Page says it did not pick a route |
| Crew conveyor | Display-only panel + `GET /v1/belt` proxy of Crew JSON (`:8020`). Converse stays on Crew (NETIE.md still display-and-launch). Public name work.netie.ai is HUMAN_STOP |
| CI | `.github/workflows/ci.yml` - ruff + pytest. Remote still unpushed |
| Fleet view | Crew `/crew/health` + KB `/healthz` + OpenVault custody plugin copy. Display only |
| Who/where | CLAIMS kanban + lane guess + live Claude pads + tasklist + parsed RUNTIME. `GET /v1/fleet` |
| Chrome | Rail + inspector + kanban. Guaca/Rakazo tokens. Not Plane source, not Paperclip React |
| YOU desk | Numbered HITL with GitHub URLs. HT1/HT2 HUMAN_STOP. No invented prices or host URLs. `GET /v1/you` |
| Pickup tray | Unseated CLAIMS + open issues. `GET /v1/pickup` display only. Agents claim on GitHub |
| Agent contract | `AGENTS.md` + `GET /v1/contract`. Every lane reads Control then claims GitHub. No assign POST |
| Estate gate | Desk paints first. Live verdict is `GET /v1/gate`. Banner stays UNKNOWN until then |
| Cortex governance | Displays `activity.governance` window (refusals, bound session ids). No ledger scrape |
| Spaceship host | Display `SHIP_SPACESHIP.md`. Reopen Hosting Manager. No passwords. Do not buy New hosting |

## Open next

| ID | Work |
|----|------|
| **NEEDS-YOU** | Lift `dms#61` in `FLEET.md`. The PR is MERGED. Gate still HOLD_MISSING |
| **NEEDS-YOU** | Point **work.netie.ai** at this box (tunnel / Access), then `/healthz` |
| **NEEDS-YOU** | Answer **F36** (extract vs live federation) and **F45** (insights epic). Both park finished, green dms branches. YOU steps 2 and 3 link them |
| Not built | FreeRoute budget numbers. Launchers unwired (P-CTL-2: no principal) |
| Charter | Crew converse inside Control still needs NETIE.md display-launch-converse (DR-PROPOSED). Belt display is shipped |

## What this does NOT claim

Not an engine, vault, router, or third orchestrator. Four routes still 405.
Goal stays open. Cortex internals and Crew host are built; converse-in-Control is not.
