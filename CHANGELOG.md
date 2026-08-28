# Changelog - Netie Control

Append-only. Newest first.

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
