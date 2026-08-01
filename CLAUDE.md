@AGENTS.md

## Claude Code

Skills are exposed at `.claude/skills/` by symlink; the canonical copy is `skills/`.

Hook registration is **generated**, not shipped — `filmkit-doctor --install` writes it to the
FILM's `.claude/settings.json` with an absolute path to the gate. Nothing in this repo is a
live registration. See `hooks/registration/README.md` for why.
