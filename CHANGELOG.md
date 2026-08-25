# Changelog - Netie Control

Append-only. Newest first.

## 2026-08-25 - first slice

Created. Plane 4 operator shell, per NETIE.md section 3, which has named this product
since version 1.0 without a repo existing for it.

**Why now:** the founder asked whether the estate's apps could be merged into one
supervised app. The constitution already answered that - Netie Control - and also said
where it must not go: *"Cortex does not grow a UI organ. This app is plane 4."* Crew was
already over that line with `CortexOS/crew/ui/index.html`.

**What it does:** reads four real sources - the estate gate (run live, never a cached
verdict, because a cached green is a claim about the past), the watchdog RUNTIME view,
the CLAIMS board, and the open epic/ticket board via `gh`.

**What it refuses:** `/v1/secrets`, `/v1/route`, `/v1/goal` and `/v1/run` answer 405
with the owning product named. These are routes rather than omissions because an absent
capability gets added back by the next person who does not know why it was left out.

25 tests. The ones that matter are not the happy paths: an unreadable gate must never
render as a pass, no source file may contain key material, and no launcher may target
the founder's desktop software (R-0015).

On its first real run the page reported `GATE FAIL - HOLD_MISSING Netie-AI/dms#61`,
which is true and current: that PR was merged while under a named hold in FLEET.md, by
an agent that read `MERGEABLE` as permission. FLEET.md line 22 says in as many words
that it is not. The branch was restored to its held head; the hold itself needs a human
to lift.
