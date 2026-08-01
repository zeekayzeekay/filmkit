#!/usr/bin/env python3
"""
Record which frame is selected, and INVALIDATE it when the facts move.

WHY THIS EXISTS — F-19
----------------------
`k5-24` was declared the final start frame because it was the only candidate to
pass the head-box rim gate. That was correct on the day. Hours later four
`@cafe_int` facts were corrected — the glazing count, the brass position, the
counter front, the door — and the selection was never re-opened. Measured
against the corrected facts `k5-24` had three of them wrong, and it was still
being cited as the gated start frame three messages later.

Nothing caught it, and nothing could have: `frames_check` measures light only,
and the asset guard reads PROMPTS, never the frames those prompts produced. A
frame built from a wrong specification is invisible to every automatic check.

THE RULE
    A selection is a claim that a frame satisfies the facts as they stood when it
    was made. Correct a fact and every selection older than that correction is
    provisional again until someone re-checks it and says so.

Usage
  python3 selections.py --set start G3/k5-29.png --depends @cafe_int @hero
  python3 selections.py --check          # anything selected under stale facts?
  python3 selections.py --confirm start  # re-checked by hand; stamp it today
"""
import argparse, datetime, json, pathlib, sys
import _project as P  # FK1: where the film is

HERE = P.DIR
FACTS = P.PATH


def load():
    return json.loads(FACTS.read_text(encoding="utf-8"))


def save(d):
    FACTS.write_text(json.dumps(d, indent=2), encoding="utf-8")


def newest_fact(d, tag):
    """Highest REVISION of any verified claim on an asset.

    Dates were the obvious choice and were wrong: every correction and every
    selection in this project happened on the same day, so a date comparison
    reported everything current. Revisions are a monotonic counter, immune to
    clock granularity, and they make staleness exactly decidable."""
    rec = d.get("assets", {}).get(tag, {})
    rs = [v.get("rev", 0) for v in rec.get("verified", [])]
    return max(rs) if rs else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", nargs=2, metavar=("ROLE", "FILE"))
    ap.add_argument("--depends", nargs="*", default=[])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--confirm", metavar="ROLE")
    ap.add_argument("--withdraw", metavar="ROLE")
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    d = load()
    sel = d.setdefault("selections", {})

    if a.set:
        role, f = a.set
        sel[role] = {"file": f, "selected_on": datetime.date.today().isoformat(),
                     "at_rev": d.get("_fact_rev", 0), "depends_on": a.depends, "note": a.note}
        save(d)
        print(f"  {role} = {f}  (depends on {', '.join(a.depends) or 'nothing declared'})")
        print("  If any of those facts is corrected later, this selection goes stale "
              "and --check will say so.")
        return 0

    if a.confirm:
        if a.confirm not in sel:
            print(f"  no selection named {a.confirm!r}")
            return 1
        sel[a.confirm]["selected_on"] = datetime.date.today().isoformat()
        sel[a.confirm]["at_rev"] = d.get("_fact_rev", 0)
        sel[a.confirm]["reconfirmed"] = a.note or "re-checked against current facts"
        save(d)
        print(f"  {a.confirm} re-confirmed today: {sel[a.confirm]['file']}")
        return 0

    if a.withdraw:
        if a.withdraw not in sel:
            print(f"  no selection named {a.withdraw!r}")
            return 1
        sel[a.withdraw]["withdrawn"] = a.note or "withdrawn"
        save(d)
        print(f"  {a.withdraw} withdrawn: {sel[a.withdraw]['file']} — {sel[a.withdraw]['withdrawn']}")
        return 0

    print("\n  selections vs the facts they rest on\n")
    if not sel:
        print("  none recorded. Record them — an unrecorded selection cannot go stale, "
              "which is not the same as being correct.\n")
        return 0
    stale = False
    for role, s in sorted(sel.items()):
        if s.get("withdrawn"):
            print(f"  -- {role:8s} {s['file']:22s} WITHDRAWN — {s['withdrawn'][:70]}")
            continue
        when = s.get("at_rev", 0)
        bad = []
        for tag in s.get("depends_on", []):
            nf = newest_fact(d, tag)
            if nf > when:
                claims = [v for v in d["assets"][tag]["verified"] if v.get("rev", 0) > when]
                for c in claims:
                    bad.append(f"{tag} rev{c['rev']}: {c['claim'][:78]}")
        if bad:
            stale = True
            print(f"  !! {role:8s} {s['file']:22s} selected at fact-rev {when}, now rev {d.get('_fact_rev','?')}")
            for b in bad:
                print(f"       STALE — {b}")
        else:
            print(f"  ok {role:8s} {s['file']:22s} current at fact-rev {when}")
    if stale:
        print("\n  A selection made under superseded facts is not a selection. Re-check the "
              "\n  frame against the corrected claims, then `--confirm ROLE` to stamp it.\n")
        return 1
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
