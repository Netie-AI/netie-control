# AGENTS.md - every lane, every runtime

Cursor, Claude Code, Grok Bot, cloud agents, and humans. Same law as `CLAUDE.md`.
`D:\Netie\NETIE.md` wins if this file disagrees.

This repo is public: https://github.com/Netie-AI/netie-control
Live desk: `http://127.0.0.1:8040/`

## Before you sit (do not skip)

1. `GET http://127.0.0.1:8040/v1/contract`
2. `GET /v1/pickup` then `GET /v1/fleet` then `GET /v1/you`
3. Claim the GitHub issue. Then CLAIMS.json. Then work.

Control is the assignment **surface**. Control does not assign. Cortex runs.
GitHub Issues are SoT (F-0025). Converse is Crew `http://127.0.0.1:8020`.

## Do not

- `POST /v1/run` `/v1/goal` `/v1/route` `/v1/secrets` -- they 405 with an owner
- Spawn PRD / Epic / Ticket agents from this shell (F-0030)
- Invent HT1 host URLs or prices
- Start, restart, or kill Grok Bot / Cursor / founder desktop apps (R-0015)
- Copy Plane AGPL, Paperclip React, or Crew composer into this tree

## Communication layer

| Job | Owner |
|---|---|
| See who holds what | Control `:8040` |
| Claim / comment | GitHub Issues + CLAIMS.json |
| Run work | Cortex |
| Talk | Crew `:8020` |
| Keys | OpenVault |

A scale request ("fully automate", "1000 executors") is still this loop.
It is not a third orchestrator inside Control.
