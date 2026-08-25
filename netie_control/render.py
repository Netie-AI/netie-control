"""Render the operator page.

One rule shapes all of this: an unreachable source renders as a stated absence, never
as an empty panel. An empty panel and a healthy-but-quiet panel look identical, and the
operator cannot tell which they are looking at (R-0011).
"""

from __future__ import annotations

import html
from typing import Any

CSS = """
:root{--bg:#0d0f12;--panel:#14181d;--line:#232a32;--ink:#dfe5ec;--dim:#8b96a5;
--ok:#5fb98a;--bad:#e0674f;--warn:#d9a441;--acc:#6ea8d8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.55 ui-monospace,"Cascadia Mono",Consolas,monospace}
.wrap{max-width:78rem;margin:0 auto;padding:2rem 1.25rem 4rem;
display:flex;flex-direction:column;gap:1.5rem}
h1{font-size:1.05rem;letter-spacing:.14em;text-transform:uppercase;margin:0;color:var(--dim)}
h2{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);
margin:0 0 .6rem}
.banner{padding:.85rem 1rem;border-radius:2px;border:1px solid;font-weight:600}
.banner.ok{border-color:var(--ok);color:var(--ok);background:rgba(95,185,138,.07)}
.banner.bad{border-color:var(--bad);color:var(--bad);background:rgba(224,103,79,.07)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(20rem,1fr));gap:1rem}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:2px;padding:1rem}
.absent{color:var(--warn);font-style:italic}
ul{margin:0;padding-left:1.1rem}li{margin:.15rem 0}
.fail{color:var(--bad)}
table{width:100%;border-collapse:collapse;font-size:.86rem}
td,th{text-align:left;padding:.3rem .5rem;border-bottom:1px solid var(--line);
vertical-align:top}
th{color:var(--dim);font-weight:600;font-size:.68rem;letter-spacing:.1em;text-transform:uppercase}
.tag{font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;padding:.1em .4em;
border:1px solid var(--line);border-radius:2px;color:var(--dim)}
.tag.epic{color:var(--acc);border-color:var(--acc)}
.tag.blocked{color:var(--warn);border-color:var(--warn)}
code{color:var(--acc)}
footer{color:var(--dim);font-size:.75rem;border-top:1px solid var(--line);padding-top:1rem}
"""


def _esc(x: Any) -> str:
    return html.escape(str(x))


def _panel(title: str, reading: dict[str, Any], body_fn) -> str:
    """Render one source. If it could not be read, say so instead of showing nothing."""
    if not reading.get("ok"):
        return (
            f'<div class="panel"><h2>{_esc(title)}</h2>'
            f'<p class="absent">Could not read this source: '
            f'{_esc(reading.get("detail") or "no reason given")}</p>'
            f'<p class="absent">Source: <code>{_esc(reading.get("source"))}</code></p></div>'
        )
    return f'<div class="panel"><h2>{_esc(title)}</h2>{body_fn(reading.get("data"))}</div>'


def _gate_body(d: dict[str, Any]) -> str:
    if d.get("passing"):
        return '<p style="color:var(--ok)">Gate passes. Seating is permitted.</p>'
    items = "".join(f'<li class="fail">{_esc(x)}</li>' for x in (d.get("output") or [])[:20])
    return (
        f'<p class="fail">Gate FAILS (exit {_esc(d.get("exit_code"))}). '
        f"No writer may be seated until a human acts.</p><ul>{items}</ul>"
    )


def _board_body(d: dict[str, Any]) -> str:
    rows = d.get("items") or []
    if not rows:
        return '<p class="absent">No open items returned.</p>'
    out = ["<table><tr><th>repo</th><th>#</th><th>title</th><th></th></tr>"]
    for r in rows[:40]:
        tags = ""
        if r.get("is_epic"):
            tags += '<span class="tag epic">epic</span> '
        if r.get("blocked"):
            tags += '<span class="tag blocked">blocked</span>'
        repo = str(r.get("repo", "")).split("/")[-1]
        out.append(
            f'<tr><td>{_esc(repo)}</td><td>{_esc(r.get("number"))}</td>'
            f'<td>{_esc(r.get("title"))}</td><td>{tags}</td></tr>'
        )
    out.append("</table>")
    if d.get("unreachable"):
        out.append(
            '<p class="absent">Not shown, unreachable: '
            + _esc("; ".join(d["unreachable"]))
            + "</p>"
        )
    return "".join(out)


def _text_body(d: Any) -> str:
    text = str(d or "")
    head = "\n".join(text.splitlines()[:14])
    return f'<pre style="white-space:pre-wrap;margin:0;color:var(--dim)">{_esc(head)}</pre>'


def _claims_body(d: Any) -> str:
    by_pr = (d or {}).get("by_pr") or {}
    if not by_pr:
        return '<p class="absent">Claims board carries no entries.</p>'
    items = "".join(
        f"<li><code>{_esc(k)}</code> {_esc((v or {}).get('role', '?'))}</li>"
        for k, v in list(by_pr.items())[:15]
    )
    return f"<ul>{items}</ul>"


def render_page(state: dict[str, Any]) -> str:
    gate = state.get("gate") or {}
    passing = bool(gate.get("ok") and (gate.get("data") or {}).get("passing"))

    if not gate.get("ok"):
        banner = (
            '<div class="banner bad">Gate status UNKNOWN - Control could not run it. '
            "Treat the estate as unsafe to seat until this reads.</div>"
        )
    elif passing:
        banner = '<div class="banner ok">Estate gate PASSES</div>'
    else:
        banner = (
            '<div class="banner bad">Estate gate FAILS - no writer may be seated '
            "until a human acts</div>"
        )

    launchers = "".join(
        f"<li><code>{_esc(x['name'])}</code> - {_esc(x['blurb'])}</li>"
        for x in (state.get("launchers") or [])
    )

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Netie Control</title><style>{CSS}</style></head><body><div class="wrap">
<h1>Netie Control &middot; operator shell &middot; plane 4</h1>
{banner}
<div class="grid">
{_panel("Estate gate", gate, _gate_body)}
{_panel("Board - open epics and tickets", state.get("board") or {}, _board_body)}
{_panel("Runtime view (watchdog)", state.get("runtime") or {}, _text_body)}
{_panel("Claims - who holds what", state.get("claims") or {}, _claims_body)}
<div class="panel"><h2>Local CLI lanes</h2><ul>{launchers}</ul>
<p class="absent">Display and launch only. Nothing here starts, restarts or kills
the founder's desktop software (R-0015).</p></div>
</div>
<footer>Holds no keys. Owns no route decision. Decides no work shape.
<code>/v1/secrets</code>, <code>/v1/route</code>, <code>/v1/goal</code> and
<code>/v1/run</code> answer 405 by design - see NETIE.md section 3.</footer>
</div></body></html>"""
