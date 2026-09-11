# 2026-09-11 org-board-regex

keywords: board, pickup, gh search, regex, BOARD_REPOS, git pull, Claude Code, F-0021, F-0030
main_idea: Control board was a frozen four-repo `gh issue list`. Friends pulling GitHub do not get the ticket census from git. GitHub Issues are SoT. Fix is owner-wide `gh search issues` plus allow/deny regex, named truncation, hourly GitHub Pages. Control still does not assign.

## Verify

```
python -m pytest tests/test_board_org.py tests/test_control_stays_plane_4.py -q
curl.exe -sS http://127.0.0.1:8040/v1/board
```

Does not prove: friend's clone is current. That needs commit + push of this branch. `git pull` is still code, not the bus.
