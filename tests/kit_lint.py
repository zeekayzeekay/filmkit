#!/usr/bin/env python3
"""
THE KIT LINTS ITSELF.

WHY THIS EXISTS (FK-02)
-----------------------
The origin project's tools lived beside the film, so one word -- `HERE` -- meant
both "where the film is" and "where the tools are". Porting them into a kit
splits that word in two, and the split is a decision per USE SITE, not per file.

The first port rebound `HERE` once per file and declared itself done. Twelve
subprocess calls then invoked a sibling tool by BARE NAME with `cwd` set to the
film directory, where the tool no longer was. `guard_coverage.py` additionally
read `lint_prompt.py` out of the film folder to count its rules -- so it would
have reported zero rules defined, on every project, forever.

None of it was caught by the diff review, because every hunk in that diff was an
INTENDED change. The review asked "did the port change anything it should not?"
and never asked "is each intended change correct everywhere it lands?"

    A diff shows you what moved. It cannot show you what should have moved
    with it.

These checks are cheap, they are mechanical, and each one is a defect that
actually shipped in the first port.
"""
import ast, pathlib, re, sys

KIT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = KIT / "tools"


def scripts():
    """Everything executable in the kit. hooks/gate.py was outside the first
    five checks entirely -- the one file whose correctness costs money."""
    # tests/ was outside every check until FK5's review. The files that verify
    # the kit are as capable of a bare sibling invocation or a hard-coded project
    # noun as the files they verify -- and a broken verifier reports success.
    return (sorted(TOOLS.glob("*.py"))
            + sorted((KIT / "hooks").glob("*.py"))
            + sorted((KIT / "tests").glob("*.py")))
FAIL = []


def fail(rule, where, msg):
    FAIL.append((rule, where, msg))


# ---------------------------------------------------------------------------
# 1. A sibling tool is invoked by absolute KIT path, never by bare name.
#    Twelve of these shipped.
# ---------------------------------------------------------------------------
BARE_SIBLING = re.compile(r'sys\.executable,\s*["\']([a-z_]+\.py)["\']')
for f in scripts():
    for m in BARE_SIBLING.finditer(f.read_text(encoding="utf-8")):
        fail("bare-sibling-invocation", f"{f.name}",
             f"runs {m.group(1)!r} by bare name. cwd is the FILM; the tool is in the KIT. "
             f"Use P.tool({m.group(1)!r}).")

# ---------------------------------------------------------------------------
# 2. No tool reads another tool's SOURCE from a film-relative path.
# ---------------------------------------------------------------------------
FILM_RELATIVE_TOOL = re.compile(r'HERE\s*/\s*["\']([a-z_]+\.py)["\']')
for f in scripts():
    for m in FILM_RELATIVE_TOOL.finditer(f.read_text(encoding="utf-8")):
        fail("tool-read-from-film", f"{f.name}",
             f"reads {m.group(1)!r} relative to the film. Use P.tool().")

# ---------------------------------------------------------------------------
# 3. No project filename is hard-coded in CODE. Prose may name one as evidence;
#    an expression may not depend on one.
# ---------------------------------------------------------------------------
# A project noun is defined STRUCTURALLY, not by listing one film's words. The
# first version's pattern spelled out `tarn_facts` and `TARN_*.md`, which is the
# same allow-list-of-dangers shape as the gate's first matcher — and it meant the
# check proving the kit knows about no particular film was written knowing about
# exactly one. It also flagged itself, which is how it was found.
#
# Generic instead: a facts file that is not the template's, or an upper-case
# document name that is not one of the roles the kit itself defines.
GENERIC_DOCS = {
    "README.md", "SKILL.md", "AGENTS.md", "CLAUDE.md", "ARCHITECTURE.md", "STATUS.md",
    "FINDINGS.md", "KIT_FINDINGS.md", "REVIEW_CHECKLIST.md", "RUN_RECORD.md",
    "SHOT_SCRIPT.md", "PROMPTS.md", "GUARD_SELFTEST.md", "WORKFLOW.md", "OPERATING.md",
    "HANDOFF.md", "PORTABILITY.md", "METHOD_SOURCES.md", "MEMORY.md",
}
# Facts filenames the KIT itself generates. film_facts.json is the template's;
# shadow_facts.json is the de-nouned copy portability_test writes into a temp dir.
# Neither names a film.
GENERIC_FACTS = {"film_facts.json", "shadow_facts.json"}
FACTS_LITERAL = re.compile(r"\b([A-Za-z0-9]+_facts\.json)\b")
DOC_LITERAL = re.compile(r"\b([A-Z][A-Z0-9_]{3,}\.md)\b")


def project_nouns_in(s):
    hits = [m for m in FACTS_LITERAL.findall(s) if m not in GENERIC_FACTS]
    hits += [m for m in DOC_LITERAL.findall(s) if m not in GENERIC_DOCS]
    return hits
for f in scripts():
    src = f.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        fail("syntax", f.name, str(e))
        continue
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            d = ast.get_docstring(node, clean=False)
            if d:
                docstrings.add(d)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in docstrings:
                continue
            hits = project_nouns_in(node.value)
            if hits:
                fail("hardcoded-project-noun", f"{f.name}:{node.lineno}",
                     f"string literal names a specific film's file ({', '.join(sorted(set(hits)))}): "
                     f"{node.value[:60]!r}")

# ---------------------------------------------------------------------------
# 4. A tool imports _project IF AND ONLY IF it uses it. The first port added the
#    import to all fourteen, which gave two argument-driven tools a hard
#    dependency on a film existing -- they died with "no film found".
# ---------------------------------------------------------------------------
for f in scripts():
    if f.name == "_project.py":
        continue
    src = f.read_text(encoding="utf-8")
    imports = "import _project as P" in src
    uses = re.search(r"\bP\.[A-Za-z_]", src) is not None
    if imports and not uses:
        fail("unused-project-import", f.name,
             "imports _project but never uses it. That is not a dead import — resolving the "
             "film has side effects, and this tool now needs a film it does not read.")
    if uses and not imports:
        fail("missing-project-import", f.name, "uses P.* without importing _project.")

# ---------------------------------------------------------------------------
# 5. Every tool parses, and every document role used exists in DEFAULT_FILES.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(TOOLS))
import _project as P  # noqa: E402

for f in scripts():
    for m in re.finditer(r'P\.(?:files|globs)\(["\']([a-z_]+)["\']\)', f.read_text(encoding="utf-8")):
        if m.group(1) not in P.DEFAULT_FILES:
            fail("unknown-document-role", f.name,
                 f"asks for document role {m.group(1)!r}, which _project does not define.")


# ---------------------------------------------------------------------------
# 6. Every path a plugin manifest references must EXIST AND BE TRACKED BY GIT.
#    The first scaffold created ten directories, left them empty, and committed.
#    Git does not track empty directories, so a clone arrived with no skills/ at
#    all while both manifests pointed at "./skills/". I verified the files I had
#    written and never verified the thing that has to ARRIVE.
# ---------------------------------------------------------------------------
import json as _json, subprocess as _sp

_tracked = set(_sp.run(["git", "ls-files"], capture_output=True, text=True,
                       cwd=KIT).stdout.split())

for man in (KIT / ".claude-plugin" / "plugin.json", KIT / ".codex-plugin" / "plugin.json"):
    if not man.exists():
        fail("missing-manifest", man.name, "plugin manifest absent")
        continue
    d = _json.loads(man.read_text(encoding="utf-8"))
    for key, val in d.items():
        if not isinstance(val, str) or not val.startswith("./"):
            continue
        rel = val.lstrip("./").rstrip("/")
        if not (KIT / rel).exists():
            fail("manifest-path-missing", f"{man.parent.name}/{man.name}",
                 f"{key!r} points at {val!r}, which does not exist.")
        elif not any(x == rel or x.startswith(rel + "/") for x in _tracked):
            fail("manifest-path-untracked", f"{man.parent.name}/{man.name}",
                 f"{key!r} points at {val!r}, which exists here but is NOT IN GIT. "
                 f"A clone will not have it.")

# ---------------------------------------------------------------------------
# 7. No directory is empty of tracked files. An empty directory is a directory
#    that does not survive a clone.
# ---------------------------------------------------------------------------
for d in sorted(x for x in KIT.rglob("*") if x.is_dir()):
    rel = d.relative_to(KIT).as_posix()
    if rel.startswith(".git") or "__pycache__" in rel:
        continue
    if not any(x.startswith(rel + "/") for x in _tracked):
        fail("untracked-directory", rel,
             "no tracked file inside; git does not track empty directories, so this "
             "will not survive a clone. Put a README in it or delete it.")

# ---------------------------------------------------------------------------
# 8. A shipped hook registration must not interpolate an environment variable.
#    The first scaffold guessed $CODEX_PLUGIN_ROOT. A hook command that fails to
#    expand does not block the call -- per both hosts' exit-code semantics it is
#    a hook FAILURE and processing continues -- so the guess produced a spend
#    gate that silently was not one. Registrations are GENERATED with absolute
#    paths by filmkit-doctor.
# ---------------------------------------------------------------------------
for h in sorted((KIT / "hooks").rglob("*.json")):
    src = h.read_text(encoding="utf-8")
    if "$" in src and "__GATE_PATH__" not in src:
        fail("env-var-in-hook", h.relative_to(KIT).as_posix(),
             "interpolates an environment variable. Registrations are generated with "
             "absolute paths; a variable that does not expand fails OPEN.")


# ---------------------------------------------------------------------------
# 9. THE KIT'S OWN DOCUMENTS DO NOT NAME FILES THAT ARE NOT THERE.
#    staleness.py does exactly this for a FILM and nothing did it for the kit.
#    ARCHITECTURE.md was written before the FK0 audit and went on describing
#    settings/claude.settings.json for two commits after that file was deleted —
#    a design record that documents a layout the repo does not have is worse than
#    no design record, because it is read as authority.
#
#    A path that does not exist YET is legitimate: mark it (PLANNED) on the same
#    line, and say which task builds it.
# ---------------------------------------------------------------------------
_DOCS = ["ARCHITECTURE.md", "README.md", "AGENTS.md", "CLAUDE.md", "docs/STATUS.md"]
_PATH_IN_PROSE = re.compile(r"`([a-z_][\w./-]*\.(?:py|json|md|txt))`")
_PATH_IN_TREE = re.compile(r"^\s*[│├└─\s]*([a-z_][\w-]*/[\w./-]+)\s", re.M)

for name in _DOCS:
    doc = KIT / name
    if not doc.exists():
        continue
    text = doc.read_text(encoding="utf-8")
    for line in text.splitlines():
        # ONE convention, explicit. The first version also exempted any line
        # containing the word "historical", which is a fuzzy match on prose and
        # would exempt a genuinely stale path in a sentence that happened to use
        # the word. A path that is not there now must SAY which it is.
        if any(k in line for k in ("(PLANNED", "(REMOVED", "(HISTORICAL")):
            continue
        for rx in (_PATH_IN_PROSE, _PATH_IN_TREE):
            for m in rx.finditer(line + " "):
                rel = m.group(1).rstrip("/")
                if "<" in rel or "/" not in rel:
                    continue
                if not (KIT / rel).exists():
                    fail("kit-doc-names-missing-file", f"{name}",
                         f"names {rel!r}, which does not exist. If it is not built yet, mark "
                         f"the line (PLANNED — FKn).")


# ---------------------------------------------------------------------------
# 10. LAYER 1 EXPIRES. knowledge/engine.json carries a _verified_on date and an
#     _expires_after_days, and a date nothing reads is a decoration. The origin
#     project's script carried a false duration claim for days because nothing
#     made it expire, so nothing made anybody look.
# ---------------------------------------------------------------------------
_eng = KIT / "knowledge" / "engine.json"
if _eng.exists():
    import datetime as _dt
    e = _json.loads(_eng.read_text(encoding="utf-8"))
    on, days = e.get("_verified_on"), e.get("_expires_after_days")
    if not on:
        fail("engine-facts-unverified", "knowledge/engine.json",
             "_verified_on is null. These are somebody else's API facts; undated, they are "
             "folklore.")
    else:
        try:
            age = (_dt.date.today() - _dt.date.fromisoformat(on)).days
            if days and age > days:
                fail("engine-facts-stale", "knowledge/engine.json",
                     f"verified {age} days ago, limit {days}. Re-run models_explore and "
                     f"update it — a model's parameters are not a thing to remember.")
        except ValueError:
            fail("engine-facts-unverified", "knowledge/engine.json",
                 f"_verified_on {on!r} is not an ISO date.")


# ---------------------------------------------------------------------------
# 11. SKILLS CONFORM TO THE OPEN SPEC. agentskills.io standardises the FOLDER
#     FORMAT, and both hosts read it -- only the install path differs
#     (.claude/skills vs .agents/skills). `name` must match the parent
#     directory, or the skill loads under a name nothing refers to.
# ---------------------------------------------------------------------------
_SKILLS = KIT / "skills"
if _SKILLS.exists():
    for _d in sorted(x for x in _SKILLS.iterdir() if x.is_dir()):
        _s = _d / "SKILL.md"
        if not _s.exists():
            fail("skill-without-skill-md", f"skills/{_d.name}",
                 "a skill directory with no SKILL.md is a directory both hosts ignore.")
            continue
        _t = _s.read_text(encoding="utf-8")
        _m = re.match(r"^---\n(.*?)\n---\n", _t, re.S)
        if not _m:
            fail("skill-without-frontmatter", f"skills/{_d.name}",
                 "no YAML frontmatter; name and description are how a host decides to load it.")
            continue
        # STRIP the values. `description: ` with a trailing space parsed as a
        # one-character description and sailed through `1 <= len(desc)` — a
        # whitespace-only description is exactly as useless to a host as an
        # absent one, and this check existed to catch absent ones.
        _fm = {k: v.strip() for k, v in
               re.findall(r"^(\w[\w-]*):\s*(.+)$", _m.group(1), re.M)}
        _name, _desc = _fm.get("name", ""), _fm.get("description", "")
        if _name != _d.name:
            fail("skill-name-mismatch", f"skills/{_d.name}",
                 f"frontmatter name is {_name!r}; the spec requires it to match the directory.")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", _name or ""):
            fail("skill-name-shape", f"skills/{_d.name}",
                 f"{_name!r} is not lowercase-alnum-with-single-hyphens.")
        if not (1 <= len(_desc) <= 1024):
            fail("skill-description", f"skills/{_d.name}",
                 f"description is {len(_desc)} chars; the spec allows 1 to 1024. It is the only "
                 f"thing a host reads before deciding to load the skill.")


def main():
    tools = sorted(p.name for p in TOOLS.glob("*.py"))
    print(f"\n  kit lint — {len(tools)} tools\n")
    if not FAIL:
        print("  \033[92mNo faults of any known class.\033[0m")
        print("  Checked: bare sibling invocation · tool source read from the film ·")
        print("           hard-coded project nouns in code · unused or missing _project")
        print("           import · unknown document roles · manifest paths present AND")
        print("           tracked · no empty directories · no env var in a hook")
        print("           registration · kit docs name no missing file · engine facts")
        print("           still inside their expiry · skills conform to the open spec.\n")
        print("  NOT checked: whether a rule is CORRECT, whether a threshold is right for")
        print("  your film, or whether a tool does what its docstring claims.\n")
        return 0
    print(f"  \033[91m{len(FAIL)} FAULT(S)\033[0m\n")
    for rule, where, msg in FAIL:
        print(f"  [{rule}] {where}\n      {msg}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
