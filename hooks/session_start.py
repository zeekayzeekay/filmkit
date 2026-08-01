#!/usr/bin/env python3
"""
STATE LOADER — SessionStart, both hosts.

Puts the film's actual state into the model's context at the start of every
session, without anybody asking for it.

WHY THIS EXISTS
---------------
The operator's complaint, in his words: *"this whole process has to be
predictable, reproducible and verifiable ... invariably you are forgetting or
missing out on stuff."*

He was right, and the reason is structural rather than a matter of effort. Every
piece of state in a film project lives in a document, and a document only reaches
the model if somebody says "read these six documents" — every session, in the
right order, remembering which six. That is not a system. It is a hope with a
checklist attached.

WHAT IT LOADS, AND WHY EACH ONE
-------------------------------
    kit version vs the film's pin   a film shot under one kit and checked by
                                    another is not reproducible, and the drift is
                                    silent
    fact_rev                        every selection and every receipt is keyed to
                                    it; if it moved, things that looked settled
                                    are stale
    failing gates                   what shotmap and verify_asset would say if
                                    asked, said without being asked
    unanswered manual items         "listed but unanswered" is what every
                                    recurrence in the origin project had in common
    open decisions                  questions put to the operator that nobody has
                                    answered, which otherwise get quietly assumed

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
Summarise the film, the script, or the craft. Those are large, they are stable,
and loading them every session would push out the thing that actually changed.
This loads STATE — what is true right now and was not necessarily true last time.

It is also strictly read-only and never blocks. A SessionStart hook that fails
should cost a session nothing.
"""
import json, pathlib, sys

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "tools"))

MAX_LINES = 40   # a briefing nobody reads is worse than none


def find_film(start):
    d = pathlib.Path(start or ".").resolve()
    for cand in [d] + list(d.parents):
        if (cand / "film_facts.json").exists():
            return cand, cand / "film_facts.json"
        found = sorted(cand.glob("*_facts.json"))
        if len(found) == 1:
            return cand, found[0]
    return None, None


def brief(cwd):
    film, facts_path = find_film(cwd)
    if film is None:
        return []

    # Point the tools at the film WE found, before importing any of them. They
    # resolve from the process's cwd, and a hook's cwd is whatever the host chose
    # — importing them first makes them look in the wrong place and raise.
    import os
    os.environ["FILMKIT_PROJECT"] = str(facts_path)
    import _project as P
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    out = [f"FILMKIT — {film.name}", ""]

    pinned, running = facts.get("kit_version"), P.kit_version()
    if pinned and pinned != running:
        out.append(f"  !! kit {running} running against a film pinned to {pinned}")
    elif not pinned:
        out.append(f"  !! this film pins no kit_version (running {running})")
    else:
        out.append(f"  kit {running}, matching the film's pin")

    out.append(f"  fact_rev {facts.get('_fact_rev')}"
               f" · {len(facts.get('assets', {}))} assets"
               f" · {len(facts.get('shot_requirements', {}))} shot rows")

    if "look_pack" not in facts:
        out.append("  !! look_pack is not declared. Set it to a pack name or to null;")
        out.append("     silence is not the same as none.")

    try:
        import verify_asset as VA
        locked = [(t, w) for t, rec in facts.get("assets", {}).items()
                  for w in VA.locked_reasons(rec)]
    except BaseException:
        locked = []
    if locked:
        out.append(f"  !! {len({t for t, _ in locked})} asset(s) cannot receive a new claim:")
        for t, w in locked[:4]:
            out.append(f"     {t} — {w}")

    # Unanswered manual items, from the ledger rather than from a second list.
    try:
        import checklist as C
        manual = [f for f in C.findings() if f.get("guard") == "manual"]
        record = film / "RUN_RECORD.md"
        answered = 0
        if record.exists():
            txt = record.read_text(encoding="utf-8")
            answered = sum(1 for f in manual if f["id"] in txt)
        if manual:
            out.append(f"  {len(manual)} manual review item(s); "
                       f"{len(manual) - answered} with no written answer in RUN_RECORD.md")
    except BaseException:
        pass

    open_q = facts.get("open_decisions") or []
    if open_q:
        out.append(f"  !! {len(open_q)} decision(s) waiting on the operator:")
        for q in open_q[:4]:
            out.append(f"     {q if isinstance(q, str) else q.get('question', q)}")

    out += ["",
            "  Nothing fires without a receipt. preflight must be all-green INCLUDING the",
            "  manual items — the gate refuses any generation whose prompt does not hash to one.",
            "  Credits belong to the operator: ask before spending."]
    return out[:MAX_LINES]


def main():
    if "--selftest" in sys.argv:
        return selftest()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    try:
        lines = brief(payload.get("cwd"))
    except BaseException as e:
        # A briefing that fails must cost the session nothing. Unlike the spend
        # gate, the safe direction here is to say nothing and get out of the way:
        # this hook protects nobody, so failing loudly would only add noise to
        # the start of every session.
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"filmkit could not load project state ({type(e).__name__}: {e})."
        }}))
        return 0
    if not lines:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n".join(lines)}}))
    return 0


def selftest():
    import tempfile
    ok = True
    print("\n  SESSION-START SELFTEST\n")

    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d)
        (p / "film_facts.json").write_text(json.dumps({
            "_fact_rev": 12, "kit_version": "0.0.1", "assets": {},
            "shot_requirements": {"1": {}},
            "open_decisions": ["6B duration: 3s or 5s?"]}), encoding="utf-8")
        lines = brief(str(p))
        checks = [
            ("names the film", any(p.name in l for l in lines)),
            ("flags the version mismatch", any("pinned to 0.0.1" in l for l in lines)),
            ("reports fact_rev", any("fact_rev 12" in l for l in lines)),
            ("flags undeclared look_pack", any("look_pack" in l for l in lines)),
            ("surfaces the open decision", any("6B duration" in l for l in lines)),
            ("stays under the line budget", len(lines) <= MAX_LINES),
        ]
        for name, good in checks:
            ok &= good
            print(f"  {'ok ' if good else '!! '}{name}")

    with tempfile.TemporaryDirectory() as d:
        empty = brief(d)
        print(f"  {'ok ' if empty == [] else '!! '}silent outside any film")
        ok &= (empty == [])

    import subprocess
    r = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve())],
                       input="not json", capture_output=True, text=True, cwd="/")
    good = r.returncode == 0
    ok &= good
    print(f"  {'ok ' if good else '!! '}unparseable payload costs the session nothing "
          f"(exit {r.returncode})")

    print()
    print("  \033[92mAll cases pass.\033[0m" if ok else "  \033[91mFAILED.\033[0m")
    print("  NOT tested: whether a host actually invokes this, or whether the operator")
    print("  has trusted it. An untrusted SessionStart hook is silent, and silence here")
    print("  looks exactly like a film with nothing to report.\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
