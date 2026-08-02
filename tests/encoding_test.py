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
ARROW = "→"

HOSTILE = {**os.environ, "LC_ALL": "C", "LANG": "C",
           "PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0"}
HOSTILE.pop("PYTHONIOENCODING", None)


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

        # 3. A CHILD OF A TOOL. The instruction must be INHERITED, because the
        #    scripts a tool spawns are not all ours -- dual_run runs the origin
        #    project's own copies, which import nothing from this kit. If only
        #    our processes were fixed, the acceptance gate would compare a
        #    surviving kit against a dying origin and call it a difference.
        child = d / "child.py"
        child.write_text(f'print("{ARROW}")\n', encoding="utf-8")
        parent = d / "parent.py"
        parent.write_text(
            "import sys, subprocess, pathlib\n"
            f"sys.path.insert(0, {str(KIT / 'tools')!r})\n"
            "import _project\n"
            f"r = subprocess.run([sys.executable, {str(child)!r}], capture_output=True,\n"
            '                   text=True, encoding="utf-8", errors="backslashreplace")\n'
            'print("CHILD_RC", r.returncode)\n'
            'print("CHILD_OUT", r.stdout.strip())\n', encoding="utf-8")
        r = run(parent, HOSTILE)
        good = "CHILD_RC 0" in r.stdout and ARROW in r.stdout
        ok &= good
        print(f"  {'ok ' if good else '!! '}a child that imports nothing of ours inherits it")
        if not good:
            print(f"       {(r.stdout + r.stderr).strip()[-300:]}")

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
