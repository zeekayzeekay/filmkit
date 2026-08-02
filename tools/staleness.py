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
  1. Every heading carries a machine-readable status:
       LIVE        the one current version for its role
       DRAFT       written, not yet fired — neither current nor dead. Without it,
                   future work gets mislabelled superseded and quietly disappears.
       SUPERSEDED  replaced by something else, which it must NAME
       DONE        it RAN, it produced registered assets, and nothing replaced it
       INFO        not a prompt
     A file-level marker above the first heading applies to the whole file, and a
     heading with its own marker overrides it.

     DONE exists because SUPERSEDED was being made to carry two different facts.
     A prompt that ran and produced a verified asset has not been replaced by
     anything, and requiring it to name a successor asks the document to state
     something untrue — which is the surest way to get a file that says whatever
     satisfied the checker. DONE names what it PRODUCED instead, and every tag it
     names must be in the ledger, so it is evidence rather than an escape hatch.
  2. Exactly ONE block is LIVE per role.
  3. No heading claims to be live in its TEXT unless it is marked LIVE — the
     words "live", "final", "selected" in a superseded heading are the trap.
  4. Every SUPERSEDED block names what replaced it; every DONE block names what
     it produced, and those tags must exist in the facts ledger.
  5. No live document cites an archived file except through `_archive/`.
  6. Every withdrawn selection and every retracted claim stays flagged.

Usage
  python3 staleness.py                 # report, exit 1 on any violation
  python3 staleness.py --list          # show every block and its status

Status comment shapes:
  <!-- status: LIVE role: k5_start -->
  <!-- status: SUPERSEDED by: `k5-28` -->
  <!-- status: DONE produced: @tarn_view_alt_1, @tarn_reverse_view -->
"""
import json, pathlib, re, sys
import _project as P  # FK1: where the film is

HERE = P.DIR
PROMPTS = P.file_list("prompts")
FACTS = P.PATH
ARCHIVE = HERE / "_archive"

# Documents a reader is told to trust. If one of these cites an archived file
# without the _archive/ prefix, the reader will follow it to something dead.
LIVE_DOCS = [p.name for p in P.files("live_docs")]

CLAIMS_CURRENT = re.compile(r"\blive\b|\bfinal\b|\bselected\b|\bcurrent\b", re.I)

# A DONE block WAS selected and WAS the final version — those words are true of
# it. What it must not claim is to be running now. Reusing CLAIMS_CURRENT here
# would flag honest headings, and a rule that flags honest text gets switched
# off.
CLAIMS_RUNNING = re.compile(r"\blive\b|\bcurrent\b", re.I)
TAG = re.compile(r"@[A-Za-z0-9_]+")


def blocks():
    """
    (file, heading, status, attrs) for every heading in EVERY prompt ledger.

    A film may keep its prompts in one file or in several. The origin project kept
    four and its own staleness read one of them, so three ledgers were never
    checked for a superseded block calling itself live. Reading all of them also
    makes the LIVE-role uniqueness check work ACROSS ledgers, which is where a
    duplicate is most likely and least visible.
    """
    out = []
    for f in PROMPTS:
        if not f.exists():
            continue
        lines = f.read_text(encoding="utf-8").splitlines()

        # A FILE-LEVEL MARKER, above the first heading, applies to the whole
        # file. Three of the origin project's four prompt ledgers open with
        #
        #     <!-- status: SUPERSEDED -->
        #     > SUPERSEDED 1 Aug — DONE, do not run. ...
        #
        # and the first version of this reader only looked at the line AFTER a
        # heading, so it called seventeen headings unmarked in files whose very
        # first line marks them. Seventeen violations, none of them real, in a
        # tool whose whole job is to be believed when it says something is
        # stale. A false positive at that volume retires the tool.
        file_status, file_attrs = None, ""
        for l in lines:
            if not l.strip():
                continue
            if re.match(r"^#{1,3} ", l):
                break                       # a heading; no file-level marker
            fm = re.match(r"<!--\s*status:\s*(\w+)(.*?)-->", l.strip())
            if fm:
                file_status, file_attrs = fm.group(1), fm.group(2)
                break

        for i, l in enumerate(lines):
            m = re.match(r"^#{1,3} (.+?)\s*$", l)
            if not m:
                continue
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            s = re.match(r"<!--\s*status:\s*(\w+)(.*?)-->", nxt.strip())
            if s:
                out.append((f.name, m.group(1), s.group(1), s.group(2), False))
            else:
                # inherited, and MARKED AS INHERITED. A heading that carries its
                # own SUPERSEDED must name what replaced it; one that inherits
                # the file's cannot, and demanding it per heading turns one
                # missing fact into as many violations as the file has sections.
                out.append((f.name, m.group(1), file_status, file_attrs, True))
    return out


def main():
    bad, blks = [], blocks()

    unmarked = [(fn, h) for fn, h, s, _, _ in blks if s is None or s == "UNMARKED"]
    for fn, h in unmarked:
        bad.append(f"{fn}: heading has no status marker: {h[:70]!r}")

    roles = {}
    for fn, h, s, a, _inh in blks:
        if s == "LIVE":
            r = re.search(r"role:\s*(\S+)", a)
            roles.setdefault(r.group(1) if r else "?", []).append(f"{fn}: {h}")
    for role, hs in roles.items():
        if len(hs) > 1:
            bad.append(f"{len(hs)} blocks claim to be LIVE for role {role}: {hs}")

    for fn, h, s, a, inherited in blks:
        if s in ("SUPERSEDED", "INFO", "DRAFT") and CLAIMS_CURRENT.search(h):
            bad.append(f"a {s} heading still calls itself live/final/selected — this is the "
                       f"exact trap that put two edits in the wrong block: {h[:70]!r}")
        if s == "DONE" and CLAIMS_RUNNING.search(h):
            bad.append(f"{fn}: a DONE heading still calls itself live or current — it ran and "
                       f"finished: {h[:70]!r}")
        if s == "SUPERSEDED" and "by:" not in a and not inherited:
            bad.append(f"{fn}: SUPERSEDED block does not name its replacement: {h[:70]!r}")

    # ---- DONE must name what it produced, and the ledger must have it ------
    # The whole value of DONE over SUPERSEDED is that it carries evidence. A DONE
    # block naming nothing, or naming a tag that was never registered, is the
    # escape hatch this status would otherwise be.
    _assets = set()
    if FACTS.exists():
        _assets = set(json.loads(FACTS.read_text(encoding="utf-8")).get("assets", {}))
    _seen_done = set()
    for fn, h, s, a, inherited in blks:
        if s != "DONE":
            continue
        key = fn if inherited else (fn, h)
        if key in _seen_done:
            continue
        _seen_done.add(key)
        where = f"{fn}: the whole file" if inherited else f"{fn}: {h[:60]!r}"
        named = TAG.findall(a or "")
        if "produced:" not in (a or "") or not named:
            bad.append(f"{where} is marked DONE and names nothing it produced. "
                       f"Add  produced: @tag[, @tag]  — DONE without evidence is "
                       f"SUPERSEDED with the requirement removed.")
            continue
        unknown = [x for x in named if x not in _assets]
        if unknown:
            bad.append(f"{where} is marked DONE and claims to have produced "
                       f"{', '.join(unknown)}, which the ledger does not have. A finished "
                       f"prompt is finished because its output was REGISTERED.")

    # A file declared SUPERSEDED as a whole must say so once, and say what
    # replaced it once. Once, not per heading.
    for f in PROMPTS:
        if not f.exists():
            continue
        inherited_here = [b for b in blks if b[0] == f.name and b[4]]
        if inherited_here and inherited_here[0][2] == "SUPERSEDED" \
                and "by:" not in inherited_here[0][3]:
            bad.append(f"{f.name}: the whole file is marked SUPERSEDED and names no "
                       f"replacement. Add by: to the file's status comment, or give the "
                       f"blocks that are still worth reading their own marker.")

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
        # Group by ledger only when there is more than one. With a single file
        # the listing must be byte-identical to what it has always been: a
        # cosmetic change shows up in the acceptance gate as a difference, and
        # a gate that has learned to expect a difference in a tool is a gate
        # that will not notice the next one.
        multi = len({fn for fn, _, _, _, _ in blks}) > 1
        last = None
        for fn, h, s, a, _inh in blks:
            if multi and fn != last:
                print(f"\n  --- {fn}")
                last = fn
            print(f"  {str(s):11s} {h[:74]}")
        print()

    from collections import Counter
    c = Counter(s or "UNMARKED" for _, _, s, _, _ in blks)
    # Say "in N ledgers" only when there ARE several. A film with one prompts
    # file must produce the SAME line it always produced -- a cosmetic change
    # here shows up in the acceptance gate as a divergence, and a divergence
    # somebody has already agreed to expect is a place a real change can hide.
    n_files = len({fn for fn, _, _, _, _ in blks})
    where = f" in {n_files} ledgers" if n_files > 1 else ""
    print(f"\n  {len(blks)} headings{where} · " + " · ".join(f"{n} {k}" for k, n in sorted(c.items())))

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
