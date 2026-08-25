# PARKING_LOT - Netie Control

Every entry carries an unlock condition. No entry sits here without one.

## P-CTL-1 - Cortex internals on the first page

NETIE.md section 3 names live runs, ledger, manifest and refusal views, and a downtime
banner as the FIRST page. None is built; today's first page is the gate and the board.

**Unlock:** a read-only Cortex endpoint exposing run and refusal history. Control must
not query the ledger directly - one ledger, reached through Cortex (DMS CLAUDE.md hard
rule 3), and the same applies here.

## P-CTL-2 - wiring the launchers

They are declared and rendered; clicking one does nothing.

**Unlock:** an answer to who may launch. Under DR-0004 Option A there is no
authentication anywhere in the estate, so a wired launcher is remote code execution for
anyone who can reach the port. Wire them when Control has a principal, or bind to
loopback and say so in the SOW.

## P-CTL-3 - moving Crew's UI here

`CortexOS/crew/ui/index.html` lives inside Cortex, which NETIE.md section 3 forbids -
*"Cortex does not grow a UI organ."*

**Unlock:** Crew's server exposing its board and A2A transcript over HTTP so Control can
render them remotely. Do not copy the HTML across; that leaves two copies to diverge,
which is exactly F-0026's root cause class.

## P-CTL-4 - the estate gate is run as a subprocess

`sources.estate_gate()` shells out to `estate_gate.py` in `D:\Netie`. That is a hard
path to another repo, and it means Control cannot run anywhere but this machine.

**Unlock:** the gate published as a library or a service. Not urgent - Control is a
local operator shell today and the coupling is honest rather than hidden.
