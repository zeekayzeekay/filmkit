# WHERE THE GATE ACTUALLY RUNS — measured, not assumed

Every row here was produced by running a probe on the operator's own machine and reading
what came back. Nothing in this file is inference. Where a cell is unmeasured it says so,
because an unmeasured cell and a passing one are the same colour in a table nobody labels.

**Kit `7418a55` · Windows 11 · Python 3.12.1 (pyenv-win) · cp1252 locale · film
`C:\ai-video\tarn` · 6 August 2026**

| surface | hook loads | hook consulted | finds the film | shell road | MCP road |
|---|---|---|---|---|---|
| **Claude desktop app, Code, folder open** | **yes** | **yes** | **yes** | **gated** | **gated** |
| Claude Code CLI, same folder | yes (used to authenticate MCP) | not probed | not probed | not probed | not probed |
| Cowork on the operator's computer | not probed | not probed | not probed | not probed | not probed |
| Cowork in the cloud | **no** | **no** | n/a | n/a | **ungated** |

## What each cell rests on

**Desktop app, hook loads.** The `SessionStart` briefing appeared and quoted
`session_start.py`'s own wording — `matching the film's pin`, `cannot receive a new claim`,
`Credits belong to the operator` — none of which appears in any `.md` or `.json` in the film.
Grepped to confirm.

**Desktop app, consulted + finds the film.** With the canary armed, a balance request was
REFUSED, on both roads, reporting `cwd 'C:\ai-video\tarn'` and `film found at
C:\ai-video\tarn`. **Only a refusal is evidence**: four earlier probes returned an allow and
every one was ambiguous, because a permitted call and an absent gate are indistinguishable.

**Desktop app, no `/hooks`.** The command does not exist in that surface. The registration
was read off disk instead.

**Cloud Cowork, ungated.** The generation tools are attached directly and the film's
`.claude/settings.json` is never read. Measured by their presence in the tool list, not
inferred.

## What had to be true first, and was not

| | |
|---|---|
| the CLI is a road to the same service | FK-20 |
| a host may expose two shells, and use the one you did not list | FK-21 |
| the road the operator actually uses had no receipt logic at all | FK-23 |
| **the MCP server is exposed under a UUID, not its name** | FK-24 |

Four name-based selections, four misses. The last would have allowed every generation on
this machine while every line of `filmkit-doctor` read green.

## What is still not covered anywhere

- **The direct API.** A script using the SDK, or `curl`, carries no tool name this gate
  recognises and no command line it can read. Nothing here sees it.
- **A session outside the film's folder.** The registration lives in the film, so a host
  opened elsewhere never loads it. An assistant identified this as the way around the gate,
  unprompted, while declining to take it. FK-19.
- **`permissions.ask`.** It lists `mcp__higgsfield__*`, which does not match the UUID either.
  Untested against this host, so it is a belt of unknown thickness. The hook is what covers
  these roads.

## How to re-measure

`filmkit-doctor --canary on`, then ask the surface for a Higgsfield balance. A refusal
quoting `filmkit CANARY` means the host consulted the gate. An answer means it did not.
`filmkit-doctor --canary off` when done. Costs nothing either way, which is the whole point
of doing it this way rather than attempting a generation.
