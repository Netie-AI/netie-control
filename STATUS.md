# STATUS.md - Netie Control

**Last updated:** 2026-09-03
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
| Cortex first page | GET loopback `/health` + activity + features in one pool (1.5s). Hero with OpenVault. Hung activity is workflow unread, not idle. Hung features named. Unreachable never "Cortex is up" |
| OpenVault liveness | GET `/api/healthz` + `/api/usage` + free register + ship + `:3010` playground in parallel (1.5s). Display only. `priced=false`. No invented prices. Control does not start `:3010` |
| Pointer | `GET /v1/pointer` confirm-gate from `plan-guard.js`. Process present/absent only. Does not start Electron |
| Crew conveyor | Display-only. Probes Crew `/v1/belt` and `/crew/belt` (1.5s). Belt skipped Cortex ping is named skip, not a hung ping. Idle names wakes none. Converse stays on Crew. Control does not POST wakes or approve. Hung `:8020` falls through to engine `:8023` |
| CI | `.github/workflows/ci.yml` - ruff + pytest. Remote still unpushed |
| Fleet view | Crew `/crew/health` (engine_ok named, never dropped) + KB `/healthz` + OpenVault custody copy. Display only |
| Who/where | CLAIMS kanban + lane guess + live Claude pads (`GET /v1/pads`) + tasklist + parsed RUNTIME. `GET /v1/fleet` |
| Chrome | Rail + inspector + kanban. Unread live-dot is warn, not mint. Strip unread is not `?`. Guaca/Rakazo tokens. Not Plane source, not Paperclip React |
| YOU desk | Numbered HITL with GitHub URLs. HT1/HT2 HUMAN_STOP. Step 8: founder binds live `:8020` to engine Crew. No invented prices or host URLs. `GET /v1/you` |
| Pickup tray | Unseated CLAIMS first. Board overlay 1.5s. Live issues stay `GET /v1/board`. Display only |
| Incomplete plans | `GET /v1/plans` analog remaining + parked lots. Display only. Does not unpark |
| Grok/Crew pastes | `GET /v1/prompts` paste-ready grok-master + 7 writer briefs. WIP cap 2. Display only. Does not spawn |
| Coordinate map | Numbered invoke lanes. `crew-bind` never green. Poll names chips unread; does not idle-wipe SSR workers. Talk = `/crew/wakes` in the peer pool (named source is wakes). GET `/` talk+health one pool. Pads live hop is `GET /v1/pads`. Live hops throw on HTTP error so FastAPI 404 cannot paint as a reading. Panel counts unread not ?. No spawn |
| Agent contract | `AGENTS.md` + `GET /v1/contract`. before_seating includes `/v1/coordinate`. Desk names crew_belt and openvault waits. No assign POST |
| Estate gate | Desk paints first (`GET /v1/gate not yet`, not checking). Live verdict is `GET /v1/gate`. Banner stays UNKNOWN until then |
| Gh board | Desk paints first. Live issues are `GET /v1/board` (4s). Hung gh named unread. Pickup overlay 1.5s. Favicon 204 |
| Cortex governance | Displays `activity.governance` window (refusals, bound session ids). No ledger scrape |
| Spaceship host | Display `SHIP_SPACESHIP.md`. Reopen Hosting Manager. No passwords. Do not buy New hosting |

## Open next

| ID | Work |
|----|------|
| **NEEDS-YOU** | Lift `dms#61` in `FLEET.md`. The PR is MERGED. Gate still HOLD_MISSING |
| **NEEDS-YOU** | Bind live `:8020` to `python -m CortexOS.crew` from `D:\Cortex`. Agents must not start or kill that process (R-0015). Disk YOU step 8 + coordinate `crew-bind` (`live` false) + strip crew-belt cell. |
| **NEEDS-YOU** | Point **work.netie.ai** at this box (tunnel / Access), then `/healthz` |
| **NEEDS-YOU** | Answer **F36** (extract vs live federation) and **F45** (insights epic). Both park finished, green dms branches. YOU steps 2 and 3 link them |
| Not built | Launchers unwired (P-CTL-2: desk names cwd, does not execute) |
| Charter | Crew converse inside Control still needs NETIE.md display-launch-converse (DR-PROPOSED). Toolbar launches `:8020` in a new tab. No iframe. Belt display is shipped |

## What this does NOT claim

Not an engine, vault, router, or third orchestrator. Four routes still 405.
Goal stays open. Cortex internals and Crew host are built; converse-in-Control is not.
