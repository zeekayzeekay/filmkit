#!/usr/bin/env python3
"""
Put a prompt next to the shots either side of it, and next to the script.

WHY THIS EXISTS
---------------
Every prompt edit in this project has been reviewed against the prompt. Not once
against the shot before it, the shot after it, or the script — and the faults
that cost the most were exactly there:

  the walk was added to Shot 6      and the script still said he stops mid-turn
  the arc was removed from Shot 6   and Shot 4's "no arc here" note still said
                                    it existed to protect Shot 6's arc
  the light was corrected to cool   and the script's Shot 6 still said hard sun,
                                    while Shot 7 had said the sun was behind the
                                    building all along
  Shot 5 was trimmed to 4.5s        and every timecode after it was stale

None of those is visible from inside the prompt. All four are obvious the moment
the neighbours are on the same screen — which is all this tool does.

It does not judge. It gathers: the continuity row for N-1, N, N+1, the script
text for the same three shots, and the invariants. The reading is a person's;
what was missing was the gathering.

Usage
  python3 crossshot.py 6                       # shots 5, 6, 7
  python3 crossshot.py 6 --grep "arc|sun"      # only lines matching, for a targeted check
"""
import argparse, json, pathlib, re, sys
import _project as P  # FK1: where the film is

HERE = P.DIR
FACTS = P.PATH
SCRIPT = P.files("script")


def script_block(n):
    """The script's own text for one shot, heading to next heading."""
    if not SCRIPT.exists():
        return None
    t = SCRIPT.read_text(encoding="utf-8")
    m = re.search(rf"^### SHOT {n} · .*?(?=^### SHOT |\Z)", t, re.M | re.S)
    return m.group(0) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot")
    ap.add_argument("--grep", help="only show script lines matching this regex")
    ap.add_argument("--quiet", action="store_true", help="continuity table only")
    a = ap.parse_args()

    d = json.loads(FACTS.read_text(encoding="utf-8"))
    cont = d.get("continuity", {})
    cols = re.findall(r"[a-z_]+", cont.get("_columns", "").split(":")[-1])
    # ---- neighbours come from the ORDER of the continuity table, not from
    # arithmetic. Shot 6B exists (F-50): with integer stepping, shot 7's true
    # predecessor was invisible and the tool compared it to shot 6 while
    # silently skipping the shot actually before it. A cross-shot check that
    # cannot see the adjacent shot is worse than none, because it reports.
    order = [k for k in cont if k != "_columns" and k != "invariants"]
    key = str(a.shot)
    if key not in order:
        print(f"\n  unknown shot {a.shot!r}. Known: {', '.join(order)}\n")
        return 1
    i = order.index(key)
    shots = order[max(0, i - 1): i + 2]

    print(f"\n{'='*78}\n  CONTINUITY — shot {a.shot} and its neighbours\n{'='*78}")
    if cols and shots:
        w = max(len(c) for c in cols) + 2
        print(f"  {'':{w}}" + "".join(f"shot {s:<26}" for s in shots))
        for i, c in enumerate(cols):
            vals = [str(cont[str(s)][i])[:28] if i < len(cont[str(s)]) else "" for s in shots]
            row = "".join(f"{v:<31}" for v in vals)
            # a column that changes between neighbours is where continuity breaks
            mark = "  " if len(set(vals)) == 1 else "! "
            print(f"{mark}{c:{w}}" + row)
        print("\n  '!' marks a property that CHANGES across these shots. Each one is either")
        print("  deliberate and in the script, or a continuity fault. There is no third case.")

    inv = cont.get("invariants", {})
    if inv and not a.quiet:
        print(f"\n{'='*78}\n  INVARIANTS — true in every shot, so true in this one\n{'='*78}")
        for k, v in inv.items():
            print(f"  · {k}: {v[:150]}")

    if a.quiet:
        return 0

    for s in shots:
        blk = script_block(s)
        print(f"\n{'='*78}\n  SCRIPT — shot {s}\n{'='*78}")
        if not blk:
            print("  (no block found — the script heading format may have changed)")
            continue
        lines = [l for l in blk.splitlines() if l.strip()]
        if a.grep:
            lines = [l for l in lines if re.search(a.grep, l, re.I)]
            if not lines:
                print(f"  (nothing matching /{a.grep}/)")
        for l in lines[:40]:
            print("  " + l[:150])
        if len(lines) > 40:
            print(f"  … {len(lines)-40} more lines")

    print(f"\n{'='*78}")
    print("  Three questions, and they are the ones no guard can ask for you:")
    print("   1. Does the prompt contradict the script for THIS shot?")
    print("   2. Does anything the prompt changed invalidate a neighbour's text?")
    print("   3. Does any '!' above appear in the script as a deliberate change?")
    print(f"{'='*78}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
