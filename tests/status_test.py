#!/usr/bin/env python3
"""
THE BLOCK-STATUS VOCABULARY, ON FIXTURES.

    python3 tests/status_test.py

`staleness.py` resolves its film at import, so it cannot test itself against a
fabricated one from inside its own process. This builds a throwaway film and runs
the real tool against it with `--project`, which is the only way to check a rule
on text that does not exist in anybody's actual film.

WHY THIS FILE EXISTS AT ALL
---------------------------
`DONE` was added because `SUPERSEDED` was being made to carry two different
facts. The origin project's rebuild ledgers say, at the top:

    SUPERSEDED 1 Aug — DONE, do not run. These prompts produced
    @tarn_view_alt_1 and @tarn_reverse_view, which are registered and verified.

Nothing replaced those prompts. They ran and finished. Demanding they name a
successor asks the document to state something untrue, and a rule that can only
be satisfied by writing something untrue produces files that say whatever
satisfied the checker.

So `DONE` names what it PRODUCED, and every tag it names must be in the ledger.
That is the difference between a status and an escape hatch, and cases 3 and 4
are the ones that keep it.

EVERY CASE IS PAIRED
--------------------
For each rule there is text that must trip it and text that must not. A test that
only asserts the failing direction cannot tell a working rule from one that
fires on everything.
"""
import json, pathlib, subprocess, sys, tempfile

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "tools"))
import _utf8  # noqa: F401,E402

FACTS = {"_fact_rev": 1, "kit_version": None, "look_pack": None,
         "assets": {"@real_one": {}, "@real_two": {}, "@retired_one": {}},
         "element_rules": {"retired_tags": {"_why": "fixture", "@retired_one": "x"}},
         "_files": {"prompts": "PROMPTS.md", "findings": "FINDINGS.md",
                    "script": "SHOT_SCRIPT.md", "selftest": "GUARD_SELFTEST.md",
                    "checklist": "REVIEW_CHECKLIST.md", "run_record": "RUN_RECORD.md",
                    "workflow": "WORKFLOW.md", "live_docs": [], "regression_globs": []}}

CASES = [
    # (name, prompts-file body, substring that must appear / must NOT appear)
    ("DONE naming registered assets is accepted",
     "# Ran and finished\n<!-- status: DONE produced: @real_one, @real_two -->\nbody\n",
     None),
    ("DONE naming nothing is refused",
     "# Ran and finished\n<!-- status: DONE -->\nbody\n",
     "names nothing it produced"),
    ("DONE naming an unregistered tag is refused",
     "# Ran and finished\n<!-- status: DONE produced: @ghost -->\nbody\n",
     "which the ledger does not have"),
    ("DONE calling itself live is refused",
     "# The live prompt\n<!-- status: DONE produced: @real_one -->\nbody\n",
     "calls itself live or current"),
    ("DONE calling itself final is ACCEPTED — it was",
     "# The final version, as fired\n<!-- status: DONE produced: @real_one -->\nbody\n",
     None),
    ("SUPERSEDED still has to name its replacement",
     "# Old one\n<!-- status: SUPERSEDED -->\nbody\n",
     "does not name its replacement"),
    ("SUPERSEDED naming one is accepted",
     "# Old one\n<!-- status: SUPERSEDED by: `v3` -->\nbody\n",
     None),
    ("a file-level DONE covers every heading, and is asked ONCE",
     "<!-- status: DONE produced: @real_one -->\n\n# One\nbody\n\n# Two\nbody\n\n# Three\nb\n",
     None),
    ("a file-level DONE with no produced: is one violation, not three",
     "<!-- status: DONE -->\n\n# One\nbody\n\n# Two\nbody\n\n# Three\nb\n",
     "names nothing it produced"),
    ("ABANDONED naming a target and a reason is accepted",
     "# Ran, nothing kept\n<!-- status: ABANDONED targeted: @gone why: the tag was retired -->\nb\n",
     None),
    ("ABANDONED naming a RETIRED registered tag is accepted",
     "# Ran, nothing kept\n<!-- status: ABANDONED targeted: @retired_one why: retired -->\nb\n",
     None),
    ("ABANDONED naming a LIVE registered asset is refused — it succeeded",
     "# Ran, nothing kept\n<!-- status: ABANDONED targeted: @real_one why: retired -->\nb\n",
     "IS a registered asset"),
    ("ABANDONED with no target is refused",
     "# Ran, nothing kept\n<!-- status: ABANDONED why: it did not work -->\nb\n",
     "names nothing it was aiming at"),
    ("ABANDONED with no reason is refused",
     "# Ran, nothing kept\n<!-- status: ABANDONED targeted: @gone -->\nb\n",
     "with no  why:"),
    ("a tag mentioned only in why: is not counted as a target",
     "# Ran, nothing kept\n<!-- status: ABANDONED targeted: @gone why: replaced by @real_one -->\nb\n",
     None),
    ("a heading with no marker anywhere is still refused",
     "# Bare\nbody\n",
     "heading has no status marker"),
]


# FK-26. A LIVE block may not name a conditioning frame that is not the current
# selection. The last two cases are the origin's own first line, reproduced
# character for character including the markdown emphasis — the regex IS the
# guard, and a regex tested only against text written to suit it is tested
# against nothing.
SEL = {"start": {"file": "G3/k5-30.png", "selected_on": "2026-07-31", "at_rev": 16},
       "end": {"file": "G3/k6-v16-output.png", "selected_on": "2026-07-31", "at_rev": 29}}

_ORIGIN_LINE = (
    "**Elements:** `@cafe_int` `@hero` · **`start_image` = `G3/k5-24.png` · "
    "`end_image` = `G3/k6-3.png`** · **duration 12** · `seedance_2_0`\n")

FRAME_CASES = [
    # (name, prompts body, selections, want-substring or None for "accepted")
    ("a LIVE block naming the current selection is accepted",
     "# The prompt\n<!-- status: LIVE  role: g3 -->\n`start_image` = `G3/k5-30.png`\n",
     SEL, None),
    ("a LIVE block naming a superseded frame is refused",
     "# The prompt\n<!-- status: LIVE  role: g3 -->\n`start_image` = `G3/k5-24.png`\n",
     SEL, "selections.start is G3/k5-30.png"),
    ("...and the refusal names the dead frame too, not only the live one",
     "# The prompt\n<!-- status: LIVE  role: g3 -->\n`start_image` = `G3/k5-24.png`\n",
     SEL, "start_image = G3/k5-24.png"),
    # THE DISCRIMINATION CONTROL. A superseded block naming the frame it was
    # fired with is not stale — it IS the record. A rule that cannot tell those
    # apart asks the project to delete its own history to satisfy a checker.
    ("a SUPERSEDED block naming the OLD frame is accepted — that is the record",
     "# The old prompt\n<!-- status: SUPERSEDED by: `v4` -->\n"
     "`start_image` = `G3/k5-24.png`\n",
     SEL, None),
    ("a DRAFT block naming another frame is accepted — it has not been fired",
     "# Next one\n<!-- status: DRAFT -->\n`start_image` = `G3/k5-24.png`\n",
     SEL, None),
    # Prose naming the ROLE is not a claim about a FILE. The origin says
    # "roles `start_image` / `end_image`" in three places nobody would call a
    # frame reference, and a guard that reads those as claims gets switched off.
    ("naming the role in prose with no file is not read as a claim",
     "# The prompt\n<!-- status: LIVE  role: g3 -->\n"
     "Pass them in `medias[]` with roles `start_image` and `end_image`.\n",
     SEL, None),
    ("job ids are not filenames",
     "# The prompt\n<!-- status: LIVE  role: g3 -->\n"
     "**start_image** `1bb6178a…` · **end_image** `94e40bb1…` · **duration 10**\n",
     SEL, None),
    ("a leading ./ is the same file",
     "# The prompt\n<!-- status: LIVE  role: g3 -->\n`start_image` = `./G3/k5-30.png`\n",
     SEL, None),
    ("a role the film does not select is reported UNCHECKED, not passed",
     "# The prompt\n<!-- status: LIVE  role: g3 -->\n`middle_image` = `G3/x.png`\n",
     SEL, "NOT CHECKED"),
    ("a film with no selections at all says nothing and exits 0",
     "# The prompt\n<!-- status: LIVE  role: g3 -->\n`start_image` = `G3/k5-24.png`\n",
     None, None),
    ("the origin's own first line, character for character, is refused",
     "# G3 v4 · SHOTS 5 + 6 — the turn and the walk · 12s · 54 cr at 720p std\n"
     "<!-- status: LIVE  role: G3 -->\n" + _ORIGIN_LINE,
     SEL, "selections.end is G3/k6-v16-output.png"),
    ("...and it catches BOTH frames in that line, not only the first",
     "# G3 v4 · SHOTS 5 + 6 — the turn and the walk · 12s · 54 cr at 720p std\n"
     "<!-- status: LIVE  role: G3 -->\n" + _ORIGIN_LINE,
     SEL, "selections.start is G3/k5-30.png"),
]


def run_case(body, selections="unset"):
    with tempfile.TemporaryDirectory() as d:
        film = pathlib.Path(d)
        facts = dict(FACTS)
        if selections != "unset" and selections is not None:
            facts["selections"] = selections
        (film / "film_facts.json").write_text(json.dumps(facts), encoding="utf-8")
        (film / "PROMPTS.md").write_text(body, encoding="utf-8")
        p = subprocess.run([sys.executable, str(KIT / "tools" / "staleness.py"),
                            "--project", str(film / "film_facts.json")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="backslashreplace", timeout=120)
        return p.stdout + p.stderr, p.returncode


def main():
    ok = True
    print("\n  BLOCK STATUS — LIVE / DRAFT / SUPERSEDED / DONE / ABANDONED / INFO\n")
    for name, body, want in CASES:
        out, rc = run_case(body)
        if "Traceback" in out:
            good = False
        elif want is None:
            good = rc == 0
        else:
            good = want in out
        ok &= good
        print(f"  {'ok ' if good else '!! '}{name}")
        if not good:
            for line in out.strip().splitlines()[-4:]:
                print(f"       {line[:100]}")

    # THE COUNT, not just the presence. The file-level rule exists because the
    # first version reported one violation per HEADING in files whose first line
    # marked them -- seventeen of them, none real. Asserting the message appears
    # would have passed on that version too.
    out, _ = run_case("<!-- status: DONE -->\n\n# One\nb\n\n# Two\nb\n\n# Three\nb\n")
    n = out.count("names nothing it produced")
    good = n == 1
    ok &= good
    print(f"  {'ok ' if good else '!! '}...and it is asked once, not once per heading "
          f"(counted {n})")

    print("\n  FK-26 — a LIVE block may not name a frame that is not the selection\n")
    for name, body, sel, want in FRAME_CASES:
        out, rc = run_case(body, sel)
        if "Traceback" in out:
            good = False
        elif want is None:
            good = rc == 0
        else:
            good = want in out
        ok &= good
        print(f"  {'ok ' if good else '!! '}{name}")
        if not good:
            for line in out.strip().splitlines()[-4:]:
                print(f"       {line[:100]}")

    print()
    print("  \033[92mNo faults of any known class.\033[0m" if ok
          else "  \033[91mFAILED.\033[0m")
    print("  NOT tested: whether these statuses are the RIGHT vocabulary for a film, only")
    print("  that each rule fires on text that should trip it and stays quiet on text that")
    print("  should not.\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
