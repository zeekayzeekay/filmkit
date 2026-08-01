#!/usr/bin/env python3
"""
THE PORTABILITY TEST — which lessons belong to the KIT, and which to one FILM.

    A rule is GENERAL if it still fires when every proper noun belonging to the
    film is replaced by a neutral token.

WHY THIS EXISTS
---------------
The origin project's `PORTABILITY.md` said: *"keep the generic findings, delete
the film-specific evidence."* That is a human judgement with no check, made once,
under time pressure, about seventy-odd items -- and a human judgement with no
check is the shape of every recurrence this kit was built from.

Strip the nouns. If the rule still catches the fault, it belongs to the kit. If
it goes quiet, it was about one film. That is a script, not an opinion.

TWO ARTEFACTS, TWO TESTS
------------------------
A lesson exists in two forms and they need different tests:

  RULES are code. Their fixture can be mechanically de-nouned and re-run, and
  the rule's own behaviour answers the question. This is a real experiment.

  FINDINGS are prose. Nothing can mechanically decide whether a paragraph is
  about films-in-general. What CAN be decided is whether it is portable AS
  WRITTEN -- whether the question it asks a reviewer names a specific film. A
  finding that does is not disqualified; it needs rewriting before promotion,
  and this test says which ones.

WHERE THE NOUNS COME FROM
-------------------------
The film, never a hard-coded list -- otherwise the portability test is itself
unportable, which would be a joke this kit cannot afford. Asset tags, geometry
location keys, the film's own name, plus anything it declares under
`vocabulary.proper_nouns`.

Document FILENAMES are deliberately not a source. The first version harvested
upper-case parts of them and produced REVIEW, CHECKLIST, GUARD, BUILD, PLAN,
METHOD, SOURCES, AUTHORITY, OPERATING and HANDOFF -- ordinary English, stripped
out of every fixture and every `ask:`. It changed the finding verdict from
7-name-this-film to 1. A film's proper nouns are its assets, its places and its
name; anything else is a deliberate declaration.

WHAT THIS TEST CANNOT DO
------------------------
De-nouning edits text, and a lint rule may read structure as well as content. If
stripping a noun breaks a block header the fixture needed, a rule can go quiet
for a reason that has nothing to do with portability. Those cases surface as
`TO READ` rather than a verdict, and they are for a person.

It also cannot tell whether a general rule is CORRECT. A wrong rule strips just
as cleanly as a right one.
"""
import pathlib, re, subprocess, sys, tempfile

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "tools"))
import _project as P  # noqa: E402

NEUTRAL_TAG = "@thing"
NEUTRAL_WORD = "PLACE"


# --------------------------------------------------------------- the nouns --
def project_nouns():
    """Every proper noun this film owns, longest first so substrings do not win."""
    facts = P.FACTS
    tags, words = set(), set()

    for tag in facts.get("assets", {}):
        tags.add(tag)                       # @cafe_int
        words.add(tag.lstrip("@"))          # cafe_int, so prose mentions match too

    for k in facts.get("geometry", {}):
        if isinstance(k, str) and not k.startswith("_"):
            words.add(k)                    # cafe, bedroom, tarn

    # The film's own name. `film_facts.json` is the generic template name and
    # names nothing, so it contributes no noun.
    stem = P.PATH.stem.replace("_facts", "")
    if stem not in ("film", "project", ""):
        words.add(stem)

    # NOT harvested: words from document FILENAMES. The first version split every
    # declared filename on separators and took the upper-case parts, which
    # produced REVIEW, CHECKLIST, GUARD, BUILD, PLAN, METHOD, SOURCES, AUTHORITY,
    # OPERATING and HANDOFF -- ordinary English, stripped out of every fixture,
    # silently changing which rules looked film-specific. A film's proper nouns
    # are its ASSETS, its PLACES and its NAME. Anything else it must declare in
    # vocabulary.proper_nouns, deliberately.

    words |= set(facts.get("vocabulary", {}).get("proper_nouns", []))
    words = {w for w in words if len(w) > 2}
    return (sorted(tags, key=len, reverse=True),
            sorted(words, key=len, reverse=True))


def tag_map(tags):
    """
    Each tag gets its OWN neutral name. Collapsing them all to one token was the
    first version, and it broke every rule that COUNTS tags or looks one up: two
    environment elements became one, and a tag with no verified claims became a
    tag with no ledger row at all. The rules were reported film-specific; they
    are entirely general and the test simply could not reach them.
    """
    return {t: f"@thing{i:02d}" for i, t in enumerate(sorted(tags), 1)}


def denoun(text, tmap, words):
    for t, neutral in tmap.items():
        text = text.replace(t, neutral)
    for w in words:
        text = re.sub(rf"\b{re.escape(w)}\b", NEUTRAL_WORD, text, flags=re.I)
    return text


def shadow_facts(tmap, words, dest):
    """
    De-noun the FILM, not just the fixture.

    A lint rule reads the prompt AND the ledger. Stripping nouns from one side
    only is not a portability experiment, it is a broken lookup -- the rule goes
    quiet because its subject vanished, and quiet reads as 'film-specific'.

    Renaming both sides keeps every relationship intact: a tag that had no
    verified claims still has none, an environment tag is still an environment
    tag, and the rule fires or does not fire on its own merits.
    """
    import json
    raw = json.dumps(P.FACTS)
    for t, neutral in tmap.items():
        raw = raw.replace(t, neutral).replace(t.lstrip("@"), neutral.lstrip("@"))
    for w in words:
        raw = re.sub(rf"\b{re.escape(w)}\b", NEUTRAL_WORD, raw, flags=re.I)
    dest.write_text(raw, encoding="utf-8")
    return dest


# --------------------------------------------------------------- the rules --
RULE_LINE = re.compile(r"\[(?:ERROR|WARN|CHECK)\] ([a-z0-9][a-z0-9:_-]*)")


def rules_in(path, project=None):
    cmd = [sys.executable, P.tool("lint_prompt.py"), str(path)]
    if project:
        cmd += ["--project", str(project)]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=P.DIR).stdout
    names = set()
    for m in RULE_LINE.findall(out):
        n = m.rstrip(":")
        names.add("consistency" if n.startswith("consistency") else n)
    return names


def corpus():
    files = [P.files("selftest")] + P.globs("regression_globs")
    d = KIT / "tests" / "fixtures"
    files += sorted(d.glob("*.md")) if d.exists() else []
    return [f for f in files if f.exists()]


def test_rules():
    tags, words = project_nouns()
    tmap = tag_map(tags)
    general, filmonly, check = {}, {}, {}
    with tempfile.TemporaryDirectory(dir=P.DIR) as tmp:
        shadow = shadow_facts(tmap, words, pathlib.Path(tmp) / "shadow_facts.json")
        for f in corpus():
            before = rules_in(f)
            stripped = pathlib.Path(tmp) / f.name
            stripped.write_text(denoun(f.read_text(encoding="utf-8"), tmap, words),
                                encoding="utf-8")
            after = rules_in(stripped, project=shadow)
            for r in before & after:
                general.setdefault(r, f.name)
            for r in before - after:
                filmonly.setdefault(r, f.name)
            for r in after - before:
                check.setdefault(r, f.name)
    # A rule proven general ANYWHERE is general. One fixture's phrasing is not a
    # verdict on the rule -- it is a verdict on that fixture.
    for r in list(filmonly):
        if r in general:
            del filmonly[r]
    for r in list(check):
        if r in general:
            del check[r]
    return general, filmonly, check, (tags, words)


# ------------------------------------------------------------- the findings --
def test_findings(tags, words):
    import checklist
    portable, needs_rewrite = [], []
    for f in checklist.findings():
        ask = f.get("ask") or ""
        hits = sorted({t for t in tags if t in ask} |
                      {w for w in words if re.search(rf"\b{re.escape(w)}\b", ask, re.I)})
        (needs_rewrite if hits else portable).append((f, hits))
    return portable, needs_rewrite


def selftest():
    """
    DISCRIMINATION. A test that passes everything is not a test.

    56 of 56 rules reported general is the right answer -- kit_lint already
    proves no rule's code names a film -- but "everything passes" is exactly what
    a broken comparison also says. So prove the machinery can tell the difference,
    by running the FIRST version's method as a control.

    Mode A de-nouns the fixture only, leaving the ledger intact. That severs
    every tag from its row, so ledger-reading rules must go quiet.
    Mode B de-nouns both. Nothing is severed, so they must not.

    If A and B agree, the comparison is not measuring anything.
    """
    tags, words = project_nouns()
    tmap = tag_map(tags)
    quiet_a, quiet_b = set(), set()
    with tempfile.TemporaryDirectory(dir=P.DIR) as tmp:
        shadow = shadow_facts(tmap, words, pathlib.Path(tmp) / "shadow_facts.json")
        for f in corpus():
            before = rules_in(f)
            s = pathlib.Path(tmp) / f.name
            s.write_text(denoun(f.read_text(encoding="utf-8"), tmap, words), encoding="utf-8")
            quiet_a |= before - rules_in(s)                       # ledger NOT de-nouned
            quiet_b |= before - rules_in(s, project=shadow)       # ledger de-nouned
    print("\n  DISCRIMINATION\n")
    print(f"    mode A — fixture de-nouned, ledger intact : {len(quiet_a)} rule(s) go quiet")
    print(f"    mode B — both de-nouned                   : {len(quiet_b)} rule(s) go quiet")
    if quiet_a:
        print(f"      A-only: {', '.join(sorted(quiet_a - quiet_b))}")
    if not quiet_a:
        print("\n  \033[91mFAILED\033[0m — mode A silenced nothing. Severing every tag from its")
        print("  ledger row must silence the rules that read the ledger. If it does not,")
        print("  this test is not comparing anything and its verdict means nothing.\n")
        return 1
    if quiet_a == quiet_b:
        print("\n  \033[91mFAILED\033[0m — both modes agree, so de-nouning the ledger changed")
        print("  nothing and the shadow-facts step is not doing its job.\n")
        return 1
    print("\n  \033[92mDiscriminates.\033[0m Rules silenced only by the broken method are")
    print("  ledger-readers, and they are general -- which is why the film is de-nouned")
    print("  alongside the fixture rather than instead of it.\n")
    return 0


def main():
    P.check_pin()
    if "--selftest" in sys.argv:
        return selftest()
    general, filmonly, check, (tags, words) = test_rules()
    portable, rewrite = test_findings(tags, words)

    print(f"\n  PORTABILITY TEST — {P.PATH.name}")
    print(f"  {len(tags)} asset tags and {len(words)} proper nouns derived from the film\n")
    print(f"  RULES   {len(general):3d} general · {len(filmonly):3d} film-specific · "
          f"{len(check):3d} to read")
    print(f"  ASKS    {len(portable):3d} portable as written · {len(rewrite):3d} name this film\n")

    if "--rules" in sys.argv:
        print("  GENERAL — survive de-nouning, belong to the kit:")
        for r in sorted(general):
            print(f"    {r:34s} {general[r]}")
        if filmonly:
            print("\n  FILM-SPECIFIC — go quiet when the nouns go:")
            for r in sorted(filmonly):
                print(f"    {r:34s} {filmonly[r]}")
        if check:
            print("\n  TO READ — fired only AFTER stripping, so the edit changed structure,")
            print("  not portability. A person decides these:")
            for r in sorted(check):
                print(f"    {r:34s} {check[r]}")
        print()

    if "--asks" in sys.argv:
        print("  ASKS THAT NAME THIS FILM — rewrite before promoting:")
        for f, hits in rewrite:
            print(f"    {f['id']:8s} {', '.join(hits)}")
            print(f"             {(f['ask'] or '')[:96]}")
        print()

    if "--nouns" in sys.argv:
        print(f"  TAGS  {' '.join(tags)}\n")
        print(f"  WORDS {' '.join(words)}\n")

    print("  NOT decided here: whether a general rule is CORRECT, or whether a")
    print("  film-specific rule SHOULD have been general. This test answers one")
    print("  question -- does it still fire without the nouns -- and nothing else.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
