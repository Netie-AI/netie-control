# 2026-09-23 shared-reads

keywords: scale, cache, coalesce, singleflight, board, gh, estate gate, age_s, skip
main_idea: Every open tab ran its own `gh` fan-out on the 15s `/v1/ops` poll, and each `/v1/gate` hit spawned its own gate subprocess (up to 120s). `shared_read` puts one read behind N callers. Board keeps good readings 10s; gate/pads/coordinate coalesce only. Reused readings carry `age_s`.

## Expected vs actual

- Expected: N tabs cost one `gh` scan per poll window. Actual before: N scans.
- Expected: CI runs the no-FTP-password check. Actual before: skipped (no D: drive).

## Repro

```
python -m uvicorn netie_control.app:app --port 8040
# 5 concurrent: 1 reply has age_s null, 4 share it
for i in 1 2 3 4 5; do curl -s localhost:8040/v1/board & done; wait
python -m pytest tests/test_shared_reads.py -q
```

Gate proven: removing `@shared_read(BOARD_TTL_S)` turns `test_board_route_and_panel_show_shared_age` red.

## Root-cause class

Per-request reads of shared, slow, external state with no coalescing. Env-gated skip hiding a security assertion.

## Invariants

Silent fallback is a lie (cache age shown, unread never kept). A skipped test is a failing test.

Does not prove: real `gh` latency on the operator box. Sandbox has no `gh`, so the live check ran on the unread path.
