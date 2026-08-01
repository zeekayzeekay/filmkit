#!/usr/bin/env python3
"""
Find the sentences that were LEFT STANDING when their neighbours were rewritten.

WHY THIS EXISTS — F-31, class 3
-------------------------------
When K6's destination moved from the middle of the glazing to the door, nine
sentences kept describing the old one. Three of them could not be caught by any
rule that reads the prompt alone:

    "@hero stands a little left of the centre of the frame"
    "His shoulders are square to the window"
    "from this far back the riser's top edge projects lower in the picture ..."

None of them names a destination. They were true BECAUSE of the old one, and the
link is a piece of reasoning, not a word. No amount of vocabulary matching
reaches them, and "re-read the prompt" is what let them through in the first
place.

THE OBSERVATION THIS TOOL IS BUILT ON
    A sentence like that is not scattered at random. It sits in a paragraph its
    author was actively editing, and survived because the author was editing
    AROUND it. So: diff two versions, find the paragraphs that CHANGED, and list
    the sentences inside them that DID NOT.

    That is mechanical, repeatable, and it does not need to understand anything.
    Validated on the real pair: run against K6 v8 -> v9 it surfaces all three of
    the sentences above, because all three sit in paragraphs that were rewritten
    around them.

WHAT IT IS NOT
    It cannot tell you a survivor is wrong — only that it is a survivor, which
    is the population the wrong ones live in. It narrows a 2900-word prompt to a
    handful of sentences a person can actually read with the decision in mind.

Usage
  python3 stale_neighbours.py OLD.txt NEW.txt
  python3 stale_neighbours.py OLD.txt NEW.txt --decision "destination: glazing -> door"
  python3 stale_neighbours.py OLD.txt NEW.txt --quiet     # exit code only
"""
import argparse, difflib, pathlib, re, sys

# Terms that make a surviving sentence WORTH READING. A sentence about grain or
# colour rarely depends on where a man is standing; one about position,
# orientation or framing usually does. This list only sets the ORDER of the
# report — nothing is hidden by being absent from it.
POSITIONAL = re.compile(
    r"\b(left|right|centre|center|behind|in front|toward|towards|square to|"
    r"facing|angle[ds]?|nearer|closer|short of|beyond|past|across|"
    r"frame height|fills?|edge of the (?:frame|picture)|projects?|"
    r"height|hip|shoulder|knee|thigh|foot|feet|heel)\b", re.I)

# Do NOT split on a colon. "It fills the frame directly behind him:" is a
# fragment, not a claim, and splitting there filled the first report with
# half-sentences that no one can evaluate. A survivor has to be readable on
# its own or it is noise, and noise is what gets a report skimmed.
SENT = re.compile(r"(?<=[.;])\s+")


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def sentences(par):
    flat = re.sub(r"[*_`]+", "", par)
    return [s.strip() for s in SENT.split(flat) if len(s.strip()) > 45]


def norm(s):
    return re.sub(r"\s+", " ", s.lower()).strip()


def align(old_pars, new_pars):
    """Pair paragraphs across versions by best textual similarity.

    Not by index: a version that adds or drops a paragraph shifts every one
    after it, and an index-aligned diff then reports the whole tail as changed,
    which buries the finding in noise.
    """
    pairs, used = [], set()
    for np_ in new_pars:
        best, score = None, 0.0
        for i, op in enumerate(old_pars):
            if i in used:
                continue
            r = difflib.SequenceMatcher(None, norm(op)[:400], norm(np_)[:400]).ratio()
            if r > score:
                best, score = i, r
        if best is not None and score > 0.35:
            used.add(best)
            pairs.append((old_pars[best], np_, score))
        else:
            pairs.append((None, np_, 0.0))      # wholly new paragraph
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old"); ap.add_argument("new")
    ap.add_argument("--decision", default="",
                    help="what changed, in your words — printed at the top so the "
                         "reader has it in mind while reading the survivors")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    old = pathlib.Path(a.old).read_text(encoding="utf-8")
    new = pathlib.Path(a.new).read_text(encoding="utf-8")
    pairs = align(paragraphs(old), paragraphs(new))

    ranked, plain, changed_pars = [], [], 0
    for op, np_, score in pairs:
        if op is None or norm(op) == norm(np_):
            continue                    # untouched paragraph: not the population
        changed_pars += 1
        old_s = {norm(s) for s in sentences(op)}
        for s in sentences(np_):
            if norm(s) in old_s:        # survived a rewrite of its neighbours
                (ranked if POSITIONAL.search(s) else plain).append((np_.split(".")[0][:46], s))

    if a.quiet:
        return 1 if ranked else 0

    print(f"\n  {pathlib.Path(a.old).name}  ->  {pathlib.Path(a.new).name}")
    if a.decision:
        print(f"  DECISION CHANGED: {a.decision}")
    print(f"  {changed_pars} paragraph(s) rewritten\n")

    if not ranked and not plain:
        print("  No sentence survived a rewritten paragraph. Nothing to read.\n")
        return 0

    print(f"  {len(ranked)} SURVIVING SENTENCE(S) THAT TALK ABOUT POSITION OR FRAMING.")
    print("  Read each one with the decision in mind and ask: was this true ONLY")
    print("  because of the old one?\n")
    for head, s in ranked:
        print(f"    [{head}...]")
        print(f"      {s[:240]}")
    if plain:
        print(f"\n  {len(plain)} other survivor(s), unlikely but listed for completeness:")
        for head, s in plain:
            print(f"    - {s[:110]}")
    print("\n  A survivor is not a fault. It is where the faults live: every one of")
    print("  K6 v9's undetectable stale sentences was a survivor of this kind.\n")
    return 1 if ranked else 0


if __name__ == "__main__":
    sys.exit(main())
