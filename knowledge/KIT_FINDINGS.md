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

---

## FK-04 · THE PHASE THAT VERIFIES THE EXPORT RAN BEFORE THE PHASE THAT WRITES IT

<!-- guard: manual  scope: process
     ask: has the documented command been run from a clean directory, or only where earlier runs left files behind? -->

**Cost:** none yet, and only because the fault hides itself. Inherited from the origin project,
byte-identical — this is not a porting defect.

`preflight.py`'s documented invocation is

```
python3 preflight.py --block "<BLOCK>" --record RUN.md --export OUT.txt
```

`check_fullread` **reads** the export. `check_export` **writes** it. In `main()` the read ran
two lines before the write.

So the first run of the documented command, in a directory where that export does not yet
exist, dies on `FileNotFoundError` with a stack trace — no phase verdict, no `FAIL — do not
fire`, just a traceback. It has always appeared to work because a previous run always left the
file behind.

**Why it survived.** A tool used every day in one directory accumulates its own outputs, and
those outputs become undeclared inputs. The command was never run anywhere clean, so the
dependency never showed. **The kit made it visible immediately**, because a fresh scratch
project is by definition a clean directory — which is an argument for building one even when
you already have a working project.

**A traceback is not a phase result.** `preflight`'s central promise is *no partial pass: any
phase failing means do not fire.* A stack trace is the absence of a verdict, and an absence is
the one thing that promise cannot describe. A phase that cannot run must FAIL, loudly, by name,
with the reason.

**Fix.** Produce, then verify — `check_export` now runs first. And `check_fullread` reports a
named phase failure with the likely cause when the export is missing, instead of raising.

Verified afterwards on the real prompts file: with a unique block name, `export` PASS writing
20 KB of prompt, `prompt` PASS, and `full-read` / `manual` FAIL exactly as designed, because
both require a person to read and attest. That last part matters for FK3 — **the receipt must
be keyed on the fully green run, which is the one a human has signed.**

**What is not encoded:** nothing runs the documented command in a clean directory as part of
the suite. That is what a scratch project is for, and it is currently a habit rather than a
test.

---

## FK-05 · I WROTE DOWN THAT A FAILING HOOK FAILS OPEN, THEN BUILT ONE

<!-- guard: automatic  scope: process
     ask: does every path out of this gate produce a DECISION — including the paths that are errors? -->

**Cost:** none, caught in review one commit later. Had it shipped, the gate would have stopped
gating **in exactly the situation where somebody is most likely to be experimenting** — outside
a project — and said nothing at all.

FK-03, written the previous working session, established this:

> a hook command that fails for any reason other than exit 2 is a **hook failure, and
> processing continues** — so an env var that does not expand does not block the generation and
> does not raise an alarm.

I removed the guessed variable. Then I wrote `gate.py` with a `try/except` around **only** the
JSON parse, and left every other failure path to propagate.

```
$ cd /tmp/nofilm
$ echo '{"tool_name":"mcp__higgsfield__generate_video", ...}' | python3 gate.py
  ! no film found in /tmp/nofilm
[exit 1]
```

Exit 1, no `hookSpecificOutput`. Both hosts read that as hook failure. **The generation
proceeds.** `_project` resolves the film from the *process's* cwd and raises `SystemExit` when
it cannot find one — correct behaviour for a command-line tool, fatal for a hook.

**Two distinct faults, one symptom.**

*The gate asked the wrong question about location.* A hook's cwd is whatever the host chose. The
payload carries `cwd` and the gate ignored it. It now walks up from the reported directory and,
finding no film, **denies with a reason** instead of dying.

*The gate had no floor.* Every exit must be `0` with a decision. It now catches `BaseException`
— `SystemExit` included, deliberately — and denies with the exception in the reason.

> **A gate is a thing that says no when it cannot say yes.**

**And the tests could not have caught it**, which is the part worth keeping. All fifteen cases
called `decide()`, a pure function that returns a tuple. The fail-open lived in `main()`, in the
gap between that tuple and the process's exit code. **A test that only ever calls the pure core
cannot see the shell around it.** Four end-to-end cases now run the script as a subprocess and
assert exit 0 *and* a deny: outside any film, unparseable stdin, `tool_input` that is not a
dict, and a payload that is a list.

**A third fault, found in the same pass.** The selftest built its temp film as an empty
directory and wrote receipts using the *surrounding* film's `fact_rev` — 103 against `None`.
Two cases failed for a reason that had nothing to do with the gate, and `--selftest` only
worked from inside a film, which is precisely the wrong dependency for a test of a hook. The
fixture is now a real, minimal film; the selftest runs anywhere.

**What is not encoded:** nothing proves the host actually invokes this file, or that the
operator has trusted it. An inert gate is indistinguishable from a permissive one from the
inside — `filmkit-doctor` must report *registered* and *trusted* as two separate states, and
until it exists that check is a habit.

---

## FK-06 · FIVE FAULTS, ONE HABIT — AND A COMMAND INSTEAD OF A RESOLUTION

<!-- guard: automatic  scope: process
     ask: was this verified from a clone, in a directory with no history, by running the process rather than the function? -->

**Cost:** nothing directly. This finding exists because the previous five have one shape, and
a shape repeated five times is not five mistakes, it is one missing check.

| | what I verified | what mattered |
|---|---|---|
| FK-01 | the transfer tool's success report | the bytes |
| FK-02 | the diff | the use sites |
| FK-03 | the working copy | the deliverable |
| FK-04 | the tool where its own outputs already sat | a clean directory |
| FK-05 | the pure function | the process around it |

**Each time I checked the artefact in front of me rather than the one that has to survive the
trip.** The obvious response — review more carefully — is the one that cannot work, because the
same habit does the reviewing. Four of these were found by accident: an absurd number, a
question from the operator, an unrelated smoke test, and one deliberate probe.

**Guard.** `tests/verify.py`. It never tests the working tree. It clones **HEAD** into a temp
directory — so uncommitted work is excluded on purpose, because what is not committed is not
delivered — builds a film from `templates/new-project`, and runs every suite from that clone.
Uncommitted changes are listed, loudly, as *not verified*.

The clean-film phase asserts something weaker than PASS and more useful: **the tools must RUN
and report, never raise.** A brand-new film has no prompts, findings or assets, so nothing can
pass; what must not happen is a traceback, because *a traceback is not a phase result* and the
only place one surfaces is a directory where nothing has accumulated.

**It found two on its first run, both in the first command a new user would type.**

`checklist.py` opened the findings ledger unconditionally. A film that has not had its first
fault yet has no ledger — the normal state of every new project — and the tool that derives the
review checklist died with `FileNotFoundError`.

`preflight.py` opened every fixture named in the corpus. The kit seeds that corpus from the
origin project, so a new film names fixtures whose files are in **someone else's directory**,
and the phase whose entire purpose is *proving the guards still fire* raised instead. It now
reports them as what they are: rules nobody in **this** film has watched fire.

**The transferable rule.** *Verify the delivered thing, from a clone, in a directory with no
history, by running the process rather than the function.* Every one of the five would have
been caught by that sentence, and none of them was caught by intending to be careful.

**What is not encoded:** `verify.py` cannot say whether a rule is correct, whether the hosts
invoke the hook, or whether the operator has trusted it. It also runs only when someone types
it — there is no CI here. It is one command instead of five habits, which is progress, not a
guarantee.

---

## FK-07 · THE PROVENANCE CLAIM WAS ITSELF UNVERIFIED

<!-- guard: manual  scope: process
     ask: does the "how this was checked" line describe what was actually done, for every row — or for the rows I happened to check? -->

**Cost:** caught in review, in the same session. Nothing downstream had used it yet.

`knowledge/engine.json` is the layer that expires, so it carries a `_verified_how` line saying
how its facts were established. The first version said:

> *models_explore action=get for each model id, plus action=search for discovery.*

**Two of the nine had been fetched by id.** The other seven — `seedance_2_0_mini`,
`minimax_h3`, `gpt_image_2`, `seedream_v4_5`, `seedream_v5_pro`, `flux_kontext`,
`openai_hazel` — were copied out of a search listing, which is a summary the server chose to
return, not a record of the model.

**A false provenance claim is worse than no provenance claim**, because the next person
reading it stops checking. And this is the file whose entire reason for existing is that facts
from someone else's API go stale without anyone noticing. Writing an unverified line into it
is the failure the file was built to prevent, performed on the file itself.

**Doing it properly changed the contents**, which is the argument for doing it at all. Seven
`get` calls returned fields the search listing had not:

- `minimax_h3` has a `folder_id` parameter no other model here has
- three models — `minimax_h3`, `flux_kontext`, `openai_hazel` — carry **no** `supports_unlim`,
  where the other six carry `true`. Recorded now as an explicit `false`, because a missing key
  and a false value read the same to a person skimming and differently to anything that checks.
- aspect-ratio lists were absent for four models

**Fix.** Every model row carries its own `verified: "models_explore action=get, <date>"`. The
claim is now per-row and true, rather than one sentence covering rows it did not cover.

**Second correction in the same pass.** `_expires_after_days: 45` was a number with nothing
behind it, in a kit whose own portability document says *re-derive every threshold from your
own material; a budget calibrated on someone else's drafts is a number with no reason behind
it*. It is now labelled as a guess, with what would replace it: an observed rate, once there
are two dated versions of this file to compare.

**The transferable rule.** *A provenance line describes rows. Write it per row, or it will
describe the rows you happened to check.* Same shape as F-68 — a lineage field that records one
step reads as though it recorded the chain.

**What is not encoded:** nothing verifies that a `verified:` line is true. It is a signed
statement, like F-68's exemption and F-72's `is_master`, and its value is that the signature
is now per-row and dated rather than one confident sentence at the top.

---

## FK-08 · A DIFFERENTIAL TEST COMPARES INVOCATIONS, NOT TOOLS

<!-- guard: automatic  scope: process
     ask: which code paths does this comparison actually reach — and which rules never fire on this film at all? -->

**Cost:** none. Found by testing the acceptance gate instead of trusting it.

`tests/dual_run.py` runs the origin project's own guard scripts and the kit's ported ones
against two copies of one film and diffs every line. It reported **all ten tools identical**.

That was worth almost nothing until it was checked, for two separate reasons.

**First: I had been asserting the same thing all along, from memory.** Through the whole
extraction I wrote things like *"checklist 74 findings, 32 manual, 0 untagged — matches its own
run."* That is a number read off a screen, compared against a number remembered from earlier.
It is precisely the method that produced six wrong divergence reports in the origin project,
and precisely what `compare_asset.py` exists to replace. **Remembered numbers agree far more
readily than outputs do** — a tool can print an identical summary line and differ in every
finding above it.

**Second, and worse: the gate could not see most changes.** Three deliberate mutations:

| mutation | caught? |
|---|---|
| a trailing space in one message | no — and correctly so, the normaliser strips trailing whitespace |
| **`verify_asset`'s 6% scale threshold, `0.06` → `0.60`** | **NO** |
| **a `return 1` flipped to `return 0` in `staleness`** | **NO** |
| one word changed in a shotmap finding message | yes |

Neither miss was a bug in the comparison. **No invocation in the list reached either line.**
`verify_asset` was called only as `--audit` and `--selftest`, never on the claim-recording path
where that threshold lives; `staleness`'s `return 1` is on a failure branch this film does not
take.

> **Ten tools invoked is not ten tools compared. It is ten code paths compared, and a rule that
> never fires on this film is a rule this gate never sees.**

**Fix, in three parts.**

*More invocations.* 34 rather than 10 — every tool in each of its modes, plus `lint_prompt` on
every markdown file in the film, because that one tool holds 56 of the kit's rules and running
it on one file reaches a fraction of them.

*An honest report.* It no longer says "the extraction changed nothing". It says the extraction
changed nothing **observable through these 34 calls**, names the two mutations an earlier list
missed, and states that neither version is proven correct — only that they agree.

*A declared expected-difference ledger.* Widening coverage immediately surfaced a real
behavioural difference: FK1 removed a hard-coded project filename from `lint_prompt`'s
direction-audit message, so it now names whichever facts file the film uses. That is an
intended change, and the right handling is neither to fail forever nor to loosen the
comparison. Each entry carries a sentence saying why the two versions *should* differ, the
report prints them, and a difference not on the list still fails — **proven, by changing one
more word on the same line and confirming it is caught.**

**What is not encoded:** nothing measures coverage. There is no count of which lines these 34
calls reach, so the honest claim is bounded by the list and the list is a judgement. A rule
that fires only on a film nobody has shot yet is invisible to this gate and will stay invisible.

---

## FK-09 · THE CHECK FOR "NO PROJECT NOUNS" WAS WRITTEN WITH ONE PROJECT'S NOUNS

<!-- guard: automatic  scope: process
     ask: does this detector define its target structurally, or by listing the instances that have already gone wrong? -->

**Cost:** none. Found by pointing the kit's linter at the kit's own tests, which had been
outside every check since the linter was written.

`kit_lint` check 3 refuses a project filename in code. Its pattern was:

```python
PROJECT_NOUN = re.compile(r'["\'][^"\']*(?:tarn_facts|TARN_[A-Za-z0-9_]+\.md)[^"\']*["\']')
```

**The check that proves the kit knows about no particular film was written knowing about
exactly one.** It would pass a second film's nouns silently, forever — and that is the same
allow-list-of-dangers shape as F-56 and as the gate's first matcher. Three times now.

**It flagged itself, which is how it was found.** The detector's own pattern is a string
literal containing `tarn_facts`.

**Fix — define it structurally.** A project noun is a facts filename that is not one the kit
itself generates, or an upper-case document name that is not one of the document roles the kit
defines. No film appears anywhere in the rule. Proven to fire on `seabird_facts.json` and
`SEABIRD_SHOTS.md` — nouns from a film that does not exist — and to stay quiet otherwise.

**Two more faults in the same pass, both in the acceptance gate itself.**

`dual_run.py` hard-coded `tarn_facts.json` to set up the origin-side copy. **The gate whose
purpose is proving one film's name was removed from the tools knew exactly one film's name.**
It now reads the filename out of the origin scripts' own source — which is the very thing the
extraction removed from them — with `--origin-facts` to override.

And its expected-difference ledger was a Python list containing that filename. It is data about
one comparison, so it is now `tests/expected_differences.json`, the same treatment preflight's
fixture corpus got.

**And the gate was not a gate.** `dual_run` ran only when somebody remembered to type it. It is
now a phase of `tests/verify.py`, which runs it whenever both a real film and its origin
scripts are given.

**The transferable rule.** *A detector that lists instances guards the instances. Define the
class.* Every time this has come up — F-56's counting allow-list, the gate's tool matcher, this
— the fix was the same shape: stop naming what has gone wrong, and describe what wrong looks
like.

**What is not encoded:** the structural definition needs an allow-list of its own — the generic
document names the kit legitimately uses. That list is a judgement, and a film that names a
document `README.md` will not be caught.

---

## FK-10 · A FILM THAT NUMBERED ITS FINDINGS DIFFERENTLY WOULD HAVE HAD NO REVIEW LAYER AT ALL

<!-- guard: automatic  scope: process
     ask: when this parser does not recognise something, does it SAY SO — or does it skip and report success? -->

**Cost:** none, and only because a selftest I was writing for something else happened to invent
a finding called `X-9`.

`checklist.py` derives the review checklist from the findings ledger, and `preflight` refuses
to pass until every `manual` item in it has a written answer. That chain is the entire manual
review layer.

Its heading parser matched `(F-\d+[a-z]?|FK-\d+|DECISION)` — **one project's naming convention,
hard-coded in the engine.** A film numbering its findings `BUG-3`, `SHOT-12` or anything else
gets:

```
wrote REVIEW_CHECKLIST.md: 0 findings, 0 manual, 0 untagged
```

**Zero, and a success message.** No error, no warning, exit 0. Every finding invisible, the
manual gate with nothing to require, and `preflight` printing PASS on a film whose entire
review layer had silently evaporated.

**This is the fourth time.** F-56's counting detector was an allow-list of ten nouns. The spend
gate's first matcher was an allow-list of six tool names. `kit_lint`'s project-noun check
spelled out one film's filenames. Now this. Every one is the same move: **enumerate the
instances you have seen instead of describing the class.**

**And the file already knew.** Its own comment records F-56b — a two-word `scope:` value that
silently dropped a finding out of this same parser — and the fix recorded there was not to
widen the pattern by one case but to make `untagged` a **failure** rather than a note, because
*"in nobody's process"* is the condition the file exists to make impossible. The id pattern
kept its silence anyway.

**Fix, in two parts.** The pattern is now general — `LETTERS-NUMBER`, so `F-12`, `FK-3`,
`BUG-7` and `DECISION` all parse. And a heading that carries a metadata block but whose id is
still unrecognised is **reported by name**, because widening a pattern only moves the edge; it
is the silence at the edge that does the damage.

**The transferable rule.** *A parser that skips what it does not recognise must say what it
skipped.* Widening the pattern fixes today's case; reporting the remainder fixes the class.

**What is not encoded:** the heading must still carry a metadata block to be noticed. A finding
with neither a recognisable id nor a metadata block is indistinguishable from an ordinary
section heading, and nothing can tell them apart.

---

## FK-11 · THE GATE INVOKED ITS INTERPRETER BY NAME

<!-- guard: automatic  scope: process
     ask: does anything in the enforcement path require a LOOKUP — a PATH entry, an environment variable, a default — that could resolve to nothing? -->

**Cost:** none, caught by testing a thing I had built and never exercised: whether the matcher
in the installed registration would actually match a real tool name.

It does. But the line above it read:

```json
"command": "python3 \"/root/filmkit/hooks/gate.py\""
```

The script path was absolute — FK-03 saw to that, after the guessed `$CODEX_PLUGIN_ROOT`. The
**interpreter** was not. `python3` is a PATH lookup, and on Windows — where this kit is meant to
run — `python3` is frequently not a command at all. The host would run it, it would fail, and
**a hook that fails lets the call through.**

Same fault as the guessed environment variable, one layer down, and it survived the fix for the
variable because I was looking at the part I had just been burned by.

> **Any lookup in the enforcement path is a way for the gate to become silently absent.**
> An environment variable that does not expand, a PATH entry that resolves to nothing, a
> default that differs by platform — each of them fails, and every failure fails open.

**Fix.** `--install` now writes the absolute path of the interpreter that is running it, so the
command needs neither a variable nor a PATH lookup. `filmkit-doctor` **refuses** a registration
whose command invokes `python`, `python3` or `py` by name, with the reason.

**And the thing that found it is worth more than the fix.** I had never checked that the
matcher matched. A wrong regex there makes the whole gate inert while every other check in the
kit reports green — the registration present, the script correct, the receipt logic sound, and
nothing ever invoked. The doctor's selftest now asserts the installed matcher catches
`generate_video`, `generate_3d` and `apps_invoke`, and ignores another server's tools and
`Bash`.

**The transferable rule.** *Test the connection, not the ends.* Both ends of this were verified
repeatedly. The wire between them — a regex and a command string, written once and never
run — was the only part that could silently disconnect, and it was the only part nothing tested.

**What is not encoded:** whether either host actually reads these files, or parses the extra
`_generated_by` key without complaint. Neither is knowable from in here. The registration is
also machine-specific by design — absolute paths mean a film shared across machines needs
`filmkit-doctor --install` on each, which doctor detects and reports as "points at a different
kit".

---

## FK-12 · THE ACCEPTANCE GATE WAS RUN AGAINST A FILM THAT DOES NOT EXIST

<!-- guard: automatic   scope: process
     ask: name the artefact each gate you ran actually measured, and say how you know it was the one that ships -->

**What happened.** `dual_run.py` reported *"All 34 invocations agree"*, and that sentence was
the whole basis for saying the extraction changed nothing. The film it compared against held 19
files. The real film holds 26 documents. Eight were missing outright — including both prompt
ledgers, the run record and the findings-derived checklist. Three were stale copies from an
earlier staging. The facts file had been renamed.

The origin *scripts* were genuine: re-hashed against the operator's own disk, all fifteen
byte-identical. So the manifest discipline worked perfectly, in the one place it was applied —
`--origin-scripts`. `--film` took any directory and asked it nothing.

**Why the trimmed film existed at all.** Cost. Two `copytree` calls over a 2.7 GB film is 5.4 GB
and several minutes, so at some point a smaller stand-in got assembled and never replaced. That
is the actual mechanism, and it generalises: **a gate too expensive to run on the real thing
will be run on something else, and the report will not mention the substitution.**

**Fix.** `dual_run` hard-links pictures and copies only text, deny-by-default: unknown suffixes
are COPIED, because a text file wrongly linked would be rewritten through the link into the
operator's own film. The real film now stages in seconds. Run against it, the invocation count
went from 34 to 43 — nine calls that had never happened.

**The transferable rule.** *Hash the subject as well as the instrument.* Both inputs to a
differential test are inputs. Verifying one of them and trusting the other by name is the same
error as trusting a transfer tool's success report, which is FK-01 — and this is FK-01 again,
one level up, four gates later, in the gate built to prevent it.

**What is not encoded:** there is still no manifest on `--film`. The check that exists is
"does this film declare its documents" (FK-13), which is not the same question as "is this the
film you think it is".

---

## FK-13 · THREE TOOLS REPORTED NOTHING, TRUTHFULLY, AND EXITED ZERO

<!-- guard: automatic   scope: process
     ask: for each tool that reported an empty result this run, name the file it read and confirm it exists -->

**What happened.** Run against the real film, seven tools "differed" and the gate called every
difference an extraction bug. None of them was. The film has never been adopted: its ledger is
`TARN_FINDINGS.md` and its script `TARN_shot_script.md`, and the kit resolves `FINDINGS.md` and
`SHOT_SCRIPT.md`.

So `checklist.py` looked for a ledger, did not find one, and printed:

> no findings ledger at FINDINGS.md — nothing to derive a checklist from. **That is correct for
> a film with no faults recorded yet.** Write the first finding when the first thing costs you
> something.

then wrote a checklist of nothing and **exited zero**. The film has 74 findings. `crossshot`
reported *"no block found — the script heading format may have changed"* for every shot in the
film. `staleness` reported 0 headings against 23. Three tools, one cause, all three green.

Every word of that message is true of the file it looked for and false of the film in front of
it. **An empty result with a zero exit is indistinguishable from a clean one** — which is the
failure class the entire kit exists to remove, found in the kit's own reporting paths.

Note what it is NOT: not a crash, not a warning, not a silent skip. It is a considered,
well-written, reassuring sentence about a file that is not there.

**Fix.**

| | |
|---|---|
| `_project.undeclared()` | names every role where the kit fell back to a default, the default is absent, and a file answering to that name is sitting in the film |
| `_project.files()` | **refuses** in that case rather than resolving to a path it knows is not there |
| `filmkit-adopt` | proposes the `_files` block; **refuses to choose** when a role has several candidates |
| `filmkit-doctor` | reports undeclared roles as a red line |
| `dual_run`, `verify` | refuse up front — an undeclared film makes them compare configuration and report it as defect |

**The transferable rule.** *A tool that can report zero must be able to distinguish "nothing
there" from "not looking there".* Where it cannot, zero is not a result and must not be
rendered as one. The test is cheap and mechanical: when a lookup comes back empty, does
anything in the directory answer to that name? If so, the emptiness is a configuration error
wearing a result's clothes.

**What is not encoded:** the match is on the tail of the filename, case-insensitively. A film
that calls its ledger `notes.md` gets no candidate and no refusal — it gets the reassuring
sentence, correctly, because from the outside that film really does look like it has no ledger.
