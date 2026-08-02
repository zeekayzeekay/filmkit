#!/usr/bin/env python3
"""
TARN preflight — ONE command, run before any generation is fired.

WHY THIS EXISTS
---------------
The review protocol was three separate commands plus two manual steps, and the
manual steps were the ones that got skipped. Not through carelessness: a review
spread across five actions has five places to stop, and "I ran the linter" reads
as "I reviewed it" when it only ever meant "I ran one of the five".

G3 v3 was fired after a review that reported zero errors. It shipped with:
  * 45 negations (Lesson 1)              — linter WARNed; warnings get skimmed
  * a warm rim baked into the start frame — nothing looked at the frames at all
  * a lock the end frame could not satisfy — nothing compared the two
  * a heading priced at the wrong rate    — nothing checked the arithmetic

So this is one command with one exit code. If it does not print PASS, the
generation is not fired. There is no partial pass.

Usage
  python3 preflight.py --block "G3 v4" --start G3/k5-24.png --end G3/k6-3.png
  python3 preflight.py --fixtures              # just prove the guards still fire
"""
import argparse, pathlib, re, subprocess, sys
import json
import _project as P  # FK1: where the film is



HERE = P.DIR

# Fixtures assert RULE NAMES, not totals. Totals go stale the moment a new check
# is added — which happened on the first day this file existed, when three new
# checks pushed the sibling fixture from 3 errors to 6 and made its own header
# wrong. A rule name is stable; a count is a hostage to the next commit.
# ---------------------------------------------------------------------------
# FK1. These were literal dicts keyed by one film's filenames. They are DATA:
# the kit seeds them, a film may add its own, and neither lives in the engine.
# ---------------------------------------------------------------------------
def _load_corpus():
    merged = {"fixtures": {}, "mutations": {}}
    seeds = [P.KIT.parent / "tests" / "fixtures" / "manifest.json"]
    film = P.DIR / "fixtures_manifest.json"
    if film.exists():
        seeds.append(film)
    for s in seeds:
        if not s.exists():
            continue
        d = json.loads(s.read_text(encoding="utf-8"))
        merged["fixtures"].update(d.get("fixtures", {}))
        for k, v in d.get("mutations", {}).items():
            merged["mutations"].setdefault(k, []).extend(v)
    return merged


_CORPUS = _load_corpus()
FIXTURES = _CORPUS["fixtures"]
MUTATIONS = {k: [tuple(x) for x in v] for k, v in _CORPUS["mutations"].items()}

# MUTATION TESTS. A fixture proves a guard FIRES. It does not prove the guard
# DISCRIMINATES — a rule that matches everything passes its fixture and is
# worthless. Three guards written in this session had first versions that
# silently matched NOTHING (the MEASURED-LOCK regex missed blockquoted lines;
# scope-conflict compared vocabulary instead of polarity; the warm mask was a
# skin detector). Each was caught by accident.
#
# So: repair the fault in the fixture text and assert the rule goes QUIET. If it
# still fires on repaired text it is not testing what it claims to.

def check_mutations():
    """Repair each fixture's fault; the guard must fall silent."""
    print("\n=== DISCRIMINATION — does each guard go quiet when the fault is fixed?")
    ok = True
    for f, cases in MUTATIONS.items():
        src = HERE / f
        if not src.exists():
            print(f"  -- {f} is not in this film; its repairs cannot be checked here")
            continue
        original = src.read_text(encoding="utf-8")
        # group by rule: a fault stated N times needs all N repaired at once
        grouped = {}
        for rule, bad, good in cases:
            grouped.setdefault(rule, []).append((bad, good))
        for rule, pairs in grouped.items():
            missing = [b for b, _ in pairs if b not in original]
            if missing:
                print(f"  FAIL {rule:24s} mutation text not found — the fixture changed under it")
                ok = False
                continue
            try:
                mutated = original
                for b, g in pairs:
                    mutated = mutated.replace(b, g)
                src.write_text(mutated, encoding="utf-8")
                _, out = run([sys.executable, P.tool("lint_prompt.py"), f])
                still = len(re.findall(rf"\[(?:ERROR|WARN|CHECK)\] {re.escape(rule)}", out))
            finally:
                src.write_text(original, encoding="utf-8")
            mark = "ok " if still == 0 else "FAIL"
            if still:
                ok = False
            print(f"  {mark} {rule:24s} fires {still}x on repaired text (want 0)")
    if not ok:
        print("\n  A guard that still fires after the fault is removed is not testing what it "
              "claims to. Fix the rule, not the fixture.")
    return ok


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="backslashreplace", cwd=HERE)
    return p.returncode, p.stdout + p.stderr


def check_fixtures():
    print("\n=== GUARDS — do the checks still fire?")
    ok = True
    # A fixture the corpus names but this film does not have. The kit seeds the
    # manifest from the origin project, so a NEW film names fixtures whose files
    # live in someone else's directory -- and opening one was a traceback, in the
    # phase whose whole purpose is proving the guards still fire. Report it as
    # what it is: a rule nobody in THIS film has watched fire.
    missing = [f for f in FIXTURES if not (HERE / f).exists()]
    if missing:
        print(f"  {len(missing)} fixture(s) named in the corpus are not in this film:")
        for f in missing:
            print(f"     -- {f}")
        print("     Their rules are UNPROVEN here. Promote a neutral fixture into the kit")
        print("     (bin/filmkit-promote) or write one for this film.")
    for f, expect in FIXTURES.items():
        if f in missing:
            continue
        _, out = run([sys.executable, P.tool("lint_prompt.py"), f])
        for rule, n in expect.items():
            got = len(re.findall(rf"\[(?:ERROR|WARN|CHECK)\] {re.escape(rule)}", out))
            mark = "ok " if got >= n else "FAIL"
            if got < n:
                ok = False
            print(f"  {mark} {f:38s} {rule:24s} {got}/{n}")
    if not ok:
        print("\n  A guard has stopped firing. That is worse than no guard — fix it "
              "before trusting any other result in this run.")
    return ok


def prompts_file(block):
    """
    Which of this film's prompt ledgers holds this block.

    A film may keep prompts in several files. A tool that must act on ONE -- lint
    a block, export a block -- cannot take element zero of that list, so it
    locates the block instead. Two ledgers holding the same heading is its own
    fault and is refused rather than resolved: whichever one you patched, the
    other still says it is live.
    """
    hits = [f for f in P.file_list("prompts")
            if f.exists() and block in f.read_text(encoding="utf-8")]
    if not hits:
        raise SystemExit(f"\n  ! no prompt ledger in this film contains a block matching "
                         f"{block!r}.\n    Looked in: "
                         + ", ".join(f.name for f in P.file_list("prompts")) + "\n")
    if len(hits) > 1:
        raise SystemExit(f"\n  ! {len(hits)} ledgers contain {block!r}: "
                         + ", ".join(f.name for f in hits) + "\n"
                         "    Patch one and the other still claims to be live. Rename the\n"
                         "    block, or supersede the copy you are not using.\n")
    return hits[0]


def check_prompt(block):
    print(f"\n=== PROMPT — lint_prompt.py --block {block!r}")
    code, out = run([sys.executable, P.tool("lint_prompt.py"), str(prompts_file(block)),
                     "--block", block])
    errs = re.findall(r"\[ERROR\] .*", out)
    warns = re.findall(r"\[WARN\] .*", out)
    checks = re.findall(r"\[CHECK\] [^\n]*", out)
    for line in re.findall(r"· (?:negations|beats|words|cost|tags): .*", out):
        print(f"  · {line[2:]}")
    for e in errs:
        print(f"  {e}")
    print(f"  {len(errs)} error · {len(warns)} warn · {len(checks)} consistency-check")
    if checks:
        print("  CHECK items are not automatic passes — read each group before firing:")
        for c in checks:
            print(f"    - {c[8:120]}")
    return not errs


def check_frames(start, end, expect):
    print("\n=== CONDITIONING FRAMES — the check that did not exist when v3 was fired")
    ok = True
    for path, role in ((start, "start"), (end, "end")):
        if not path:
            continue
        code, out = run([sys.executable, P.tool("frames_check.py"), path, "--role", role])
        print("  " + "\n  ".join(l for l in out.splitlines() if l.strip()))
        ok &= (code == 0)
    if start and end:
        code, out = run([sys.executable, P.tool("frames_check.py"), start, end,
                         "--pair", "--expect", expect])
        print("  " + "\n  ".join(l for l in out.splitlines()[-6:] if l.strip()))
        ok &= (code == 0)
    return ok



def check_shotmap(shot):
    """THE PLANNING GATE, re-asserted at fire time.

    shotmap.py is meant to run BEFORE anything is built. This is the cheap
    re-check that the world has not moved since: do this shot's elements all
    exist and carry proof, and is its conditioning-frame decision still the one
    recorded? Firing a prompt whose elements are not ready is how @whale went
    unnoticed until two shots could not be written."""
    print(f"\n=== SHOT MAP — is shot {shot} actually ready to build?")
    code, out = run([sys.executable, P.tool("shotmap.py")])
    keep = [l for l in out.splitlines()
            if f"shot {shot}:" in l or f"shot {shot} " in l]
    if keep:
        for l in keep:
            print("  " + l.strip())
        return False
    print(f"  ok  every element shot {shot} names exists and carries verified claims")
    return True


def check_selections():
    """F-19: a frame chosen before a fact was corrected is provisional again."""
    print("\n=== SELECTIONS — chosen under the facts as they stand now?")
    code, out = run([sys.executable, P.tool("selections.py"), "--check"])
    for l in out.splitlines():
        if l.strip():
            print("  " + l.strip())
    return code == 0


def check_export(block, path):
    """The text handed over must BE the block. The exported v2b file once did not
    match the file it came from, and the difference was only caught by eye."""
    print("\n=== EXPORT — does the handed-over file match the block?")
    if not path:
        print("  no --export given; the prompt was not exported this run")
        return True
    code, out = run([sys.executable, P.tool("patch_block.py"), str(prompts_file(block)),
                     "--block", block, "--export", path])
    print("  " + out.strip().replace("\n", "\n  "))
    return code == 0


def check_record(path):
    """The manual items, derived from the findings ledger, must be ANSWERED.

    Listing them was not enough. Every recurrence in this project happened after
    the lesson had been written down and read. So PASS is withheld until each
    item has a written answer — an unanswered item is a failed run, exactly like
    a failed assertion."""
    import subprocess as sp
    blank = sp.run([sys.executable, P.tool("checklist.py"), "--manual"],
                   capture_output=True, text=True, encoding="utf-8", errors="backslashreplace", cwd=HERE).stdout
    items = re.findall(r"^## (M\d+) · (F-\d+|DECISION)", blank, re.M)
    print(f"\n=== MANUAL ITEMS — {len(items)}, derived from the findings ledger")
    p = HERE / path
    if not p.exists():
        p.write_text(blank, encoding="utf-8")
        print(f"  no run record found — a blank one has been written to {path}")
        print("  Answer every item, then re-run. This is the step that keeps getting skipped.")
        return False
    text = p.read_text(encoding="utf-8")

    # ---- F-49: pair by FINDING ID, never by item number.
    # M-numbers are positions in the ledger, so inserting one finding renumbers
    # every later item -- and the old matcher keyed on the number alone, so each
    # answer silently slid onto the NEXT question and preflight reported it
    # green. Ten of twenty-five were mis-paired when this was found, including
    # F-39 (roll vs edit), whose slot held an answer written about the cup hand.
    # Same shape as the F-37 addendum: an attestation that names something other
    # than the thing it attests to is worse than none, because it looks like
    # verification.
    in_record = dict(re.findall(r"^## (M\d+) · (F-\d+|DECISION)", text, re.M))
    mis = [(m, fid, in_record.get(m)) for m, fid in items
           if m in in_record and in_record[m] != fid]
    if mis:
        print("\n  \033[91m! RUN RECORD IS MIS-PAIRED WITH THE LEDGER\033[0m")
        for m, want, got in mis:
            print(f"    {m}: this run needs {want}, the record answers {got}")
        print("    Answers are keyed to the finding, not the number. Re-key the record"
              "\n    (python3 checklist.py --manual gives the current numbering) and re-run.")
        return False

    answered, unanswered = [], []
    for m, fid in items:
        blk = re.search(rf"^## {m} · {re.escape(fid)}\b.*?(?=\n## |\Z)", text, re.S | re.M)
        body = blk.group(0) if blk else ""
        ans = re.findall(r"^> ?(.*)$", body, re.M)
        ans = [x.strip() for x in ans if x.strip() and x.strip().lower() != "unanswered"]
        (answered if ans else unanswered).append((m, fid))
    for m, fid in answered:
        print(f"  ok  {m} ({fid})")
    for m, fid in unanswered:
        print(f"  !!  {m} ({fid})  UNANSWERED")
    if unanswered:
        print(f"\n  {len(unanswered)} manual item(s) unanswered. A listed-but-unanswered "
              "check is what every recurrence in this project has had in common.")
    return not unanswered



def check_neighbours(prev, new, record):
    """F-31 class 3. The sentences left standing when their neighbours were rewritten.

    No rule that reads the prompt alone can reach this class: "his shoulders are
    square to the window" does not name a destination, it was merely TRUE
    BECAUSE OF one. What is mechanical is WHERE such a sentence lives — inside a
    paragraph its author was editing around. So diff the versions and list the
    survivors.

    The list is a reading aid, not a verdict, so it cannot fail on its own
    content. It fails only if nobody has recorded reading it — because
    listed-but-unanswered is what every recurrence in this project has shared.
    The acknowledgement carries the COUNT, so it goes stale the moment the
    prompt changes again.
    """
    import subprocess
    print("\n=== SURVIVING SENTENCES — rewritten paragraphs, unchanged lines")
    r = subprocess.run([sys.executable, P.tool("stale_neighbours.py"), prev, new],
                       capture_output=True, text=True, encoding="utf-8", errors="backslashreplace", cwd=HERE)
    print(r.stdout.rstrip())
    n = 0
    for line in r.stdout.splitlines():
        m = re.match(r"\s*(\d+) SURVIVING SENTENCE", line)
        if m:
            n = int(m.group(1))
    if n == 0:
        return True
    want = f"NEIGHBOURS-CHECKED: {n}"
    text = (HERE / record).read_text(encoding="utf-8") if record and (HERE / record).exists() else ""
    if want in text:
        print(f"  ok  run record acknowledges all {n}")
        return True
    print(f"\n  !! the run record does not carry '{want}'.")
    print("     Read the list above with the changed decision in mind, then add that")
    print("     line. The count is part of it, so an old acknowledgement will not pass.")
    return False



def check_fullread(export, record):
    """F-37. The whole prompt, read once, against a hash of THIS version.

    Every fault found this week was found by reading the prompt end to end, and
    every version that shipped a fault had only its DIFF reviewed. The diff
    tools are real and they work, but they only ever look at what changed —
    and a stale sentence is by definition one that did not.

    Reading cannot be automated. Recording that it happened, against a hash that
    changes the moment the text does, can. An acknowledgement cannot be
    recycled: edit one word and the hash moves and this phase fails again.
    """
    import hashlib
    # Hash the file EXACTLY as patch_block hashes what it writes. The first
    # version of this phase hashed the file with its trailing newline while
    # patch_block hashed the body without one, so the two disagreed and the
    # attestation I wrote pointed at a version that did not exist. One artefact,
    # one hash — two schemes for the same thing is a way to attest to nothing.
    src = HERE / export
    if not src.exists():
        # A phase that cannot run is a phase that FAILS, loudly and by name. It
        # is never a traceback -- "no partial pass" means every phase reports a
        # verdict, and a stack trace is the absence of one.
        print(f"\n=== FULL READ — {export}")
        print(f"  !! {export} was not written, so there is nothing to read.")
        print("     The export phase runs first and produces it; if that phase failed,")
        print("     fix it there. A common cause is a --block name that matches no block.")
        return False
    txt = src.read_text(encoding="utf-8")
    h = hashlib.sha256(txt.encode()).hexdigest()[:12]
    words = len(txt.split())
    print(f"\n=== FULL READ — {export}  sha {h}  ({words} words)")
    rec = (HERE / record).read_text(encoding="utf-8") if record and (HERE / record).exists() else ""
    want = f"FULL-READ: {h}"
    if want in rec:
        print(f"  ok  run record carries '{want}'")
        return True
    print(f"  !! the run record does not carry '{want}'.")
    print("     Read the EXPORT end to end — not the diff, not the survivor list —")
    print("     then add that line. The hash is version-specific, so an old one will not pass.")
    return False



def check_crossshot(shot, record):
    """F-41. The shot before, the shot after, and the script — on one screen.

    Every prompt edit here was reviewed against the prompt. The four most
    expensive faults were all invisible from inside it: a walk added while the
    script still said he stops; an arc removed while a neighbour's note still
    protected it; light corrected to cool while the script still said hard sun;
    a duration trimmed while every later timecode went stale.

    No rule can judge these. What was missing was the GATHERING, and that is
    mechanical. The acknowledgement carries the shot number so it cannot be
    recycled onto a different shot.
    """
    import subprocess
    print(f"\n=== CROSS-SHOT — shot {shot} against its neighbours and the script")
    r = subprocess.run([sys.executable, P.tool("crossshot.py"), str(shot), "--quiet"],
                       capture_output=True, text=True, encoding="utf-8", errors="backslashreplace", cwd=HERE)
    print(r.stdout.rstrip())
    want = f"CROSSSHOT-CHECKED: {shot}"
    rec = (HERE / record).read_text(encoding="utf-8") if record and (HERE / record).exists() else ""
    if want in rec:
        print(f"  ok  run record carries '{want}'")
        return True
    print(f"\n  !! the run record does not carry '{want}'.")
    print("     Run `python3 crossshot.py {0}` in full, answer its three questions in".format(shot))
    print("     writing, and add that line.")
    return False



def check_staleness():
    """F-45. Nothing superseded may present itself as current.

    Facts had enforcement — withdrawn selections, retracted claims, superseded
    wording. Documents and prompt blocks had CONVENTIONS, and a convention holds
    until somebody is in a hurry. Two edits landed in historical blocks that
    way, and two dead headings still read "SELECTED" and "FINAL" days after the
    frames they named had been withdrawn.
    """
    code, out = run([sys.executable, P.tool("staleness.py")])
    print(out.rstrip())
    return code == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--expect", default="warmer")
    ap.add_argument("--fixtures", action="store_true")
    ap.add_argument("--record", help="run record holding the answers to the manual items")
    ap.add_argument("--export", help="write the block to this file and verify it matches")
    ap.add_argument("--shot", help="shot number, turns on the cross-shot phase")
    ap.add_argument("--prev", help="the PREVIOUS export of this block. Turns on the surviving-sentence report (F-31 class 3).")
    a = ap.parse_args()

    results = {}
    results["staleness"] = check_staleness()
    results["guards"] = check_fixtures()
    results["discriminate"] = check_mutations()
    if a.fixtures:
        return 0 if all(results.values()) else 1
    if a.block:
        results["prompt"] = check_prompt(a.block)
    if a.start or a.end:
        results["frames"] = check_frames(a.start, a.end, a.expect)
    results["selections"] = check_selections()
    if a.prev and a.export:
        results["neighbours"] = check_neighbours(a.prev, a.export, a.record)
    if a.shot:
        results["shotmap"] = check_shotmap(a.shot)
        results["cross-shot"] = check_crossshot(a.shot, a.record)
    # ORDER MATTERS, and it was wrong. check_fullread READS the export and
    # check_export WRITES it, and full-read ran first -- so the first run of the
    # documented command died with a FileNotFoundError traceback instead of a
    # phase result. It only ever appeared to work because a previous run had
    # left the file behind. Produce, then verify.
    if a.export:
        results["export"] = check_export(a.block, a.export)
        results["full-read"] = check_fullread(a.export, a.record)
    if a.record:
        results["manual"] = check_record(a.record)

    print("\n" + "=" * 66)
    for k, v in results.items():
        print(f"  {k:10s} {'PASS' if v else 'FAIL'}")
    allok = all(results.values())
    print("=" * 66)

    # ---- FK3. THE RECEIPT. Written ONLY on an all-green run that includes the
    # manual items -- which is to say, only when a person has read the exported
    # prompt end to end and signed for it. A gate keyed on the automatic phases
    # alone would pass a prompt nobody had read, which is the fault F-37 exists
    # about. No receipt, no fire: hooks/gate.py refuses any Higgsfield call whose
    # prompt does not hash to one.
    if allok and a.export and "manual" in results:
        import datetime as _dt
        import _receipt as R
        txt = (HERE / a.export).read_text(encoding="utf-8")
        rp = R.write(HERE, txt,
                     block=a.block,
                     fact_rev=P.FACTS.get("_fact_rev"),
                     kit_version=P.kit_version(),
                     phases=dict(results),
                     stamp=_dt.datetime.now(_dt.timezone.utc)
                           .strftime("%Y-%m-%dT%H:%M:%SZ"))
        print(f"  receipt written: {rp.relative_to(HERE)}")
        print(f"  it authorises THIS prompt only — {R.short(R.digest(txt))} — and expires "
              f"in {R.STALE_AFTER_HOURS}h\n")
    elif a.export:
        print("  \033[93mno receipt written — a generation will be REFUSED.\033[0m")
        if "manual" not in results:
            print("  Pass --record so the manual items are checked; the receipt requires them.\n")
        else:
            print("  Every phase above must be PASS, including the ones only a person can "
                  "answer.\n")

    if allok and "manual" in results:
        print("  PASS — automatic checks green and every manual item answered.")
        print("  Report 'no faults of any known class', never 'clean', and name")
        print("  what is not encoded.")
    elif allok:
        print("  AUTOMATIC CHECKS PASS — but the manual items have not been run.")
        print("  Re-run with --record RUN.md before firing. Those items exist")
        print("  because each one is a fault that has already cost something.")
        return 2
    else:
        print("  FAIL — do not fire.")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
