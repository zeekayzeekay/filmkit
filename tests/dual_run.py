#!/usr/bin/env python3
"""
THE ACCEPTANCE GATE — the kit must reproduce the origin project, exactly.

    python3 tests/dual_run.py --origin-scripts DIR --film DIR

`--origin-scripts` is a directory holding the project's OWN copies of the guard
scripts, as they were before extraction, with a `_SHA256SUMS.txt` beside them.
`--film` is that project's documents and facts file.

Both sets run against the SAME film, in two separate copies of it, and every
tool's output is compared line by line. Any difference is an extraction bug.

WHY IT IS A DIFF AND NOT A NUMBER
---------------------------------
Through the whole extraction I asserted things like *"checklist 74 findings, 32
manual, 0 untagged — matches its own run"*. That comparison was me reading a
number off a screen and comparing it against a number I remembered reading
earlier. It is the same method that produced six wrong divergence reports in the
origin project and the same method `compare_asset.py` exists to replace.

Remembered numbers agree far more readily than outputs do. A tool can print an
identical summary line and differ in every finding above it.

WHY IT REFUSES WITHOUT A MANIFEST
---------------------------------
FK-01: the transfer that brought those scripts into this container reported
`ok: true` with current timestamps for all fifteen files and served six of them
from a two-day-old snapshot. An acceptance gate run against stale sources
certifies a kit against a film that no longer exists. Hash first, or do not run.

WHAT A CLEAN RUN DOES NOT PROVE
-------------------------------
That either version is CORRECT. It proves they are the same, which is exactly
what an extraction should be and no more.
"""
import argparse, pathlib, re, shutil, subprocess, sys, tempfile

KIT = pathlib.Path(__file__).resolve().parent.parent

# (tool, args, needs_film_docs). Ordered cheapest first so a broken run fails early.
# INVOCATIONS, not tools. A differential test compares the code paths its calls
# reach, and nothing else. Proven: changing verify_asset's 6% scale threshold and
# flipping a return code in staleness were both MISSED by the first version of
# this list, because no invocation in it reached either line. More modes here is
# more coverage; it is never total coverage, and the report must not pretend
# otherwise.
TOOLS = [
    ("shotmap.py", []),
    ("verify_asset.py", ["--audit"]),
    ("verify_asset.py", ["--selftest"]),
    ("compare_asset.py", ["--audit"]),
    ("selections.py", ["--check"]),
    ("selections.py", ["--list"]),
    ("staleness.py", []),
    ("staleness.py", ["--list"]),
    ("checklist.py", []),
    ("checklist.py", ["--manual"]),
    ("guard_coverage.py", []),
    ("guard_coverage.py", ["--list"]),
    ("crossshot.py", ["5"]),
    ("crossshot.py", ["6B", "--quiet"]),
    ("crossshot.py", ["14"]),
    ("preflight.py", []),
]

# Every fixture and every prompt block, linted by both. lint_prompt holds 56 of
# the kit's rules; running it on one file reaches a fraction of them.
def lint_invocations(film):
    out = []
    for f in sorted(pathlib.Path(film).glob("*.md")):
        out.append(("lint_prompt.py", [f.name]))
    return out


# ---------------------------------------------------------------------------
# DECLARED EXPECTED DIFFERENCES. Short, justified, and each one a change the
# extraction MEANT to make. Same discipline as guard_coverage's EXEMPT list: an
# entry here is a difference somebody has looked at and signed for, and the
# report still prints it. Anything not on this list fails.
#
# Do not add an entry to make a red run go green. Add one when you can say, in a
# sentence, why the two versions SHOULD differ.
# ---------------------------------------------------------------------------
EXPECTED = [
    ("tarn_facts.json", None,
     "FK1 removed a hard-coded project filename from lint_prompt's direction-audit "
     "message, so it now names whichever facts file the film actually uses. The origin "
     "says tarn_facts.json because that is the only film it could ever describe."),
]


def account_for(origin_line, kit_line, film_facts_name):
    """True if the two lines differ ONLY by a declared expected substitution."""
    for frm, to, _why in EXPECTED:
        if origin_line.replace(frm, to or film_facts_name) == kit_line:
            return True
    return False


def normalise(text, *root_dirs):
    """
    Strip everything that MUST differ between two copies of one film: absolute
    paths, and the ANSI colour a terminal never sees in a pipe anyway. Anything
    else that differs is a real difference and must survive this.
    """
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    for d in root_dirs:
        text = text.replace(str(pathlib.Path(d).resolve()), "<FILM>")
    text = re.sub(r"/tmp/[A-Za-z0-9_.-]+", "<TMP>", text)
    return [ln.rstrip() for ln in text.strip().splitlines()]


def verify_sources(d):
    man = d / "_SHA256SUMS.txt"
    if not man.exists():
        raise SystemExit(
            f"\n  ! {d} has no _SHA256SUMS.txt — refusing to run.\n"
            "    FK-01: the transfer that brought these files here once reported success for\n"
            "    fifteen files and served six from a two-day-old snapshot. An acceptance gate\n"
            "    run on stale sources certifies the kit against a film that no longer exists.\n"
            "    Hash at the source, in the same operation that copies.\n")
    r = subprocess.run(["sha256sum", "-c", man.name], cwd=d, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"\n  ! source files do not match their manifest:\n{r.stdout}{r.stderr}\n")
    n = len([l for l in r.stdout.splitlines() if l.strip()])
    print(f"  {n} source file(s) verified against their manifest\n")


def run(tool_path, args, cwd):
    p = subprocess.run([sys.executable, str(tool_path), *args],
                       cwd=cwd, capture_output=True, text=True, timeout=900)
    return p.stdout + p.stderr, p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin-scripts", required=True)
    ap.add_argument("--film", required=True)
    ap.add_argument("--show", action="store_true", help="print the differing lines")
    a = ap.parse_args()

    origin = pathlib.Path(a.origin_scripts).resolve()
    film = pathlib.Path(a.film).resolve()
    verify_sources(origin)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dualrun-"))
    try:
        # TWO copies of one film. The origin's tools expect to live beside the
        # film and WRITE to it -- checklist regenerates, preflight mutates
        # fixtures. Sharing one directory would let each run see the other's
        # leavings, which is FK-04's fault deliberately reproduced.
        a_dir, b_dir = tmp / "origin", tmp / "kit"
        shutil.copytree(film, a_dir)
        shutil.copytree(film, b_dir)
        for f in origin.glob("*.py"):
            shutil.copy(f, a_dir / f.name)
        # the origin resolved its facts by a project-specific filename
        for cand in list(a_dir.glob("*_facts.json")):
            if cand.name != "tarn_facts.json":
                shutil.copy(cand, a_dir / "tarn_facts.json")
                break

        facts_name = next((c.name for c in sorted(b_dir.glob("*_facts.json"))), "film_facts.json")
        invocations = TOOLS + lint_invocations(a_dir)
        print(f"  DUAL RUN — {len(invocations)} invocations, two copies of {film.name}\n")
        same = diff = 0
        for tool, args in invocations:
            src = origin / tool
            if not src.exists():
                print(f"  -- {tool:22s} not in the origin set; nothing to compare against")
                continue
            if tool == "lint_prompt.py" and not (a_dir / args[0]).exists():
                continue
            out_a, rc_a = run(a_dir / tool, args, a_dir)
            out_b, rc_b = run(KIT / "tools" / tool, args, b_dir)
            la, lb = normalise(out_a, a_dir), normalise(out_b, b_dir)
            label = f"{tool} {' '.join(args)}".strip()
            accounted = 0
            if la != lb and len(la) == len(lb):
                pairs = [(x, y) for x, y in zip(la, lb) if x != y]
                if pairs and all(account_for(x, y, facts_name) for x, y in pairs):
                    accounted = len(pairs)
                    lb = la
            if la == lb and rc_a == rc_b:
                same += 1
                note = f", {accounted} expected" if accounted else ""
                print(f"  ok {label:30s} identical ({len(la)} lines, exit {rc_a}{note})")
            else:
                diff += 1
                print(f"  !! {label:30s} DIFFERS  (exit {rc_a} vs {rc_b}, "
                      f"{len(la)} vs {len(lb)} lines)")
                if a.show:
                    import difflib
                    for d in list(difflib.unified_diff(la, lb, "origin", "kit", lineterm="",
                                                       n=1))[:24]:
                        print(f"        {d[:120]}")
        print()
        if diff:
            print(f"  \033[91m{diff} tool(s) differ.\033[0m Every difference is an extraction bug "
                  f"until shown otherwise.")
            print("  Re-run with --show to see the lines.\n")
            return 1
        print(f"  \033[92mAll {same} invocations agree.\033[0m\n")
        if EXPECTED:
            print("  DECLARED EXPECTED DIFFERENCES — each one signed for, not ignored:")
            for frm, _to, why in EXPECTED:
                print(f"    {frm}")
                for line in __import__("textwrap").wrap(why, 74):
                    print(f"      {line}")
            print()
        print("  WHAT THIS PROVES: the extraction changed nothing OBSERVABLE THROUGH THESE")
        print(f"  {same} CALLS. Not that the tools are identical — a differential test compares")
        print("  the code paths its invocations reach, and a rule that never fires on this")
        print("  film is a rule this gate never sees. Changing verify_asset's 6% scale")
        print("  threshold and flipping a return code in staleness were both MISSED by an")
        print("  earlier, shorter version of this list.")
        print("\n  WHAT IT DOES NOT PROVE: that either version is CORRECT. Only that they")
        print("  agree, which is exactly what an extraction should be and no more.\n")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
