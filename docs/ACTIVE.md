# ACTIVE - what exists in Netie Control and where

| Path | What |
|---|---|
| `netie_control/app.py` | FastAPI app. Routes, four 405 refusals, `GET /v1/contract` `GET /v1/belt` `GET /v1/fleet` `GET /v1/you` `GET /v1/pickup` `GET /v1/gate` display proxies, Constructor sketch launch at `/constructor/` |
| `AGENTS.md` | Seating contract for Cursor, Claude Code, Grok Bot. Same clause as CLAUDE.md operator desk |
| `netie_control/sources.py` | Read-only readers. Every one returns real data or an explicit unreachable marker. Writes nothing |
| `netie_control/render.py` | The operator page. An unreachable source renders its reason, never an empty panel |
| `netie_control/static/control.css` | Operator chrome. Guaca/Rakazo tokens, Gastown live-dots, original layout |
| `tests/test_control_stays_plane_4.py` | The constitution as tests - 405s, no key material, no desktop launcher, unknown never renders green |

## Reads (all read-only)

| Source | Path | Via |
|---|---|---|
| Cortex internals | `GET {NETIE_CORTEX_URL}/health` and `/api/engine/activity` (default `:8010`) | urllib, loopback only |
| OpenVault liveness | `GET {NETIE_OPENVAULT_URL}/api/healthz` (default `:5000`) | urllib, loopback only |
| Spaceship host | `Internal/Agents/SHIP_SPACESHIP.md` | file read. Public facts only. No FTP password. Agents reopen Hosting Manager |
| Crew conveyor | `GET {NETIE_CREW_URL}/v1/belt` (default `:8020`). Also exposed as Control `GET /v1/belt` | urllib, loopback only. Display. No handoff POST |
| Crew laptop tools | `GET {NETIE_CREW_URL}/crew/health` | urllib, loopback only. MCP name/armed/running only. Does not arm |
| Skill chest | `GET {NETIE_KB_URL}/healthz` (default `:8030`) | urllib, loopback only. Counts, not artifact bodies |
| Estate gate | `D:\Netie\Internal\Agents\estate_gate.py` (also `E:\Netie` / `NETIE_ROOT`) | subprocess, live, never cached. Desk paints first; live verdict is `GET /v1/gate` |
| Claims board | `D:\Netie\Internal\Agents\CLAIMS.json` plus `snapshots/latest.json` titles | file read. Displayed as who/where/what via `GET /v1/fleet` |
| Runtime view | `D:\Netie\Internal\Agents\RUNTIME.md` | file read, parsed; stale named |
| Claude pads | `claude agents --json` | subprocess, list only, timeout 8s |
| Desktop surfaces | `tasklist` for Cursor / Claude / Grok Bot | present/absent only. Never start or kill |
| Epic/ticket board | GitHub | `gh issue list` (dms, Cortex, OpenVault, netie-control in parallel) |

## Does not exist yet

Cortex dedicated refusal/manifest GET (P-CTL-1 remainder; activity.governance is
on the page), FreeRoute budget numbers, launcher execution, Crew converse *inside*
Control (charter still display-and-launch; belt JSON is displayed), pushed remote.
Control does not spawn PRD/Epic/Ticket agents and does not hand out vault
credentials - those stay Cortex Crew and OpenVault. See `PARKING_LOT.md`.
