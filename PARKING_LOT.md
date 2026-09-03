# PARKING_LOT - Netie Control

Every entry carries an unlock condition. No entry sits here without one.

## P-CTL-1 - Cortex internals on the first page

NETIE.md section 3 names live runs, ledger, manifest and refusal views, and a downtime
banner as the FIRST page.

**2026-08-27 first slice:** loopback GET `/health` + `/api/engine/activity` render on
the page. Unreachable Cortex never paints as up. Control does not query the ledger.

**2026-08-28:** Cortex `GET /api/engine/activity` now includes `governance`
(ledger tip, bound session ids, refusals; no payloads). Control displays that
window. It still will not scrape the chain for more.

**2026-09-03:** Cortex + OpenVault sit in `#hero` on the first viewport, not
inside collapsed details. Pickup/board/fleet stay the seating workbench.

**Still parked:** a dedicated Cortex GET for refusal/manifest *history* beyond
the activity window. Unlock remainder: Cortex ships that endpoint; Control
displays it.


## P-CTL-2 - wiring the launchers

They are declared and rendered; clicking one does nothing.

**Unlock:** an answer to who may launch. Under DR-0004 Option A there is no
authentication anywhere in the estate, so a wired launcher is remote code execution for
anyone who can reach the port. Wire them when Control has a principal, or bind to
loopback and say so in the SOW.

## P-CTL-3 - moving Crew's UI here

**2026-08-27 first slice:** Crew at `:8020` exposes `GET /v1/belt`. Control
proxies that JSON onto the first page and at `GET /v1/belt`. Display only.
HTML is not copied. Converse/handoff stay on Crew because NETIE.md is still
display-and-launch (`DR-PROPOSED-control-converse.md` is not law).

**2026-09-03:** Control "Crew chat" is a `target=_blank` launch to `:8020`.
The iframe overlay is gone (F-0026). Display-and-launch holds.

**Still parked:** converse rail *inside* Control. Unlock: NETIE.md section 3
amendment merges, then chat routes to Cortex HTTP. 405s stay. Do not copy
Crew HTML across (F-0026).

## P-CTL-4 - the estate gate is run as a subprocess

`sources.estate_gate()` shells out to `estate_gate.py` in `D:\Netie`. That is a hard
path to another repo, and it means Control cannot run anywhere but this machine.

**Unlock:** the gate published as a library or a service. Not urgent - Control is a
local operator shell today and the coupling is honest rather than hidden.
