# CLAUDE.md - Netie Control agent contract

**Repo:** `Netie-AI/netie-control` (public: https://github.com/Netie-AI/netie-control). **Plane 4.** Operator shell.

Governed by the Netie document system. `D:\Netie\NETIE.md` is the constitution and wins
over anything here. If this file contradicts it, this file is wrong.

## What this is

The estate shell operators use. First page is Cortex internals - live runs, ledger and
manifest and refusal views, the downtime and degradation banner. Second ring is
OpenVault/FreeRoute route and budget status, the repo/epic/ticket board, and local CLI
launchers.

## What this is not, and why the refusals are routes

Not an engine, not a key vault, not a route picker, not a third orchestrator.

A capability that is merely **absent** gets added back by the next person who needs it
and does not know why it was left out. So each forbidden capability is a route that
answers **405 with its owner named**, and `tests/test_control_stays_plane_4.py` asserts
each one. That turns "we decided not to" into something that goes red.

| Route | Answers | Owner |
|---|---|---|
| `/v1/secrets` | 405 | OpenVault - there is exactly one key vault in this company |
| `/v1/route` | 405 | OpenVault FreeRoute - Control may display a route, never choose one |
| `/v1/goal` | 405 | Cortex - deciding work shape is plane 3 |
| `/v1/run` | 405 | Cortex - no write reaches a customer except through an action type |

## Operator desk (every lane)

Before seating on a ticket, read Control `GET http://127.0.0.1:8040/v1/contract`,
then `GET /v1/pickup`, `GET /v1/fleet`, `GET /v1/you`, and `GET /v1/coordinate`.
`GET /v1/coordinate` is the Grok-class invoke map (who to talk to, who runs,
which desktop app is present).
Pickup is the tray of unseated GitHub work. That is the operator view of who holds
what. It is **not** a third orchestrator: Control still answers 405 on `/v1/run`
`/v1/goal` `/v1/route` `/v1/secrets`. GitHub Issues remain SoT. Converse lives on
Crew `:8020`. HT1 and HT2 stay HUMAN_STOP - do not invent host URLs or prices.

`AGENTS.md` is the same operator-desk clause in the filename Cursor, Claude Code,
and Grok look for. It must not contradict this file. It is not a sixth constitution.

## Hard rules

1. **Holds no key material.** Asserted on the source, not at runtime, because a key
   behind a config branch would pass a runtime probe.
2. **Owns no route decision.** It may show which route was chosen and what it cost.
3. **Decides no work shape.** A second thing that decides work shape is a third
   orchestrator, which NETIE.md section 6 declines.
4. **Display and launch only.** Launchers start *local CLI lanes*. Nothing here starts,
   restarts or kills the founder's desktop software - Grok Bot, Cursor and every
   user-facing app open and close by the founder's own hand (R-0015). A test enforces it.
5. **An unreachable source renders as a stated absence, never an empty panel.** An empty
   panel and a healthy-but-quiet panel look identical and the operator cannot tell which
   they are reading (R-0011). Unknown must never render as green.
6. **No invented data, ever.** This page's whole job is "what is actually true". It is
   the worst possible place to fake. If a source cannot be read, say so and name it.
7. **Read-only against the estate.** `sources.py` writes nothing.

## Five files, no sixth

`CLAUDE.md` (law) - `docs/ACTIVE.md` (map) - `STATUS.md` (state, <=60 lines) -
`CHANGELOG.md` (history, append-only) - `PARKING_LOT.md` (deferred, every entry carries
an unlock condition). Decisions in `docs/decisions/DR-NNNN-*.md`.

No per-agent files. No per-session files. No dates in filenames outside an archive.

## Before non-trivial work

`python D:\Netie-KB\scripts\kb.py search "<keywords>"`. Note S-0004: only 4 of roughly
44 skill-shaped files in the estate are registry entries, so "no hits" is weak evidence
of absence - grep the runtime skill directories too.

After: file a finding (`kb.py new finding`). "Nothing new" is a valid finding.

## Run it

```
python -m uvicorn netie_control.app:app --port 8040
python -m pytest tests/ -q
```
