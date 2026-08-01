#!/usr/bin/env python3
"""
THE SPEND GATE — PreToolUse, registered in BOTH hosts from this one file.

Reads the hook payload as JSON on stdin. Denies any Higgsfield generation call unless a
preflight receipt exists for THE EXACT PROMPT about to be fired, the project's fact_rev
is still current, and the kit version matches the project's pin.

Keyed on the hash of the prompt, not on "preflight ran recently" — because a fired prompt
that did not match its own file is a fault this kit has already paid for once.

Wire format is shared between Claude Code and Codex:
    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": "..."}}

NOTE: both hosts require the operator to TRUST a repo-committed hook before it runs.
This gate is therefore only half the enforcement. The other half lives inside the tools,
which refuse to emit a fireable prompt without a receipt. Never rely on this file alone.

Implemented in FK3.
"""
raise SystemExit("not implemented yet — FK3")
