# 2026-09-24 workflow-scale-slices

keywords: workflow, subagents, worktree, gzip, no-store, coalesce, load test, rule 5, fleet lane
main_idea: One workflow, 8 agents (4 builders in isolated worktrees, 4 adversarial verifiers, one per slice, pipelined). Skeptics found 0 blockers, 2 majors (ops/fleet/pickup dropped age_s; 4 of 5 new decorators untested) and surfaced a pre-existing rule-5 bug: coordinate `fleet` lane hardcoded `live: True`.

## Shape (record for reuse)

- Agents: 8. Build x4 (`isolation: worktree`, commit to `wf/<slice>`, must prove gate fails), Verify x4 (detached checkout of builder sha, rerun ruff+pytest, re-prove gate, hunt rule breaks). Pipeline, no barrier.
- Integrator (main session) merges branches, fixes majors, reruns everything.
- Why it worked: slices were file-disjoint by design, docs reserved for integrator, so 4 merges had 0 conflicts.

## Expected vs actual

- Expected: coalesced readers show age on the wire. Actual: 3 routes dropped `age_s` (builder file scope excluded app.py).
- Expected: an unread CLAIMS.json never paints green. Actual: `fleet` lane was `live: True` regardless.

## Repro

`python -m pytest tests/test_ops_coalesce.py -q`. Gates proven: each decorator removed -> its param fails; fleet lane reverted -> lane test fails; age_s removed -> 3 route tests fail.

## Root-cause class

File-scoped delegation drops cross-file obligations (the route that serializes the reading). Hardcoded status literals bypass the unknown-never-green rule.

## Invariants

Silent fallback is a lie. Unknown never green. Adversary != verifier.
