#!/usr/bin/env python3
"""
THE PLANNING GATE — run this BEFORE building any asset.

WHY THIS EXISTS
---------------
Every other tool in this kit guards a PROMPT. None of them guarded the decision
about WHAT TO BUILD, and that is where this project wasted the most.

  @tarn_view / @tarn_water / @tarn_shore — three plates built, fought over for
  two days, eight generations across two models, and in the end NO SHOT USED
  ANY OF THEM. One reverse-angle plate replaced all three. The analysis that
  showed it took ten minutes and could have been done before the first one was
  generated: read the shot list, ask what is actually on screen.

  K6 — eleven generations for a conditioning frame, and asset_economy already
  said a frame is earned ONLY when a state changes inside the shot.

  @whale / @whale_skin — discovered late, and Shots 11 and 12 cannot be written
  without them.

Those are three different failures with one shape: NOBODY ASKED, PER SHOT, WHAT
MUST BE ON SCREEN AND WHAT SUPPLIES IT.

WHAT IT CHECKS
    orphan-element   an element exists that no shot names        -> DO NOT BUILD
    missing-element  a shot names an element the ledger cannot
                     supply                                      -> REGISTER OR BUILD
    unverified       a shot rests on an element with no proof    -> VERIFY IT
    angle-without-plate  a shot is photographed on an axis no
                     attached plate covers                      -> DERIVE THE PLATE
    no-load-bearing  a shot never says which single relationship
                     decides whether the frame is the right room -> NAME IT
    frame-unearned   a frame is justified for a shot that has
                     no state change                             -> DELETE IT
    frame-needed     a state changes inside a shot and no frame
                     is justified for it                         -> DECIDE
    uncovered        a shot has no row at all                    -> FILL IT IN

Exit 1 on anything that would waste a generation.

Usage
  python3 shotmap.py                # the table and the findings
  python3 shotmap.py --plan         # only what to build next, in order
"""
import argparse, json, os, pathlib, sys
import _project as P  # FK1: where the film is

HERE = P.DIR
R, G, Y, C, X = "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[0m"


def load():
    f = str(P.PATH)
    return json.loads((HERE / f).read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args()

    d = load()
    req = {k: v for k, v in d.get("shot_requirements", {}).items() if not k.startswith("_")}
    if not req:
        print(f"\n  {R}NO shot_requirements IN THE PROJECT FILE{X}")
        print("  This is the planning gate and it has nothing to read. Fill it in")
        print("  BEFORE building assets — that is the whole point of it.\n")
        return 1

    assets = d.get("assets", {})
    env = set(d.get("element_rules", {}).get("environment_tags", []))
    retired = set(d.get("element_rules", {}).get("retired_tags", {}))
    frames = d.get("asset_economy", {}).get("frames_justified", {})
    # explicit shot lists, never parsed from prose — a machine decision read out
    # of a sentence is how "shot 1" appeared from the phrase "frame 1".
    framed_shots = set()
    for k, v in frames.items():
        if k.startswith("_") or not isinstance(v, dict):
            continue
        framed_shots.update(str(x) for x in v.get("shots", []))

    findings, used = [], set()

    print(f"\n{'='*84}\n  SHOT MAP — what each shot needs, and what supplies it\n{'='*84}")
    print(f"  {'shot':5s} {'elements':44s} {'state change'}")
    for s, row in req.items():
        els = row.get("elements") or ([row["supplied_by"]] if row.get("supplied_by") else [])
        used.update(els)
        # max_environment_tags — a shot may attach only one location element
        envs = [e for e in els if e in env or e in retired]
        if len(envs) > int(d.get("element_rules", {}).get("max_environment_tags", 1)):
            findings.append(("two-environments",
                f"shot {s} lists {len(envs)} environment elements ({', '.join(envs)}) and only one may be attached"))
        cells = []
        for e in els:
            rec = assets.get(e)
            if e in retired:
                cells.append(f"{e}!RET"); findings.append(("missing-element", f"shot {s}: {e} is RETIRED"))
            elif rec is None:
                # F-55. This used to read "is not in the ledger at all — BUILD IT",
                # which conflates two different states with two different costs:
                # "we have no record of it" and "it does not exist". @phone was
                # already built and sitting in the workspace; the tool told me to
                # build it again. This script cannot see Higgsfield, so it must not
                # claim to know. Look there BEFORE spending anything.
                cells.append(f"{e}!ROW"); findings.append(("missing-element", f"shot {s}: {e} has NO LEDGER ROW — look in the workspace first: REGISTER it if it already exists, BUILD it only if it does not"))
            elif not rec.get("file"):
                cells.append(f"{e}!PLN"); findings.append(("missing-element", f"shot {s}: {e} is PLANNED but not built — no file"))
            elif not rec.get("verified"):
                cells.append(f"{e}!unv"); findings.append(("unverified", f"shot {s}: {e} has no verified claims"))
            else:
                cells.append(e)
        # F-58. A shot with no stated load-bearing relationship cannot be
        # reviewed, only inventoried — and an inventory of correct objects
        # passed eight checks while the door stood on the wrong wall.
        if not (row.get("load_bearing") or "").strip():
            findings.append(("no-load-bearing",
                f"shot {s}: no load_bearing relationship recorded. Name the ONE thing that "
                f"decides whether a returned frame is the right room, before anything is built."))
        # F-59. A shot photographed on an axis no attached plate covers is a
        # shot arguing with its own reference. Six previz renders of Shot 6B
        # were spent discovering that prose does not win that argument.
        ax = (row.get("camera_axis") or "").strip()
        if not ax:
            findings.append(("angle-without-plate",
                f"shot {s}: no camera_axis recorded. Say which way this room is being looked at."))
        else:
            covered = set()
            for e in els:
                covered.update(assets.get(e, {}).get("covers_axes") or [])
            if ax not in covered:
                # F-67. This finding could only ever be satisfied by an ELEMENT, and
                # the plate that holds Shot 6B's axis is barred from being one: it is
                # a conditioning frame, and element_rules.conditioning_frames_are_not_elements
                # forbids registering one. So the guard demanded a thing the rules
                # refuse to supply, and stayed red with the work already done. It now
                # says what the ledger actually holds on this axis, and which of those
                # may be attached and which may only be passed as a frame.
                cand_el, cand_fr = [], []
                for _tag, _rec in sorted(assets.items()):
                    if ax in (_rec.get("covers_axes") or []):
                        (cand_fr if _rec.get("is_conditioning_frame") else cand_el).append(_tag)
                if cand_el or cand_fr:
                    extra = ""
                    if cand_el:
                        extra += (f" The ledger holds ATTACHABLE plates on this axis: "
                                  f"{' '.join(cand_el)} — attach one.")
                    if cand_fr:
                        extra += (f" It also holds CONDITIONING FRAMES on this axis: "
                                  f"{' '.join(cand_fr)} — these go in medias[] as start_image or "
                                  f"end_image and must NEVER be attached as elements.")
                else:
                    extra = (" Derive a plate for this angle from the master FIRST — reframe or "
                             "edit, never fresh prose — or change the axis.")
                findings.append(("angle-without-plate",
                    f"shot {s}: camera_axis {ax!r} is covered by NO attached element "
                    f"(they hold {sorted(covered) or 'nothing'})." + extra))
        sc = row.get("state_change") or {}
        what, carried = sc.get("what", ""), sc.get("carried_by", "")
        mark = " " if not what else "!"
        cell = f"[{carried}] {what}" if what else "—"
        print(f"  {mark}{s:4s} {' '.join(cells)[:44]:44s} {cell[:32]}")

        if what and not carried:
            findings.append(("undecided", f"shot {s} changes state and nobody has said what carries it"))
        if carried == "frame" and s not in framed_shots:
            findings.append(("frame-needed", f"shot {s} is ruled to need a FRAME and frames_justified does not list it"))
        if s in framed_shots and carried != "frame":
            findings.append(("frame-unearned", f"shot {s} has a justified frame but its change is carried by {carried or 'nothing'}"))

    # THE TWO-WAY STREET. A shot added to the script and not to the map is
    # invisible to every check here; a row here for a shot the script dropped is
    # a build order for nothing. Production changes the script as often as the
    # script changes production, so the two are compared rather than trusted.
    import re as _re
    script = HERE / d["_script"] if d.get("_script") else P.files("script")
    if script.exists():
        in_script = set(_re.findall(r"^### SHOT ([0-9]+[A-Z]?) ", script.read_text(encoding="utf-8"), _re.M))
        for s_ in sorted(in_script - set(req)):
            findings.append(("uncovered", f"shot {s_} is in the script and has NO row in shot_requirements"))
        for s_ in sorted(set(req) - in_script):
            findings.append(("uncovered", f"shot {s_} has a row in shot_requirements and is NOT in the script"))

    orphans = sorted(env - used - retired)
    for o in orphans:
        findings.append(("orphan-element", f"{o} — no shot names it"))

    print(f"\n{'='*84}\n  FINDINGS\n{'='*84}")
    if not findings:
        print(f"  {G}Nothing to build and nothing unearned.{X}")
    # F-59b. This ORDER list used to be a filter as well as a sort: a finding
    # whose level was not on it printed nowhere at all, and `angle-without-plate`
    # vanished silently on the day it was written. Same shape as F-56 — a guard
    # whose reach is an allow-list. It now sorts what it knows and prints the
    # rest anyway, loudly, because an unrecognised finding is the interesting one.
    order = ["angle-without-plate", "missing-element", "orphan-element", "two-environments",
             "no-load-bearing", "frame-unearned", "frame-needed", "undecided",
             "unverified", "uncovered"]
    LOUD = ("angle-without-plate", "missing-element", "orphan-element", "frame-unearned",
            "no-load-bearing")
    for lvl in order:
        for l, msg in [f for f in findings if f[0] == lvl]:
            print(f"  {(R if l in LOUD else Y)}{l:20s}{X} {msg}")
    for l, msg in [f for f in findings if f[0] not in order]:
        print(f"  {R}{l:20s}{X} {msg}   <- finding type not in the print order; nothing was suppressed")

    if orphans:
        print(f"\n  {R}ORPHANS ARE THE EXPENSIVE ONE.{X} An element no shot names is an element")
        print("  nobody needs. @tarn_view, @tarn_water and @tarn_shore were all orphans and")
        print("  cost eight generations before anybody asked what the shots were looking at.")

    if a.plan:
        todo = [m for l, m in findings if l in ("angle-without-plate", "missing-element")]
        print(f"\n{'='*84}\n  BUILD NEXT — and nothing else\n{'='*84}")
        for t in todo or ["  (nothing)"]:
            print(f"  · {t}")

    print()
    return 1 if any(l in ("angle-without-plate", "missing-element", "orphan-element",
                          "frame-unearned", "two-environments", "no-load-bearing")
                    for l, _ in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
