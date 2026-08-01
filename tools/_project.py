#!/usr/bin/env python3
"""
WHERE THE FILM IS — the one place any tool asks.

WHY THIS EXISTS
---------------
In the origin project the tools lived in the same folder as the film, so every
one of them resolved its inputs against `pathlib.Path(__file__).parent` and got
away with it. Seven of the fourteen additionally hard-coded `tarn_facts.json`,
and four hard-coded document names.

`PORTABILITY.md` claimed "nothing in the tooling knows what TARN is". That was
true of the RULES and false of the PLUMBING, and the difference is invisible
until you point the kit at a second film — at which point `checklist.py`
silently regenerates nothing, because the ledger it wants is not there.

THE RULE
    A tool resolves the FILM from the environment, and every document from the
    film's own `_files` block. It never resolves anything against its own
    location, because it no longer lives where the film lives.

Resolution order for the film, first hit wins:

    1. --project PATH on the command line
    2. $FILMKIT_PROJECT
    3. $PROMPTGUARD_PROJECT          (accepted, and warned about — origin name)
    4. ./film_facts.json
    5. exactly one *_facts.json in the working directory
       -- more than one is an error, not a guess

PROJECT_DIR is then the directory CONTAINING that file, and every document name
resolves against it.
"""
import json, os, pathlib, sys

_WARNED = set()


def _warn(key, msg):
    if key not in _WARNED:
        _WARNED.add(key)
        print(f"  \033[93m! {msg}\033[0m", file=sys.stderr)


def project_path():
    for i, a in enumerate(sys.argv):
        if a == "--project" and i + 1 < len(sys.argv):
            return pathlib.Path(sys.argv[i + 1]).resolve()
    for var in ("FILMKIT_PROJECT", "PROMPTGUARD_PROJECT"):
        v = os.environ.get(var)
        if v:
            if var == "PROMPTGUARD_PROJECT":
                _warn("legacy-var", "$PROMPTGUARD_PROJECT is the origin project's name for "
                                    "$FILMKIT_PROJECT. Honoured, but rename it.")
            return pathlib.Path(v).resolve()
    cwd = pathlib.Path.cwd()
    default = cwd / "film_facts.json"
    if default.exists():
        return default
    found = sorted(cwd.glob("*_facts.json"))
    if len(found) == 1:
        return found[0].resolve()
    if len(found) > 1:
        raise SystemExit(
            f"\n  ! {len(found)} candidate project files in {cwd}: "
            f"{', '.join(p.name for p in found)}\n"
            "    Name one film_facts.json, or say which with --project. This tool will not\n"
            "    guess which film you are working on.\n")
    raise SystemExit(
        f"\n  ! no film found in {cwd}\n"
        "    Expected film_facts.json, or --project PATH, or $FILMKIT_PROJECT.\n"
        "    Start one with: filmkit-init .\n")


PATH = project_path()
DIR = PATH.parent
FACTS = json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else {}

# ------------------------------------------------------------ the documents --
# Defaults are what `filmkit-init` lays down. A film that renames one says so
# ONCE, in its own `_files` block, and every tool follows -- rather than four
# tools each carrying their own spelling of the same filename.
DEFAULT_FILES = {
    "prompts": "PROMPTS.md",
    "findings": "FINDINGS.md",
    "checklist": "REVIEW_CHECKLIST.md",
    "run_record": "RUN_RECORD.md",
    "script": "SHOT_SCRIPT.md",
    "selftest": "GUARD_SELFTEST.md",
    "workflow": "WORKFLOW.md",
    "live_docs": ["OPERATING.md", "WORKFLOW.md", "HANDOFF.md"],
    "regression_globs": ["*lint_regression*.md"],
    "archive_dir": "_archive",
}


def files(key):
    """A document this film uses, resolved against the FILM's directory."""
    if key not in DEFAULT_FILES:
        raise KeyError(f"_project.files({key!r}) — not a known document role. "
                       f"Known: {sorted(DEFAULT_FILES)}")
    v = FACTS.get("_files", {}).get(key, DEFAULT_FILES[key])
    if isinstance(v, list):
        return [DIR / x for x in v]
    return DIR / v


def globs(key):
    """Expand the glob list under a document role, against the FILM's directory."""
    pats = FACTS.get("_files", {}).get(key, DEFAULT_FILES[key])
    out = []
    for p in pats:
        out.extend(sorted(DIR.glob(p)))
    return out


def cfg(key, default):
    """Project override for anything the engine would otherwise hard-code."""
    return FACTS.get("vocabulary", {}).get(key, default)


def save(d):
    PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")


def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the version ---
def kit_version():
    manifest = pathlib.Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))["version"]
    except Exception:
        return "unknown"


def check_pin():
    """
    A film PINS the kit version it was shot under. That pin is the whole
    reproducibility claim: a film shot in August still runs its August guards in
    December. A mismatch is not fatal -- it is a decision somebody has to make --
    but it is never silent.
    """
    pinned = FACTS.get("kit_version")
    running = kit_version()
    if pinned is None:
        _warn("no-pin", f"{PATH.name} pins no kit_version. Running {running}. "
                        f"Pin it, or a future kit will change this film's guards without saying so.")
        return
    if pinned != running:
        pmaj, rmaj = str(pinned).split(".")[0], str(running).split(".")[0]
        if pmaj != rmaj:
            raise SystemExit(
                f"\n  ! KIT MAJOR VERSION MISMATCH — refused.\n"
                f"    {PATH.name} pins {pinned}; this kit is {running}.\n"
                "    A major bump means a rule changed meaning. Upgrade the film deliberately\n"
                "    (re-run the full suite and re-answer the manual items), or run the kit\n"
                "    version this film was shot under.\n")
        _warn("pin-drift", f"{PATH.name} pins kit {pinned}; running {running}. "
                           f"Same major, so the rules still mean what they meant.")


# ------------------------------------------------------------------ the look --
def look_pack():
    """
    Layer 4 is OPT-IN. Inheriting another film's colour targets is how one film's
    water ends up governing a different lake -- the exact drift this kit exists to
    prevent. So a film either names a pack or explicitly declares none, and
    silence is neither.
    """
    if "look_pack" not in FACTS:
        _warn("no-look", f"{PATH.name} does not declare look_pack. Set it to a pack name or "
                         f"to null. Silence is not the same as 'none'.")
        return None
    return FACTS["look_pack"]


# --------------------------------------------------------------- provenance --
def source_manifest():
    """
    FK1. A transfer tool reporting success is not evidence the bytes are current.
    Staging the origin project's scripts into this container returned ok:true with
    fresh mtimes for all fifteen files, and delivered SIX of them from a snapshot
    two days stale -- including the facts file, which read fact_rev 16 against a
    live 103. Had the extraction proceeded, the kit would have been 'verified'
    against a film that stopped existing on 31 July.

    Anything crossing a machine boundary is checked by CONTENT. The manifest that
    proves it travels with the payload.
    """
    m = pathlib.Path(__file__).resolve().parent.parent / "tests" / "SOURCE_SHA256.txt"
    return m if m.exists() else None
