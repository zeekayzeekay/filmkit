# Hook registration — generated, not hand-written

These are **templates**. `filmkit-doctor --install` writes the real registration with an
absolute path to `gate.py`, into the host's own config location:

| host | written to |
|---|---|
| Claude Code | `<project>/.claude/settings.json` |
| Codex | `<project>/.codex/hooks.json` |

## Why generated

The first version of this scaffold shipped two hand-written registrations, each interpolating
a plugin-root environment variable — `${CLAUDE_PLUGIN_ROOT}` for Claude, `$CODEX_PLUGIN_ROOT`
for Codex.

**The Codex variable was a guess.** The research that established Codex's hook format confirmed
the event names, the JSON wire format, the matcher syntax and the exit codes — and did **not**
confirm any plugin-root variable name. I wrote one that looked plausible.

That is the worst possible place to guess. Per Codex's documented exit-code semantics, a hook
command that fails for any reason other than exit 2 is a **hook failure, and processing
continues**. So an env var that does not expand does not block the generation and does not
raise an alarm — it produces a spend gate that is silently not a gate.

Writing an absolute path at install time removes the variable, and therefore the guess.

## The second reason: one file was at the other host's path

`hooks/hooks.json` is the conventional auto-discovery location for a plugin's hooks in **both**
hosts. Shipping the Codex registration there meant Claude Code would likely load it too —
complete with the unexpandable Codex variable. Two registrations, one of them planted at the
other host's front door.

## What ships here

- `gate.template.json` — the shared shape, with `__GATE_PATH__` as an unmistakable placeholder
- neither file is a valid registration until `filmkit-doctor --install` fills it in

`filmkit-doctor` (with no arguments) reports whether a registration exists, whether it points
at a `gate.py` that is actually there, and — separately — whether the host has been told to
**trust** it. A registered hook and a trusted hook are different states, and only the second
one blocks anything.
