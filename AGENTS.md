# FILMKIT — operating instructions

You are working on a film made with Higgsfield/Seedance. This kit exists because
**prose does not enforce.** Every rule here was written after a fault that cost
something real. Read `knowledge/FINDINGS.md` for the evidence behind any rule you are
tempted to skip.

## The five standing rules

1. **Credits belong to the operator. Always ask before spending.**
2. **Never fire a generation yourself unless told to.** Produce the prompt; they run it.
3. **Report "no faults of any known class", never "clean"** — and name what is not encoded.
4. **Every prompt change is checked against the previous shot, the next shot, and the script.**
5. **Not every mismatch is a fault.** Consult the tolerance table before calling anything drift.

## Before you write a prompt

```
python3 tools/shotmap.py            # what does this shot need, and what supplies it?
python3 tools/verify_asset.py --audit   # is anything unverified, or LOCKED?
```

A shot photographed on an axis no attached plate covers is a shot arguing with its own
reference. Build the plate first — **derived from the master, never fresh from prose.**

## Before anything fires

```
python3 tools/preflight.py --block "<BLOCK>" --record RUN.md --export OUT.txt
```

No partial pass. Any phase failing means do not fire. A receipt is written on green, and
**the generation is blocked without one** — by a PreToolUse hook where hooks are trusted,
and by the tools themselves everywhere else.

## When something goes wrong

A fault that cost something becomes a finding, and **a finding is not closed until it has
a guard and a fixture.** If it cannot be automated it becomes a `manual` checklist item
with a written question. Never leave it as a paragraph.

If the lesson is general rather than about this film:

```
python3 bin/filmkit-promote FINDING-ID
```

which runs the portability test, demands a neutral fixture, and moves it into the kit.

## Two habits that no script can hold

- **A divergence is COMPARED, never noticed.** Run `compare_asset.py` before the word
  leaves your mouth. Ask which face, then ask which end.
- **After writing any gate, ask which existing rows can no longer satisfy it** — and
  check. Three separate guards have been unsatisfiable by an entire class of asset.

Kit version: 0.1.0. See `ARCHITECTURE.md` for why this is shaped the way it is.
