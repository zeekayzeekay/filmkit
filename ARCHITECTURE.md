# FILMKIT — architecture

**One payload. Two hosts. Four layers with different lifetimes. One ritual that keeps it alive.**

This document is the design record for extracting the TARN guard kit into a reusable
system that runs identically under Claude Code and OpenAI Codex.

It supersedes nothing in `PORTABILITY.md` — it *extends* it. That document got the hard
part right on day one: the engine is project-agnostic, every film fact lives in one JSON
file, and it ends on the rule the whole system is built to serve:

> **A lesson that has not become a guard is a lesson you will pay for again.**

What it did not cover, and what this adds:

| gap in `PORTABILITY.md` | consequence | fixed by |
|---|---|---|
| Tells you to **copy** the kit per project | forks it — a guard fixed on film 3 never reaches films 1 and 2 | one versioned repo, projects pin a `kit_version` |
| Splits general from film-specific **by judgement** | decays in one film; it is the same shape as every recurrence we logged | `portability_test.py` — a mechanical test |
| Holds **no craft knowledge** — guards only | Leera, the Seedance method, sheet-building and script↔shot discipline live nowhere reusable | `skills/` and `knowledge/craft.md` |
| Nothing **loads state into the model** | the operator has to say "read these six documents", and I still forget | `SessionStart` hook |
| Nothing **stops the spend** | every guard is advisory at the moment money is committed | `PreToolUse` deny + self-gating tools |

---

## 1 · What is portable, verified

Researched 1 Aug 2026 against `code.claude.com/docs` and `developers.openai.com/codex`.
The headline: **Codex now has the same hook system Claude Code has** — `PreToolUse`
with `permissionDecision: "deny"`, identical stdin-JSON wire format, identical exit-2
semantics, regex matchers on tool name. And Skills are a genuine open standard
([agentskills.io](https://agentskills.io)) that both hosts read.

| piece | portable | mechanism |
|---|---|---|
| Guard scripts | **fully** | plain Python in `tools/`; both hosts shell out |
| The gate | **fully** | one script reading stdin JSON, registered twice |
| Skills | **format yes, path no** | one `skills/` dir; symlinked to `.claude/skills` and `.agents/skills` |
| Instructions | **via import** | `AGENTS.md` is the source; `CLAUDE.md` is `@AGENTS.md` |
| MCP config | **semantically** | Claude JSON vs Codex TOML — generate both from one source |
| Plugin manifest | **no** | two files around one shared payload |

### The one risk designed around

**Both hosts require explicit user trust before a repo-committed hook runs.** Codex gates
this behind `/hooks`; Claude Code behind the workspace trust dialog. A hook is therefore
*not* a guarantee on first run, on a new machine, or in a headless session.

So enforcement lives in **two independent places**:

1. the hook denies the generation call, and
2. **every tool that emits a fireable prompt refuses without a receipt.**

If the hook is untrusted, absent, or unsupported in a given host, the kit still cannot
hand over something unchecked. This is F-67 applied to the kit itself: *a guard that
cannot be satisfied gets routed around, and the routing is invisible* — so never build
a single gate that can be silently missing.

---

## 2 · The four layers

They are separate because they have **different lifetimes and different update rules**.
Collapse them and the general lessons die with the film that taught them.

### Layer 1 · ENGINE — true of Higgsfield/Seedance, whatever you film

Durations 4–15 s · elements are **global** to a generation · an element carries a
composition and an **axis**, not just materials (F-59) · an element is not a derivation
(F-62) · the models do **not** do novel view synthesis (F-63) · `medias[]` roles ·
`<<<element_id>>>` placeholders · job ids as media values · model ids and credit rates.

*Lifetime:* changes when Higgsfield ships, not when you start a film.

*Update rule:* **this is the only layer that expires.** It carries a `verified_on` date
and warns when stale. The proof that this matters is already in TARN — the shot script
still says *"13s is not a length the model offers"*, which was true once, is false now,
and cost nothing only by luck.

### Layer 2 · CRAFT — true of any film made this way

Prompt block order and the FOV anchor table · Leera's 4-D deconstruct · **one element per
camera angle** · derive an angle, never describe it · a conditioning frame is earned only
when a state changes *inside* the shot · the face/end disclosure taxonomy (F-71) · a
prohibition is a description with a minus sign (F-66) · say each important thing once ·
test ONE thing first · how to build a location plate, a character sheet, a prop sheet ·
how script and shot list stay in sync · the tolerance table — MUST match / SHOULD match /
MAY drift.

*Lifetime:* permanent, and it grows.

*Update rule:* additive only, through the promotion ritual (§4).

### Layer 3 · GUARDS — the executable layer

Thirteen scripts, 56 rules, the fixtures, the mutations, `guard_coverage`, plus the
findings that survive the portability test.

*Lifetime:* versioned.

*Update rule:* **a film pins a `kit_version`.** Tools warn on mismatch and refuse on a
major one. A film shot in August still runs its August guards in December — that is the
reproducibility requirement. Because fixtures travel with rules, an upgrade that breaks a
rule is caught in the kit's own test suite before it reaches any film.

### Layer 4 · LOOK — the shared style library, opt-in

Colour targets and the R−B method · palette · lens vocabulary · grading scripts ·
recurring wardrobe and props where films share a world.

*This is the layer most likely to be wrong to share.* Inheriting TARN's water target into
a different lake is precisely the drift the kit exists to prevent. A project therefore
declares `look_pack: "<name>"` or `look_pack: none`, and inheriting one is a decision
somebody writes down.

---

## 3 · Enforcement — how a generation actually gets blocked

```
  prompt written
        │
        ▼
  preflight.py ──── all phases green? ──no──▶ nothing is written, nothing can fire
        │ yes
        ▼
  receipt: .filmkit/receipts/<sha256(prompt)>.json
        │   { kit_version, fact_rev, phases, block, utc }
        ▼
  you fire  →  mcp__higgsfield__generate_video
        │
        ▼
  hooks/gate.py  (PreToolUse, registered in BOTH hosts)
        │
        ├─ receipt exists for THIS EXACT prompt text?      no ──▶ deny
        ├─ fact_rev still current?                         no ──▶ deny
        ├─ kit_version matches the project pin?            no ──▶ deny
        └─ yes ──▶ allow, and append to RUN_RECORD
```

The receipt is keyed on the **hash of the prompt about to be fired**, not on "preflight
was run recently". That closes the gap that already bit TARN once: a fired prompt that
did not match its own file.

**Override** exists, requires an explicit phrase, and writes the reason into the run
record. An override you cannot audit is not an override, it is a hole.

**Second layer:** the tools self-gate. `preflight --export` is the only path to a fireable
prompt file, and it will not write one without a green run. So even with the hook absent,
there is nothing to paste.

---

## 4 · The ritual that keeps it alive

Layers are storage. **The promotion ritual is what stops lessons being lost**, and it
needs a mechanical test or it becomes judgement and decays in one film.

### The portability test

> **A finding is general if its fixture still fires with every project proper noun
> replaced by a neutral token.**

Strip `@cafe_int`, `TARN`, `k6-v16`, `hero`, `tarn`, character names. If the rule still
catches the fault, it belongs to the kit. If it goes quiet, it was about your film.

That is a script, not an opinion, and it runs on every commit.

### `filmkit promote F-71`

1. run the portability test → refuse and explain if it fails
2. require a **neutral fixture** and a **mutation pair** (fires on the fault, silent on the repair)
3. append to `knowledge/FINDINGS.md`, preserving the `<!-- guard: … scope: … ask: … -->` block
4. bump `kit_version`
5. regenerate the checklist

`checklist.py` already guarantees the checklist cannot drift from the ledger, because
there is no second place to update. Promotion extends that guarantee across films.

### Session state

A `SessionStart` hook loads, every session, without being asked:

- kit version, and whether it matches the project pin
- current `fact_rev`
- failing gates
- unanswered manual checklist items
- open decisions awaiting the operator

This is the direct answer to *"invariably you are forgetting"*. Today that state only
reaches the model if the operator says "read these six documents" — which is not a
system, it is a hope.

---

## 5 · Repository layout

```
filmkit/
├── .claude-plugin/plugin.json      Claude Code manifest
├── .codex-plugin/plugin.json       Codex manifest
├── AGENTS.md                       single instruction source
├── CLAUDE.md                       "@AGENTS.md"
├── skills/                         shared payload, agentskills.io spec
│   ├── seedance-prompt/            block order, FOV table, Leera 4-D
│   ├── location-plate/             masters, derived angles, the axis rule
│   ├── character-sheet/            one face, panel discipline
│   ├── prop-sheet/
│   ├── shot-script-coherence/      script ↔ shot map, both directions
│   └── film-review/                review order, tolerance table
├── hooks/
│   ├── gate.py                     ONE gate script
│   ├── session_start.py            state loader
│   └── hooks.json                  Codex registration
├── settings/claude.settings.json   Claude registration
├── tools/                          the thirteen guards, de-TARNed
├── knowledge/
│   ├── engine.json                 layer 1, with verified_on
│   ├── craft.md                    layer 2
│   ├── FINDINGS.md                 layer 3, general only
│   └── looks/<pack>/               layer 4, opt-in
├── templates/new-project/          what filmkit init lays down
├── bin/{filmkit-init,doctor,promote}
└── tests/{fixtures,portability_test.py,dual_run.py}
```

A film project is then just:

```
myfilm/
├── film_facts.json      ← kit_version pinned, look_pack declared
├── SHOT_SCRIPT.md
├── FINDINGS.md          ← this film's faults only
├── .filmkit/receipts/
├── .claude/settings.json
└── .codex/hooks.json
```

---

## 6 · Acceptance

The kit is not "done" when it runs. It is done when it **reproduces TARN exactly**.

`tests/dual_run.py` points the extracted kit at `tarn_facts.json` **read-only** and
asserts byte-identical output from every tool against TARN's own copy — `shotmap`
findings, `preflight` phases, `guard_coverage`, `checklist`, `staleness`,
`verify_asset --audit`.

Any diff is the extraction bug list. TARN is never modified. The kit ships verified
against a real 17-shot film carrying 74 findings, rather than hoped-for.

---

## 7 · What is not encoded

Stated plainly, because the alternative is discovering it later:

- **Nothing gates a sentence.** The ledger cannot hold an unproven divergence and the
  tools cannot emit an unchecked prompt, but a person can still *say* a wrong thing.
  That stays a manual gate.
- **Trust is per-machine and per-host.** `filmkit doctor` can detect an untrusted hook
  and refuse to call itself healthy; it cannot grant the trust.
- **The portability test proves a fixture survives noun-stripping, not that a lesson is
  true.** A wrong general rule promotes just as cleanly as a right one.
- **Engine facts are only as fresh as the last check.** The expiry warning fires; it does
  not go and look.
- **The kit cannot see a gate that does not exist yet.** After writing any gate, ask
  which existing rows can no longer satisfy it — and check. That is F-72's lesson and it
  remains a habit, backed by `--audit`'s LOCKED report.
