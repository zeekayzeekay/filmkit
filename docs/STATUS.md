# Build status

| task | what | state |
|---|---|---|
| FK0 | repo skeleton, both manifests, AGENTS.md | **done** |
| FK1 | extract and de-TARN the fourteen guards | **done** |
| FK2 | portability test, split the 74 findings | **test done**, split pending |
| FK3 | gate.py + self-gating tools | **done** |
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

## FK2 result

`tests/portability_test.py` — de-nouns the FILM as well as the fixture, because a lint
rule reads both and stripping one side is a broken lookup rather than an experiment.

**All 56 rules are general.** Nothing in the rule engine depends on one film's nouns, so
the code side needs no split — the whole engine is the kit's. 73 of 74 finding `ask:`
lines are portable as written; one names a facts-file section rather than a place.

`--selftest` proves discrimination: the first method (fixture only) silences three
ledger-reading rules, the current one silences none. Without that control, 56-of-56
general is indistinguishable from a comparison that measures nothing.

Also fixed in passing: `checklist.py` parsed `F-61b` as id `F-61` titled `b · …`,
colliding with the real F-61 — in the tool whose whole purpose is that the checklist
cannot disagree with the ledger.

## Review pass before FK3

kit_lint gains check 9: the kit's own documents may not name a file that is not there.
`staleness.py` does this for a FILM and nothing did it for the kit — `ARCHITECTURE.md`
went on describing `settings/claude.settings.json` (REMOVED in the FK0 audit — registrations are generated) for two commits after that file was
deleted in the FK0 audit. A design record documenting a layout the repo does not have is
worse than none, because it is read as authority. Paths not built yet are marked (PLANNED).

`preflight --record --export` exercised for the first time and found FK-04: the export
was verified before it was written, so the documented command crashed on any clean
directory. Byte-identical to the origin — inherited, not introduced.

## FK3

`tools/_receipt.py` owns the hash, and both `preflight` and `gate` import it — one
artefact, one hash, which is `check_fullread`'s own rule applied to a second artefact.

A receipt is written ONLY on an all-green run **including the manual items**, so the
thing that authorises a fire is a run a person signed. Verified in both directions: a
not-all-green run writes nothing and says a generation will be refused.

`hooks/gate.py` is deny-by-default across the whole Higgsfield surface, with free calls
named individually. 15 selftest cases, four of which the first matcher got wrong
(`generate_3d`, `dubbing`, `apps_invoke`, and any tool shipped after it was written).
It fails CLOSED on an unreadable payload.

kit_lint now covers `hooks/` — gate.py was the one file in the repo whose correctness
costs money and it was outside every check.
