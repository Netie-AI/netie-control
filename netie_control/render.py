"""Render the operator page.

One rule shapes all of this: an unreachable source renders as a stated absence, never
as an empty panel. An empty panel and a healthy-but-quiet panel look identical, and the
operator cannot tell which they are looking at (R-0011).
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from netie_control.sources import constructor_live_url, constructor_seeds

_CSS_PATH = Path(__file__).with_name("static") / "control.css"


def _css() -> str:
    try:
        return _CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return "body{background:#050506;color:#e7ebe2}"


def _esc(x: Any) -> str:
    return html.escape(str(x))


def _named_absence(detail: Any, source: Any, extra: str = "") -> str:
    bits = [
        "<ol class=\"steps\">",
        f'<li class="absent">Could not read this source: {_esc(detail or "no reason given")}</li>',
        f'<li class="absent">Source: <code>{_esc(source or "")}</code></li>',
    ]
    if extra:
        bits.append(f"<li>{extra}</li>")
    bits.append("</ol>")
    return "".join(bits)


def _panel(title: str, reading: dict[str, Any], body_fn, extra: str = "", panel_id: str = "", count: str = "") -> str:
    """Render one source. If it could not be read, say so instead of showing nothing."""
    cls = "panel" + (f" {extra}" if extra else "")
    id_attr = f' id="{html.escape(panel_id)}"' if panel_id else ""
    badge = f' <span class="count">{_esc(count)}</span>' if count else ""
    wrap_id = f"{panel_id}Body" if panel_id in {"pickup", "board", "pads", "plans", "prompts", "openide", "pointer", "stage"} else ""
    wrap_open = f'<div id="{html.escape(wrap_id)}">' if wrap_id else ""
    wrap_close = "</div>" if wrap_id else ""
    if not reading.get("ok"):
        extra_step = ""
        if panel_id == "pickup":
            extra_step = "Claim on GitHub. Control does not assign. POST /v1/run stays 405."
        elif panel_id == "crew":
            extra_step = (
                'Talk is Crew <a href="http://127.0.0.1:8020">http://127.0.0.1:8020</a>. '
                "Control does not converse. Control does not POST wakes."
            )
        return (
            f'<div class="{cls}"{id_attr}><h2>{_esc(title)}{badge}</h2>'
            f"{wrap_open}"
            f"{_named_absence(reading.get('detail'), reading.get('source'), extra_step)}"
            f"{wrap_close}</div>"
        )
    return (
        f'<div class="{cls}"{id_attr}><h2>{_esc(title)}{badge}</h2>'
        f"{wrap_open}{body_fn(reading.get('data'))}{wrap_close}</div>"
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


def _named_omission(d: dict[str, Any]) -> str:
    """Truncation and deny-regex skips must be named, never a quiet slice."""
    bits: list[str] = []
    if d.get("truncated"):
        shown = d.get("shown") or d.get("count") or len(d.get("items") or [])
        cap = d.get("cap") or shown
        bits.append(
            '<p class="absent">Truncated: showing '
            f"{_esc(shown)} at cap {_esc(cap)}. Not a quiet omission.</p>"
        )
    skipped = [str(x) for x in (d.get("skipped") or []) if x]
    if skipped:
        bits.append(
            '<p class="absent">Skipped by deny regex: '
            + _esc("; ".join(skipped))
            + "</p>"
        )
    return "".join(bits)


def _board_body(d: dict[str, Any]) -> str:
    rows = [r for r in (d.get("items") or []) if isinstance(r, dict)]
    bits: list[str] = [
        "<p>GitHub Issues are SoT. Open, then comment there. Control does not assign.</p>"
    ]
    query = d.get("query")
    if query:
        bits.append(f"<p>Owner scan <code>{_esc(query)}</code>.</p>")
    bits.append(_named_omission(d))
    if not rows:
        bits.append('<p class="absent">No open items returned.</p>')
    else:
        by_repo: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            by_repo.setdefault(str(r.get("repo") or "?"), []).append(r)
        cols = []
        for repo, items in by_repo.items():
            cards = "".join(_ticket_card(x) for x in items)
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


def public_board_page(reading: dict[str, Any], *, built_at: str = "") -> str:
    """Static org board for GitHub Pages. Display only. Issues stay SoT."""
    reading = reading if isinstance(reading, dict) else {}
    ok = bool(reading.get("ok"))
    data = reading.get("data") if isinstance(reading.get("data"), dict) else {}
    if ok:
        inner = _board_body(data)
    else:
        inner = (
            '<p class="absent">Board unread: '
            f'{_esc(reading.get("detail") or "no reason given")}</p>'
            '<p class="absent">Source: <code>'
            f'{_esc(reading.get("source") or "")}</code></p>'
        )
    built = ""
    if built_at:
        built = (
            f"<p>Page built <code>{_esc(built_at)}</code>. "
            "GitHub Issues are SoT. This page is a view, not a second ticket list.</p>"
        )
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Netie Control public board</title>"
        "<style>body{margin:1rem;font:14px/1.4 ui-sans-serif,system-ui,sans-serif;"
        "background:#111;color:#e7ebe2}a{color:#8ab4ff}.absent{color:#c9a227}"
        ".kanban{display:flex;gap:1rem;align-items:flex-start;overflow:auto}"
        ".kcol{min-width:16rem;flex:1}"
        ".work-row{margin:0.4rem 0;padding:0.4rem 0;border-bottom:1px solid #333}"
        ".btn{display:inline-block;margin-right:0.3rem}code{font-size:12px}</style>"
        "</head><body><h1>Netie-AI open tasks</h1>"
        f"{built}"
        "<p>Control does not assign. Claim on the GitHub issue. "
        "POST /v1/run stays 405. PRD/Epic/Ticket minting stays Cortex "
        "Ticket Runner, not this page (F-0030).</p>"
        f"{inner}"
        '<p>Repo <a href="https://github.com/Netie-AI/netie-control">'
        "Netie-AI/netie-control</a>. Local desk "
        "<code>http://127.0.0.1:8040/#board</code>.</p>"
        "</body></html>"
    )


def _pickup_body(d: Any) -> str:
    d = d or {}
    items = [r for r in (d.get("items") or []) if isinstance(r, dict)]
    bits: list[str] = [
        "<p>Pickup - claim on GitHub. Control does not assign.</p>",
        '<ol class="steps">',
        "<li>Open the GitHub issue and comment that you are seating.</li>",
        "<li>Write CLAIMS.json. Then /ticket-runner in Claude Code. Control does not spawn.</li>",
        "<li>Cortex runs. POST /v1/run stays 405.</li>",
        "</ol>",
        f'<p class="absent">{_esc(d.get("rule") or "")}</p>',
        _named_omission(d),
    ]
    if d.get("board_deferred"):
        bits.append(
            '<p class="absent">Board deferred: '
            f'{_esc(d.get("board_detail") or "unread")}. '
            f'Source: <code>{_esc(d.get("board_source") or "GET /v1/board")}</code>. '
            "Live issues are GET /v1/board. This tray is CLAIMS unseated.</p>"
        )
    if not items:
        bits.append(
            '<p class="absent">No unseated CLAIMS items. Fleet empty or unread. '
            "Board is not required for this tray.</p>"
        )
        return "".join(bits)
    rows_html = []
    for r in items:
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


def _plans_body(d: Any) -> str:
    d = d or {}
    analog = [r for r in (d.get("analog") or []) if isinstance(r, dict)]
    items = [r for r in (d.get("items") or []) if isinstance(r, dict)]
    bits: list[str] = [
        "<p>Incomplete plans - analog lifts and parked lots. Control does not unpark or copy.</p>",
        '<ol class="steps">',
        "<li>DISTILL/PARK rows are remaining work on the live product named in the row.</li>",
        "<li>BAN/SKIP means the clone stays frozen. Do not paste analog reconstructions, AGPL, GPL, or leaked trees.</li>",
        "<li>Claim on GitHub. POST /v1/run stays 405. Cortex runs.</li>",
        "</ol>",
        f'<p class="absent">{_esc(d.get("rule") or "")}</p>',
    ]
    present = d.get("analog_present")
    absent = d.get("analog_absent")
    bits.append(
        f"<p>Analog trees present <code>{_esc(present)}</code>. "
        f"Absent <code>{_esc(absent)}</code>. "
        f"Open <code>{_esc(d.get('open'))}</code>"
        + (" none." if d.get("none") else ".")
        + " Laptop fetch analog leftover is GET /v1/fetch analog_next. "
        "Control does not seat. Ontology stays Cortex. P1 parked."
        "</p>"
    )
    beat = [r for r in (d.get("heartbeat") or []) if isinstance(r, dict)]
    if beat:
        bits.append(
            "<p>Heartbeat labels (no extra probe). Control does not start peers.</p>"
        )
        rows = [
            "<table><tr><th>product</th><th>href</th><th>role</th></tr>"
        ]
        for row in beat[:8]:
            rows.append(
                "<tr><td>"
                f"{_esc(row.get('product'))}</td>"
                f"<td><code>{_esc(row.get('href'))}</code></td>"
                f"<td>{_esc(row.get('role'))}</td></tr>"
            )
        rows.append("</table>")
        bits.append("".join(rows))
    if d.get("parking_unread"):
        bits.append(
            '<p class="absent">Parking unread: '
            + _esc("; ".join(str(x) for x in d["parking_unread"]))
            + "</p>"
        )
    if analog:
        rows = [
            "<table><tr><th>lane</th><th>name</th><th>surface</th><th>home</th><th>verdict</th></tr>"
        ]
        for row in analog:
            tree = str(row.get("tree") or "unread")
            cls = "absent" if tree == "absent" else ""
            label = row.get("name") or row.get("product")
            rows.append(
                f'<tr class="{cls}"><td>{_esc(row.get("lane"))}</td>'
                f"<td>{_esc(label)}</td><td>{_esc(row.get('surface'))}</td>"
                f"<td><code>{_esc(row.get('home'))}</code></td>"
                f"<td>{_esc(row.get('verdict'))}</td></tr>"
            )
        rows.append("</table>")
        bits.append("".join(rows))
    if not items:
        bits.append('<p class="absent">Incomplete plans none.</p>')
        return "".join(bits)
    work = []
    for row in items[:40]:
        if row.get("kind") == "parking":
            label = f"{row.get('id')} {row.get('title')}"
            tag = row.get("state") or "parked"
        else:
            label = (
                f"{row.get('name') or row.get('product')} "
                f"({row.get('surface')}) -> {row.get('home') or row.get('path')}"
            )
            tag = row.get("verdict") or row.get("tree") or "open"
        work.append(
            f'<div class="work-row"><code>{_esc(row.get("lane") or row.get("id"))}</code>'
            f'<span class="work-row__title">{_esc(label)}</span>'
            f'<span class="tags"><span class="tag">{_esc(tag)}</span></span></div>'
        )
    bits.append(f'<div class="work-list">{"".join(work)}</div>')
    return "".join(bits)


def _prompts_body(d: Any) -> str:
    d = d or {}
    items = [r for r in (d.get("items") or []) if isinstance(r, dict)]
    pastes = [r for r in (d.get("pastes") or []) if isinstance(r, dict)]
    bits: list[str] = [
        "<p>Prompt surfaces and Crew paste briefs. Control lists them. It does not spawn or edit a charter.</p>",
        '<ol class="steps">',
        "<li>Paste grok-master, then prd-agent. Then at most two writer pastes (WIP cap 2).</li>",
        "<li>Reuse analog segments in the live product. Do not redesign UI tokens or layout DNA. ALREADY rows are live Crew/Cortex files.</li>",
        "<li>DISTILL is ideas only. Do not paste Anthropic prompt strings. BAN trees stay frozen. POST /v1/run stays 405.</li>",
        "</ol>",
        f'<p class="absent">{_esc(d.get("rule") or "")}</p>',
    ]
    if pastes:
        work = []
        for row in pastes:
            work.append(
                f'<div class="work-row"><code>{_esc(row.get("id"))}</code>'
                f'<span class="work-row__title">{_esc(row.get("product"))} ({_esc(row.get("wip"))})</span>'
                f'<span class="tags"><span class="tag">paste</span></span></div>'
                f"<pre>{_esc((row.get('paste') or '')[:1200])}</pre>"
            )
        bits.append(f'<div class="work-list">{"".join(work)}</div>')
    if not items:
        bits.append('<p class="absent">Prompt surfaces none.</p>')
        return "".join(bits)
    work = []
    for row in items:
        files = row.get("files") or []
        extra = f" files {', '.join(str(x) for x in files[:8])}" if files else ""
        label = f"{row.get('path')} -> {row.get('product')}{extra}"
        work.append(
            f'<div class="work-row"><code>{_esc(row.get("id"))}</code>'
            f'<span class="work-row__title">{_esc(label)}</span>'
            f'<span class="tags"><span class="tag">{_esc(row.get("verdict"))}</span>'
            f'<span class="tag">{_esc(row.get("tree"))}</span></span></div>'
        )
    bits.append(f'<div class="work-list">{"".join(work)}</div>')
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
    features = d.get("features")
    if features is None:
        bits.append(
            f'<p class="absent">Features: {_esc(d.get("features_detail") or "unread")}</p>'
        )
    else:
        ver = features.get("engine_version") if isinstance(features, dict) else None
        if ver:
            bits.append(f"<p>engine <code>{_esc(ver)}</code></p>")
        extras = features.get("extras") if isinstance(features, dict) else None
        if isinstance(extras, dict) and extras.get("agentic") is True:
            bits.append("<p>features.extras.agentic=true (Cortex actions. Ontology stays Cortex).</p>")
    insights = d.get("insights") if isinstance(d.get("insights"), dict) else None
    if insights:
        bits.append(
            "<p>Constructor ontology (display): "
            f"view={_esc(insights.get('constructor_view'))} "
            f"pack={_esc(insights.get('pack'))} "
            f"p1={_esc(insights.get('p1'))}. "
            "Control holds no viewer key. POST /v1/run stays 405.</p>"
        )
        if insights.get("constructor_view") == "gated":
            bits.append(
                f'<p class="absent">{_esc(insights.get("constructor_detail") or "Control holds no viewer key")}. '
                "Ask Cortex with a viewer key. Ontology stays Cortex. P1 parked.</p>"
            )
        lite = insights.get("constructor_seeds") if isinstance(insights.get("constructor_seeds"), dict) else None
        if not lite:
            lite = insights.get("palantir_lite") if isinstance(insights.get("palantir_lite"), dict) else None
        if not lite:
            lite = constructor_seeds()
        bits.append(
            "<p>Constructor seeds (generate, p1="
            f"{_esc(lite.get('p1'))}): define data, govern agents, "
            "business insights. DMS Ontology opens Constructor canvas. "
            "Control does not POST generate.</p>"
        )
        onto = insights.get("ontology") if isinstance(insights.get("ontology"), dict) else None
        if onto:
            bits.append(
                "<p>ontology counts "
                f"objects={_esc(onto.get('object_count'))} "
                f"actions={_esc(onto.get('action_count'))} "
                f"fetch_places={_esc(onto.get('fetch_place_count'))}</p>"
            )
    activity = d.get("activity")
    if activity is None:
        bits.append(
            f'<p class="absent">Activity: {_esc(d.get("activity_detail") or "unread")}</p>'
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
    live = _esc(d.get("constructor_live") or constructor_live_url())
    bits.append(
        "<p>Constructor flow (this shell launches the skin, Cortex is the engine): "
        '<a href="/constructor/">/constructor/</a> sketch · '
        f'<a href="{live}">{live}</a> live. '
        "Constructor seeds on the sketch: Define data, Govern agents, Insights. "
        "P1 stays parked. Control does not POST generate.</p>"
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
    usage = d.get("usage") if isinstance(d.get("usage"), dict) else None
    if usage:
        summary = usage.get("summary") if isinstance(usage.get("summary"), dict) else {}
        bits.append(
            "<p>FreeRoute usage (display). Control did not pick a route. "
            f"priced={_esc(summary.get('priced'))}. "
            "estimated_tokens is labelled separately. Do not invent prices.</p>"
        )
        shown = " ".join(
            f"{_esc(k)}={_esc(v)}"
            for k, v in summary.items()
            if k != "priced"
        )
        if shown:
            bits.append(f"<p>{shown}</p>")
    else:
        bits.append(
            f'<p class="absent">OpenVault usage unread. '
            f"{_esc(d.get('usage_detail') or 'usage unread')}. "
            "Control does not invent spend.</p>"
        )
    register = d.get("register") if isinstance(d.get("register"), dict) else None
    if register:
        bits.append(
            "<p>Free register help (display). Control did not mint a key. "
            f"priced={_esc(register.get('priced'))}. "
            "Open register_url then POST /api/keys on OpenVault :5000. "
            "Do not start :3010 from Control.</p>"
        )
        if register.get("help"):
            bits.append(f'<p class="absent">{_esc(register.get("help"))}</p>')
        for step in register.get("next_steps") or []:
            if not isinstance(step, dict):
                continue
            bits.append(f"<p><code>{_esc(step.get('do'))}</code></p>")
        ladder = register.get("ladder") if isinstance(register.get("ladder"), list) else []
        if ladder:
            shown = " ".join(
                f"{_esc(row.get('kind'))}:{_esc(row.get('id'))}"
                for row in ladder[:8]
                if isinstance(row, dict)
            )
            bits.append(
                f"<p>Free ladder (display, local first): {shown}. "
                "Control did not pick a route. Do not invent prices.</p>"
            )
        # priced stays false; ladder ids only
    else:
        bits.append(
            f'<p class="absent">OpenVault register help unread. '
            f"{_esc(d.get('register_detail') or 'unread')}. "
            "Control does not auto-register.</p>"
        )
    ship = d.get("ship") if isinstance(d.get("ship"), dict) else None
    if ship:
        bits.append(
            "<p>OpenShip (display). Control did not publish. "
            f"openship={_esc(ship.get('openship_effective') or ship.get('mode'))} "
            f"gate={_esc(ship.get('human_test_gate'))} "
            f"live_url_observed={_esc(ship.get('live_url_observed'))} "
            f"targets={_esc(ship.get('target_count'))} "
            f"tabs={_esc(' '.join(str(t) for t in (ship.get('tabs') or [])[:8]))}. "
            f"{_esc(ship.get('rule') or 'Control does not publish.')}</p>"
        )
    else:
        bits.append(
            f'<p class="absent">OpenVault ship unread. '
            f"{_esc(d.get('ship_detail') or 'unread')}. "
            "Publish stays OpenVault :5000. Do not start :3010 from Control.</p>"
        )
    play = d.get("playground") if isinstance(d.get("playground"), dict) else None
    if play:
        href = play.get("href") or "http://127.0.0.1:3010/"
        vault = play.get("vault") or "http://127.0.0.1:3010/vault"
        playground = play.get("playground") or "http://127.0.0.1:3010/playground"
        if play.get("up"):
            bits.append(
                f'<p style="color:var(--ok)">OpenVault app ok. '
                f'<a href="{_esc(href)}">{_esc(href)}</a> '
                f'<a href="{_esc(vault)}">/vault</a> '
                f'<a href="{_esc(playground)}">/playground</a>. '
                "Control did not start :3010.</p>"
            )
        else:
            bits.append(
                f'<p class="absent">OpenVault app unread. '
                f"{_esc(play.get('detail') or 'unread')}. "
                "npm run dev in D:\\OpenVault\\apps\\web. "
                "Control does not start :3010.</p>"
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
    if d.get("engine_ok"):
        bits.append(
            '<p style="color:var(--ok)">Crew engine ping ok '
            f"(<code>{_esc(d.get('engine_url') or 'ok')}</code>). "
            "Control does not start Cortex.</p>"
        )
    else:
        why = d.get("engine_detail") or "not ok"
        bits.append(
            f'<p class="absent">Crew engine ping: {_esc(why)}. '
            "Control does not start Cortex.</p>"
        )
    return "".join(bits)


def _crew_sidecar_body(d: Any) -> str:
    d = d or {}
    converse = _esc(d.get("converse") or "http://127.0.0.1:8023")
    fork = _esc(d.get("fork") or "http://127.0.0.1:8020")
    bits: list[str] = [
        "<p>Engine Crew sidecar. Hung converse stays "
        f'<a href="{fork}">{fork}</a>. Agents must not kill it (R-0015).</p>',
        f'<p>Talk here: <a href="{converse}">{converse}</a></p>',
        f'<p class="absent">{_esc(d.get("rule") or "")}</p>',
    ]
    cc = d.get("computer_control")
    if cc:
        bits.append(
            '<p style="color:var(--ok)">Sidecar computer_control flag is on. '
            "UACC is the OS mouse. Control does not click.</p>"
        )
    else:
        bits.append(
            '<p class="absent">Sidecar computer_control flag unread or off. '
            "Control will not set CORTEX_COMPUTER_CONTROL.</p>"
        )
    if d.get("grok_offloaded"):
        bits.append("<p>Crew owns converse. Reconstruction exe stays off (R-0015).</p>")
    if d.get("engine_ok"):
        bits.append(
            '<p style="color:var(--ok)">Sidecar engine ping ok '
            f"(<code>{_esc(d.get('engine_url') or 'ok')}</code>).</p>"
        )
    else:
        bits.append(
            f'<p class="absent">Sidecar engine ping: {_esc(d.get("engine_detail") or "unread")}.</p>'
        )
    wakes_view = d.get("wakes_view")
    if wakes_view == "none":
        bits.append(
            '<p class="absent">Wakes none. Sidecar tick is running. Control does not POST wakes.</p>'
        )
    elif wakes_view == "present":
        bits.append(
            f"<p>Wakes present n={_esc(d.get('wakes_n'))}. Crew owns the tick. "
            "Control does not POST wakes.</p>"
        )
    else:
        bits.append(
            f'<p class="absent">Wakes unread. {_esc(d.get("wakes_detail") or "GET /crew/wakes")}. '
            "Control does not POST wakes.</p>"
        )
    tick = d.get("wake_tick_at")
    if tick:
        bits.append(
            f'<p class="absent">Wake loop last tick {_esc(tick)}. '
            "Empty wakes is none, not unread.</p>"
        )
    return "".join(bits)


def _openide_body(d: Any) -> str:
    d = d or {}
    bits: list[str] = [
        "<p>AirGPT OpenIDE. Control lists liveness. It does not run the IDE or mint keys.</p>"
    ]
    href = d.get("href") or "http://127.0.0.1:8765/OpenIDE/ui/"
    if d.get("up"):
        bits.append(
            f'<p style="color:var(--ok)">OpenIDE host ok '
            f"(<code>{_esc(d.get('service') or 'airgpt')}</code>). "
            f'<a href="{_esc(href)}">{_esc(href)}</a></p>'
        )
    else:
        bits.append(
            '<p class="absent">OpenIDE unread. GET /v1/openide. '
            "Start D:\\AirGPT clipdrop.py with AIRGPT_NO_BROWSER=1. "
            "Do not start OpenFree :20128.</p>"
        )
    ready = d.get("ready") if isinstance(d.get("ready"), dict) else None
    if ready:
        missing = ready.get("missing") or []
        bits.append(
            f"<p>ready ok={_esc(ready.get('ok'))} backend={_esc(ready.get('backend'))}"
            f" usable={_esc(ready.get('usable_count'))}"
            f"{' missing ' + _esc(', '.join(str(x) for x in missing[:8])) if missing else ''}</p>"
        )
    elif d.get("ready_detail"):
        bits.append(f'<p class="absent">OpenIDE ready: {_esc(d.get("ready_detail"))}</p>')
    if d.get("rule"):
        bits.append(f'<p class="absent">{_esc(d.get("rule"))}</p>')
    leftover = d.get("leftover") or "OpenIDE leftover TUI. SKIP second IDE."
    bits.append(
        f'<p class="absent">Leftover: {_esc(leftover)} POST /v1/run stays 405.</p>'
    )
    return "".join(bits)


def _pointer_body(d: Any) -> str:
    d = d or {}
    bits: list[str] = [
        "<p>Pointer HUD + Cortex POST /dms/secure. UACC is the only OS mouse. "
        "Control does not start Pointer (R-0015).</p>"
    ]
    if d.get("confirm_gated"):
        bits.append(
            '<p style="color:var(--ok)">plan-guard launches set _requireConfirm. '
            f"nod_confirm={_esc(d.get('nod_confirm'))}.</p>"
        )
    else:
        bits.append(
            f'<p class="absent">Pointer confirm gate unread. GET /v1/pointer. '
            f"{_esc(d.get('detail') or 'unread')}</p>"
        )
    if d.get("up"):
        bits.append('<p style="color:var(--ok)">Pointer.exe present on this PC.</p>')
    else:
        bits.append(
            '<p class="absent">Pointer not running. Founder starts D:\\Pointer. '
            "Control will not.</p>"
        )
    if d.get("rule"):
        bits.append(f'<p class="absent">{_esc(d.get("rule"))}</p>')
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
        ('<p>Display-only of Crew conveyor JSON (<code>/v1/belt</code> or '
        "<code>/crew/belt</code>). "
        "Control does not converse (NETIE.md is still display-and-launch). "
        "Crew surface (converse + handoff): "
        '<a href="http://127.0.0.1:8020">http://127.0.0.1:8020</a></p>'),
        '<ol class="steps">',
        "<li>This panel is Crew JSON. Control does not hand off.</li>",
        "<li>Talk stays on Crew :8020. No converse form here.</li>",
        "<li>Wakes listed when Crew JSON has them. Control does not POST wakes.</li>",
        ("<li>Belt unread means live :8020 is still the Cortex-crew fork. "
        "YOU step 8: you start python -m CortexOS.crew from E:\\Cortex. "
        "Agents do not restart it (R-0015).</li>"),
        "</ol>",
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
    wakes = d.get("wakes") or []
    if wakes:
        bits.append(
            "<p>wakes (Crew owns the tick. Control does not POST wakes.)</p>"
            "<table><tr><th>kind</th><th>state</th><th>note</th></tr>"
        )
        for wake in wakes[:20]:
            bits.append(
                "<tr>"
                f"<td>{_esc(wake.get('kind'))}</td>"
                f"<td>{_esc(wake.get('state'))}</td>"
                f"<td>{_esc(wake.get('note'))}</td>"
                "</tr>"
            )
        bits.append("</table>")
    else:
        bits.append(
            '<p class="absent">wakes none (Crew tick idle). '
            "Control does not POST wakes.</p>"
        )
    queue = d.get("queue") if isinstance(d.get("queue"), dict) else {}
    if queue:
        bits.append(
            "<p>queue (Crew owns leases. Control does not POST.)</p><ul>"
        )
        for key, val in list(queue.items())[:8]:
            bits.append(f"<li><code>{_esc(key)}</code> {_esc(val)}</li>")
        bits.append("</ul>")
    else:
        bits.append(
            '<p class="absent">queue none. Crew owns leases. Control does not POST.</p>'
        )
    confirms = d.get("confirms") or []
    bits.append(
        f"<p>HITL pending={_esc(len(confirms))}. Decide on Crew :8020. "
        "Control does not approve.</p>"
    )
    spaces = d.get("spaces") or []
    agents = d.get("agents") or []
    if spaces or agents:
        bits.append(
            f"<p>spaces={_esc(len(spaces))} agents={_esc(len(agents))}. "
            "Roster is Crew's. Control does not spawn.</p>"
        )
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
    elif str(cortex.get("detail") or "") == "not probed":
        bits.append(
            "<p>Crew belt does not ping Cortex. Laptop-tools engine_ok is the live probe.</p>"
        )
    elif cortex:
        bits.append(
            f'<p class="absent">Crew Cortex ping: {_esc(cortex.get("detail") or "unread")}</p>'
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


def _coordinate_body(d: Any) -> str:
    d = d or {}
    bits: list[str] = [
        f'<p class="absent">{_esc(d.get("note") or "Control displays who to invoke.")}</p>',
        '<ol class="steps">',
        "<li>Owners invoke. Control displays this map. Control does not spawn.</li>",
        "<li>Talk is Crew :8020. POST /v1/run stays 405.</li>",
        "<li>Talk unread: YOU step 8 binds :8020 to E:\\Cortex. Agents do not restart it.</li>",
        "</ol>",
        ('<p><a class="btn" href="/v1/coordinate">GET /v1/coordinate</a> '
        '<a class="btn btn-ghost" href="/v1/contract">GET /v1/contract</a></p>'),
    ]
    lanes = d.get("lanes") or []
    if not lanes:
        bits.append('<p class="absent">No coordinate lanes. GET /v1/coordinate unread or empty.</p>')
        return "".join(bits)
    bits.append('<div class="coord">')
    n = 0
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        n += 1
        live = bool(lane.get("live"))
        dot = "live" if live else "down"
        state = "live" if live else "absent"
        extra = ""
        if lane.get("count") is not None:
            extra = f' · {_esc(lane.get("count"))} pads'
        counts = lane.get("counts") if isinstance(lane.get("counts"), dict) else {}
        if counts:
            extra += " · " + " ".join(f"{_esc(k)}={_esc(v)}" for k, v in counts.items())
        href = str(lane.get("href") or "#")
        bits.append(
            f'<a class="coord__row" href="{_esc(href)}">'
            f'<span class="coord__n">{n}</span>'
            f'<span class="dot {dot}"></span>'
            f"<span><strong>{_esc(lane.get('job'))}</strong>"
            f"<small>{_esc(lane.get('owner'))} -> {_esc(lane.get('invoke'))}{extra}</small>"
            f"<small>{_esc(lane.get('do_not') or '')}</small></span>"
            f"<em>{state}</em></a>"
        )
    bits.append("</div>")
    mates = d.get("teammates") or []
    if mates:
        bits.append("<p><strong>Teammates</strong> (named roster. Owners invoke.)</p>")
        bits.append('<div class="coord">')
        for mate in mates[:24]:
            if not isinstance(mate, dict):
                continue
            live = bool(mate.get("live"))
            dot = "live" if live else "down"
            extra = ""
            if mate.get("pickup") is not None:
                extra = f' · pickup {_esc(mate.get("pickup"))}'
            if mate.get("lane"):
                extra += f' · {_esc(mate.get("lane"))}'
            bits.append(
                f'<a class="coord__row" href="{_esc(mate.get("href") or "#")}">'
                f'<span class="coord__n"></span>'
                f'<span class="dot {dot}"></span>'
                f"<span><strong>{_esc(mate.get('name'))}</strong>"
                f"<small>{_esc(mate.get('kind'))} -> {_esc(mate.get('invoke'))}{extra}</small>"
                f"<small>{_esc(mate.get('do_not') or '')}</small></span>"
                f"<em>{'live' if live else 'absent'}</em></a>"
            )
        bits.append("</div>")
    router = d.get("router") if isinstance(d.get("router"), dict) else {}
    if router.get("note"):
        bits.append(f'<p class="absent">{_esc(router.get("note"))}</p>')
    return "".join(bits)


def _coord_chips(reading: dict[str, Any]) -> str:
    """First-viewport invoke chips. Inspector holds the long form."""
    if not reading.get("ok"):
        return (
            '<p class="absent" id="coordChips">Coordinate unread. GET /v1/coordinate.</p>'
        )
    data = reading.get("data") or {}
    lanes = data.get("lanes") or []
    if not lanes:
        return '<p class="absent">No coordinate lanes.</p>'
    bits = ['<div class="coord-chips" id="coordChips" aria-label="Invoke owners">']
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        live = "live" if lane.get("live") else "down"
        href = str(lane.get("href") or "#coordinate")
        bits.append(
            f'<a class="coord-chip {live}" href="{_esc(href)}" '
            f'title="{_esc(lane.get("do_not") or "")}">'
            f'<span class="dot {live}"></span>{_esc(lane.get("job"))}</a>'
        )
    shown = 0
    for mate in data.get("teammates") or []:
        if not isinstance(mate, dict):
            continue
        if mate.get("kind") not in {"seater", "talk", "run", "pad", "task"}:
            continue
        if shown >= 8:
            break
        shown += 1
        live = "live" if mate.get("live") else "down"
        bits.append(
            f'<a class="coord-chip {live}" href="{_esc(mate.get("href") or "#coordinate")}" '
            f'title="{_esc(mate.get("do_not") or "")}">'
            f'<span class="dot {live}"></span>{_esc(mate.get("name"))}</a>'
        )
    bits.append("</div>")
    return "".join(bits)


def _workers_chips(reading: dict[str, Any]) -> str:
    """First-viewport live workers. Unread Cortex/Crew is named, never idle-green."""
    if not reading.get("ok"):
        return '<p class="absent" id="workers">Workers unread. GET /v1/coordinate.</p>'
    workers = (reading.get("data") or {}).get("workers") or []
    if not workers:
        return (
            '<p class="absent" id="workers">No live Cortex workflows or armed Crew MCPs this tick.</p>'
        )
    bits = ['<div class="coord-chips" id="workers" aria-label="Live workers">']
    for row in workers[:12]:
        if not isinstance(row, dict):
            continue
        live = "live" if row.get("live") and not row.get("unread") else "down"
        bits.append(
            f'<a class="coord-chip {live}" href="{_esc(row.get("href") or "#cortex")}" '
            f'title="{_esc(row.get("do_not") or "")}">'
            f'<span class="dot {live}"></span>{_esc(row.get("kind"))} {_esc(row.get("name"))}</a>'
        )
    bits.append("</div>")
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
        if row.get("unread"):
            status, dot = "unread", "down"
        elif row.get("present"):
            status, dot = "running", "live"
        else:
            status, dot = "not running", "down"
        bits.append(
            f'<tr><td><span class="dot {dot}">{_esc(row.get("name"))}</span></td>'
            f"<td>{_esc(status)}</td></tr>"
        )
    bits.append("</table>")
    return "".join(bits)


def _stage_body(d: Any) -> str:
    d = d or {}
    bits: list[str] = [
        f'<p class="absent">{_esc(d.get("note") or "Backstage only.")}</p>'
    ]
    peers = d.get("peers") or []
    if not peers:
        bits.append('<p class="absent">No backstage listeners listed.</p>')
    else:
        bits.append("<table><tr><th>backend</th><th>port</th><th>owner</th><th>stage</th></tr>")
        for row in peers:
            if row.get("up"):
                status, dot = "listening", "live"
            else:
                status, dot = "down", "down"
            bits.append(
                f'<tr><td><span class="dot {dot}">{_esc(row.get("name"))}</span></td>'
                f"<td>{_esc(row.get('port'))}</td>"
                f"<td>{_esc(row.get('owner'))}</td>"
                f"<td>{_esc(status)}</td></tr>"
            )
        bits.append("</table>")
    popups = d.get("popups") or []
    bits.append("<p>Console popups (PowerShell). Owner is the parent process. Control does not hide or kill them.</p>")
    if not popups:
        bits.append('<p class="absent">No powershell.exe popups on the snapshot.</p>')
        return "".join(bits)
    bits.append("<table><tr><th>pid</th><th>image</th><th>parent</th><th>owner</th></tr>")
    for row in popups[:24]:
        bits.append(
            f"<tr><td>{_esc(row.get('pid'))}</td>"
            f"<td>{_esc(row.get('image'))}</td>"
            f"<td>{_esc(row.get('parent'))}</td>"
            f"<td>{_esc(row.get('owner'))}</td></tr>"
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


def _stat(reading: dict[str, Any], key: str, fallback: str = "unread") -> str:
    if not reading.get("ok"):
        return fallback
    data = reading.get("data") or {}
    if not isinstance(data, dict) or key not in data:
        return fallback
    return str(data.get(key))


def _strip_cell(
    href: str,
    ok: bool,
    value: str,
    label: str,
    *,
    cell_id: str = "",
    attrs: str = "",
) -> str:
    """Unread readings say unread in warn color, never a quiet '?' (R-0011)."""
    cls = "" if ok else " is-absent"
    shown = value if ok else "unread"
    id_attr = f' id="{html.escape(cell_id)}"' if cell_id else ""
    return (
        f'<a class="strip__cell{cls}" href="{href}"{attrs}>'
        f"<b{id_attr}>{_esc(shown)}</b><span>{_esc(label)}</span></a>"
    )


def _strip(state: dict[str, Any]) -> str:
    pickup = state.get("pickup") or {}
    fleet = state.get("fleet") or {}
    pads = state.get("claude_pads") or {}
    surfaces = state.get("surfaces") or {}
    pick_n = _stat(pickup, "count")
    plans = state.get("plans") or {}
    plan_n = _stat(plans, "open")
    prompts = state.get("prompts") or {}
    prompt_n = _stat(prompts, "open")
    seated = _stat(fleet, "seated")
    held = _stat(fleet, "held")
    pad_ok = bool(pads.get("ok"))
    pad_rows = (pads.get("data") or {}).get("pads") if pad_ok else None
    pad_n = str(len(pad_rows)) if isinstance(pad_rows, list) else "0"
    surf_ok = bool(surfaces.get("ok"))
    surf_rows = (surfaces.get("data") or {}).get("rows") if surf_ok else None
    live_n = "0"
    if isinstance(surf_rows, list):
        live_n = str(sum(1 for r in surf_rows if isinstance(r, dict) and r.get("present")))
    coord = state.get("coordinate") or {}
    coord_n = _stat(coord, "live")
    crew = state.get("crew") or {}
    crew_ok = bool(crew.get("ok"))
    talk = state.get("crew_talk") or {}
    talk_ok = bool(talk.get("ok"))
    converse = _esc(state.get("crew_converse") or "http://127.0.0.1:8020")
    return (
        '<div class="strip" id="strip">'
        + _strip_cell("#pickup", bool(pickup.get("ok")), pick_n, "pickup", cell_id="stripPickup")
        + _strip_cell("#plans", bool(plans.get("ok")), plan_n, "plans", cell_id="stripPlans")
        + _strip_cell("#prompts", bool(prompts.get("ok")), prompt_n, "prompts", cell_id="stripPrompts")
        + _strip_cell("#fleet", bool(fleet.get("ok")), seated, "seated")
        + _strip_cell("#fleet", bool(fleet.get("ok")), held, "held")
        + _strip_cell("#pads", pad_ok, pad_n, "claude pads", cell_id="stripPads")
        + _strip_cell("#pc", surf_ok, live_n, "this PC live")
        + _strip_cell("#coordinate", bool(coord.get("ok")), coord_n, "invoke live")
        + _strip_cell("#crew", crew_ok, "up", "crew belt", cell_id="stripCrew")
        + _strip_cell(
            converse,
            talk_ok,
            "up",
            "crew talk",
            cell_id="stripTalk",
            attrs=' target="_blank" rel="noopener"',
        )
        + "</div>"
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
        return "unread"
    data = reading.get("data") or {}
    if not isinstance(data, dict):
        return "unread"
    if "count" in data and data.get("count") is not None:
        return str(data.get("count"))
    for key in keys:
        rows = data.get(key)
        if isinstance(rows, list):
            return str(len(rows))
    return "unread"


def _howto(contract: dict[str, Any]) -> str:
    converse = ((contract.get("communication_layer") or {}).get("converse") or "http://127.0.0.1:8020")
    desk = contract.get("desk") or {}
    talk = desk.get("talk_probe") or "/crew/wakes"
    steps = desk.get("you_steps")
    usage = desk.get("usage_probe") or "/api/usage"
    board_wait = desk.get("board_wait_s")
    pickup_wait = desk.get("pickup_board_wait_s")
    kb_wait = desk.get("kb_wait_s")
    cortex_wait = desk.get("cortex_wait_s")
    crew_wait = desk.get("crew_belt_wait_s")
    vault_wait = desk.get("openvault_usage_wait_s")
    return (
        '<nav class="howto" id="howto" aria-label="Every agent seating steps">'
        "<strong>Every agent</strong>"
        '<a class="btn" href="/v1/contract">GET /v1/contract</a>'
        "<code>/v1/pickup</code> <code>/v1/fleet</code> <code>/v1/you</code> "
        "<code>/v1/coordinate</code> <code>/v1/plans</code> <code>/v1/prompts</code> <code>/v1/fetch</code> <code>/v1/openide</code> <code>/v1/pointer</code> <code>/v1/insights</code>"
        "<span>then claim on GitHub. YOU step 8 binds :8020. "
        f"talk_probe={_esc(talk)} you_steps={_esc(steps)} usage_probe={_esc(usage)} "
        f"board_wait_s={_esc(board_wait)} pickup_board_wait_s={_esc(pickup_wait)} "
        f"kb_wait_s={_esc(kb_wait)} cortex_wait_s={_esc(cortex_wait)} "
        f"crew_belt_wait_s={_esc(crew_wait)} openvault_usage_wait_s={_esc(vault_wait)}. "
        "Cortex runs. Control does not assign. Crew "
        f'<a href="{_esc(converse)}" target="_blank" rel="noopener">:8020</a></span>'
        "</nav>"
    )


def render_page(state: dict[str, Any]) -> str:
    gate = state.get("gate") or {}
    passing = bool(gate.get("ok") and (gate.get("data") or {}).get("passing"))

    if not gate.get("ok"):
        banner = (
            '<div class="banner bad" id="gateBanner">Gate status UNKNOWN - GET /v1/gate not yet. '
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

    converse_url = _esc(state.get("crew_converse") or "http://127.0.0.1:8020")
    launchers = "".join(
        f"<li><code>{_esc(x['name'])}</code> - {_esc(x['blurb'])} "
        f"<small>cwd {_esc(x.get('cwd') or '')}</small></li>"
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
<a href="#fetch">Fetch</a>
<a href="#plans">Plans</a>
<a href="#prompts">Prompts</a>
<a href="#coordinate">Coordinate</a>
<a href="#you">YOU</a>
<a href="#board">Board</a>
<a href="#fleet">Fleet</a>
</nav>
<p class="rail__label">Estate</p>
<nav>
<a href="#cortex">Cortex</a>
<a href="#pc">This PC</a>
<a href="#stage">Backstage</a>
<a href="#pads">Claude pads</a>
<a href="#runtime">Watchdog</a>
<a href="/constructor/">Constructor</a>
<a href="#vault">OpenVault</a>
<a href="#pointer">Pointer</a>
<a href="#ship">Spaceship</a>
<a href="#crew">Crew belt</a>
<a href="#tools">Laptop tools</a>
<a href="#kb">Skill chest</a>
<a href="#gate">Gate</a>
</nav>
<p class="absent" style="color:var(--rail-muted)">Display and launch only.
No third orchestrator. POST /v1/run stays 405.</p>
</aside>
<main class="stage">
<div class="pane__head">
<h1>Netie Control</h1>
<span class="live" id="liveDot">loopback</span>
<div class="toolbar">
<input id="filterQ" placeholder="Filter (Ctrl+K)" />
<button type="button" id="reload">Refresh</button>
<a class="btn" id="openCrew" href="{converse_url}" target="_blank" rel="noopener">Crew chat</a>
</div>
</div>
{banner}
{_howto(state.get("contract") or {{}})}
{_coord_chips(state.get("coordinate") or {{}})}
<div class="skill-find">
<input id="skillQ" placeholder="Find skill / rule (S-0003)" />
<button type="button" id="skillGo">Search KB</button>
<button type="button" class="btn btn-ghost" id="skillFleet">GET /v1/skills</button>
<p id="skillHits" class="absent">Type a query. Control does not run the skill.</p>
</div>
{_workers_chips(state.get("coordinate") or {{}})}
{_strip(state)}
<div class="hero" id="hero">
{_panel("Cortex internals", state.get("cortex") or {{}}, _cortex_body, "", "cortex")}
{_panel("OpenVault / FreeRoute liveness", state.get("openvault") or {{}}, _openvault_body, "", "vault")}
</div>
<div class="workbench" id="desk">
{_panel("Pickup", pick, _pickup_body, "", "pickup", _reading_n(pick, "items"))}
<div class="panel" id="fetch"><h2>Laptop fetch <span class="count"></span></h2>
<div id="fetchBody"><p class="absent">Laptop fetch unread. GET /v1/fetch.</p></div>
</div>
{_panel("Incomplete plans", state.get("plans") or {{}}, _plans_body, "", "plans", _reading_n(state.get("plans") or {{}}, "items"))}
{_panel("Prompt surfaces", state.get("prompts") or {{}}, _prompts_body, "", "prompts", _reading_n(state.get("prompts") or {{}}, "items"))}
{_panel("Board", board, _board_body, "", "board", _reading_n(board, "items"))}
{_panel("Who is seated", fleet, _fleet_body, "", "fleet", _reading_n(fleet, "rows"))}
</div>
<details class="more" id="more">
<summary>More estate (gate, crew, ship, kb)</summary>
<div class="grid">
{_panel("Watchdog snapshot (RUNTIME.md)", state.get("runtime") or {{}}, _runtime_body, "", "runtime")}
{_panel("Spaceship host (reuse, do not buy)", state.get("spaceship") or {{}}, _spaceship_body, "", "ship")}
{_panel("Crew conveyor (display-only)", state.get("crew") or {{}}, _crew_belt_body, "", "crew")}
{_panel("Laptop tools (Crew health)", state.get("crew_health") or {{}}, _crew_health_body, "", "tools")}
{_panel("Crew sidecar :8023", state.get("crew_sidecar") or {{}}, _crew_sidecar_body, "", "sidecar")}
{_panel("Skill chest (Netie-KB)", state.get("kb") or {{}}, _kb_body, "", "kb")}
{_panel("OpenIDE (AirGPT :8765)", state.get("openide") or {{}}, _openide_body, "", "openide")}
{_panel("Pointer (confirm-gated HUD)", state.get("pointer") or {{}}, _pointer_body, "", "pointer")}
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
Control <code>GET /v1/fleet</code> is CLAIMS seats. <code>GET /v1/pickup</code> is unseated work.
<code>GET /v1/fetch</code> is the same tray (laptop task fetch). Ticket Runner seats. POST /v1/run stays 405.
<code>GET /v1/plans</code> is analog remaining plus parked lots. Control does not assign.
<code>GET /v1/prompts</code> is Crew/Cortex prompt surfaces. Control does not edit prompts.
<code>GET /v1/openide</code> is AirGPT OpenIDE liveness. Control does not run the IDE.
<code>GET /v1/pointer</code> is Pointer confirm-gate. Control does not start Electron.
<code>GET /v1/stage</code> is backstage listeners and PowerShell popup owners. Control does not start or kill them.
<code>GET /v1/insights</code> is Cortex pack/constructor detection. Constructor <code>/constructor/</code> seeds: Define data, Govern agents, Insights. Ontology stays Cortex. P1 parked.
Skill chest is Netie-KB <code>:8030</code>. Custody is OpenVault, never this shell.</footer>
</main>
<aside class="inspector">
{_panel("Coordinate - invoke owners", state.get("coordinate") or {{}}, _coordinate_body, "", "coordinate", _stat(state.get("coordinate") or {{}}, "live"))}
<div class="panel" id="focus"><h2>Selected ticket</h2>
<p id="focusEmpty">Click a pickup, board, fleet, or rail row. Control does not assign.</p>
<div id="focusBody" hidden>
<p><strong id="focusTicket"></strong></p>
<p id="focusTitle"></p>
<p><code id="focusHref"></code></p>
<p>
<a class="btn" id="focusOpen" target="_blank" rel="noopener">Open</a>
<a class="btn btn-ghost" id="focusComment" target="_blank" rel="noopener">Comment / seat</a>
</p>
<p class="absent">Ticket Runner seats on GitHub + CLAIMS.json. Control does not spawn. POST /v1/run stays 405. Cortex#51 is kind=task, one writer per branch.</p>
</div>
</div>
{_panel("YOU - founder actions", state.get("you") or {{}}, _you_body, "", "you")}
<div class="panel" id="feedback"><h2>If this feels wrong</h2>
<p>Comment on that GitHub issue. GitHub is the bus (W-0005). This page does not auto-route chat to an agent.</p>
<p><a class="btn" href="#pickup">Go to Pickup</a>
<a class="btn btn-ghost" href="#board">Board</a></p>
</div>
{_panel("This PC right now", state.get("surfaces") or {{}}, _surfaces_body, "", "pc")}
{_panel("Backstage backends", state.get("stage") or {{}}, _stage_body, "", "stage")}
{_panel("Live Claude pads (this PC)", state.get("claude_pads") or {{}}, _claude_pads_body, "", "pads")}
<div class="panel" id="lanes"><h2>Local CLI lanes</h2>
<ol class="steps">
<li>Declared lanes. Click does nothing. P-CTL-2: no principal yet.</li>
<li>Control does not execute them. Copy cwd. Run in your own shell.</li>
<li>Nothing here starts Grok Bot or Cursor (R-0015).</li>
</ol>
<ul>{launchers}</ul>
<p class="absent">Display only until P-CTL-2. Nothing here starts, restarts or kills
the founder's desktop software (R-0015).</p></div>
</aside>
</div>
<script>
(function () {{
  const ids = ["pickup","plans","prompts","coordinate","you","board","fleet","runtime","cortex","vault","ship","crew","tools","kb","gate","stage","pc"];
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
    if (!row) return;
    fillFocus(row);
  }});
  document.getElementById("reload").onclick = function () {{ location.reload(); }};
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
  function skillSearch() {{
    var box = document.getElementById("skillQ");
    var out = document.getElementById("skillHits");
    if (!box || !out) return;
    var q = (box.value || "").trim();
    if (!q) {{ out.textContent = "Type a query. Control does not run the skill."; return; }}
    out.textContent = "KB search unread. GET /v1/skills not yet.";
    var ctrl = new AbortController();
    var timer = setTimeout(function () {{ ctrl.abort(); }}, 2500);
    fetch("/v1/skills?q=" + encodeURIComponent(q), {{ signal: ctrl.signal }}).then(function (r) {{
      return r.json().then(function (b) {{
        if (!r.ok || !b.ok) {{
          out.textContent = (b && b.detail) || "KB search unread";
          return;
        }}
        var hits = (b.data && b.data.hits) || [];
        if (!hits.length) {{ out.textContent = "No hits for " + q + ". Grep runtime skill dirs (S-0004)."; return; }}
        out.innerHTML = "<ul>" + hits.slice(0, 8).map(function (h) {{
          var id = esc(h.id);
          return '<li><button type="button" class="btn btn-ghost" data-skill="' + id
            + '"><code>' + id + "</code></button> "
            + esc(h.kind) + " - " + esc(h.title) + "</li>";
        }}).join("") + "</ul>";
      }});
    }}).catch(function () {{ out.textContent = "KB search unread"; }})
      .finally(function () {{ clearTimeout(timer); }});
  }}
  function skillShow(id) {{
    var out = document.getElementById("skillHits");
    if (!out || !id) return;
    out.textContent = "Skill unread. GET /v1/skill/" + id + " not yet.";
    var ctrl = new AbortController();
    var timer = setTimeout(function () {{ ctrl.abort(); }}, 2500);
    fetch("/v1/skill/" + encodeURIComponent(id), {{ signal: ctrl.signal }}).then(function (r) {{
      return r.json().then(function (b) {{
        if (!r.ok || !b.ok) {{
          out.textContent = (b && b.detail) || ("Skill unread. GET /v1/skill/" + id);
          return;
        }}
        var text = (b.data && b.data.text) || "";
        var cap = (b.data && b.data.capped) ? " truncated." : "";
        out.innerHTML = "<p>Display only. Control does not run <code>" + esc(id)
          + "</code>." + cap + "</p><pre>" + esc(text) + "</pre>";
      }});
    }}).catch(function () {{ out.textContent = "Skill unread. GET /v1/skill/" + id; }})
      .finally(function () {{ clearTimeout(timer); }});
  }}
  var skillHits = document.getElementById("skillHits");
  if (skillHits) skillHits.addEventListener("click", function (e) {{
    var btn = e.target.closest("[data-skill]");
    if (btn) skillShow(btn.getAttribute("data-skill"));
  }});
  var skillGo = document.getElementById("skillGo");
  if (skillGo) skillGo.onclick = skillSearch;
  var skillFleet = document.getElementById("skillFleet");
  if (skillFleet) skillFleet.onclick = function () {{
    var box = document.getElementById("skillQ");
    if (box) box.value = "fleet";
    skillSearch();
  }};
  var skillQ = document.getElementById("skillQ");
  if (skillQ) skillQ.addEventListener("keydown", function (e) {{
    if (e.key === "Enter") {{ e.preventDefault(); skillSearch(); }}
  }});
  function setCount(panelId, n) {{
    var el = document.querySelector("#" + panelId + " h2 .count");
    if (el) el.textContent = String(n);
    if (panelId === "pickup") {{
      var strip = document.getElementById("stripPickup");
      if (strip) strip.textContent = String(n);
    }}
    if (panelId === "plans") {{
      var stripP = document.getElementById("stripPlans");
      if (stripP) stripP.textContent = String(n);
    }}
    if (panelId === "prompts") {{
      var stripPr = document.getElementById("stripPrompts");
      if (stripPr) stripPr.textContent = String(n);
    }}
  }}
  function readingJson(r) {{
    if (!r.ok) throw new Error("unread " + r.status);
    return r.json();
  }}
  function absentHtml(detail, source) {{
    return '<ol class="steps">'
      + '<li class="absent">Could not read this source: ' + esc(detail || "no reason given") + "</li>"
      + '<li class="absent">Source: <code>' + esc(source || "") + "</code></li>"
      + "<li>Claim on GitHub. Control does not assign. POST /v1/run stays 405.</li></ol>";
  }}
  function actBtns(href, primary) {{
    if (!href) return "";
    return '<span class="work-row__act"><a class="btn" href="' + esc(href)
      + '" target="_blank" rel="noopener">' + esc(primary)
      + '</a> <a class="btn btn-ghost" href="' + esc(href)
      + '" target="_blank" rel="noopener">Comment</a></span>';
  }}
  function namedOmission(d) {{
    var extra = "";
    if (d.truncated) {{
      extra += '<p class="absent">Truncated: showing '
        + esc(d.shown || d.count || ((d.items || []).length))
        + " at cap " + esc(d.cap || "") + ". Not a quiet omission.</p>";
    }}
    if (d.skipped && d.skipped.length) {{
      extra += '<p class="absent">Skipped by deny regex: ' + esc(d.skipped.join("; ")) + "</p>";
    }}
    return extra;
  }}
  function boardHtml(b) {{
    if (!b.ok) return absentHtml(b.detail, b.source);
    var d = b.data || {{}};
    var rows = d.items || [];
    var byRepo = {{}};
    rows.forEach(function (r) {{
      var repo = String(r.repo || "?");
      if (!byRepo[repo]) byRepo[repo] = [];
      byRepo[repo].push(r);
    }});
    var cols = Object.keys(byRepo).map(function (repo) {{
      var items = byRepo[repo];
      var cards = items.map(function (r) {{
        var href = r.url || "";
        var short = String(r.repo || "").split("/").pop();
        var ticket = short + "#" + r.number;
        var tags = "";
        if (r.is_epic) tags += '<span class="tag epic">epic</span> ';
        if (r.blocked) tags += '<span class="tag blocked">blocked</span>';
        return '<div class="work-row ticket-card" data-ticket="' + esc(ticket)
          + '" data-title="' + esc(r.title) + '" data-href="' + esc(href) + '"><code>'
          + esc(ticket) + '</code><span class="work-row__title">' + esc(r.title)
          + '</span><span class="tags">' + tags + "</span>" + actBtns(href, "Open") + "</div>";
      }}).join("");
      return '<section class="kcol"><h3>' + esc(String(repo).split("/").pop()) + " " + items.length
        + "</h3>" + cards + "</section>";
    }}).join("");
    var extra = namedOmission(d);
    if (d.unreachable && d.unreachable.length) {{
      extra += '<p class="absent">Not shown, unreachable: ' + esc(d.unreachable.join("; ")) + "</p>";
    }}
    var list = rows.length
      ? '<div class="kanban">' + cols + "</div>"
      : '<p class="absent">No open items returned.</p>';
    var query = d.query ? "<p>Owner scan <code>" + esc(d.query) + "</code>.</p>" : "";
    return "<p>GitHub Issues are SoT. Open, then comment there. Control does not assign.</p>"
      + query + extra + list;
  }}
  function pickupHtml(b) {{
    if (!b.ok) return absentHtml(b.detail, b.source);
    var d = b.data || {{}};
    var items = d.items || [];
    var head = "<p>Pickup - claim on GitHub. Control does not assign.</p>"
      + '<ol class="steps">'
      + "<li>Open the GitHub issue and comment that you are seating.</li>"
      + "<li>Write CLAIMS.json. Then /ticket-runner in Claude Code. Control does not spawn.</li>"
      + "<li>Cortex runs. POST /v1/run stays 405.</li></ol>"
      + '<p class="absent">' + esc(d.rule || "") + "</p>"
      + namedOmission(d);
    if (d.board_deferred) {{
      head += '<p class="absent">Board deferred: ' + esc(d.board_detail || "unread")
        + ". Source: <code>" + esc(d.board_source || "GET /v1/board") + "</code>. "
        + "Live issues are GET /v1/board. This tray is CLAIMS unseated.</p>";
    }}
    if (!items.length) {{
      return head + '<p class="absent">No unseated CLAIMS items. Fleet empty or unread. '
        + "Board is not required for this tray.</p>";
    }}
    var rows = items.map(function (r) {{
      var href = r.href || "";
      var tags = '<span class="tag">' + esc(r.kind) + "</span>";
      if (r.is_epic) tags += ' <span class="tag epic">epic</span>';
      if (r.blocked) tags += ' <span class="tag blocked">blocked</span>';
      return '<div class="work-row pickup-card" data-ticket="' + esc(r.ticket)
        + '" data-title="' + esc(r.title) + '" data-href="' + esc(href) + '"><code>'
        + esc(r.ticket) + '</code><span class="work-row__title">' + esc(r.title)
        + '</span><span class="tags">' + tags + "</span>" + actBtns(href, "Pick up") + "</div>";
    }}).join("");
    return head + '<div class="work-list">' + rows + "</div>";
  }}
  fetch("/v1/gate").then(readingJson).then(function (g) {{
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
  }}).catch(function () {{
    var banner = document.getElementById("gateBanner");
    var pill = document.getElementById("gatePill");
    var body = document.getElementById("gateBody");
    if (banner) {{
      banner.className = "banner bad";
      banner.textContent = "Gate status UNKNOWN - GET /v1/gate unread. Treat the estate as unsafe to seat until this reads.";
    }}
    if (pill) {{ pill.className = "pill warn"; pill.textContent = "gate unread"; }}
    if (body) body.innerHTML = '<p class="absent">Gate unread. GET /v1/gate.</p>';
  }});
  fetch("/v1/board").then(readingJson).then(function (b) {{
    var body = document.getElementById("boardBody");
    if (!body) return;
    body.innerHTML = boardHtml(b);
    var n = (b.ok && b.data && b.data.items) ? b.data.items.length : "unread";
    setCount("board", n);
  }}).catch(function () {{
    var body = document.getElementById("boardBody");
    if (body) body.innerHTML = '<p class="absent">Board unread. GET /v1/board.</p>';
  }});
  fetch("/v1/pickup").then(readingJson).then(function (b) {{
    var body = document.getElementById("pickupBody");
    if (!body) return;
    body.innerHTML = pickupHtml(b);
    var n = (b.ok && b.data && typeof b.data.count === "number") ? b.data.count
      : ((b.ok && b.data && b.data.items) ? b.data.items.length : "unread");
    setCount("pickup", n);
  }}).catch(function () {{
    var body = document.getElementById("pickupBody");
    if (body) body.innerHTML = '<p class="absent">Pickup unread. GET /v1/pickup.</p>';
  }});
  function fetchHtml(b) {{
    if (!b.ok) return absentHtml(b.detail, b.source);
    var d = b.data || {{}};
    var head = "<p>Laptop task fetch. Ticket Runner seats. Control does not run. POST /v1/run stays 405.</p>";
    if (d.next && d.next.ticket) {{
      head += "<p>GitHub next <code>" + esc(d.next.ticket) + "</code> "
        + esc(d.next.title || "") + ". Unseated. Do not write.</p>";
    }}
    var analog = d.analog_next || null;
    if (analog) {{
      head += "<p>Analog leftover <code>" + esc(analog.name || analog.product)
        + "</code> " + esc(analog.surface || "") + " -&gt; <code>"
        + esc(analog.home || analog.path) + "</code>. Clone frozen.</p>";
    }}
    head += "<p>P1 parked. Ontology stays Cortex. Do not start OpenIDE or Pointer.</p>";
    var work = d.working || [];
    var table = "";
    if (work.length) {{
      table = "<table><tr><th>product</th><th>state</th><th>role</th><th>detail</th></tr>"
        + work.map(function (r) {{
          var cls = r.state === "unread" || !r.up ? "absent" : "";
          return '<tr class="' + cls + '"><td>' + esc(r.product)
            + "</td><td>" + esc(r.state) + "</td><td>" + esc(r.role)
            + "</td><td>" + esc(r.detail || "") + "</td></tr>";
        }}).join("")
        + "</table>";
    }}
    return head + table;
  }}
  fetch("/v1/fetch").then(readingJson).then(function (b) {{
    var body = document.getElementById("fetchBody");
    if (!body) return;
    body.innerHTML = fetchHtml(b);
    var n = (b.ok && b.data && b.data.working) ? b.data.working.length : "unread";
    setCount("fetch", n);
  }}).catch(function () {{
    var body = document.getElementById("fetchBody");
    if (body) body.innerHTML = '<p class="absent">Laptop fetch unread. GET /v1/fetch.</p>';
  }});
  function plansHtml(b) {{
    if (!b.ok) return absentHtml(b.detail, b.source);
    var d = b.data || {{}};
    var analog = d.analog || [];
    var items = d.items || [];
    var head = "<p>Incomplete plans - analog lifts and parked lots. Control does not unpark or copy.</p>"
      + '<ol class="steps">'
      + "<li>DISTILL/PARK rows are remaining work on the live product named in the row.</li>"
      + "<li>BAN/SKIP means the clone stays frozen.</li>"
      + "<li>Claim on GitHub. POST /v1/run stays 405.</li></ol>";
    if (d.rule) head += '<p class="absent">' + esc(d.rule) + "</p>";
    head += "<p>Analog trees present <code>" + esc(d.analog_present)
      + "</code>. Absent <code>" + esc(d.analog_absent)
      + "</code>. Open <code>" + esc(d.open) + "</code>"
      + (d.none ? " none." : ".")
      + " Laptop fetch analog leftover is GET /v1/fetch analog_next. Control does not seat. Ontology stays Cortex. P1 parked.</p>";
    var beat = d.heartbeat || [];
    if (beat.length) {{
      head += "<p>Heartbeat labels (no extra probe). Control does not start peers.</p>"
        + "<table><tr><th>product</th><th>href</th><th>role</th></tr>"
        + beat.slice(0, 8).map(function (r) {{
          return "<tr><td>" + esc(r.product) + "</td><td><code>" + esc(r.href)
            + "</code></td><td>" + esc(r.role) + "</td></tr>";
        }}).join("")
        + "</table>";
    }}
    var table = "";
    if (analog.length) {{
      table = "<table><tr><th>lane</th><th>name</th><th>surface</th><th>home</th><th>verdict</th></tr>"
        + analog.map(function (r) {{
          return "<tr><td>" + esc(r.lane) + "</td><td>" + esc(r.name || r.product)
            + "</td><td>" + esc(r.surface) + "</td><td><code>" + esc(r.home)
            + "</code></td><td>" + esc(r.verdict) + "</td></tr>";
        }}).join("")
        + "</table>";
    }}
    var list = "";
    if (!items.length) {{
      list = '<p class="absent">Incomplete plans none.</p>';
    }} else {{
      list = '<div class="work-list">' + items.slice(0, 40).map(function (r) {{
        var label = r.kind === "parking"
          ? (r.id + " " + (r.title || ""))
          : ((r.name || r.product || "") + " (" + (r.surface || "") + ") -> "
            + (r.home || r.path || ""));
        var tag = r.state || r.verdict || r.tree || "open";
        return '<div class="work-row"><code>' + esc(r.lane || r.id)
          + '</code><span class="work-row__title">' + esc(label)
          + '</span><span class="tags"><span class="tag">' + esc(tag)
          + "</span></span></div>";
      }}).join("") + "</div>";
    }}
    return head + table + list;
  }}
  fetch("/v1/plans").then(readingJson).then(function (b) {{
    var body = document.getElementById("plansBody");
    if (!body) return;
    body.innerHTML = plansHtml(b);
    var n = (b.ok && b.data && typeof b.data.open === "number") ? b.data.open
      : ((b.ok && b.data && b.data.items) ? b.data.items.length : "unread");
    setCount("plans", n);
  }}).catch(function () {{
    var body = document.getElementById("plansBody");
    if (body) body.innerHTML = '<p class="absent">Plans unread. GET /v1/plans.</p>';
  }});
  function promptsHtml(b) {{
    if (!b.ok) return absentHtml(b.detail, b.source);
    var d = b.data || {{}};
    var items = d.items || [];
    var head = "<p>Prompt surfaces and Crew paste briefs. Control lists them. It does not spawn.</p>"
      + "<p>Paste grok-master, then prd-agent. Reuse analog segments. Do not redesign UI tokens or layout DNA. WIP two writers.</p>";
    if (d.rule) head += '<p class="absent">' + esc(d.rule) + "</p>";
    var pastes = d.pastes || [];
    var pasteList = "";
    if (pastes.length) {{
      pasteList = '<div class="work-list">' + pastes.map(function (r) {{
        var body = String(r.paste || "").slice(0, 1200);
        return '<div class="work-row"><code>' + esc(r.id)
          + '</code><span class="work-row__title">' + esc((r.product || "") + " (" + (r.wip || "") + ")")
          + '</span><span class="tags"><span class="tag">paste</span></span></div>'
          + "<pre>" + esc(body) + "</pre>";
      }}).join("") + "</div>";
    }}
    if (!items.length && !pastes.length) {{
      return head + '<p class="absent">Prompts unread. GET /v1/prompts.</p>';
    }}
    var list = '<div class="work-list">' + items.map(function (r) {{
      return '<div class="work-row"><code>' + esc(r.id)
        + '</code><span class="work-row__title">' + esc((r.path || "") + " -> " + (r.product || ""))
        + '</span><span class="tags"><span class="tag">' + esc(r.verdict || "")
        + "</span></span></div>";
    }}).join("") + "</div>";
    return head + pasteList + list;
  }}
  fetch("/v1/prompts").then(readingJson).then(function (b) {{
    var body = document.getElementById("promptsBody");
    if (!body) return;
    body.innerHTML = promptsHtml(b);
    var n = (b.ok && b.data && typeof b.data.open === "number") ? b.data.open
      : ((b.ok && b.data && b.data.items) ? b.data.items.length : "unread");
    setCount("prompts", n);
  }}).catch(function () {{
    var body = document.getElementById("promptsBody");
    if (body) body.innerHTML = '<p class="absent">Prompts unread. GET /v1/prompts.</p>';
  }});
  function openideHtml(b) {{
    if (!b.ok) return absentHtml(b.detail, b.source);
    var d = b.data || {{}};
    var head = "<p>AirGPT OpenIDE. Control lists liveness. It does not run the IDE.</p>";
    if (d.up) {{
      head += '<p style="color:var(--ok)">OpenIDE host ok (<code>' + esc(d.service || "airgpt")
        + '</code>). <a href="' + esc(d.href || "http://127.0.0.1:8765/OpenIDE/ui/") + '">'
        + esc(d.href || "http://127.0.0.1:8765/OpenIDE/ui/") + "</a></p>";
    }} else {{
      head += '<p class="absent">OpenIDE unread. GET /v1/openide.</p>';
    }}
    if (d.rule) head += '<p class="absent">' + esc(d.rule) + "</p>";
    return head;
  }}
  fetch("/v1/openide").then(readingJson).then(function (b) {{
    var body = document.getElementById("openideBody");
    if (!body) return;
    body.innerHTML = openideHtml(b);
    setCount("openide", (b.ok && b.data && b.data.up) ? "up" : "unread");
  }}).catch(function () {{
    var body = document.getElementById("openideBody");
    if (body) body.innerHTML = '<p class="absent">OpenIDE unread. GET /v1/openide.</p>';
  }});
  function pointerHtml(b) {{
    if (!b.ok) return absentHtml(b.detail, b.source);
    var d = b.data || {{}};
    var head = "<p>Pointer HUD + Cortex POST /dms/secure. UACC is the only OS mouse. "
      + "Control does not start Pointer (R-0015).</p>";
    if (d.confirm_gated) {{
      head += '<p style="color:var(--ok)">plan-guard launches set _requireConfirm. nod_confirm='
        + esc(d.nod_confirm) + ".</p>";
    }} else {{
      head += '<p class="absent">Pointer confirm gate unread. GET /v1/pointer.</p>';
    }}
    if (d.up) {{
      head += '<p style="color:var(--ok)">Pointer.exe present on this PC.</p>';
    }} else {{
      head += '<p class="absent">Pointer not running. Founder starts D:\\\\Pointer. Control will not.</p>';
    }}
    if (d.rule) head += '<p class="absent">' + esc(d.rule) + "</p>";
    return head;
  }}
  fetch("/v1/pointer").then(readingJson).then(function (b) {{
    var body = document.getElementById("pointerBody");
    if (!body) return;
    body.innerHTML = pointerHtml(b);
    setCount("pointer", (b.ok && b.data && b.data.confirm_gated) ? "gated" : "unread");
  }}).catch(function () {{
    var body = document.getElementById("pointerBody");
    if (body) body.innerHTML = '<p class="absent">Pointer unread. GET /v1/pointer.</p>';
  }});
  function padsHtml(b) {{
    if (!b.ok) return absentHtml(b.detail, b.source);
    var d = b.data || {{}};
    var pads = d.pads || [];
    var head = "<p>Live <code>claude agents --json</code> on this PC. "
      + "Control did not start Claude.</p>";
    if (d.note) head += '<p class="absent">' + esc(d.note) + "</p>";
    if (!pads.length) {{
      return head + '<p class="absent">No live Claude pads returned.</p>';
    }}
    var rows = pads.slice(0, 20).map(function (p) {{
      return "<tr><td>" + esc(p.name) + "</td><td>" + esc(p.pid) + "</td><td>"
        + esc(p.kind) + "</td><td><code>" + esc(p.cwd) + "</code></td></tr>";
    }}).join("");
    return head + "<table><tr><th>name</th><th>pid</th><th>kind</th><th>cwd</th></tr>"
      + rows + "</table>";
  }}
  fetch("/v1/pads").then(readingJson).then(function (b) {{
    var body = document.getElementById("padsBody");
    if (body) body.innerHTML = padsHtml(b);
    var strip = document.getElementById("stripPads");
    var n = (b.ok && b.data && Array.isArray(b.data.pads)) ? b.data.pads.length : "unread";
    if (strip) strip.textContent = String(n);
    var cell = strip && strip.closest(".strip__cell");
    if (cell) {{
      if (b.ok) cell.classList.remove("is-absent");
      else cell.classList.add("is-absent");
    }}
  }}).catch(function () {{
    var body = document.getElementById("padsBody");
    if (body) body.innerHTML = '<p class="absent">Pads unread. GET /v1/pads.</p>';
    var strip = document.getElementById("stripPads");
    if (strip) strip.textContent = "unread";
  }});
  function stageHtml(b) {{
    if (!b.ok) return absentHtml(b.detail, b.source);
    var d = b.data || {{}};
    var head = '<p class="absent">' + esc(d.note || "Backstage only.") + "</p>";
    var peers = d.peers || [];
    if (!peers.length) {{
      head += '<p class="absent">No backstage listeners listed.</p>';
    }} else {{
      head += "<table><tr><th>backend</th><th>port</th><th>owner</th><th>stage</th></tr>";
      head += peers.map(function (row) {{
        var status = row.up ? "listening" : "down";
        var dot = row.up ? "live" : "down";
        return "<tr><td><span class=\\"dot " + dot + "\\">" + esc(row.name)
          + "</span></td><td>" + esc(row.port) + "</td><td>" + esc(row.owner)
          + "</td><td>" + esc(status) + "</td></tr>";
      }}).join("");
      head += "</table>";
    }}
    head += "<p>Console popups (PowerShell). Owner is the parent process. Control does not hide or kill them.</p>";
    var popups = d.popups || [];
    if (!popups.length) {{
      return head + '<p class="absent">No powershell.exe popups on the snapshot.</p>';
    }}
    head += "<table><tr><th>pid</th><th>image</th><th>parent</th><th>owner</th></tr>";
    head += popups.slice(0, 24).map(function (row) {{
      return "<tr><td>" + esc(row.pid) + "</td><td>" + esc(row.image) + "</td><td>"
        + esc(row.parent) + "</td><td>" + esc(row.owner) + "</td></tr>";
    }}).join("");
    return head + "</table>";
  }}
  fetch("/v1/stage").then(readingJson).then(function (b) {{
    var body = document.getElementById("stageBody");
    if (body) body.innerHTML = stageHtml(b);
  }}).catch(function () {{
    var body = document.getElementById("stageBody");
    if (body) body.innerHTML = '<p class="absent">Stage unread. GET /v1/stage.</p>';
  }});
  function chipHtml(live, href, label, title) {{
    var cls = live ? "live" : "down";
    return '<a class="coord-chip ' + cls + '" href="' + esc(href || "#coordinate")
      + '" title="' + esc(title || "") + '"><span class="dot ' + cls + '"></span>'
      + esc(label) + "</a>";
  }}
  function coordChipsHtml(d) {{
    var bits = [];
    (d.lanes || []).forEach(function (lane) {{
      if (!lane) return;
      bits.push(chipHtml(!!lane.live, lane.href, lane.job, lane.do_not));
    }});
    var shown = 0;
    (d.teammates || []).forEach(function (mate) {{
      if (!mate || ["seater", "talk", "run", "pad", "task"].indexOf(mate.kind) < 0) return;
      if (shown >= 8) return;
      shown += 1;
      bits.push(chipHtml(!!mate.live, mate.href, mate.name, mate.do_not));
    }});
    return '<div class="coord-chips" id="coordChips" aria-label="Invoke owners">'
      + bits.join("") + "</div>";
  }}
  function workersHtml(d) {{
    var workers = d.workers || [];
    if (!workers.length) {{
      return '<p class="absent" id="workers">No live Cortex workflows or armed Crew MCPs this tick.</p>';
    }}
    var bits = workers.slice(0, 12).map(function (row) {{
      return chipHtml(!!row.live && !row.unread, row.href, (row.kind || "") + " " + (row.name || ""), row.do_not);
    }});
    return '<div class="coord-chips" id="workers" aria-label="Live workers">'
      + bits.join("") + "</div>";
  }}
  function coordUnread() {{
    var liveDot = document.getElementById("liveDot");
    var workers = document.getElementById("workers");
    var chips = document.getElementById("coordChips");
    if (liveDot) {{
      liveDot.className = "live is-unread";
      liveDot.textContent = "coordinate unread";
    }}
    if (chips) chips.outerHTML = '<p class="absent" id="coordChips">Coordinate unread. GET /v1/coordinate.</p>';
    if (workers) workers.outerHTML = '<p class="absent" id="workers">Workers unread. GET /v1/coordinate.</p>';
  }}
  function tickCoordinate() {{
    fetch("/v1/coordinate").then(readingJson).then(function (b) {{
      var d = (b && b.ok && b.data) ? b.data : null;
      var chips = document.getElementById("coordChips");
      var workers = document.getElementById("workers");
      var liveDot = document.getElementById("liveDot");
      if (!d) {{
        coordUnread();
        return;
      }}
      if (chips) chips.outerHTML = coordChipsHtml(d);
      if (workers && !d.health_deferred) workers.outerHTML = workersHtml(d);
      if (liveDot) {{
        liveDot.className = "live";
        liveDot.textContent = "live " + (d.live || 0);
      }}
    }}).catch(function () {{ coordUnread(); }});
  }}
  tickCoordinate();
  setInterval(tickCoordinate, 15000);
}})();
</script>
</body></html>"""
