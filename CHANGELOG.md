## 2026-09-03 - Sidecar GET surfaces stay GET

`GET /v1/sidecar` probes engine host `:8023` JSON `/health` (HTML GET `/` is
not enough). `GET /v1/plans` `/v1/prompts` `/v1/fetch` proxy that sidecar and
drop prompt bodies. `GET /v1/launchers` lists cwd and argv. Click still does
nothing (P-CTL-2). POST `/v1/run` `/v1/goal` `/v1/route` `/v1/secrets` stay
405. No paperclip clone. No Crew composer. crew-bind never green. Non-Windows
This-PC snapshot is unread, not a 500.

## 2026-09-03 - GET /v1/state stays display-only

Desk JSON skips gate, gh board, and pads. POST is not 200. Four 405s
unchanged.

## 2026-09-03 - Fleet KB demo stays on the desk

GET /v1/skills ghost is a button that searches in-panel, not a JSON
navigation. Four 405s unchanged.

## 2026-09-03 - Skill show stays on the desk

KB hits open `GET /v1/skill/{id}` in-panel (2.5s abort), not a JSON
navigation. Control still does not run the skill. Four 405s unchanged.

## 2026-09-03 - Gate unread and KB search abort

Desk first-paint names GET /v1/gate not yet, not checking. KB search
aborts at 2.5s and never says searching. Four 405s unchanged.

## 2026-09-03 - Live hops fail-close HTTP errors as unread

Desk JS `readingJson` throws on non-OK GET so FastAPI 404 JSON cannot
paint as a quiet reading. Gate / board / pickup / pads / coordinate catch
paths keep their named unread copy. Four 405s unchanged.

## 2026-09-03 - Pads live hop; talk source is wakes

GET / still skips `claude agents --json`. Live pads are `GET /v1/pads`.
Talk unread names `/crew/wakes`, not HTML GET `/`. Four 405s unchanged.

## 2026-09-03 - Panel counts say unread, not a quiet ?

Deferred board/pickup/fleet badges say unread. Live fetch setCount
uses unread, not ?. Four 405s unchanged.

## 2026-09-03 - Constructor 503 and unread chrome stay warn

Missing Constructor skin is HTML `class=absent` 503, not FastAPI JSON.
Coordinate poll paints `#liveDot` warn (`is-unread`), never mint.
Strip deferred/unread cells say unread, not a quiet `?`. Four 405s unchanged.

## 2026-09-03 - Belt skipped Cortex ping is not a failed probe

Engine Crew belt JSON may say `cortex.detail=not probed`. Control paints
that as a skip (laptop-tools `engine_ok` is the live probe), not a hung
ping. Four 405s unchanged.

## 2026-09-03 - Cortex activity unread is not idle workers

Health-ok Cortex with hung `/api/engine/activity` names a workflow unread
chip. Hung `/health/features` is Features unread, not a silent omit.
Idle stays empty activity lists. Four 405s unchanged.

## 2026-09-03 - Coordinate talk shares the peer pool

Hung `/crew/wakes` no longer stacks a Cortex wait on GET `/v1/coordinate`.
Cortex health+activity+features share one 1.5s pool. Coordinate poll does
not overwrite SSR worker unread with idle. Desk names crew and vault waits.
Four 405s unchanged.

## 2026-09-03 - GET / talk and health share one pool

Hung `/crew/wakes` no longer stacks a second 1.5s `/crew/health` wait on
GET `/`. Both stay in the desk pool. Four 405s unchanged.

## 2026-09-03 - OpenVault healthz and usage run in parallel

Hung `/api/healthz` no longer stacks a second 1.5s usage wait. Both
probes use `OPENVAULT_USAGE_WAIT_S`. `/v1/route` stays 405.

## 2026-09-03 - Favicon 204, not a missing-app 404

GET `/favicon.ico` is 204. Browsers stop logging a fake missing route.
Four 405s unchanged.

## 2026-09-03 - Cortex follow-ups and skill show fail-close

Hung Cortex activity/features no longer stack on GET /. `kb_show` uses
KB_WAIT_S 1.5s. Coordinate poll names chips unread. Contract before_seating
includes `/v1/coordinate`. Four 405s unchanged.

## 2026-09-03 - GET /v1/board fail-closes hung gh

`BOARD_WAIT_S` is 4s (pickup overlay stays 1.5s). Board and pickup fetch
catches name unread. Contract `desk.board_wait_s` is 4. KB search wait is
1.5s. Four 405s unchanged.

## 2026-09-03 - Unread workers, skill search, gate, constructor 503

Unread Cortex or Crew health names worker chips, not idle-empty. Skill
search catch and gate fetch catch say unread. Missing Constructor skin
is 503 unread. Four 405s unchanged.

## 2026-09-03 - Strip names crew talk unread vs belt

First-viewport strip has a crew-talk cell (`GET /crew/wakes`). Unread uses
warn color. Belt cell stays separate. Four 405s unchanged.

## 2026-09-03 - Coordinate poll names unread on fetch fail

Coordinate tick catch sets liveDot to coordinate unread. Cortex/OpenVault
stay on `#hero`. Four 405s unchanged.

## 2026-09-03 - Cortex and FreeRoute sit on the first viewport

Cortex internals and OpenVault usage sit in `#hero`, not collapsed details.
Howto names talk_probe=/crew/wakes, you_steps, usage_probe. Four 405s unchanged.

## 2026-09-03 - FreeRoute usage counts, idle belt named

Talk live follows Crew `GET /crew/wakes`. OpenVault budget ring displays
`GET /api/usage` summary counts (`priced=false`). Ledger rows are dropped.
Idle belt JSON says wakes none / queue none / HITL 0. Four 405s unchanged.

## 2026-09-03 - Talk chip needs engine wakes, not GET /

Talk live follows Crew `GET /crew/wakes`. A hung fork that still serves
HTML `/` does not go green. Four 405s unchanged.

## 2026-09-03 - TAS belt GET is shipped, not future

TAS-CONTROL section 8 named belt as a future GET. Disk already proxies
`GET /v1/belt` (Crew `/v1/belt` then `/crew/belt`, 1.5s). Converse stays
`:8020`. Four 405s unchanged. No launcher wiring.

## 2026-09-03 - Strip names Crew belt unread

First-viewport strip has a crew-belt cell. Unread uses warn color, never green
(R-0011). Howto names YOU step 8. Four 405s unchanged.

## 2026-09-03 - Coordinate names founder Crew rebind, never green

Coordinate lane `crew-bind` points at YOU step 8. `live` stays false
(R-0011 / R-0015). Control does not start or kill :8020. Four 405s
unchanged.

## 2026-09-03 - Crew engine ping is named, not dropped

Laptop-tools slim keeps `engine_ok` from Crew `/crew/health`. Absent engine
is `class=absent`. Control does not start Cortex. Four 405s unchanged.

## 2026-09-03 - Crew chat launches :8020, no iframe

Toolbar "Crew chat" is `target=_blank` to Crew. The overlay iframe is gone
(F-0026, P-CTL-3). POST /v1/run stays 405. Four 405s unchanged.

## 2026-09-03 - Launcher lanes named, not executed

Local CLI lanes list cwd and P-CTL-2. Click does nothing. POST /v1/run stays 405.
R-0015 unchanged. Four 405s unchanged.

## 2026-09-03 - Belt paints Crew queue and HITL count

Crew conveyor HTML lists queue histogram, pending confirms, and space/agent
counts when Crew JSON carries them. Control still does not POST, approve, or
spawn. YOU step 8 says stop the hung fork yourself, then start engine Crew.
Four 405s unchanged.

## 2026-09-03 - YOU step 8 binds live Crew; health matches belt wait

YOU desk names founder rebind of `:8020` to `python -m CortexOS.crew` from
`E:\Cortex` (R-0015: agents do not restart it). Crew conveyor and coordinate
steps point at that card. `/crew/health` probe caps at `CREW_BELT_WAIT_S`
(1.5s) so a hung fork cannot stall GET /. Four 405s unchanged. No converse
form. No POST wakes.

## 2026-09-03 - Belt probes /v1/belt and /crew/belt

Crew conveyor GET tries both paths in 1.5s. Live fork may hang `/v1/belt` and 404
`/crew/belt`. Named absence lists both. Control still does not POST. Four 405s
unchanged.

## 2026-09-03 - Pickup does not wait on hung gh

GET `/v1/pickup` returns unseated CLAIMS without calling full desk `state()`.
Board overlay is capped at 1.5s; live issues stay `GET /v1/board`. Desk HTML
numbers pickup / coordinate / crew absences. Unreachable Crew belt names
its source. Control still does not assign. Four 405s unchanged. No converse
form. No POST wakes.

## 2026-08-28 - Belt panel shows Crew wakes

Crew conveyor HTML lists wake kind/state/note when Crew JSON carries `wakes`.
Control still does not POST wakes or converse. Four 405s unchanged.

## 2026-08-28 - Chip poll does not take Crew's thread

`GET /v1/coordinate` (15s desk poll) no longer calls `/crew/health`. That probe
starved Talk. GET `/` probes Talk before the parallel pool. MCP workers stay
on the laptop-tools panel. Four 405s unchanged.

## 2026-08-28 - Talk chip follows Crew host, not slow /crew/health

`GET /crew/health` takes ~7s (Crew waits on Cortex). Talk / A2A now probes
Crew `/` first (http.client, HTML discarded) so health cannot starve it.
POST `/v1/run` stays 405. Four 405s unchanged.

## 2026-08-28 - Live chips + honest this-PC probe

Desk polls `GET /v1/coordinate` every 15s and refreshes invoke chips. This-PC
surfaces use a process snapshot (tasklist of ~80 Cursor.exe rows timed out and
painted Cursor down). GET `/` defers `claude agents --json` so first paint is
not the CLI. Missing Claude CLI stays unread, not green. Four 405s unchanged.

## 2026-08-28 - Desk paints before gh board

GET `/` and GET `/v1/state` skip `gh issue list`. Live issues are `GET /v1/board`.
JS fills `#boardBody` and `#pickupBody`. GET `/v1/pickup` still includes the board
for agents and may stay slow. POST `/v1/board` is not 200. Four 405s unchanged.

## 2026-08-28 - Live workers + skill show

First viewport lists Cortex workflows and armed Crew MCPs. `GET /v1/skill/S-0001`
shows a truncated registry artifact. POST is not 200. Path-shaped ids are refused.
Four 405s unchanged.

## 2026-08-28 - Skills search on the desk (display only)

`GET /v1/skills?q=` proxies Netie-KB `/search`. Hits are id/kind/title only.
POST `/v1/skills` is not 200. Control does not run a skill. Four 405s unchanged.

## 2026-08-28 - Teammate chips and Ticket Runner seat recipe

First viewport chips include Ticket Runner / pads / Cortex#51. Pickup names
the seat loop. Control still does not spawn. Four 405s unchanged.

## 2026-08-28 - Named teammates on the invoke map

`GET /v1/coordinate` now lists Cursor / Claude pads / seated writers / Ticket
Runner / Cortex#51 kind=task / Crew / Cortex. Roster is display. Ticket Runner
stays unspawned. Router note names OpenVault FreeRoute. Four 405s unchanged.

## 2026-08-28 - Coordinate invoke map (F-0030 holds)

`GET /v1/coordinate` names who to invoke for Grok-class jobs (Cursor, Claude pads,
Crew talk, Cortex run, KB chest, OpenVault). The desk paints live/down per owner.
POST `/v1/coordinate` is not 200. Control still does not spawn, start desktop apps,
or answer 200 on `/v1/run`. Four 405s unchanged.

## 2026-08-28 - YOU desk names the two DMS decisions that park finished code

Steps 2 and 3 are F36 (extract vs live federation, open since 2026-08-07) and
F45 (insights + brief epic). Each links the dms branch that is written, green,
and waiting. Control decides neither - it shows that they are open. A hold that
lives only in a PRD markdown file gets merged by the next person. Four 405s
unchanged; no assign POST; numbering stays contiguous and a test asserts it.

## 2026-08-28 - Local type stack

Dropped the Google Fonts import so the desk does not wait on the network.
Space Grotesk / Inter / JetBrains names stay as roles; Segoe UI is the fallback.

## 2026-08-28 - How-to is one row

The every-agent bar is a single flex row so pickup / board / fleet keep the
first viewport. Contract JSON and AGENTS.md still carry the long form.

## 2026-08-28 - Every-agent contract (F-0030 holds)

Public repo. `AGENTS.md` plus `GET /v1/contract` tell every lane (Cursor, Claude,
Grok Bot) to read Control then claim on GitHub. How-to bar on the desk.
POST `/v1/contract` is not 200. Control still does not assign or run. Four 405s
unchanged.

## 2026-08-28 - Column counts and one-line tickets

Pickup / Board / Who is seated headers carry live counts. Ticket titles
ellipsis in the column. Filter sits in the title row so the trio gets more
height. Still original HTML.

## 2026-08-28 - Three-column first viewport

Pickup, board, and fleet sit in one 100vh row so all three stay on screen.
Lists scroll inside the columns. Still original HTML. No Plane / Paperclip
React / Crew composer copy. Ticket Open still goes to GitHub.

## 2026-08-28 - Gate deferred so the desk paints first

GET `/` and `GET /v1/state` no longer wait on `estate_gate.py` (up to 120s).
The banner stays UNKNOWN/warn until `GET /v1/gate` returns. JS fills the
banner, pill, and gate panel. POST `/v1/gate` is not 200. Unknown still
never renders green.

## 2026-08-28 - Sticky strip, capped lists

Pickup/board/fleet lists scroll in place. Strip stays on screen. More stays
collapsed so the first viewport is the workbench.

## 2026-08-28 - Workbench first viewport

First screen is strip + pickup + board/fleet, Optio-shaped. YOU sits in the
inspector. Cortex/vault/gate live under a collapsed More block so the desk is
not a 11-panel dump. Still original HTML. Still no assign POST.

## 2026-08-28 - Inspector follows the clicked ticket

Click a pickup, board, fleet, or rail row and the inspector shows that GitHub
ticket with Open / Comment. No assign POST. Guaca-like detail column without
copying Guaca Inspector.tsx.

## 2026-08-28 - Command strip + dense pickup

Optio-shaped overview numbers (pickup / seated / held / pads / this PC) sit
above the board. Seated writers are a Guaca-like rail list (links only, no
avatars copied). Pickup is dense rows. `.cursor/rules/operator-desk.mdc`
tells lanes to GET /v1/pickup. Still display-only. `/v1/run` stays 405.

## 2026-08-28 - Dashboard + pickup tray

The one-panel hide made Control look empty. All panes are visible. Type is
Space Grotesk + Inter (Guaca roles, not their files). Pickup is an Optio-shaped
tray of GitHub tickets at `GET /v1/pickup`. Agents read it; Control still does
not assign. `/v1/run` stays 405. dms#61 is a FLEET.md hold, not the product.

## 2026-08-28 - Board tickets + Cortex governance window

Founder needed Jira-shaped tickets: each open GitHub issue is now a card with
Open and Comment. Board includes `netie-control`. Cortex panel shows the
activity.governance window (refusals + bound session ids) instead of saying
the view is absent. Page probes run in parallel so gate wait is not added on
top of gh. Still display-only. Still no invented prices or host URLs.

## 2026-08-28 - YOU desk: GitHub URLs, HT1/HT2 human-stop

Founder cannot act if tickets are not clickable. Control now numbers five
human steps (dms#61, OpenVault#18 HT1, HT2, Crew converse, GitHub comment
feedback). Fleet/board titles link to GitHub. No invented host URLs, no
invented prices. Control still does not auto-route chat to agents.

## 2026-08-27 - Constructor sketch launch

`GET /constructor/` serves the Constructor skin (chat compiles locally).
Live run stays Cortex `:8010/cortex/constructor/`. Control still holds no
keys and does not run DAGs. `/v1/run` stays 405.

## 2026-08-27 - Operator chrome (rail + kanban + inspector)

The monospace dump was unreadable. Control now uses a Crew/Guaca rail,
Rakazo dark ink, Gastown live-dots, and a three-column SEATED/UNSEATED
kanban. Plane AGPL source is not copied. Paperclip React is not copied.
Crew converse/composer is not copied. Tokens attributed in
`netie_control/static/control.css`.

## 2026-08-27 - Spaceship host panel (reuse, do not buy)

Founder already has Spaceship Web Hosting Essential for `netie.ai` (cPanel +
FTP `ship@netie.ai`). Agents were inventing Cloudflare. Control now reads
`SHIP_SPACESHIP.md` and shows Hosting Manager / cPanel / Launchpad reopen
links plus the domain list. Passwords stay in OpenVault. Do not scrape
spaceship.com. Do not click New hosting.

## 2026-08-27 - Who / where / what fleet table

The operator page listed CLAIMS as `PR: role` and truncated RUNTIME to 14
lines, so Claude pads and branch-prefix writer guesses never appeared.
Control now renders CLAIMS tickets as a who/repo/branch/seat/lane table
(lane is a prefix guess, not cloud-vs-PC proof), live `claude agents --json`
pads, tasklist present/absent for Cursor / Claude / Grok Bot, and a parsed
RUNTIME snapshot that names STALE. `GET /v1/fleet` is display-only.

Does not seat anyone. Does not start or kill founder apps.

## 2026-08-27 - Fleet, skill chest, OpenVault plugin (display)

Scale question: 1000 executors need one place that shows who is doing what,
which laptop tools are armed, and where credentials live. Control now GETs
Crew `/crew/health` (UACC/Playwright arming, no tool catalogs copied) and
Netie-KB `/healthz` (artifact counts). OpenVault panel names the custody
plugin and repeats that `/v1/secrets` is 405. Cortex activity lists active
workflow titles when present.

Does not arm UACC. Does not spawn PRD/Epic/Ticket agents. Does not bypass
OS permission prompts. Does not return vault material.

## 2026-08-27 - Crew conveyor display-only (one operator page)

Fold toward one operator app without a second engine. Control now GETs Crew
`/v1/belt` on loopback, renders the JSON as a display-only panel, and exposes
the same payload at Control `GET /v1/belt`. Converse stays a labeled Crew
surface (`:8020`) because NETIE.md is still display-and-launch.

Does not POST handoff. Does not iframe a chat form. 405s unchanged.

## 2026-08-27 - Cortex first page (read-only probes)

NETIE.md section 3 says the first page is Cortex internals. The page was the estate
gate. Cortex already exposes GET `/health` and GET `/api/engine/activity`; Control
now probes those on loopback and renders them, or names the miss.

Does not scrape the ledger. Refusal/manifest history has no public GET, so the panel
says that instead of inventing a view. OpenVault `/api/healthz` is display-only; the
copy states Control did not pick a route. Off-box URLs are refused (not an open
proxy). CI workflow added; remote still unpushed.

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
