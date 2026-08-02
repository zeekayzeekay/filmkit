#!/usr/bin/env python3
"""
THE TOOLS MUST NOT DEPEND ON THE HOST'S LOCALE.

    python3 tests/encoding_test.py

THE FAULT
---------
On the operator's Windows machine:

    sys.stdout.encoding           utf-8      <- a console
    locale.getpreferredencoding   cp1252     <- a PIPE

Python takes a pipe's encoding from the second. Every tool in this kit runs other
tools and captures their output, so in normal operation the encoding is always
the second one. `lint_prompt.py` prints `→`, which cp1252 cannot represent, so the
child raises UnicodeEncodeError partway through its report and dies — and the
parent reads a truncated run as a short one.

Measured: `guard_coverage` reported three rules UNPROVEN on Windows and zero on
Linux, against byte-identical files. Nothing was wrong with the rules.

WHY THIS TEST CAN RUN ANYWHERE
------------------------------
A hostile locale is reproducible on any platform: `LC_ALL=C` with the coercion
switches off gives an ASCII stdout, which is stricter than cp1252 and fails the
same way for the same reason. The point is not to imitate Windows. It is to run
with a stdout that cannot encode the characters the tools print.

THE CONTROL COMES FIRST
-----------------------
Case 1 asserts the harness is actually hostile. Without it, a green result would
mean either 'the fix works' or 'the environment was never dangerous', and those
are indistinguishable — which is the failure mode this kit keeps finding in its
own tests. If the control passes, this test proves NOTHING and says so.
"""
import os, pathlib, subprocess, sys, tempfile

KIT = pathlib.Path(__file__).resolve().parent.parent

# The harnesses are not tools and do not import _project, so the fix that lives
# there did not reach them -- and on Windows this very test crashed printing the
# line that says the fix works. FK-14b.
sys.path.insert(0, str(KIT / "tools"))
import _utf8  # noqa: F401,E402
ARROW = "→"

HOSTILE = {**os.environ, "LC_ALL": "C", "LANG": "C",
           "PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0"}
HOSTILE.pop("PYTHONIOENCODING", None)

# What a FOREIGN process would actually inherit from one of our tools: the
# hostile locale, plus anything this kit has put into the environment by being
# imported. If the kit imposes nothing, this is identical to HOSTILE.
#
# Building it by popping the variable — as case 3's first version did — makes
# the case unable to fail. It passed with the fault deliberately reinstated,
# which is the same defect it was written to catch, one level up.
INHERITED = dict(HOSTILE)
if "PYTHONIOENCODING" in os.environ:
    INHERITED["PYTHONIOENCODING"] = os.environ["PYTHONIOENCODING"]


def run(script, env):
    """Always through a PIPE. A terminal would hide the whole fault."""
    return subprocess.run([sys.executable, str(script)], env=env,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="backslashreplace", timeout=120)


def main():
    ok = True
    print("\n  ENCODING — the tools write UTF-8 whatever they are attached to\n")
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)

        # 1. THE CONTROL. Bare Python, hostile locale, no import of ours.
        bare = d / "bare.py"
        bare.write_text(f'print("{ARROW}")\n', encoding="utf-8")
        r = run(bare, HOSTILE)
        control_hostile = r.returncode != 0 and "UnicodeEncodeError" in (r.stdout + r.stderr)
        ok &= control_hostile
        print(f"  {'ok ' if control_hostile else '!! '}control: the harness IS hostile "
              f"(bare python dies on {ARROW})")
        if not control_hostile:
            print("\n     \033[91mThis environment cannot encode-fail, so nothing below means")
            print("     anything.\033[0m A test that cannot fail is not evidence. Stop here.\n")
            return 1

        # 2. A TOOL. Importing _project must make this process's stdout UTF-8,
        #    which is what every tool in the kit does on its first line.
        tool = d / "tool.py"
        tool.write_text(
            "import sys, pathlib\n"
            f"sys.path.insert(0, {str(KIT / 'tools')!r})\n"
            "import _project\n"
            f'print("{ARROW}")\n', encoding="utf-8")
        r = run(tool, HOSTILE)
        good = r.returncode == 0 and ARROW in r.stdout
        ok &= good
        print(f"  {'ok ' if good else '!! '}a tool prints {ARROW} through a pipe under a "
              f"hostile locale")
        if not good:
            print(f"       exit {r.returncode}: {(r.stdout + r.stderr).strip().splitlines()[-1:]}")

        # 3. A FOREIGN CHILD IS LEFT ALONE — and this case replaces its opposite.
        #
        #    The first version asserted that a child importing nothing of ours
        #    INHERITED the instruction, via PYTHONIOENCODING in the environment.
        #    That shipped, and the acceptance gate caught it on the operator's
        #    machine the next day:
        #
        #        - origin  23 headings Â· 2 DRAFT Â· 4 INFO ...
        #        + kit     23 headings · 2 DRAFT · 4 INFO ...
        #
        #    The origin project's preflight runs its own staleness and prints the
        #    result. staleness inherited the variable and wrote UTF-8; preflight
        #    inherited nothing that changes how it DECODES, read those bytes with
        #    the host locale, and produced mojibake. Forcing a child to write in
        #    an encoding its parent does not read is a mismatch, not a fix.
        #
        #    So: harden by IMPORT, never by ENVIRONMENT. Here that is asserted in
        #    the only way that means anything -- a parent and child that are both
        #    foreign must round-trip UNCHANGED through our tooling.
        foreign_child = d / "fchild.py"
        foreign_child.write_text('print("\u00b7 marker")\n', encoding="utf-8")
        foreign_parent = d / "fparent.py"
        foreign_parent.write_text(
            "import sys, subprocess\n"
            f"r = subprocess.run([sys.executable, {str(foreign_child)!r}],\n"
            "                   capture_output=True, text=True)\n"   # NO encoding=, on purpose
            'sys.stdout.buffer.write(b"CHILD:" + r.stdout.encode("utf-8", "replace"))\n',
            encoding="utf-8")
        # A locale whose encoding is not UTF-8 is what makes this test mean
        # something; under one, a foreign pair that agrees with ITSELF is the
        # only correct outcome, whatever bytes they agree on.
        r = run(foreign_parent, INHERITED)
        blob = r.stdout + r.stderr
        good = "\u00c2" not in blob and "UnicodeDecodeError" not in blob
        ok &= good
        print(f"  {'ok ' if good else '!! '}a foreign parent and child are not interfered with")
        if not good:
            print(f"       {blob.strip()[:160]}")
            print("       Something in this kit is imposing an encoding on processes that "
                  "are not ours —")
            print(f"       inherited: "
                  f"{ {k: v for k, v in INHERITED.items() if k.startswith('PYTHON')} }")

        # ...and OUR tool still writes UTF-8 to that same hostile pipe, by import
        # alone. Both halves, or neither is evidence.
        r = run(tool, HOSTILE)
        good = r.returncode == 0 and ARROW in r.stdout
        ok &= good
        print(f"  {'ok ' if good else '!! '}...while ours still writes {ARROW}, by import alone")

        # 4. THE REAL ENTRY POINTS, not stand-ins. Cases 1-3 test the mechanism
        #    with scripts this file wrote, which is how the first version passed
        #    on Linux while the shipped harnesses were unprotected — the fix
        #    lived in `_project`, and the harnesses do not import it. On the
        #    operator's machine THIS FILE then crashed printing the line that
        #    says the fix works.
        #
        #    So: run the things that actually ship, under the hostile locale,
        #    through a pipe.
        for rel, args in () if os.environ.get("FILMKIT_ENCODING_CHILD") else (
                         ("tests/kit_lint.py", []),
                          ("hooks/gate.py", ["--selftest"]),
                          ("hooks/session_start.py", ["--selftest"]),
                          ("bin/filmkit-promote", ["--selftest"]),
                          ("bin/filmkit-doctor", ["--selftest"]),
                          ("bin/filmkit-init", ["--help"]),
                          ("bin/filmkit-adopt", ["--help"]),
                          ("tests/snapshot_origin.py", []),
                          ("tests/dual_run.py", ["--help"]),
                          ("tests/status_test.py", []),
                          ("tests/encoding_test.py", [])):
            # ...including itself, which is why the recursion stop exists. A test
            # exempt from its own check is the shape of the fault above.
            r = subprocess.run([sys.executable, str(KIT / rel), *args],
                               env={**HOSTILE, "FILMKIT_ENCODING_CHILD": "1"},
                               capture_output=True, text=True, encoding="utf-8",
                               errors="backslashreplace", timeout=300)
            blob = r.stdout + r.stderr
            good = "UnicodeEncodeError" not in blob and "UnicodeDecodeError" not in blob
            ok &= good
            print(f"  {'ok ' if good else '!! '}{rel:26s} survives a hostile locale")
            if not good:
                print(f"       {blob.strip().splitlines()[-1][:100]}")

    print()
    if ok:
        print("  \033[92mNo faults of any known class.\033[0m")
        print("  NOT tested: Windows itself. This reproduces the CLASS — a stdout that")
        print("  cannot encode what the tools print — on whatever platform it runs. A")
        print("  cp1252 pipe and an ASCII pipe fail for the same reason; they are not the")
        print("  same environment, and only the operator's machine can close that gap.\n")
        return 0
    print("  \033[91mFAILED.\033[0m A tool that dies mid-report is read as a tool with less")
    print("  to say. That is a wrong answer, not an error.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
