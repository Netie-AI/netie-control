# ACTIVE - what exists in Netie Control and where

| Path | What |
|---|---|
| `netie_control/app.py` | FastAPI app. Routes, four 405 refusals, `GET /v1/contract` `GET /v1/coordinate` `GET /v1/belt` `GET /v1/fleet` `GET /v1/you` `GET /v1/pickup` `GET /v1/gate` `GET /v1/board` `GET /v1/ops` (15s poll: board+fleet+pickup) `GET /v1/pads` `GET /v1/sidecar` `GET /v1/plans` `GET /v1/prompts` `GET /v1/fetch` `GET /v1/launchers` display proxies, Constructor sketch at `/constructor/` (missing skin is HTML 503 unread) |
| `AGENTS.md` | Seating contract for Cursor, Claude Code, Grok Bot. Same clause as CLAUDE.md operator desk |
| `netie_control/sources.py` | Read-only readers. Every one returns real data or an explicit unreachable marker. Writes nothing |
| `netie_control/render.py` | The operator page. Numbered pickup / coordinate / crew steps. An unreachable source renders its reason, never an empty panel. Live hops use `readingJson` so HTTP 404 cannot paint as a quiet reading |
| `netie_control/static/control.css` | Operator chrome. Unread live-dot is warn (`is-unread`). Guaca/Rakazo tokens, Gastown live-dots, original layout |
| `tests/test_control_stays_plane_4.py` | The constitution as tests - 405s, no key material, no desktop launcher, unknown never renders green. Talk live is `/crew/wakes`. `crew-bind` never greens. Sidecar `:8023` JSON health. |

## Reads (all read-only)

| Source | Path | Via |
|---|---|---|
| Cortex internals | `GET {NETIE_CORTEX_URL}/health` + `/api/engine/activity` + `/health/features` in one pool (`CORTEX_WAIT_S` 1.5s). Hung health does not stack a second wait. Hung activity is workflow unread, not idle workers. Hung features named | urllib, loopback only |
| OpenVault liveness | `GET {NETIE_OPENVAULT_URL}/api/healthz` and `GET /api/usage?limit=1` in parallel (`OPENVAULT_USAGE_WAIT_S` 1.5s). Slim keeps summary counts. Drops ledger rows. `priced` stays false. Control does not pick a route | urllib, loopback only |
| Spaceship host | `Internal/Agents/SHIP_SPACESHIP.md` | file read. Public facts only. No FTP password. Agents reopen Hosting Manager |
| Crew conveyor | `GET {NETIE_CREW_URL}/v1/belt` and `/crew/belt` (1.5s each). Also Control `GET /v1/belt` | urllib, loopback only. Display. No handoff POST |
| Crew laptop tools | `GET {NETIE_CREW_URL}/crew/health` (1.5s, same as belt). Slim keeps `engine_ok`. Coordinate skips this probe | urllib, loopback only. MCP name/armed/running + engine ping. Does not arm or start Cortex |
| Crew talk | `GET {NETIE_CREW_URL}/crew/wakes` (1.5s). HTML GET `/` is not enough (hung fork still serves it). GET `/` and GET `/v1/coordinate` run talk in the same pool as other peers. Coordinate still skips `/crew/health`. Wake rows (kind/state/note) paint on the coordinate panel | urllib, loopback only. Engine converse. Does not copy Crew composer |
| Sidecar host | `GET {NETIE_SIDECAR_URL}/health` then `/healthz` (1.5s, JSON). HTML GET `/` is not enough. Control `GET /v1/sidecar` | urllib, loopback only. Engine host `:8023`. Does not start or bind |
| Sidecar catalogs | Control `GET /v1/plans` `/v1/prompts` `/v1/fetch` (ids/titles). GET `/` defers them so first paint stays fast. Fetch is loopback only | urllib. Display. Control does not run a plan |
| Launchers | Control `GET /v1/launchers` lists name, cwd, argv. P-CTL-2 does not execute | declared. Click does nothing |
| Skill chest | `GET {NETIE_KB_URL}/healthz` (default `:8030`, KB_WAIT_S 1.5s). Search and in-panel item show use the same cap. Hits stay on the desk | urllib, loopback only. Counts, not a runner |
| Estate gate | `D:\Netie\Internal\Agents\estate_gate.py` (also `E:\Netie` / `NETIE_ROOT`) | subprocess, live, never cached. Desk paints first; live verdict is `GET /v1/gate` |
| Claims board | `D:\Netie\Internal\Agents\CLAIMS.json` plus `snapshots/latest.json` titles | file read. `GET /v1/fleet` who/where/what. RUNNING/SEATED heads are occupied. One writer per unused branch. Display only |
| Runtime view | `D:\Netie\Internal\Agents\RUNTIME.md` | file read, parsed; stale named |
| Claude pads | `claude agents --json` | subprocess, list only, timeout 4s. GET / and coordinate poll defer this. Live list is `GET /v1/pads`. Hung CLI named unread. Does not start Claude |
| Desktop surfaces | process snapshot for Cursor / Claude / Grok Bot | present/absent only. Never start or kill |
| Epic/ticket board | GitHub | `gh issue/pr/run list` (dms, Cortex, OpenVault, netie-control in parallel). Open issues, completed, PRs, Actions. Desk paints first; live list is `GET /v1/board` (BOARD_WAIT_S 4s). Pickup overlay is open-issues only (1.5s). `GET /v1/ops` polls board+CLAIMS fleet+pickup every 15s. Hung gh named unread. Control does not assign |

## Does not exist yet

Cortex dedicated refusal/manifest GET (P-CTL-1 remainder; activity.governance is
on the page), launcher execution (P-CTL-2), Crew converse
*inside* Control (P-CTL-3; charter still display-and-launch; belt JSON is shipped).
Disk GET / puts Cortex + OpenVault in `#hero` (not collapsed details).
Disk contract `before_seating` lists pickup, fleet, you, coordinate.
`GET /v1/ops` 15s poll is the shared live board (issues/PRs/Actions + CLAIMS
RUNNING seats). Issue #5 stays OPEN (P-CTL-2 launchers still unwired).
Control does not spawn PRD/Epic/Ticket agents and does not hand out vault
credentials - those stay Cortex Crew and OpenVault. See `PARKING_LOT.md`.
