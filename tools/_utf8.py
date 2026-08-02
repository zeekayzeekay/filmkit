#!/usr/bin/env python3
"""
THIS PROCESS WRITES UTF-8, WHATEVER IT IS ATTACHED TO.

Import first, for the side effect. Every executable in this kit does.

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

WHAT IT DELIBERATELY DOES NOT DO — AND THIS IS THE IMPORTANT PART
-----------------------------------------------------------------
It does NOT set `PYTHONIOENCODING` in the environment. An earlier version did,
so that children would inherit the instruction even if they imported nothing of
ours. That was wrong, and the acceptance gate caught it on the operator's
machine within a day:

    - origin  23 headings Â· 2 DRAFT Â· 4 INFO Â· 3 LIVE Â· 14 SUPERSEDED
    + kit     23 headings · 2 DRAFT · 4 INFO · 3 LIVE · 14 SUPERSEDED

The origin project's `preflight` runs its own `staleness` and prints the output.
`staleness` inherited PYTHONIOENCODING and wrote UTF-8. `preflight` did not
inherit anything that changes how it DECODES, so it read those bytes with the
host locale and produced mojibake. **Forcing a child to write in an encoding its
parent does not read is not a fix, it is a mismatch** -- and the parent here is
frozen pre-extraction code that must not be edited, because reproducing it is
the whole point of the gate.

So the rule is: HARDEN A PROCESS BY IMPORT, NEVER BY ENVIRONMENT. A process that
imports this module writes UTF-8 and, being ours, also decodes UTF-8 at every
capturing call -- `kit_lint` enforces that half. A process that does not import
it is left entirely alone, and stays internally consistent with whatever its
platform decided.

The cost, stated: a foreign script that dies on a character its locale cannot
encode still dies. That is its real behaviour, the kit's differs, and the
acceptance gate should REPORT that difference rather than hide it under an
environment variable set behind both their backs.
"""
import sys

for _s in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass          # a stream we did not open, or one already closed
