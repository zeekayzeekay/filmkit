#!/usr/bin/env python3
"""
THE HOST'S LOCALE IS NOT A PLACE TO KEEP A DEPENDENCY.

Import this first, for the side effect. Every executable in this kit does.

    import _utf8   # noqa: F401

WHAT IT FIXES
-------------
On the operator's Windows machine:

    sys.stdout.encoding           utf-8      <- a console
    locale.getpreferredencoding   cp1252     <- a PIPE

Python takes a pipe's encoding from the second. Every tool here runs other tools
and captures their output, so in normal operation the encoding is always the
second one -- the first is what you see running a tool by hand, which is exactly
why it looked fine. `lint_prompt.py` prints an arrow cp1252 cannot represent, so
the child raised UnicodeEncodeError partway through its report and died, and the
parent read a truncated run as a short one.

WHY IT IS ITS OWN MODULE
------------------------
It was six lines inside `_project`, and `_project` is imported by every TOOL --
which `kit_lint` enforces. It is not imported by the HARNESSES: `verify.py`,
`dual_run.py`, `kit_lint.py`, and the encoding test itself. So the fix protected
everything except the things that run the tests, and on the operator's machine
the encoding test crashed of the exact fault it was written to prove was fixed:

    UnicodeEncodeError: 'charmap' codec can't encode character '\\u2192'
      ... in encoding_test.py, printing the line that says the fix works

A fix that lives in one module protects the importers of that module. A fix that
must hold everywhere needs somewhere everything imports, and a check that
everything does.

TWO HALVES, AND BOTH ARE NEEDED
-------------------------------
1. THIS process writes UTF-8 whatever it is attached to.
2. Every CHILD it spawns is told to do the same -- including children that import
   nothing of ours. `dual_run` runs the origin project's own scripts, and a kit
   that survives where the origin dies manufactures differences and calls them
   extraction bugs.

`setdefault`, so an operator who has deliberately chosen an encoding keeps it.
"""
import os, sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

for _s in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass          # a stream we did not open, or one already closed
