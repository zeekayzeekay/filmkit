#!/usr/bin/env python3
"""
Refuse to let anything superseded pass itself off as current.

WHY THIS EXISTS
---------------
Facts had enforcement. Documents and prompt blocks had conventions, and a
convention is a thing that holds until somebody is in a hurry.

The exposure, measured 31 Jul:

  · TARN_STAGE3_PROMPTS.md held 17 headings, THREE of them live — and TWO of
    them both called themselves "the live prompt". That ambiguity is what put
    two edits into historical blocks earlier in the project.
  · Two headings still asserted "SELECTED: k5-23" and "FINAL: k5-24". Both were
    long dead: k5-23 failed its own light gate, k5-24 was withdrawn under F-19.
    A new session reading top-down would have believed both.
  · Nothing stopped a live document citing an archived one as though current.

WHAT THIS ENFORCES
  1. Every heading carries a machine-readable status: LIVE / SUPERSEDED / DRAFT / INFO.
     DRAFT is for a prompt not yet fired — neither current nor dead. Without it,
     future work gets mislabelled superseded and quietly disappears.
  2. Exactly ONE block is LIVE per role.
  3. No heading claims to be live in its TEXT unless it is marked LIVE — the
     words "live", "final", "selected" in a superseded heading are the trap.
  4. Every SUPERSEDED block names what replaced it.
  5. No live document cites an archived file except through `_archive/`.
  6. Every withdrawn selection and every retracted claim stays flagged.

Usage
  python3 staleness.py                 # report, exit 1 on any violation
  python3 staleness.py --list          # show every block and its status
"""
import json, pathlib, re, sys
import _project as P  # FK1: where the film is

HERE = P.DIR
PROMPTS = P.files("prompts")
FACTS = P.PATH
ARCHIVE = HERE / "_archive"

# Documents a reader is told to trust. If one of these cites an archived file
# without the _archive/ prefix, the reader will follow it to something dead.
LIVE_DOCS = [p.name for p in P.files("live_docs")]

CLAIMS_CURRENT = re.compile(r"\blive\b|\bfinal\b|\bselected\b|\bcurrent\b", re.I)


def blocks():
    """(heading, status, attrs) for every heading in the prompts file."""
    if not PROMPTS.exists():
        return []
    lines = PROMPTS.read_text(encoding="utf-8").splitlines()
    out = []
    for i, l in enumerate(lines):
        m = re.match(r"^#{1,3} (.+?)\s*$", l)
        if not m:
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        s = re.match(r"<!--\s*status:\s*(\w+)(.*?)-->", nxt.strip())
        out.append((m.group(1), s.group(1) if s else None, s.group(2) if s else ""))
    return out


def main():
    bad, blks = [], blocks()

    unmarked = [h for h, s, _ in blks if s is None or s == "UNMARKED"]
    for h in unmarked:
        bad.append(f"heading has no status marker: {h[:70]!r}")

    roles = {}
    for h, s, a in blks:
        if s == "LIVE":
            r = re.search(r"role:\s*(\S+)", a)
            roles.setdefault(r.group(1) if r else "?", []).append(h)
    for role, hs in roles.items():
        if len(hs) > 1:
            bad.append(f"{len(hs)} blocks claim to be LIVE for role {role}: {hs}")

    for h, s, a in blks:
        if s in ("SUPERSEDED", "INFO", "DRAFT") and CLAIMS_CURRENT.search(h):
            bad.append(f"a {s} heading still calls itself live/final/selected — this is the "
                       f"exact trap that put two edits in the wrong block: {h[:70]!r}")
        if s == "SUPERSEDED" and "by:" not in a:
            bad.append(f"SUPERSEDED block does not name its replacement: {h[:70]!r}")

    archived = {p.name for p in ARCHIVE.glob("*.md")} if ARCHIVE.exists() else set()
    for f in LIVE_DOCS:
        p = HERE / f
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8")
        for a in archived:
            for m in re.finditer(rf"(?<!_archive/)\b{re.escape(a)}", txt):
                seg = txt[max(0, m.start() - 12):m.start()]
                if "_archive/" in seg:
                    continue
                bad.append(f"{f} cites archived {a} as if current")
                break

    if FACTS.exists():
        d = json.loads(FACTS.read_text(encoding="utf-8"))
        for role, s in d.get("selections", {}).items():
            if s.get("withdrawn") and "WITHDRAWN" not in str(s.get("withdrawn", "")).upper():
                bad.append(f"selection {role} is withdrawn but not labelled as such")
        for tag, rec in d.get("assets", {}).items():
            for v in rec.get("verified", []):
                if v.get("retracted") and not (v.get("supersedes") or v.get("retracted_in_part") or v.get("replaced_by")):
                    bad.append(f"{tag} rev{v.get('rev')} is retracted but names no replacement — "
                               "retracting a claim must MOVE its supersedes, never drop them")
            # F-70. A divergence recorded with no side-by-side on disk is a
            # divergence somebody read off a screen. Two of those went to Zee
            # on 1 Aug; one was wrong and one was not a divergence.
            for dv in rec.get("known_divergences_from_master", []) or []:
                if "proofs/asset_compare/" not in str(dv):
                    bad.append(f"{tag} records a divergence that cites no side-by-side — "
                               "run compare_asset.py and put its proof path in the entry")

    if "--list" in sys.argv:
        print()
        for h, s, a in blks:
            print(f"  {str(s):11s} {h[:74]}")
        print()

    from collections import Counter
    c = Counter(s or "UNMARKED" for _, s, _ in blks)
    print(f"\n  {len(blks)} headings · " + " · ".join(f"{n} {k}" for k, n in sorted(c.items())))

    if bad:
        print(f"\n  {len(bad)} STALENESS VIOLATION(S):")
        for b in bad:
            print(f"   · {b}")
        print("\n  Something superseded is presenting itself as current. Fix the marker or the text.\n")
        return 1
    print("\n  Nothing superseded is presenting itself as current.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
