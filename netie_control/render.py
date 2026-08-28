"""Render the operator page.

One rule shapes all of this: an unreachable source renders as a stated absence, never
as an empty panel. An empty panel and a healthy-but-quiet panel look identical, and the
operator cannot tell which they are looking at (R-0011).
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

_CSS_PATH = Path(__file__).with_name("static") / "control.css"


def _css() -> str:
    try:
        return _CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return "body{background:#050506;color:#e7ebe2}"


def _esc(x: Any) -> str:
    return html.escape(str(x))


def _panel(title: str, reading: dict[str, Any], body_fn, extra: str = "", panel_id: str = "", count: str = "") -> str:
    """Render one source. If it could not be read, say so instead of showing nothing."""
    cls = "panel" + (f" {extra}" if extra else "")
    id_attr = f' id="{html.escape(panel_id)}"' if panel_id else ""
    badge = f' <span class="count">{_esc(count)}</span>' if count else ""
    if not reading.get("ok"):
        return (
            f'<div class="{cls}"{id_attr}><h2>{_esc(title)}{badge}</h2>'
            f'<p class="absent">Could not read this source: '
            f'{_esc(reading.get("detail") or "no reason given")}</p>'
            f'<p class="absent">Source: <code>{_esc(reading.get("source"))}</code></p></div>'
        )
    return (
        f'<div class="{cls}"{id_attr}><h2>{_esc(title)}{badge}</h2>'
        f"{body_fn(reading.get('data'))}</div>"
    )


def _gate_body(d: dict[str, Any]) -> str:
    if d.get("passing"):
        return '<p style="color:var(--ok)">Gate passes. Seating is permitted.</p>'
    items = "".join(f'<li class="fail">{_esc(x)}</li>' for x in (d.get("output") or [])[:20])
    return (
        f'<p class="fail">Gate FAILS (exit {_esc(d.get("exit_code"))}). '
        f"No writer may be seated until a human acts.</p><ul>{items}</ul>"
    )


def _gate_panel(reading: dict[str, Any]) -> str:
    if not reading.get("ok"):
        body = (
            f'<p class="absent">Could not read this source: '
            f'{_esc(reading.get("detail") or "no reason given")}</p>'
            f'<p class="absent">Source: <code>{_esc(reading.get("source"))}</code></p>'
        )
    else:
        body = _gate_body(reading.get("data") or {})
    return (
        f'<div class="panel" id="gate"><h2>Estate gate</h2>'
        f'<div id="gateBody">{body}</div></div>'
    )


def _data_attrs(ticket: Any, title: Any, href: Any) -> str:
    return (
        f' data-ticket="{_esc(ticket)}" data-title="{_esc(title)}" data-href="{_esc(href)}"'
    )


def _ticket_card(r: dict[str, Any]) -> str:
    tags = ""
    if r.get("is_epic"):
        tags += '<span class="tag epic">epic</span> '
    if r.get("blocked"):
        tags += '<span class="tag blocked">blocked</span>'
    href = str(r.get("url") or "")
    repo = str(r.get("repo", "")).split("/")[-1]
    num = r.get("number")
    ticket = f"{repo}#{num}"
    title = r.get("title")
    btns = ""
    if href:
        safe = _esc(href)
        btns = (
            f'<span class="work-row__act">'
            f'<a class="btn" href="{safe}" target="_blank" rel="noopener">Open</a> '
            f'<a class="btn btn-ghost" href="{safe}" target="_blank" rel="noopener">Comment</a>'
            f"</span>"
        )
    return (
        f'<div class="work-row ticket-card"{_data_attrs(ticket, title, href)}>'
        f"<code>{_esc(ticket)}</code>"
        f'<span class="work-row__title">{_esc(title)}</span>'
        f'<span class="tags">{tags}</span>{btns}</div>'
    )


def _board_body(d: dict[str, Any]) -> str:
    rows = [r for r in (d.get("items") or []) if isinstance(r, dict)]
    bits: list[str] = [
        "<p>GitHub Issues are SoT. Open, then comment there. Control does not assign.</p>"
    ]
    if not rows:
        bits.append('<p class="absent">No open items returned.</p>')
    else:
        by_repo: dict[str, list[dict[str, Any]]] = {}
        for r in rows[:80]:
            by_repo.setdefault(str(r.get("repo") or "?"), []).append(r)
        cols = []
        for repo, items in by_repo.items():
            cards = "".join(_ticket_card(x) for x in items[:24])
            cols.append(
                f'<section class="kcol"><h3>{_esc(repo.split("/")[-1])} {len(items)}</h3>'
                f"{cards}</section>"
            )
        bits.append('<div class="kanban">' + "".join(cols) + "</div>")
    if d.get("unreachable"):
        bits.append(
            '<p class="absent">Not shown, unreachable: '
            + _esc("; ".join(d["unreachable"]))
            + "</p>"
        )
    return "".join(bits)


def _pickup_body(d: Any) -> str:
    d = d or {}
    items = [r for r in (d.get("items") or []) if isinstance(r, dict)]
    bits: list[str] = [
        "<p>Pickup - claim on GitHub. Control does not assign.</p>",
        f'<p class="absent">{_esc(d.get("rule") or "")}</p>',
    ]
    if not items:
        bits.append(
            '<p class="absent">No pickup items. Board and CLAIMS were empty or unread.</p>'
        )
        return "".join(bits)
    rows_html = []
    for r in items[:32]:
        href = str(r.get("href") or "")
        tags = f'<span class="tag">{_esc(r.get("kind"))}</span>'
        if r.get("is_epic"):
            tags += ' <span class="tag epic">epic</span>'
        if r.get("blocked"):
            tags += ' <span class="tag blocked">blocked</span>'
        btns = ""
        if href:
            safe = _esc(href)
            btns = (
                f'<span class="work-row__act">'
                f'<a class="btn" href="{safe}" target="_blank" rel="noopener">Pick up</a> '
                f'<a class="btn btn-ghost" href="{safe}" target="_blank" rel="noopener">Comment</a>'
                f"</span>"
            )
        rows_html.append(
            f'<div class="work-row pickup-card"'
            f"{_data_attrs(r.get('ticket'), r.get('title'), href)}>"
            f"<code>{_esc(r.get('ticket'))}</code>"
            f'<span class="work-row__title">{_esc(r.get("title"))}</span>'
            f'<span class="tags">{tags}</span>{btns}</div>'
        )
    bits.append(f'<div class="work-list">{"".join(rows_html)}</div>')
    return "".join(bits)


def _cortex_body(d: Any) -> str:
    d = d or {}
    bits: list[str] = []
    if d.get("up"):
        bits.append('<p style="color:var(--ok)">Cortex is up (loopback health).</p>')
    else:
        bits.append('<p class="fail">Cortex health did not report status=ok.</p>')
    health = d.get("health") or {}
    pack = health.get("pack")
    if pack:
        bits.append(f"<p>pack <code>{_esc(pack)}</code></p>")
    features = d.get("features") or {}
    ver = features.get("engine_version")
    if ver:
        bits.append(f"<p>engine <code>{_esc(ver)}</code></p>")
    activity = d.get("activity")
    if activity is None:
        bits.append(
            f'<p class="absent">Activity: {_esc(d.get("activity_detail") or "not read")}</p>'
        )
    else:
        wf = (activity.get("workflows") or {}) if isinstance(activity, dict) else {}
        rt = (activity.get("routines") or {}) if isinstance(activity, dict) else {}
        bits.append(
            "<p>activity: "
            f"workflows active={_esc(len(wf.get('active') or []))} "
            f"routines={_esc(rt.get('total', '?'))}</p>"
        )
        for run in (wf.get("active") or [])[:8]:
            if not isinstance(run, dict):
                continue
            label = run.get("title") or run.get("id") or "unnamed"
            bits.append(
                f"<p>workflow <code>{_esc(label)}</code> {_esc(run.get('status') or '')}</p>"
            )
        for rid in (rt.get("running") or [])[:8]:
            bits.append(f"<p>routine running <code>{_esc(rid)}</code></p>")
    gov = d.get("governance")
    if isinstance(gov, dict):
        led = gov.get("ledger") or {}
        man = gov.get("manifests") or {}
        ref = gov.get("refusals") or {}
        recent_led = [x for x in (led.get("recent") or []) if isinstance(x, dict)]
        recent_ref = [x for x in (ref.get("recent") or []) if isinstance(x, dict)]
        sessions = [x for x in (man.get("sessions") or []) if isinstance(x, dict)]
        bits.append(
            "<p>Governance from Cortex <code>GET /api/engine/activity</code> "
            "(identifiers only, no ledger scrape). "
            f"ledger tip={_esc(led.get('tip_seq', '?'))} "
            f"registered={_esc(led.get('registered'))} "
            f"bound sessions={_esc(man.get('bound', 0))} "
            f"refusals={_esc(len(recent_ref))}.</p>"
        )
        if recent_ref:
            bits.append("<table><tr><th>seq</th><th>refusal</th><th>actor</th></tr>")
            for row in recent_ref[:8]:
                bits.append(
                    f'<tr class="fail"><td>{_esc(row.get("seq"))}</td>'
                    f"<td>{_esc(row.get('event_type'))}</td>"
                    f"<td>{_esc(row.get('actor'))}</td></tr>"
                )
            bits.append("</table>")
        else:
            bits.append("<p>No recent refusals in the Cortex window (honest empty).</p>")
        if sessions:
            bits.append("<p>Bound session ids:</p><ul>")
            for row in sessions[:8]:
                bits.append(
                    f"<li><code>{_esc(row.get('session_id'))}</code> "
                    f"expires {_esc(row.get('expires_at'))}</li>"
                )
            bits.append("</ul>")
        if recent_led:
            bits.append("<table><tr><th>seq</th><th>ledger event</th><th>actor</th></tr>")
            for row in recent_led[:8]:
                bits.append(
                    f"<tr><td>{_esc(row.get('seq'))}</td>"
                    f"<td>{_esc(row.get('event_type'))}</td>"
                    f"<td>{_esc(row.get('actor'))}</td></tr>"
                )
            bits.append("</table>")
    else:
        bits.append(
            f'<p class="absent">Refusal/manifest view: '
            f'{_esc(d.get("refusal_why") or "absent")}</p>'
        )
    bits.append(
        "<p>Constructor flow (this shell launches the skin, Cortex is the engine): "
        '<a href="/constructor/">/constructor/</a> sketch · '
        '<a href="http://127.0.0.1:8010/cortex/constructor/">'
        "http://127.0.0.1:8010/cortex/constructor/</a> live.</p>"
    )
    return "".join(bits)


def _openvault_body(d: Any) -> str:
    d = d or {}
    bits: list[str] = []
    if d.get("up"):
        bits.append(
            '<p style="color:var(--ok)">OpenVault healthz ok. Control did not pick a route.</p>'
        )
    else:
        bits.append('<p class="fail">OpenVault healthz did not report status=ok.</p>')
    bits.append(
        "<p>Custody plugin: agents request credentials from "
        f"<code>{_esc(d.get('custody_owner') or 'OpenVault')}</code> when that gate "
        "allows. Control never stores them. "
        f"{_esc(d.get('request_path') or 'Control /v1/secrets answers 405.')}</p>"
    )
    bits.append(
        '<p class="absent">Laptop OS mouse is UACC (S-0002). Pointer is HUD + '
        "Cortex POST /dms/secure, not a second mouse stack. "
        "computer-control-mcp is declined.</p>"
    )
    bits.append(
        '<p>HT1 and HT2 stay HUMAN_STOP. Do not invent a host URL. Do not invent prices. '
        'Ticket: <a href="https://github.com/Netie-AI/OpenVault/issues/18" '
        'target="_blank" rel="noopener">OpenVault#18</a>. '
        'Local Ship/Route UI (not HT1): '
        '<a href="http://127.0.0.1:3010">http://127.0.0.1:3010</a></p>'
    )
    return "".join(bits)


def _spaceship_body(d: Any) -> str:
    d = d or {}
    rows = "".join(
        f"<tr><td>{_esc(item.get('host'))}</td><td>{_esc(item.get('site'))}</td></tr>"
        for item in (d.get("domains") or [])
    )
    return (
        f"<p>{_esc(d.get('package') or 'Spaceship')} for "
        f"<code>{_esc(d.get('apex') or 'netie.ai')}</code> at "
        f"<code>{_esc(d.get('host'))}</code> "
        f"(<code>{_esc(d.get('server'))}</code>).</p>"
        f"<p>Docroot <code>{_esc(d.get('docroot'))}</code> "
        f"- not public_html. FTP user <code>{_esc(d.get('ftp_user'))}</code> "
        "(password in OpenVault / spaceship-ftp.env).</p>"
        "<p>Always reopen: "
        f"<a href=\"{_esc(d.get('hosting_manager'))}\">Hosting Manager</a> · "
        f"<a href=\"{_esc(d.get('cpanel_access'))}\">cPanel access</a> · "
        f"<a href=\"{_esc(d.get('launchpad'))}\">Launchpad</a></p>"
        f"<p>Playwright profile <code>{_esc(d.get('playwright_profile'))}</code></p>"
        f'<p class="absent">{_esc(d.get("rule"))}</p>'
        "<table><tr><th>host</th><th>site</th></tr>"
        f"{rows}</table>"
    )


def _crew_health_body(d: Any) -> str:
    d = d or {}
    bits: list[str] = [
        ("<p>Display-only of Crew <code>GET /crew/health</code>. "
        "Control does not arm UACC, does not start Playwright, and does not "
        "bypass OS permission prompts.</p>")
    ]
    cc = d.get("computer_control")
    if cc:
        bits.append(
            '<p style="color:var(--ok)">Crew computer_control flag is on. '
            "That is Crew's flag, not Control turning the mouse on.</p>"
        )
    else:
        bits.append(
            '<p class="absent">Crew computer_control flag is off '
            "(CORTEX_COMPUTER_CONTROL unset). Cursor-session UACC can still be "
            "armed separately. Control will not set the flag.</p>"
        )
    provider = d.get("provider") or {}
    if provider.get("label") or provider.get("model"):
        bits.append(
            "<p>Crew provider "
            f"<code>{_esc(provider.get('label') or '?')}</code> "
            f"model <code>{_esc(provider.get('model') or '?')}</code></p>"
        )
    rows = d.get("mcp") or []
    if not rows:
        bits.append('<p class="absent">Crew health returned no MCP rows.</p>')
    else:
        bits.append("<table><tr><th>mcp</th><th>status</th><th>armed</th><th>running</th></tr>")
        for row in rows[:12]:
            bits.append(
                f"<tr><td>{_esc(row.get('name'))}</td>"
                f"<td>{_esc(row.get('status'))}</td>"
                f"<td>{_esc(row.get('armed'))}</td>"
                f"<td>{_esc(row.get('running'))}</td></tr>"
            )
        bits.append("</table>")
    return "".join(bits)


def _kb_body(d: Any) -> str:
    d = d or {}
    bits: list[str] = [
        ("<p>One skill chest (R-0016). Agents pull from Netie-KB before re-deriving "
        "(S-0003). New reusable work is filed there, not as a private SKILL.md "
        "in this repo.</p>")
    ]
    if d.get("ok") or d.get("service"):
        bits.append(
            f'<p style="color:var(--ok)">KB healthz ok '
            f"(<code>{_esc(d.get('service') or 'netie-kb')}</code>).</p>"
        )
    counts = d.get("counts") if isinstance(d.get("counts"), dict) else {}
    if counts:
        bits.append("<p>" + " ".join(
            f"{_esc(k)}={_esc(v)}" for k, v in counts.items()
        ) + "</p>")
    else:
        bits.append('<p class="absent">KB healthz carried no artifact counts.</p>')
    return "".join(bits)


def _crew_belt_body(d: Any) -> str:
    """Render Crew's conveyor JSON. No chat form. No handoff POST."""
    d = d or {}
    tickets_blob = d.get("tickets") if isinstance(d.get("tickets"), dict) else {}
    items = tickets_blob.get("items") or []
    unreachable = tickets_blob.get("unreachable") or []
    bits: list[str] = [
        ('<p>Display-only of Crew <code>GET /v1/belt</code>. '
        "Control does not converse (NETIE.md is still display-and-launch). "
        "Crew surface (converse + handoff): "
        '<a href="http://127.0.0.1:8020">http://127.0.0.1:8020</a></p>')
    ]
    bus = d.get("bus")
    if bus:
        bits.append(f"<p>bus <code>{_esc(bus)}</code></p>")
    if not items:
        bits.append('<p class="absent">Crew JSON carried no open tickets.</p>')
    else:
        bits.append("<table><tr><th>repo</th><th>#</th><th>title</th><th></th></tr>")
        for item in items[:40]:
            repo = str(item.get("repo", "")).split("/")[-1]
            ready = "READY" if item.get("ready") else ""
            href = item.get("url") or ""
            if not href and item.get("repo") and item.get("number"):
                href = (
                    f"https://github.com/{item.get('repo')}/issues/{item.get('number')}"
                )
            title = _esc(item.get("title"))
            if href:
                title = f'<a href="{_esc(href)}" target="_blank" rel="noopener">{title}</a>'
            bits.append(
                f"<tr><td>{_esc(repo)}</td><td>{_esc(item.get('number'))}</td>"
                f"<td>{title}</td><td>{_esc(ready)}</td></tr>"
            )
        bits.append("</table>")
    if unreachable:
        bits.append(
            '<p class="absent">Crew named unreachable: '
            + _esc("; ".join(str(x) for x in unreachable))
            + "</p>"
        )
    hands = d.get("handoffs") or []
    if hands:
        bits.append("<p>handoffs</p><ul>")
        for row in hands[:8]:
            bits.append(
                f"<li><code>{_esc(row.get('ticket'))}</code> "
                f"{_esc(row.get('from'))} - {_esc(row.get('note'))}</li>"
            )
        bits.append("</ul>")
    plan = d.get("plan_for_next") or {}
    if plan:
        bits.append(
            "<p>plan decides_work_shape="
            f"{_esc(plan.get('decides_work_shape'))} "
            f"needs_human={_esc(plan.get('needs_human'))}</p>"
        )
    cortex = d.get("cortex") or {}
    if cortex.get("ok"):
        bits.append('<p style="color:var(--ok)">Crew says Cortex ping ok.</p>')
    elif cortex:
        bits.append(
            f'<p class="absent">Crew Cortex ping: {_esc(cortex.get("detail") or "not ok")}</p>'
        )
    return "".join(bits)


def _seat_card(row: dict[str, Any]) -> str:
    role = str(row.get("role") or "?")
    lane = str(row.get("lane") or "unknown")
    role_cls = "seated" if role == "SEATED" else ""
    lane_cls = "cursor" if lane == "Cursor" else ("claude" if lane == "Claude" else "")
    what = row.get("title") or row.get("ticket") or ""
    href = str(row.get("href") or "")
    inner = (
        f"<strong>{_esc(row.get('ticket'))}</strong>"
        f'<div class="meta">{_esc(row.get("repo"))} · {_esc(what)}</div>'
        f"<div><code>{_esc(row.get('head'))}</code></div>"
        '<div class="tags">'
        f'<span class="tag {role_cls}">{_esc(role)}</span>'
        f'<span class="tag {lane_cls}">lane guess {_esc(lane)}</span>'
        "</div>"
    )
    if href:
        return (
            f'<a class="seat-card" href="{_esc(href)}" target="_blank" rel="noopener"'
            f"{_data_attrs(row.get('ticket'), what, href)}>"
            f"{inner}</a>"
        )
    return (
        f'<article class="seat-card"{_data_attrs(row.get("ticket"), what, href)}>'
        f"{inner}</article>"
    )


def _fleet_body(d: Any) -> str:
    d = d or {}
    rows = [r for r in (d.get("rows") or []) if isinstance(r, dict)]
    bits: list[str] = [
        (f"<p>Who is seated. CLAIMS seated={_esc(d.get('seated', 0))} "
        f"held={_esc(d.get('held', 0))}. GitHub is SoT. Control does not seat anyone.</p>"),
        f'<p class="absent">{_esc(d.get("lane_rule") or "Lane tags are a guess. cursor/* is not proof of cloud vs this PC.")}</p>',
    ]
    if not rows:
        bits.append('<p class="absent">Claims board carries no ticket rows.</p>')
        return "".join(bits)
    seated = [r for r in rows if r.get("role") == "SEATED"]
    unseated = [r for r in rows if r.get("role") == "UNSEATED"]
    other = [r for r in rows if r.get("role") not in {"SEATED", "UNSEATED"}]

    def col(title: str, items: list[dict[str, Any]]) -> str:
        cards = "".join(_seat_card(r) for r in items[:24]) or '<p class="absent">None.</p>'
        return f"<section class=\"kcol\"><h3>{_esc(title)} {len(items)}</h3>{cards}</section>"

    bits.append(
        '<div class="kanban">'
        + col("SEATED", seated)
        + col("UNSEATED", unseated)
        + col("held / other", other)
        + "</div>"
    )
    return "".join(bits)


def _surfaces_body(d: Any) -> str:
    d = d or {}
    bits: list[str] = [
        f'<p class="absent">{_esc(d.get("note") or "present/absent only.")}</p>'
    ]
    rows = d.get("rows") or []
    if not rows:
        bits.append('<p class="absent">No desktop surfaces listed.</p>')
        return "".join(bits)
    bits.append("<table><tr><th>surface</th><th>this PC</th></tr>")
    for row in rows:
        present = "running" if row.get("present") else "not running"
        dot = "live" if row.get("present") else "down"
        bits.append(
            f'<tr><td><span class="dot {dot}">{_esc(row.get("name"))}</span></td>'
            f"<td>{_esc(present)}</td></tr>"
        )
    bits.append("</table>")
    return "".join(bits)


def _claude_pads_body(d: Any) -> str:
    d = d or {}
    pads = d.get("pads") or []
    bits: list[str] = [
        ("<p>Live <code>claude agents --json</code> on this PC. "
        "Control did not start Claude.</p>")
    ]
    if d.get("note"):
        bits.append(f'<p class="absent">{_esc(d.get("note"))}</p>')
    if not pads:
        bits.append('<p class="absent">No live Claude pads returned.</p>')
        return "".join(bits)
    bits.append("<table><tr><th>name</th><th>pid</th><th>kind</th><th>cwd</th></tr>")
    for pad in pads[:20]:
        bits.append(
            f"<tr><td>{_esc(pad.get('name'))}</td>"
            f"<td>{_esc(pad.get('pid'))}</td>"
            f"<td>{_esc(pad.get('kind'))}</td>"
            f"<td><code>{_esc(pad.get('cwd'))}</code></td></tr>"
        )
    bits.append("</table>")
    return "".join(bits)


def _runtime_body(d: Any) -> str:
    d = d or {}
    note = d.get("generated_note") or "watchdog snapshot"
    cls = "absent" if d.get("stale") or "could not parse" in str(note) else ""
    bits: list[str] = [f'<p class="{cls}">{_esc(note)}</p>']
    for title, key in (
        ("Alive (watchdog)", "alive"),
        ("Claude pads (watchdog)", "pads"),
        ("Open PRs writer guess (watchdog)", "prs"),
        ("Who this tick (watchdog)", "who"),
    ):
        items = d.get(key) or []
        bits.append(f"<p>{_esc(title)}</p>")
        if not items:
            bits.append(f'<p class="absent">No {_esc(key)} lines in snapshot.</p>')
            continue
        bits.append("<ul>")
        for item in items[:12]:
            bits.append(f"<li>{_esc(item)}</li>")
        bits.append("</ul>")
    return "".join(bits)


def _you_body(d: Any) -> str:
    d = d or {}
    steps = d.get("steps") or []
    bits: list[str] = [
        ("<p>You are the human in the loop. Click the URL. Do the step. "
        "Agents cannot check HT1/HT2 off. Control does not spawn them.</p>")
    ]
    if not steps:
        bits.append('<p class="absent">No YOU steps loaded.</p>')
        return "".join(bits)
    bits.append('<ol class="you-list">')
    for step in steps:
        kind = str(step.get("kind") or "you")
        url = str(step.get("url") or "")
        link = ""
        if url:
            link = (
                f'<a class="btn" href="{_esc(url)}" target="_blank" rel="noopener">'
                "Open this step</a>"
            )
        bits.append(
            f'<li class="you-step {html.escape(kind)}">'
            f'<span class="you-n">{_esc(step.get("n"))}</span>'
            "<div>"
            f"<strong>{_esc(step.get('title'))}</strong>"
            f"<p>{_esc(step.get('do'))}</p>"
            f"{link}"
            "</div></li>"
        )
    bits.append("</ol>")
    return "".join(bits)


def _pill(label: str, state: str, pill_id: str = "") -> str:
    id_attr = f' id="{html.escape(pill_id)}"' if pill_id else ""
    return f'<span class="pill {html.escape(state)}"{id_attr}>{_esc(label)}</span>'


def _peer_pill(name: str, reading: dict[str, Any], up_key: str = "up") -> str:
    if not reading.get("ok"):
        return _pill(f"{name} unknown", "warn")
    data = reading.get("data") or {}
    if data.get(up_key):
        return _pill(f"{name} up", "ok")
    return _pill(f"{name} down", "bad")


def _stat(reading: dict[str, Any], key: str, fallback: str = "?") -> str:
    if not reading.get("ok"):
        return fallback
    data = reading.get("data") or {}
    if not isinstance(data, dict) or key not in data:
        return fallback
    return str(data.get(key))


def _strip(state: dict[str, Any]) -> str:
    pickup = state.get("pickup") or {}
    fleet = state.get("fleet") or {}
    pads = state.get("claude_pads") or {}
    surfaces = state.get("surfaces") or {}
    pick_n = _stat(pickup, "count")
    seated = _stat(fleet, "seated")
    held = _stat(fleet, "held")
    pad_rows = (pads.get("data") or {}).get("pads") if pads.get("ok") else None
    pad_n = str(len(pad_rows)) if isinstance(pad_rows, list) else "?"
    surf_rows = (surfaces.get("data") or {}).get("rows") if surfaces.get("ok") else None
    live_n = "?"
    if isinstance(surf_rows, list):
        live_n = str(sum(1 for r in surf_rows if isinstance(r, dict) and r.get("present")))
    return (
        '<div class="strip" id="strip">'
        f'<a class="strip__cell" href="#pickup"><b>{_esc(pick_n)}</b><span>pickup</span></a>'
        f'<a class="strip__cell" href="#fleet"><b>{_esc(seated)}</b><span>seated</span></a>'
        f'<a class="strip__cell" href="#fleet"><b>{_esc(held)}</b><span>held</span></a>'
        f'<a class="strip__cell" href="#pads"><b>{_esc(pad_n)}</b><span>claude pads</span></a>'
        f'<a class="strip__cell" href="#pc"><b>{_esc(live_n)}</b><span>this PC live</span></a>'
        "</div>"
    )


def _rail_agents(state: dict[str, Any]) -> str:
    fleet = state.get("fleet") or {}
    if not fleet.get("ok"):
        return '<p class="absent">Fleet unread. GET /v1/fleet.</p>'
    rows = [
        r
        for r in ((fleet.get("data") or {}).get("rows") or [])
        if isinstance(r, dict) and r.get("role") == "SEATED"
    ]
    if not rows:
        return '<p class="absent">No seated writers.</p>'
    bits = ['<div class="rail-agents">']
    for row in rows[:12]:
        href = str(row.get("href") or "#fleet")
        bits.append(
            f'<a class="rail-agent" href="{_esc(href)}" target="_blank" rel="noopener"'
            f"{_data_attrs(row.get('ticket'), row.get('title') or row.get('ticket'), href)}>"
            f'<span class="dot live"></span>'
            f"<strong>{_esc(row.get('ticket'))}</strong>"
            f"<small>{_esc(row.get('lane') or '?')}</small></a>"
        )
    bits.append("</div>")
    return "".join(bits)


def _reading_n(reading: dict[str, Any], *keys: str) -> str:
    if not reading.get("ok"):
        return "?"
    data = reading.get("data") or {}
    if not isinstance(data, dict):
        return "?"
    if "count" in data and data.get("count") is not None:
        return str(data.get("count"))
    for key in keys:
        rows = data.get(key)
        if isinstance(rows, list):
            return str(len(rows))
    return "?"


def _howto(contract: dict[str, Any]) -> str:
    converse = ((contract.get("communication_layer") or {}).get("converse") or "http://127.0.0.1:8020")
    return (
        '<nav class="howto" id="howto" aria-label="Every agent seating steps">'
        "<strong>Every agent</strong>"
        '<a class="btn" href="/v1/contract">GET /v1/contract</a>'
        "<code>/v1/pickup</code> <code>/v1/fleet</code> <code>/v1/you</code>"
        "<span>then claim on GitHub. Cortex runs. Control does not assign. Crew "
        f'<a href="{_esc(converse)}" target="_blank" rel="noopener">:8020</a></span>'
        "</nav>"
    )


def render_page(state: dict[str, Any]) -> str:
    gate = state.get("gate") or {}
    passing = bool(gate.get("ok") and (gate.get("data") or {}).get("passing"))

    if not gate.get("ok"):
        banner = (
            '<div class="banner bad" id="gateBanner">Gate status UNKNOWN - checking GET /v1/gate. '
            "Treat the estate as unsafe to seat until this reads.</div>"
        )
        gate_pill = _pill("gate unknown", "warn", "gatePill")
    elif passing:
        banner = '<div class="banner ok" id="gateBanner">Estate gate PASSES</div>'
        gate_pill = _pill("gate pass", "ok", "gatePill")
    else:
        banner = (
            '<div class="banner bad" id="gateBanner">Estate gate FAILS - no writer may be seated '
            "until a human acts</div>"
        )
        gate_pill = _pill("gate fail", "bad", "gatePill")

    launchers = "".join(
        f"<li><code>{_esc(x['name'])}</code> - {_esc(x['blurb'])}</li>"
        for x in (state.get("launchers") or [])
    )
    pick = state.get("pickup") or {}
    board = state.get("board") or {}
    fleet = state.get("fleet") or {}

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Netie Control</title><style>{_css()}</style></head><body>
<a class="skip" href="#desk">Skip to pickup</a>
<div class="app">
<aside class="rail">
<p class="rail__wordmark">Netie Control<small>operator shell · plane 4</small></p>
<div class="pills">
{gate_pill}
{_peer_pill("cortex", state.get("cortex") or {{}})}
{_peer_pill("openvault", state.get("openvault") or {{}})}
</div>
<p class="rail__label">Seated</p>
{_rail_agents(state)}
<nav>
<a href="#pickup">Pickup</a>
<a href="#you">YOU</a>
<a href="#board">Board</a>
<a href="#fleet">Fleet</a>
</nav>
<p class="rail__label">Estate</p>
<nav>
<a href="#cortex">Cortex</a>
<a href="#pc">This PC</a>
<a href="#pads">Claude pads</a>
<a href="#runtime">Watchdog</a>
<a href="/constructor/">Constructor</a>
<a href="#vault">OpenVault</a>
<a href="#ship">Spaceship</a>
<a href="#crew">Crew belt</a>
<a href="#tools">Laptop tools</a>
<a href="#kb">Skill chest</a>
<a href="#gate">Gate</a>
</nav>
<p class="absent" style="color:var(--rail-muted)">Display and launch only.
No Paperclip brand. No Plane source. No third orchestrator.</p>
</aside>
<main class="stage">
<div class="pane__head">
<h1>Netie Control</h1>
<span class="live" id="liveDot">loopback</span>
<div class="toolbar">
<input id="filterQ" placeholder="Filter (Ctrl+K)" />
<button type="button" id="reload">Refresh</button>
<button type="button" id="openCrew">Crew chat</button>
</div>
</div>
{banner}
{_howto(state.get("contract") or {{}})}
{_strip(state)}
<div class="workbench" id="desk">
{_panel("Pickup", pick, _pickup_body, "", "pickup", _reading_n(pick, "items"))}
{_panel("Board", board, _board_body, "", "board", _reading_n(board, "items"))}
{_panel("Who is seated", fleet, _fleet_body, "", "fleet", _reading_n(fleet, "rows"))}
</div>
<details class="more" id="more">
<summary>More estate (Cortex, vault, gate, crew)</summary>
<div class="grid">
{_panel("Watchdog snapshot (RUNTIME.md)", state.get("runtime") or {{}}, _runtime_body, "", "runtime")}
{_panel("Cortex internals", state.get("cortex") or {{}}, _cortex_body, "", "cortex")}
{_panel("OpenVault / FreeRoute liveness", state.get("openvault") or {{}}, _openvault_body, "", "vault")}
{_panel("Spaceship host (reuse, do not buy)", state.get("spaceship") or {{}}, _spaceship_body, "", "ship")}
{_panel("Crew conveyor (display-only)", state.get("crew") or {{}}, _crew_belt_body, "", "crew")}
{_panel("Laptop tools (Crew health)", state.get("crew_health") or {{}}, _crew_health_body, "", "tools")}
{_panel("Skill chest (Netie-KB)", state.get("kb") or {{}}, _kb_body, "", "kb")}
{_gate_panel(gate)}
</div>
</details>
<footer class="legal">Holds no keys. Owns no route decision. Decides no work shape.
<code>/v1/secrets</code>, <code>/v1/route</code>, <code>/v1/goal</code> and
<code>/v1/run</code> answer 405 by design - see NETIE.md section 3.
Crew surface (converse lives there, not here):
<a href="http://127.0.0.1:8020">http://127.0.0.1:8020</a>
 - public name work.netie.ai is HUMAN_STOP.
Control <code>GET /v1/belt</code> is a display proxy of Crew JSON.
Control <code>GET /v1/fleet</code> is CLAIMS seats. <code>GET /v1/pickup</code> is unseated work. Control does not assign.
Skill chest is Netie-KB <code>:8030</code>. Custody is OpenVault, never this shell.</footer>
</main>
<aside class="inspector">
<div class="panel" id="protocol"><h2>Every agent</h2>
<p>1. <a href="/v1/contract">GET /v1/contract</a></p>
<p>2. Pickup, fleet, YOU. 3. Claim on GitHub. Cortex runs. Control does not assign.</p>
<p><a class="btn" href="#pickup">Pickup</a>
<a class="btn btn-ghost" href="https://github.com/Netie-AI/netie-control" target="_blank" rel="noopener">Public repo</a></p>
</div>
<div class="panel" id="focus"><h2>Selected ticket</h2>
<p id="focusEmpty">Click a pickup, board, fleet, or rail row. Control does not assign.</p>
<div id="focusBody" hidden>
<p><strong id="focusTicket"></strong></p>
<p id="focusTitle"></p>
<p><code id="focusHref"></code></p>
<p>
<a class="btn" id="focusOpen" target="_blank" rel="noopener">Open</a>
<a class="btn btn-ghost" id="focusComment" target="_blank" rel="noopener">Comment</a>
</p>
<p class="absent">Claim on GitHub, then CLAIMS.json. GET /v1/pickup. POST /v1/run stays 405.</p>
</div>
</div>
{_panel("YOU - founder actions", state.get("you") or {{}}, _you_body, "", "you")}
<div class="panel" id="feedback"><h2>If this feels wrong</h2>
<p>Comment on that GitHub issue. GitHub is the bus (W-0005). This page does not auto-route chat to an agent.</p>
<p><a class="btn" href="#pickup">Go to Pickup</a>
<a class="btn btn-ghost" href="#board">Board</a></p>
</div>
{_panel("This PC right now", state.get("surfaces") or {{}}, _surfaces_body, "", "pc")}
{_panel("Live Claude pads (this PC)", state.get("claude_pads") or {{}}, _claude_pads_body, "", "pads")}
<div class="panel" id="lanes"><h2>Local CLI lanes</h2><ul>{launchers}</ul>
<p class="absent">Display and launch only. Nothing here starts, restarts or kills
the founder's desktop software (R-0015).</p></div>
</aside>
</div>
<div class="crew-frame" id="crewFrame">
<div class="crew-frame__box">
<div class="crew-frame__head">
<strong>Crew chat (launch)</strong>
<button type="button" id="closeCrew">Close</button>
</div>
<iframe id="crewIframe" title="Cortex Crew" src="about:blank"></iframe>
</div>
</div>
<script>
(function () {{
  const ids = ["pickup","you","board","fleet","runtime","cortex","vault","ship","crew","tools","kb","gate"];
  function show(id, scroll) {{
    const target = ids.includes(id) ? id : "pickup";
    document.querySelectorAll(".stage .panel").forEach(function (p) {{
      p.classList.toggle("is-on", p.id === target);
    }});
    document.querySelectorAll(".rail nav a").forEach(function (a) {{
      const href = a.getAttribute("href") || "";
      a.classList.toggle("is-on", href === "#" + target);
    }});
    const el = document.getElementById(target);
    const more = document.getElementById("more");
    if (more && el && more.contains(el)) more.open = true;
    if (scroll && el) el.scrollIntoView({{ behavior: "smooth", block: "start" }});
  }}
  window.addEventListener("hashchange", function () {{
    show((location.hash || "#pickup").slice(1), true);
  }});
  show((location.hash || "").slice(1) || "pickup", Boolean(location.hash));
  function fillFocus(row) {{
    var href = row.getAttribute("data-href") || "";
    var ticket = row.getAttribute("data-ticket") || "";
    var title = row.getAttribute("data-title") || "";
    if (!href && !ticket) return;
    document.getElementById("focusEmpty").hidden = true;
    document.getElementById("focusBody").hidden = false;
    document.getElementById("focusTicket").textContent = ticket;
    document.getElementById("focusTitle").textContent = title;
    document.getElementById("focusHref").textContent = href;
    document.getElementById("focusOpen").href = href || "#";
    document.getElementById("focusComment").href = href || "#";
    document.querySelectorAll("[data-href]").forEach(function (el) {{
      el.classList.toggle("is-focus", el === row);
    }});
  }}
  document.addEventListener("click", function (ev) {{
    var row = ev.target.closest("[data-href]");
    if (!row || row.closest(".crew-frame")) return;
    fillFocus(row);
  }});
  document.getElementById("reload").onclick = function () {{ location.reload(); }};
  document.getElementById("openCrew").onclick = function () {{
    var frame = document.getElementById("crewFrame");
    var iframe = document.getElementById("crewIframe");
    iframe.src = "http://127.0.0.1:8020/";
    frame.classList.add("open");
  }};
  document.getElementById("closeCrew").onclick = function () {{
    document.getElementById("crewFrame").classList.remove("open");
    document.getElementById("crewIframe").src = "about:blank";
  }};
  document.getElementById("filterQ").addEventListener("input", function (ev) {{
    var q = (ev.target.value || "").toLowerCase();
    document.querySelectorAll(".stage table tr").forEach(function (row, i) {{
      if (i === 0) return;
      row.classList.toggle("is-hid", q && row.textContent.toLowerCase().indexOf(q) < 0);
    }});
    document.querySelectorAll(".seat-card, .ticket-card, .pickup-card, .work-row").forEach(function (card) {{
      card.classList.toggle("is-hid", q && card.textContent.toLowerCase().indexOf(q) < 0);
    }});
  }});
  document.addEventListener("keydown", function (e) {{
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {{
      e.preventDefault();
      document.getElementById("filterQ").focus();
    }}
    if (e.key === "Escape") document.getElementById("crewFrame").classList.remove("open");
  }});
  function esc(s) {{
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }}
  function gateBodyHtml(g) {{
    if (!g.ok) {{
      return '<p class="absent">Could not read this source: ' + esc(g.detail || "no reason given")
        + '</p><p class="absent">Source: <code>' + esc(g.source || "") + "</code></p>";
    }}
    var d = g.data || {{}};
    if (d.passing) return '<p style="color:var(--ok)">Gate passes. Seating is permitted.</p>';
    var items = (d.output || []).slice(0, 20).map(function (x) {{
      return '<li class="fail">' + esc(x) + "</li>";
    }}).join("");
    return '<p class="fail">Gate FAILS (exit ' + esc(d.exit_code) + "). "
      + "No writer may be seated until a human acts.</p><ul>" + items + "</ul>";
  }}
  fetch("/v1/gate").then(function (r) {{ return r.json(); }}).then(function (g) {{
    var banner = document.getElementById("gateBanner");
    var pill = document.getElementById("gatePill");
    var body = document.getElementById("gateBody");
    if (!banner || !pill || !body) return;
    if (!g.ok) {{
      banner.className = "banner bad";
      banner.textContent = "Gate status UNKNOWN - Control could not run it. Treat the estate as unsafe to seat until this reads.";
      pill.className = "pill warn";
      pill.textContent = "gate unknown";
    }} else if (g.data && g.data.passing) {{
      banner.className = "banner ok";
      banner.textContent = "Estate gate PASSES";
      pill.className = "pill ok";
      pill.textContent = "gate pass";
    }} else {{
      banner.className = "banner bad";
      banner.textContent = "Estate gate FAILS - no writer may be seated until a human acts";
      pill.className = "pill bad";
      pill.textContent = "gate fail";
    }}
    body.innerHTML = gateBodyHtml(g);
  }}).catch(function () {{}});
}})();
</script>
</body></html>"""
