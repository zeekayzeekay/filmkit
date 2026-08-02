#!/usr/bin/env python3
"""
VERIFY THE THING THAT SHIPS — from a clone, in a clean directory, end to end.

WHY THIS EXISTS
---------------
Five faults in this kit's own construction, and they are one fault:

    FK-01  checked the transfer tool's success report, not the bytes
    FK-02  checked the diff, not the use sites
    FK-03  checked the working copy, not the deliverable
    FK-04  ran the tool where its own outputs already sat, not in a clean directory
    FK-05  tested the pure function, not the process around it

**Each time I verified the artefact in front of me instead of the one that has to
survive the trip.** Re-reading the code does not fix that, because the same habit
does the re-reading. A command does.

So this script never tests the working tree. It:

    1. clones HEAD into a temp directory       -- uncommitted work is excluded
                                                  ON PURPOSE: what is not
                                                  committed is not delivered
    2. builds a film from templates/new-project -- a genuinely clean directory
    3. runs every suite FROM THE CLONE
    4. optionally runs the full suite against a REAL film as well

WHAT `--fresh` CAN AND CANNOT SAY
---------------------------------
A film made from the template has no prompts, no findings and no assets, so the
tools cannot PASS -- there is nothing to pass on. What they must do is RUN, and
report the empty state by name rather than raising. That is precisely the
condition FK-04 hid in: a traceback is not a phase result, and the only place a
traceback shows up is a directory where nothing has accumulated.
"""
import json, pathlib, shutil, subprocess, sys, tempfile

KIT = pathlib.Path(__file__).resolve().parent.parent
FAIL = []


def run(cmd, cwd, expect_zero=True, name=""):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="backslashreplace", timeout=900)
    out = p.stdout + p.stderr
    crashed = "Traceback (most recent call last)" in out
    bad = crashed or (expect_zero and p.returncode != 0)
    if bad:
        FAIL.append((name, "traceback" if crashed else f"exit {p.returncode}",
                     out.strip().splitlines()[-6:]))
    print(f"  {'ok ' if not bad else '!! '}{name:46s} exit {p.returncode}"
          f"{'  TRACEBACK' if crashed else ''}")
    return out


def clone_head():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="filmkit-verify-"))
    dst = tmp / "kit"
    r = subprocess.run(["git", "clone", "-q", str(KIT), str(dst)],
                       capture_output=True, text=True, encoding="utf-8", errors="backslashreplace")
    if r.returncode:
        raise SystemExit(f"could not clone HEAD: {r.stderr}")
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=KIT,
                           capture_output=True, text=True, encoding="utf-8", errors="backslashreplace").stdout.strip()
    if dirty:
        print("\n  \033[93mNOTE — the working tree has uncommitted changes.\033[0m")
        print("  They are NOT in this verification, because they are not in the deliverable.")
        for line in dirty.splitlines()[:8]:
            print(f"    {line}")
    return tmp, dst


def fresh_film(root, kit):
    """
    Build it with the COMMAND a person would run, not by copying the template.
    The first version copied templates/new-project directly, which tested a
    directory layout nobody creates that way and left filmkit-init — the very
    first thing anyone types — completely unexercised.
    """
    film = root / "freshfilm"
    subprocess.run([sys.executable, str(kit / "bin" / "filmkit-init"), str(film),
                    "--name", "freshfilm"], capture_output=True, text=True, encoding="utf-8", errors="backslashreplace", timeout=300)
    return film


def main():
    real = origin_scripts = None
    if "--against" in sys.argv:
        real = pathlib.Path(sys.argv[sys.argv.index("--against") + 1]).resolve()
    if "--origin-scripts" in sys.argv:
        origin_scripts = pathlib.Path(sys.argv[sys.argv.index("--origin-scripts") + 1]).resolve()

    tmp, kit = clone_head()
    try:
        print(f"\n  VERIFY — from a clone of HEAD at {kit}\n")

        print("  STRUCTURE")
        run([sys.executable, str(kit / "tests" / "kit_lint.py")], cwd=kit,
            name="kit lints itself")

        print("\n  THE GATE (from outside any film)")
        run([sys.executable, str(kit / "hooks" / "gate.py"), "--selftest"], cwd=tmp,
            name="gate decides every case")

        print("\n  A CLEAN FILM — tools must RUN and report, never raise")
        film = fresh_film(tmp, kit)
        for tool, args, zero in (
            ("shotmap.py", [], False),
            ("verify_asset.py", ["--audit"], False),
            ("compare_asset.py", ["--audit"], False),
            ("checklist.py", [], False),
            ("staleness.py", [], False),
            ("guard_coverage.py", [], False),
            ("selections.py", ["--check"], False),
            ("preflight.py", [], False),
        ):
            run([sys.executable, str(kit / "tools" / tool), *args], cwd=film,
                expect_zero=zero, name=f"{tool} {' '.join(args)}".strip())

        run([sys.executable, str(kit / "bin" / "filmkit-doctor")], cwd=film,
            expect_zero=False, name="doctor reports the film's wiring")

        print("\n  SELFTESTS THAT NEED NO FILM")
        run([sys.executable, str(kit / "tools" / "verify_asset.py"), "--selftest"],
            cwd=film, name="counting detector discriminates")
        run([sys.executable, str(kit / "hooks" / "session_start.py"), "--selftest"],
            cwd=tmp, name="state loader briefs and fails silent")
        run([sys.executable, str(kit / "bin" / "filmkit-promote"), "--selftest"],
            cwd=tmp, name="promotion gates refuse what they should")
        run([sys.executable, str(kit / "bin" / "filmkit-doctor"), "--selftest"],
            cwd=tmp, name="doctor never claims the hook is trusted")
        run([sys.executable, str(kit / "tests" / "encoding_test.py")],
            cwd=tmp, name="tools survive a stdout that cannot encode them")

        if real:
            print(f"\n  A REAL FILM — {real}")
            # FIRST: can this kit read this film at all? An undeclared film makes
            # every phase below measure files that are not there and report the
            # emptiness as a result. The phase that eventually noticed was the
            # acceptance gate, which called it seven extraction bugs.
            # `--against DIR` accepts any directory; this is the check that the
            # directory is the thing it claims to be.
            u = subprocess.run([sys.executable, str(kit / "tools" / "_project.py"),
                                "--undeclared"], cwd=real, capture_output=True, text=True, encoding="utf-8", errors="backslashreplace")
            if u.returncode:
                FAIL.append(("the film has not declared its documents", "undeclared",
                             u.stdout.strip().splitlines()[-8:]))
                print("  !! film has not declared its documents         run: filmkit-adopt")
                print("     Everything below reads files that are not there.\n")
            run([sys.executable, str(kit / "tools" / "preflight.py")], cwd=real,
                expect_zero=False, name="preflight")
            run([sys.executable, str(kit / "tests" / "portability_test.py"), "--selftest"],
                cwd=real, name="portability test discriminates")
            run([sys.executable, str(kit / "tools" / "guard_coverage.py")], cwd=real,
                name="every rule proven by a fixture")

        if real and origin_scripts:
            # The acceptance gate. It existed for one commit as a thing somebody
            # had to remember to run, which is not a gate.
            print("\n  ACCEPTANCE — the kit reproduces the origin project")
            run([sys.executable, str(kit / "tests" / "dual_run.py"),
                 "--origin-scripts", str(origin_scripts), "--film", str(real)],
                cwd=kit, name="dual run against the origin's own scripts")
        elif real:
            print("\n  ACCEPTANCE — skipped: pass --origin-scripts DIR to run the dual run")

        print()
        if FAIL:
            print(f"  \033[91m{len(FAIL)} FAILURE(S)\033[0m\n")
            for name, why, tail in FAIL:
                print(f"  [{why}] {name}")
                for line in tail:
                    print(f"      {line[:110]}")
                print()
            return 1
        print("  \033[92mThe delivered kit runs clean from a clone, in a directory with"
              " no history.\033[0m")
        print("  NOT verified: that any rule is CORRECT, that the hosts invoke the hook,")
        print("  or that the operator has trusted it. Those are filmkit-doctor's and a")
        print("  person's, in that order.\n")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
