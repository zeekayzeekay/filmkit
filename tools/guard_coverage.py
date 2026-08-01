#!/usr/bin/env python3
"""
Assert that EVERY rule the linter can emit has been seen to fire.

WHY THIS EXISTS
---------------
On 31 Jul an audit found 14 of 45 rules had never fired on anything in the
project. They had been written, believed, and never demonstrated. That is not a
theoretical worry — this kit has already shipped three rules that COULD NOT
fire:

  scope-conflict     compared temperature vocabulary; the two sentences it was
                     built from used different words, so it matched nothing
  MEASURED-LOCK      its regex missed any line beginning with "> "
  released-but-locked required two shared words; the fault it was built for
                     shared one ("letterplate"), so it missed it

Each was written against a real fault, looked right, and was silent. The only
difference between those and a working rule is that somebody watched it fire.

WHAT THIS ENFORCES
    Every rule name the linter can emit must fire on at least one block in
    GUARD_SELFTEST.md or in one of the regression fixtures. A new rule with no
    block fails this check, which is the point: the rule is not finished until
    it has been seen to work.

Usage
  python3 guard_coverage.py            # report and exit 1 if any rule unproven
  python3 guard_coverage.py --list     # show which file proves each rule
"""
import glob, pathlib, re, subprocess, sys
import _project as P  # FK1: where the film is


# ---------------------------------------------------------------------------
# FK1. The regression corpus lives in TWO places on purpose: fixtures the KIT
# owns (a rule general enough to survive the portability test brings its own
# neutral fixture) and fixtures the FILM owns (a rule about this film's nouns).
# guard_coverage must see both, or a kit rule reads UNPROVEN on every project
# that has not happened to reproduce its fault yet.
# ---------------------------------------------------------------------------
def _kit_fixtures():
    d = P.KIT.parent / "tests" / "fixtures"
    return sorted(d.glob("*.md")) if d.exists() else []

HERE = P.DIR
# Absolute paths throughout. The first port mixed bare filenames (resolved
# against the film) with absolute kit-fixture paths in one list, which happened
# to work only because Path("/a") / "/b" returns "/b".
CORPUS = [P.files("selftest")] + P.globs("regression_globs") + _kit_fixtures()

# Rules that are STRUCTURALLY unprovable by a fixture, with the reason. Keeping
# this list short and justified is the whole discipline: an entry here is a rule
# nobody can demonstrate, and it should be a rule nobody relies on.
EXEMPT = {
    "asset-claim-unproven":
        "fires on the FACTS FILE, not on a prompt — it needs a ledger entry "
        "with no proof crop, and verify_asset.py refuses to write one. It is "
        "unreachable by construction, which is the guarantee it exists to give.",
}


def rules_defined():
    src = pathlib.Path(P.tool("lint_prompt.py")).read_text(encoding="utf-8")
    return set(re.findall(r'\("(?:ERROR|WARN|CHECK)",\s*"([a-z0-9:_-]+)"', src))


def rules_fired():
    seen = {}
    for f in CORPUS:
        if not f.exists():
            continue
        out = subprocess.run([sys.executable, P.tool("lint_prompt.py"), str(f)],
                             capture_output=True, text=True, cwd=HERE).stdout
        for h in re.findall(r"\[(?:ERROR|WARN|CHECK)\] ([a-z0-9:_-]+)", out):
            name = h.rstrip(":")
            if name.startswith("consistency"):
                name = "consistency"
            seen.setdefault(name, f.name)
    return seen


def main():
    defined, fired = rules_defined(), rules_fired()
    unproven = sorted(r for r in defined - set(fired) if r not in EXEMPT)
    orphan = sorted(set(fired) - defined - {"consistency"})

    print(f"\n  {len(defined)} rules defined · {len(defined) - len(unproven) - len(EXEMPT)} "
          f"proven by a fixture · {len(EXEMPT)} exempt · {len(unproven)} UNPROVEN\n")

    if "--list" in sys.argv:
        for r in sorted(defined):
            where = fired.get(r) or ("EXEMPT" if r in EXEMPT else "-- NOTHING --")
            print(f"    {r:28s} {where}")
        print()

    for r in EXEMPT:
        print(f"  exempt  {r}\n          {EXEMPT[r]}")

    if orphan:
        print("\n  !! rules fired that are not defined — the name changed and a "
              "fixture still references the old one:")
        for r in orphan:
            print(f"     {r}")

    if unproven:
        print("\n  !! UNPROVEN — no block in the corpus makes these fire:")
        for r in unproven:
            print(f"     {r}")
        print("\n  Add a block to GUARD_SELFTEST.md that triggers each, or delete the rule.")
        print("  A rule nobody has watched fire is a rule nobody should rely on.\n")
        return 1

    print("\n  Every rule has been seen to fire on real text.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
