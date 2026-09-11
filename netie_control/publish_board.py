"""Write the public org board HTML. Display only. Used by Actions Pages."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from netie_control.render import public_board_page
from netie_control.sources import board


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    dest = Path(args[0] if args else "site/index.html")
    timeout = float(os.environ.get("NETIE_BOARD_WAIT_S", "15"))
    reading = board(timeout=timeout)
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = public_board_page(reading.to_dict(), built_at=built_at)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    (dest.parent / ".nojekyll").write_text("", encoding="utf-8")
    return 0 if reading.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
