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

---

## FK-02 · THE DIFF WAS CLEAN AND THE PORT WAS BROKEN

<!-- guard: automatic  scope: process
     ask: each intended change — is it correct at EVERY site it lands on, or only at the one I grepped for? -->

**Cost:** caught in review, before FK2 built on top of it. Had it shipped, `guard_coverage.py`
would have reported **zero rules defined on every project, forever**, and twelve of the
suite's subprocess calls would have failed on the first film that was not the origin.

In the origin project the tools lived beside the film, so one word — `HERE` — meant both
*where the film is* and *where the tools are*. Porting into a kit splits that word in two.

**The split is a decision per USE SITE. I made it per FILE.** One `HERE = P.DIR` rebind at the
top of each script, and done.

| what broke | how many |
|---|---|
| `subprocess.run([sys.executable, "shotmap.py", …], cwd=film)` — tool no longer there | **12** |
| `(HERE / "lint_prompt.py").read_text()` to count rules — reads from the film | 1 |
| `LIVE_DOCS` still listing five `TARN_*.md` filenames | 1 |
| `_project` imported into two tools that take files as arguments, giving them a hard dependency on a film they never read | 2 |
| `CORPUS` mixing bare filenames with absolute paths in one list | 1 |
| `FIXTURES` / `MUTATIONS`: literal dicts keyed by one film's filenames, inside the engine | 7 entries |

**Pass 2 of the port fixed exactly two of the twelve** — the two an earlier grep had surfaced.
I searched for a pattern, fixed what the search returned, and declared the pass complete
without asking where else the pattern occurred. That is the same move as F-70 (fixed the
anchors a grep found) and F-72 (wrote a gate, never asked which rows could no longer satisfy
it), and it is now the third time in one working day.

**The review that should have caught it did not, and the reason is the interesting part.**
I diffed all fourteen ported files against verified source and read every hunk. **All 27 hunks
were intended changes.** The diff was clean. It was clean because the question a diff answers
is *did anything change that should not have?* — and every one of these defects is an intended
change that was **correct in one place and wrong in nine others.**

> **A diff shows you what moved. It cannot show you what should have moved with it.**

**What actually caught it** was reading the *use sites* rather than the *change sites*:
`grep -n "HERE" *.py` and classifying each hit as film-path or kit-path. Six minutes. It should
have been the first thing after the port, not the third.

**Guard.** `tests/kit_lint.py` — the kit lints itself, and every check is a defect that
actually shipped in the first port:

1. `bare-sibling-invocation` — a tool invoked by name rather than `P.tool()`
2. `tool-read-from-film` — a tool's source read from a film-relative path
3. `hardcoded-project-noun` — a project filename in **code** (prose may cite one as evidence; an expression may not depend on one), checked against the AST so docstrings are exempt
4. `unused-project-import` / `missing-project-import` — resolving the film has side effects, so an unused import is not a dead import
5. `unknown-document-role` — a document role no resolver defines

It found two faults I had already declared fixed: `lint_prompt`'s direction-audit message told
the reader to look things up in `tarn_facts.json`, and `preflight`'s fixture tables were
literal dicts keyed by `TARN_lint_regression*.md`. Both now resolve through the film; the
fixture corpus moved to `tests/fixtures/manifest.json`, which is also the seam FK2 needs.

**The transferable rule.** *When one name is split into two, audit the uses, not the
definition.* The definition is where the change is visible and the uses are where it is wrong.

**What is not encoded:** the lint checks structure, not meaning. It cannot tell whether a rule
is correct, whether a threshold suits your film, or whether a tool does what its docstring
claims. And it only knows the five classes that have already bitten.

---

## FK-03 · I VERIFIED WHAT I BUILT, NOT WHAT ARRIVES

<!-- guard: automatic  scope: process
     ask: has the DELIVERABLE been opened, or only the working copy it was made from? -->

**Cost:** two bundles delivered to the operator, both structurally broken. Found only because
he asked whether FK0 had been audited too — it had not.

The scaffold created seventeen directories and printed a file listing that looked complete.
**Ten of those directories were empty, and git does not track empty directories.** A
`git clone` of the delivered bundle arrives with **no `skills/` directory at all**, while both
plugin manifests point at `./skills/`. Neither plugin would load a single skill.

I never cloned the bundle. The bundle **is** the deliverable — the container is ephemeral and
that file is the only durable artifact — and I checked the working copy it was made from.

> **A working copy is not a deliverable. Open the thing you are handing over.**

Three more defects in the same scaffold, none caught at the time:

**The hook variable was a guess.** The Codex registration interpolated `$CODEX_PLUGIN_ROOT`.
The research that established Codex's hook format confirmed the events, the wire format, the
matchers and the exit codes, and **explicitly did not confirm a plugin-root variable name.**
I wrote a plausible one into the enforcement path. Per both hosts' documented semantics, a hook
command that fails for any reason other than exit 2 is a *hook failure and processing
continues* — so an unexpandable variable produces **a spend gate that silently is not a gate**.
Registrations are now GENERATED with absolute paths by `filmkit-doctor --install`; the
guess is gone rather than corrected.

**One registration was planted at the other host's front door.** `hooks/hooks.json` is the
conventional auto-discovery path for a plugin's hooks in *both* hosts. Shipping the Codex file
there meant Claude Code would likely load it too, Codex variable and all.

**The matcher was an allow-list of dangers.**
`generate|upscale|outpaint|reframe|motion_control|remove_background` — which misses
`generate_3d`, `dubbing`, `voice_change`, `create_voice`, `explainer_video`,
`shorts_studio_create`, `personal_clipper_create`, `video_analysis_create` and `apps_invoke`,
several of which spend credits, and would miss anything Higgsfield ships next month. **F-56
established that a guard whose reach is an allow-list only ever guards what has already gone
wrong once**, and I wrote one anyway, in the gate whose entire job is to stop spending.

It is now `mcp__higgsfield__.*` — deny by default — with `gate.py` allowing read-only calls by
name. A new spending tool is gated the day it appears; a new read-only tool costs one line
whose worst failure is a needless prompt.

**And `AGENTS.md` — the file the model reads every session — told the reader to run
`python3 tools/shotmap.py` from the film directory**, where `tools/` is not. The same
assumption that broke twelve call sites, restated as instruction.

**Guard.** Three checks added to `tests/kit_lint.py`:

1. `manifest-path-missing` / `manifest-path-untracked` — every path a manifest names must exist **and be in git**
2. `untracked-directory` — no directory without a tracked file inside it
3. `env-var-in-hook` — a shipped registration may not interpolate an environment variable

**What is not encoded:** nothing clones the bundle and runs the suite from the clone. That is
the real test and it is still a manual step — `tests/dual_run.py` (FK5) will do it from a
fresh clone rather than from the working copy, which is the only way this class stays dead.
