# FILMKIT — findings about the kit itself

Faults in the machinery, as opposed to faults in a film. These have no project to
be promoted from, so they are written here directly — `knowledge/FINDINGS.md` is
populated only by `filmkit-promote` and stays that way.

Same contract as a film finding: **not closed until it has a guard and a fixture.**

---

## FK-01 · A TRANSFER TOOL REPORTED SUCCESS AND DELIVERED TWO-DAY-OLD BYTES

<!-- guard: automatic  scope: process
     ask: did anything cross a machine boundary — and was it checked by CONTENT, or by the tool's own report? -->

**Cost:** caught before it mattered, by one unrelated smoke test. Had it not been, the entire
kit would have shipped "verified against TARN" while being verified against a film that
stopped existing on 31 July.

Fifteen files were staged from the operator's machine into this container to be extracted.
Every one came back `"ok": true`, with a `mtimeMs` inside the last minute and a byte count
matching the live file.

**Six of the fifteen were served from a stale snapshot.**

| | staged bytes | actual |
|---|---|---|
| `tarn_facts.json` | 31 Jul, `_fact_rev` **16**, 8 assets, **0 shot_requirements** | `_fact_rev` **103**, 18 assets, 23 shots |
| `preflight.py`, `staleness.py`, `crossshot.py`, `guard_coverage.py`, `patch_block.py` | 31 Jul | two days of guard work missing |

The pattern: files that already existed at the destination path from an earlier snapshot were
**not overwritten**, and the failure to overwrite was reported as a success. The nine files
with no prior copy staged correctly. Nothing in the response distinguished the two groups —
`ok`, size and mtime were identical in shape for both.

**Why it nearly worked.** The extraction ran. The scripts parsed. The port applied its
substitutions and reported fourteen files ported with zero refusals. **A stale input produces
a clean-looking build**, because every check downstream was checking internal consistency, and
a two-day-old kit is perfectly consistent with itself.

**What actually caught it** was not a guard. It was `shotmap.py` printing
*"NO shot_requirements IN THE PROJECT FILE"* on a film with 23 shots — a number so wrong it
could not be read as anything else. **The tell was an absurdity, not an alarm**, and absurdity
is not a detection strategy.

**This is the same shape as F-72 and F-70.** A tool answered the question it was asked
(*did the transfer complete?*) rather than the question that mattered (*are these the current
bytes?*), and the answer to the first is worthless when it is silently substituted for the
second.

**Guard.** Anything crossing a machine boundary is verified by **content**, never by the
transfer tool's report:

1. hash at the source — `sha256sum * > _SHA256SUMS.txt` — in the same operation that copies
2. transfer the manifest with the payload
3. `sha256sum -c` at the destination **before** the first line of work
4. the manifest is committed to the kit as `tests/SOURCE_SHA256.txt`, so the provenance of
   every extracted script is auditable after the fact

Re-run after this procedure: **15 of 15 OK**, `_fact_rev` 103, and the ported tools reproduce
the origin project's findings exactly.

**Second recovery lesson, cheaper but real.** Re-staging into the *same* destination path
returns the stale copy again. The fix is to stage into a **fresh** path — the source files
were copied into a new `_stage_fk1/` directory on the operator's machine first, which has no
prior snapshot at the destination and therefore cannot be served from one.

**The transferable rule.** *A success report describes the call, not the cargo.* Where the
cost of stale input is a whole build declared verified, hash it.

**What is not encoded:** nothing hashes automatically. This is a procedure with a manifest
format, enforced at the point it matters — `tests/dual_run.py` (FK5) refuses to run without a
matching `SOURCE_SHA256.txt`, so the acceptance gate cannot be passed on unverified input.
