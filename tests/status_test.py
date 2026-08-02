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
         "assets": {"@real_one": {}, "@real_two": {}},
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
    ("a heading with no marker anywhere is still refused",
     "# Bare\nbody\n",
     "heading has no status marker"),
]


def run_case(body):
    with tempfile.TemporaryDirectory() as d:
        film = pathlib.Path(d)
        (film / "film_facts.json").write_text(json.dumps(FACTS), encoding="utf-8")
        (film / "PROMPTS.md").write_text(body, encoding="utf-8")
        p = subprocess.run([sys.executable, str(KIT / "tools" / "staleness.py"),
                            "--project", str(film / "film_facts.json")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="backslashreplace", timeout=120)
        return p.stdout + p.stderr, p.returncode


def main():
    ok = True
    print("\n  BLOCK STATUS — LIVE / DRAFT / SUPERSEDED / DONE / INFO\n")
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

    print()
    print("  \033[92mNo faults of any known class.\033[0m" if ok
          else "  \033[91mFAILED.\033[0m")
    print("  NOT tested: whether these statuses are the RIGHT vocabulary for a film, only")
    print("  that each rule fires on text that should trip it and stays quiet on text that")
    print("  should not.\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
