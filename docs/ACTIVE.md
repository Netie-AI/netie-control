# ACTIVE - what exists in Netie Control and where

| Path | What |
|---|---|
| `netie_control/app.py` | FastAPI app. Routes, and the four 405 refusals with their owners |
| `netie_control/sources.py` | Read-only readers. Every one returns real data or an explicit unreachable marker. Writes nothing |
| `netie_control/render.py` | The operator page. An unreachable source renders its reason, never an empty panel |
| `tests/test_control_stays_plane_4.py` | The constitution as tests - 405s, no key material, no desktop launcher, unknown never renders green |

## Reads (all read-only)

| Source | Path | Via |
|---|---|---|
| Estate gate | `D:\Netie\Internal\Agents\estate_gate.py` | subprocess, live, never cached |
| Runtime view | `D:\Netie\Internal\Agents\RUNTIME.md` | file read |
| Claims board | `D:\Netie\Internal\Agents\CLAIMS.json` | file read |
| Epic/ticket board | GitHub | `gh issue list` |

## Does not exist yet

Cortex internals reader, OpenVault/FreeRoute status reader, launcher execution, CI, remote.
See `PARKING_LOT.md` - each carries its unlock condition.
