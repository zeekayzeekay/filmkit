#!/usr/bin/env python3
"""
Generate the review checklist FROM the findings ledger.

WHY THIS EXISTS
---------------
A hand-maintained checklist drifts from the ledger the moment either is edited,
and then people trust the stale one. This project has already proved that twice:
the sibling fixture's own header said "4 errors" long after it reported 6, and
the element-truth document carried four false facts through a dozen reviews.

So the checklist is not maintained. It is DERIVED. Add a finding to
TARN_FINDINGS.md with the metadata block below and it appears here; there is no
second place to update and no way for the two to disagree.

FINDING METADATA — put this line under any `## F-NN` heading:

    <!-- guard: automatic|manual  scope: prompt|asset|frames|process|delivery
         ask: the question a reviewer must answer in writing -->

`automatic` findings are listed for context; `manual` ones become numbered items
that preflight requires an answer to before it will print PASS.

Usage
  python3 checklist.py                 # write REVIEW_CHECKLIST.md
  python3 checklist.py --manual        # just the manual items, as a run record
"""
import argparse, pathlib, re, sys
import _project as P  # FK1: where the film is

HERE = P.DIR
LEDGER = P.files("findings")
OUT = P.files("checklist")

# F-56b. `scope:` was `\w+`, so the first finding written with a two-word scope
# ("build/verify") failed to parse and dropped silently out of the checklist —
# a finding about a guard with too narrow a vocabulary, lost to a guard with too
# narrow a vocabulary. Scope now accepts words, slashes, commas and hyphens, and
# an untagged finding is a FAILURE rather than a note: "in nobody's process" is
# the exact condition this file exists to make impossible.
META = re.compile(
    r"<!--\s*guard:\s*(?P<guard>[\w-]+)\s+scope:\s*(?P<scope>[\w/, -]+?)\s*"
    r"ask:\s*(?P<ask>.+?)\s*-->", re.S)


def findings(_report=None):
    # A film that has not had its first fault yet has no ledger. That is the
    # NORMAL state of a new project, and it was a FileNotFoundError traceback --
    # in the first command filmkit-init tells you to run. FK-04's class exactly:
    # the tool had only ever been run in a directory where the file already was.
    if not LEDGER.exists():
        print(f"\n  no findings ledger at {LEDGER.name} — nothing to derive a checklist from.")
        print("  That is correct for a film with no faults recorded yet. Write the first")
        print("  finding when the first thing costs you something.\n")
        return []
    text = LEDGER.read_text(encoding="utf-8")
    out, unparsed = [], []
    parts = re.split(r"\n## ", text)
    for p in parts[1:]:
        head = p.split("\n", 1)[0].strip()
        # A finding may carry a letter suffix -- F-56b, F-61b, F-72b -- for a
        # second lesson from the same fault. `F-\d+` swallowed the number and
        # left the letter in the TITLE, so F-61b parsed as id "F-61" titled
        # "b · CLOSES THE FAR END..." and collided with the real F-61. Two
        # findings, one id, one mangled title, in the file whose whole purpose
        # is that the checklist cannot disagree with the ledger.
        m = re.match(r"([A-Z][A-Z0-9]{0,7}-\d+[a-z]?|DECISION)\s*·?\s*(.*)", head)
        if not m:
            # A heading that carries a metadata block but whose id this parser
            # does not recognise is a finding that VANISHES. The pattern used to
            # be (F-\d+|FK-\d+|DECISION) -- one project's naming convention,
            # hard-coded -- so a film numbering its findings BUG-3 or SHOT-12 got
            # "0 findings, 0 manual, 0 untagged" and a success message. The manual
            # review layer would simply not exist, and preflight's gate would have
            # nothing to require.
            #
            # Same shape as F-56b, where a two-word scope silently dropped a
            # finding out of this same file, and the fix was to make the silence
            # impossible rather than to widen the pattern by one case.
            if META.search(p):
                unparsed.append(head[:70])
            continue
        fid, title = m.group(1), m.group(2)
        meta = META.search(p)
        out.append(dict(id=fid, title=title,
                        guard=meta.group("guard") if meta else None,
                        scope=meta.group("scope") if meta else None,
                        ask=" ".join(meta.group("ask").split()) if meta else None))
    if unparsed:
        print(f"\n  !! {len(unparsed)} heading(s) carry a metadata block and an id this parser")
        print("     does not recognise, so they are in NOBODY'S process:")
        for h in unparsed:
            print(f"       ## {h}")
        print("     Expected LETTERS-NUMBER, e.g. F-12, FK-3, BUG-7, or DECISION.\n")
        if _report is not None:
            _report.extend(unparsed)
    return out


def render(fs):
    manual = [f for f in fs if f["guard"] == "manual"]
    auto = [f for f in fs if f["guard"] == "automatic"]
    untagged = [f for f in fs if not f["guard"]]
    L = []
    L.append("# TARN — REVIEW CHECKLIST\n")
    L.append(f"> **Generated by `checklist.py` from `{LEDGER.name}`. Do not edit by hand.**")
    L.append("> A hand-kept checklist drifts from the ledger and then gets trusted anyway.")
    L.append("> Add the finding, add its metadata, re-run this.\n")
    L.append("Run before **every** prompt that is written or changed:\n")
    L.append("```\npython3 preflight.py --block \"<BLOCK>\" --start <A.png> --end <B.png> \\\n"
             "        --record RUN.md\n```\n")
    L.append(f"## Manual items — {len(manual)}\n")
    L.append("`preflight` will not print PASS until every one of these is answered "
             "in writing in the run record. An unanswered item is a failed run.\n")
    for i, f in enumerate(manual, 1):
        L.append(f"**M{i}. {f['ask']}**  \n<sub>{f['id']} · {f['title']} · scope: {f['scope']}</sub>\n")
    L.append(f"\n## Covered automatically — {len(auto)}\n")
    L.append("Listed so nobody re-checks them by hand, and so a guard that stops "
             "firing is noticed. `preflight --fixtures` proves each is alive.\n")
    for f in auto:
        L.append(f"- `{f['id']}` {f['title']}")
    if untagged:
        L.append(f"\n## Untagged — {len(untagged)}\n")
        L.append("**These have no `guard:` metadata, so they are in nobody's process.** "
                 "Tag them or delete them.\n")
        for f in untagged:
            L.append(f"- `{f['id']}` {f['title']}")
    return "\n".join(L) + "\n"


def run_record(fs):
    manual = [f for f in fs if f["guard"] == "manual"]
    L = ["# RUN RECORD\n",
         "Answer every item. `unanswered` fails the run. One line each is fine — "
         "the point is that somebody looked, not that it is written up.\n"]
    for i, f in enumerate(manual, 1):
        L.append(f"## M{i} · {f['id']}\n{f['ask']}\n\n> unanswered\n")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual", action="store_true", help="print a blank run record")
    a = ap.parse_args()
    fs = findings()
    if a.manual:
        print(run_record(fs))
        return 0
    OUT.write_text(render(fs), encoding="utf-8")
    m = sum(1 for f in fs if f["guard"] == "manual")
    u = sum(1 for f in fs if not f["guard"])
    print(f"  wrote {OUT.name}: {len(fs)} findings, {m} manual, {u} untagged")
    if u:
        print(f"  ! {u} findings have no guard metadata and are therefore in nobody's process")
        print("    Tag each one with <!-- guard: … scope: … ask: … --> and re-run. Refusing to")
        print("    report a checklist as current while a finding is outside it.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
