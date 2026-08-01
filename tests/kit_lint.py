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
FAIL = []


def fail(rule, where, msg):
    FAIL.append((rule, where, msg))


# ---------------------------------------------------------------------------
# 1. A sibling tool is invoked by absolute KIT path, never by bare name.
#    Twelve of these shipped.
# ---------------------------------------------------------------------------
BARE_SIBLING = re.compile(r'sys\.executable,\s*["\']([a-z_]+\.py)["\']')
for f in sorted(TOOLS.glob("*.py")):
    for m in BARE_SIBLING.finditer(f.read_text(encoding="utf-8")):
        fail("bare-sibling-invocation", f"{f.name}",
             f"runs {m.group(1)!r} by bare name. cwd is the FILM; the tool is in the KIT. "
             f"Use P.tool({m.group(1)!r}).")

# ---------------------------------------------------------------------------
# 2. No tool reads another tool's SOURCE from a film-relative path.
# ---------------------------------------------------------------------------
FILM_RELATIVE_TOOL = re.compile(r'HERE\s*/\s*["\']([a-z_]+\.py)["\']')
for f in sorted(TOOLS.glob("*.py")):
    for m in FILM_RELATIVE_TOOL.finditer(f.read_text(encoding="utf-8")):
        fail("tool-read-from-film", f"{f.name}",
             f"reads {m.group(1)!r} relative to the film. Use P.tool().")

# ---------------------------------------------------------------------------
# 3. No project filename is hard-coded in CODE. Prose may name one as evidence;
#    an expression may not depend on one.
# ---------------------------------------------------------------------------
PROJECT_NOUN = re.compile(r'["\'][^"\']*(?:tarn_facts|TARN_[A-Za-z0-9_]+\.md)[^"\']*["\']')
for f in sorted(TOOLS.glob("*.py")):
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
            if PROJECT_NOUN.search(f'"{node.value}"'):
                fail("hardcoded-project-noun", f"{f.name}:{node.lineno}",
                     f"string literal names a specific film's file: {node.value[:60]!r}")

# ---------------------------------------------------------------------------
# 4. A tool imports _project IF AND ONLY IF it uses it. The first port added the
#    import to all fourteen, which gave two argument-driven tools a hard
#    dependency on a film existing -- they died with "no film found".
# ---------------------------------------------------------------------------
for f in sorted(TOOLS.glob("*.py")):
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

for f in sorted(TOOLS.glob("*.py")):
    for m in re.finditer(r'P\.(?:files|globs)\(["\']([a-z_]+)["\']\)', f.read_text(encoding="utf-8")):
        if m.group(1) not in P.DEFAULT_FILES:
            fail("unknown-document-role", f.name,
                 f"asks for document role {m.group(1)!r}, which _project does not define.")


def main():
    tools = sorted(p.name for p in TOOLS.glob("*.py"))
    print(f"\n  kit lint — {len(tools)} tools\n")
    if not FAIL:
        print("  \033[92mNo faults of any known class.\033[0m")
        print("  Checked: bare sibling invocation · tool source read from the film ·")
        print("           hard-coded project nouns in code · unused or missing _project")
        print("           import · unknown document roles.\n")
        print("  NOT checked: whether a rule is CORRECT, whether a threshold is right for")
        print("  your film, or whether a tool does what its docstring claims.\n")
        return 0
    print(f"  \033[91m{len(FAIL)} FAULT(S)\033[0m\n")
    for rule, where, msg in FAIL:
        print(f"  [{rule}] {where}\n      {msg}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
