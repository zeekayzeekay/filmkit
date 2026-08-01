# Build status

| task | what | state |
|---|---|---|
| FK0 | repo skeleton, both manifests, AGENTS.md | **done** |
| FK1 | extract and de-TARN the fourteen guards | **done** |
| FK2 | portability test, split the 74 findings | pending |
| FK3 | gate.py + self-gating tools | pending |
| FK4 | engine.json, craft skills, look packs | pending |
| FK5 | dual-run against TARN | pending |
| FK6 | promotion ritual, session state | pending |
| FK7 | init, doctor, private GitHub repo | pending |

Kit version 0.1.0. Nothing in `../tarn` has been modified.

## FK1 notes

Fourteen scripts ported, not thirteen — `stale_neighbours.py` was missed in the plan.

Source verified by content, not by the transfer tool's report: `tests/SOURCE_SHA256.txt`
carries the manifest, 15/15 OK. Six files had been served stale on the first attempt —
see `knowledge/KIT_FINDINGS.md` FK-01.

Smoke test against the origin film's live data (`_fact_rev` 103) reproduces its findings
exactly: same `angle-without-plate` on 6B, same three missing elements, same 4 locked
assets, same 2 uncomparable, same selections, same counting-detector selftest.

## FK1 review pass

Diffed all 14 ported files against verified source: 27 hunks, all intended, no rule text
touched. **The clean diff hid twelve broken call sites** — see `KIT_FINDINGS.md` FK-02.

`tests/kit_lint.py` now lints the kit itself, five checks, each a defect that shipped in
the first port. Currently: no faults of any known class.

All 14 tools exercised against the origin film's live data, and every number matches its
own run: checklist 74 findings / 32 manual / 0 untagged · staleness 23 headings, nothing
stale · guard_coverage 56 rules / 55 proven / 1 exempt / 0 unproven · preflight all four
phases PASS · selections both current · crossshot and lint_prompt produce their expected
output. The scratch film deliberately keeps the ORIGIN's filenames, so `_files` is proven
rather than assumed.
