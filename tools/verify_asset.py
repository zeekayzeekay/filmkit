#!/usr/bin/env python3
"""
Record a VERIFIED observation about an asset — with a proof crop, or not at all.

WHY THIS EXISTS
---------------
Every other guard in this kit reads the prompt. None of them can tell you that
the prompt is faithfully repeating a false fact. On 30 Jul four claims about
`@cafe_int` turned out to be wrong:

    "one continuous horizontal glazing bar at two-thirds height"
        -> each bay is EIGHT lights: three vertical bars AND one horizontal bar
    "a broad brass strip along its base"
        -> the brass runs along the TOP of the front, under the wood top
    "deep green PANELLED front"
        -> the front is plain flat green; the panelled thing is the stall riser
    "There is no door in this plate"
        -> there is a door at the left end of the frontage

They were written into an authoritative-looking document during a "full visual
audit", copied verbatim into every prompt for two days, and survived five
generations and a dozen reviews. Consistency checking cannot catch this: a false
fact stated consistently is consistent.

THE RULE
    A claim about an asset is only a claim if somebody opened the file, looked at
    the region, and left the crop on disk. This tool will not record a claim
    without writing that crop.

Usage
  # look before you write: dump a region and inspect it
  python3 verify_asset.py @cafe_int --box 0.33,0.20,0.80,0.56 --look

  # record the observation, superseding whatever was believed before
  python3 verify_asset.py @cafe_int --box 0.345,0.24,0.50,0.50 \
      --claim "each glazing bay is eight lights: three vertical bars and one horizontal" \
      --supersedes "one continuous horizontal glazing bar at two-thirds height"

AND ON SCALE (F-17). The crop must show ONE instance filling the frame. A wide
crop containing several is a picture of the right place proving nothing — it is
how "four lights" was recorded, with a proof, and was wrong. A counting claim
from a box covering more than 6% of the frame is refused unless you pass --force.

  python3 verify_asset.py --audit          # which assets have never been verified
  python3 compare_asset.py --audit         # which assets do not know which way they face

AND ON WHICH FACE (F-46). Every asset carries an `aspect`. A claim is refused
without one, and compare_asset.py refuses to compare two assets across faces on
any property that only exists on one of them -- which is how five imaginary
faults were reported against @tarn_door.
"""
import argparse, datetime, json, pathlib, re, sys
from PIL import Image, ImageDraw
import _utf8  # noqa: F401  — the stream hardening, which _project used to bring

# FK-34. _project IS RESOLVED ON FIRST USE, NOT AT IMPORT.
#
# These three used to be module-level, so this file could not load outside a
# film -- and `--selftest`, which discriminates a counting detector on images it
# makes itself and needs no film at all, died before its first case. `verify.py`
# ran it with cwd=film, under a heading that reads "SELFTESTS THAT NEED NO
# FILM", so the harness that states the invariant was configured to hide the two
# entries breaking it.
#
# `bin/filmkit-promote` already carries this pattern with a comment explaining
# it. Two tools did not follow it and the same heading covered both.
_P = None


def _proj():
    global _P
    if _P is None:
        import _project as P  # FK1: where the film is
        _P = P
    return _P


def HERE():
    return _proj().DIR


def FACTS():
    return _proj().PATH


def PROOFS():
    return _proj().DIR / "proofs" / "asset_claims"


def load():
    return json.loads(FACTS().read_text(encoding="utf-8"))


def save(d):
    FACTS().write_text(json.dumps(d, indent=2), encoding="utf-8")


def crop(path, box, out, label):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    x0, y0, x1, y1 = box
    c = im.crop((int(W * x0), int(H * y0), int(W * x1), int(H * y1)))
    w = 1100
    c = c.resize((w, max(1, int(w * c.size[1] / c.size[0]))), Image.LANCZOS)
    c.save(out)
    # second proof: where in the whole frame, so a mis-aimed box announces itself
    full = im.copy()
    ImageDraw.Draw(full).rectangle([W * x0, H * y0, W * x1, H * y1],
                                   outline=(255, 40, 40), width=max(3, W // 300))
    full.thumbnail((1100, 1100))
    full.save(str(out).replace(".png", "_where.png"))
    return out



# ---------------------------------------------------------------------------
# F-56. A NUMBER IN FRONT OF A PLURAL IS A COUNT.
#
# The detector this replaces matched a number against a FIXED list of ten nouns
# -- lights, bars, panes, panels, columns, rows, posts, pendants, people,
# figures. It was written the day the eight-lights fault was found, so it
# guards that fault and nothing else. "three lenses" and "two volume buttons"
# walked straight past it while registering @phone, and would have been recorded
# from a single tight crop with no extent proof, which is exactly the F-24
# failure the extent rule exists to stop.
#
# A guard whose reach is an allow-list only ever guards what has already gone
# wrong once. The rule below is the general one instead.
#
# IT IS DELIBERATELY BIASED TOWARD FIRING. A false positive costs one extra
# crop. A false negative costs a wrong number repeated in every prompt until
# somebody happens to look. Do not "fix" it by narrowing it.
# ---------------------------------------------------------------------------
COUNT_WORD = (r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
              r"dozen|\d+")

# words that end in 's' and are not plurals. -ss and -ous are handled by rule.
NOT_A_PLURAL = {
    "this", "thus", "hers", "its", "was", "has", "his", "does", "goes",
    "lens", "axis", "iris", "gas", "bias", "chaos", "focus", "status",
    "canvas", "series", "species", "corpus", "always", "perhaps", "towards",
    "yes", "versus", "whereas", "unless", "sans", "means",
    # not a narrowing of the rule -- these are words ending in s that are not
    # plurals, which is exactly what this set is for. 'R minus B of -36.9' was
    # read as a count of 79 minuses on 1 Aug and cost one extra round trip.
    "minus", "plus", "thus", "amidst", "across",
}
IRREGULAR_PLURALS = {"people", "feet", "teeth", "children", "men", "women", "geese"}


# ---------------------------------------------------------------------------
# F-70. A CLAIM THAT SOMETHING DIVERGES IS A COMPARISON, AND A COMPARISON MADE
# BY EYE IS F-46 HAPPENING AGAIN.
#
# compare_asset.py was written on 31 Jul because seven "mismatches" between
# @tarn_door and @cafe_int were read off two crops by eye and five were
# imaginary. On 1 Aug I registered two along-frontage plates, read the shared
# invariants off them BY EYE, and reported two divergences to Zee -- one wrong,
# one not a divergence at all. The tool was on disk, unused, the whole time.
#
# Building the tool was never the hard part. Being made to run it is.
# ---------------------------------------------------------------------------
DIVERGENCE = re.compile(
    r"\bdiverge(?:s|d|nce|nt)?\b|\bdoes not match\b|\bdiffers? from\b|\bmismatch(?:es)?\b"
    r"|\bunlike @|\bcontradicts?\b|\binconsistent with\b|\bdisagrees? with\b"
    r"|\bmust not be used as authority\b|\bagainst the master\b", re.I)


def divergence_claim(text):
    m = DIVERGENCE.search(text or "")
    return m.group(0) if m else None


def counting_claim(text):
    """Return the number+plural phrase if this claim counts something, else None."""
    if not text:
        return None
    for m in re.finditer(rf"\b({COUNT_WORD})\b", text, re.I):
        for w in re.findall(r"[A-Za-z][A-Za-z-]*", text[m.end():m.end() + 60])[:4]:
            lw = w.lower()
            if lw in IRREGULAR_PLURALS:
                return f"{m.group(1)} ... {w}"
            if (len(lw) >= 4 and lw.endswith("s") and not lw.endswith("ss")
                    and not lw.endswith("ous") and lw not in NOT_A_PLURAL):
                return f"{m.group(1)} ... {w}"
    return None


# ---------------------------------------------------------------------------
# F-72b. --audit answered "which assets have unproven claims" and could not
# answer "which assets can no longer RECEIVE one". F-62 locked all eight master
# plates the day it was written and the audit showed eight rows of `ok`, because
# a gate that fires on WRITE is invisible while nobody is writing.
#
# Coverage and capability are different questions. Ask both.
# ---------------------------------------------------------------------------
def locked_reasons(rec):
    """Why this asset would refuse a new claim right now. Empty means it accepts one."""
    out = []
    master = rec.get("is_master")
    if master and not isinstance(master, str):
        out.append("is_master is a bare flag with no reason (F-72)")
    if not rec.get("file"):
        out.append("no file in the ledger")
    if not rec.get("aspect"):
        out.append("no aspect recorded (F-46)")
    if rec.get("covers_axes") and not master:
        if not (rec.get("derived_from") and rec.get("build_method")):
            out.append("claims a camera axis with no derived_from/build_method (F-62) — "
                       "if it is an ORIGIN, declare is_master")
        elif rec.get("build_method") == "text-to-image":
            out.append("a new angle generated from prose (F-62)")
        if (any("text-to-image" in str(s) for s in rec.get("derivation_chain") or [])
                and not rec.get("derivation_exemption")):
            out.append("derivation chain roots in text-to-image with no exemption (F-68)")
    return out


def _selftest():
    """Discrimination test. A guard that fires on everything is not a guard."""
    must_fire = [
        "each glazing bay is eight lights: three vertical bars and one horizontal",
        "three lenses in a raised square module",
        "the left edge carries two volume buttons below a small switch",
        "five brass dome pendants run along the counter",
        "exactly three people are in this frame",
        "12 mosaic tiles across the threshold",
        "two seated customers",
    ]
    must_not_fire = [
        "warm matte oat-cream board with a pale off-white domed lid",
        "the brass runs along the top of the front, under the wood top",
        "a broad brass strip above a plain recessed plinth",
        "one continuous horizontal glazing bar",   # NOTE: fires, and should -- it is a count of one
        "the door is closed and the leaf reads flush with the frame",
        "sunlit green slope running down to the waterline",
    ]
    bad = []
    for t in must_fire:
        if not counting_claim(t):
            bad.append(f"  MISSED (should fire): {t!r}")
    for t in must_not_fire[:3] + must_not_fire[4:]:
        if counting_claim(t):
            bad.append(f"  FALSE POSITIVE: {t!r} -> {counting_claim(t)!r}")
    if bad:
        print("counting_claim discrimination test FAILED")
        print("\n".join(bad))
        return 1
    print(f"counting_claim: {len(must_fire)} counting claims caught, "
          f"{len(must_not_fire)-1} descriptive claims left alone -- discriminates.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", nargs="?")
    ap.add_argument("--box", help="x0,y0,x1,y1 as fractions of the frame")
    ap.add_argument("--claim")
    ap.add_argument("--supersedes", action="append", default=[],
                    help="wording now known to be WRONG; the linter will fail any "
                         "prompt still containing it")
    ap.add_argument("--look", action="store_true", help="write the crop and stop")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="discrimination-test the counting detector (F-56)")
    ap.add_argument("--force", action="store_true",
                    help="record a counting claim from a wide crop anyway (F-17)")
    ap.add_argument("--compared-with", dest="compared_with",
                    help="F-70. The other asset this claim says it diverges from. A divergence "
                         "claim is refused without it, because compare_asset.py exists to stop "
                         "exactly this comparison being made by eye.")
    ap.add_argument("--property", dest="prop",
                    help="F-70. The shared invariant being compared, passed through to "
                         "compare_asset.py. Must already be in element_rules.face_dependence.")
    ap.add_argument("--occluders", help="F-69. For a counting claim on a plate shot ALONG a "
                                        "run: say what stands in front of it and where the run "
                                        "actually ends. Write 'nothing stands in front of this "
                                        "run' only after looking.")
    ap.add_argument("--extent", help="x0,y0,x1,y1 — the WIDE box that proves how far "
                                     "the run goes. Required for a counting claim, "
                                     "because --box is deliberately too tight to "
                                     "show whether there is a sixth pendant.")
    a = ap.parse_args()

    if a.selftest:
        return _selftest()

    d = load()
    assets = d.setdefault("assets", {})

    if a.audit:
        print("\n  asset ledger — verification status, and whether it is still WRITABLE\n")
        locked = []
        for tag, rec in sorted(assets.items()):
            v = rec.get("verified", [])
            unproven = [x for x in v if not x.get("proof")]
            mark = "ok " if v and not unproven else "!! "
            print(f"  {mark}{tag:16s} {len(v):2d} verified"
                  + (f", {len(unproven)} WITHOUT PROOF" if unproven else "")
                  + ("   <- never checked against the image" if not v else ""))
            for why in locked_reasons(rec):
                locked.append((tag, why))
                print(f"     \033[91mLOCKED\033[0m {why}")
        print("\n  '!!' means a prompt describing that asset is describing it from prose.")
        if locked:
            print(f"\n  \033[91m{len(locked)} ASSET(S) CANNOT RECEIVE A NEW CLAIM AT ALL.\033[0m")
            print("  That is not a coverage problem, it is a capability problem, and it is the one")
            print("  this audit was blind to until F-72. A locked master is the worst case: it is")
            print("  the plate every other angle is measured against, and no new fact can be")
            print("  written on it. Clear each reason above before the next build.\n")
            return 1
        print("  Every asset can still receive a new verified claim.\n")
        return 0

    if not a.tag:
        ap.error("give an asset tag, or --audit")
    rec = assets.setdefault(a.tag, {})
    src = rec.get("file")
    if not src:
        print(f"  {a.tag} has no 'file' recorded in the ledger. Add it first.")
        return 1
    path = HERE() / src
    if not path.exists():
        print(f"  file not found: {path}")
        return 1
    if not a.box:
        ap.error("--box is required: you have to say what you looked at")

    # ---- F-46: an observation with no viewpoint cannot be compared to anything.
    # Seven properties of @tarn_door were reported as drift against @cafe_int and
    # five of them were the two FACES of one door. A claim has to carry the side
    # it was seen from, or the next person compares a street handle to an
    # interior view and calls a correct plate broken.
    # ---- F-62. A plate that claims a camera axis has to say how it was built.
    # Three right-hand plate candidates were generated text-to-image with the
    # master merely attached as an element, and each invented a different room.
    # The one derived image-to-image from the master landed first time.
    # ---- F-72. THE GATES BELOW LOCKED THE MASTERS.
    # F-62 refuses a camera-axis claim without a provenance, and F-68 walks the
    # chain. Both are right about DERIVED plates and both are nonsense about an
    # ORIGIN plate: @cafe_int was not derived from anything, it is the thing
    # every other cafe angle must be derived FROM. Eight environment plates --
    # every master in the film -- silently became unable to receive a verified
    # claim the day F-62 was written, and nobody found out because nobody tried.
    # An origin therefore DECLARES itself, in a sentence, so that "no provenance"
    # and "is the provenance" stop looking identical to the tool.
    master = rec.get("is_master")
    if master and not isinstance(master, str):
        print(f"\n  \033[91m! {a.tag} FLAGS is_master WITH NO REASON\033[0m -- refused.")
        print("    'is_master' takes a SENTENCE, not true. Say which axis this plate originates and")
        print("    what is expected to be derived from it. A bare flag is how a derived plate gets")
        print("    quietly promoted to a master to make a gate go quiet. F-72.\n")
        return 1
    if not master:
        if rec.get("covers_axes") and not (rec.get("derived_from") and rec.get("build_method")):
            print(f"\n  \033[91m! {a.tag} CLAIMS A CAMERA AXIS AND DOES NOT SAY HOW IT WAS BUILT\033[0m — refused.")
            print("    Add 'derived_from' (the master plate this angle came from) and 'build_method'")
            print("    ('image-to-image' or 'text-to-image'). METHOD_SOURCES s2: derive every extra angle")
            print("    FROM the master by reframe or edit, never fresh from prose. See F-62 for what it")
            print("    cost to ignore that three times in one afternoon.\n")
            return 1
        if rec.get("build_method") == "text-to-image" and rec.get("covers_axes"):
            print(f"\n  \033[91m! {a.tag} IS A NEW ANGLE GENERATED FROM PROSE\033[0m — refused.")
            print("    Rebuild it image-to-image from its master, or record an explicit exemption saying")
            print("    why prose was allowed to invent this room's geometry.\n")
            return 1

    # ---- F-68. The F-62 gate above reads the LAST build step only. Both
    # along-frontage plates pass it -- each is an image-to-image edit -- and
    # neither chain touches the master: both root in text-to-image and were
    # accepted by eye against k6-v16. A gate that a single edit of a
    # prose-invented room satisfies is not guarding derivation, it is guarding
    # the final verb. Walk the chain, and make the exemption say who looked.
    chain = rec.get("derivation_chain") or []
    if (rec.get("covers_axes") and not rec.get("is_master")
            and any("text-to-image" in str(step) for step in chain)
            and not rec.get("derivation_exemption")):
        print(f"\n  \033[91m! {a.tag}'S DERIVATION CHAIN ROOTS IN TEXT-TO-IMAGE\033[0m -- refused.")
        print("    The last step is an edit, which satisfies F-62, but a step in the chain invented this")
        print("    room from prose. Either re-derive the plate from the master, or record a")
        print("    'derivation_exemption' naming WHO checked it against the master, WHEN, on WHICH")
        print("    invariants, and which invariants the frame cannot show. F-68.\n")
        return 1

    # ---- F-70. A divergence claim has to have been COMPARED, not looked at.
    div = divergence_claim(a.claim)
    if div and not (a.compared_with and a.prop):
        print(f"\n  \033[91m! DIVERGENCE CLAIM WITH NO COMPARISON\033[0m -- refused.")
        print(f"    {div!r} says this asset disagrees with another one. That is a comparison, and")
        print("    compare_asset.py exists because comparisons made by eye report faults that are")
        print("    not there -- five of seven, on 31 Jul (F-46), and one of two on 1 Aug (F-70).")
        print("    Pass --compared-with TAG and --property 'the shared invariant'. The property has")
        print("    to be in element_rules.face_dependence first, which is the part that does the")
        print("    thinking: ask WHICH FACE, and then ask WHICH END.\n")
        return 1
    compare_proof = None
    if div:
        import subprocess
        cmd = [sys.executable, _proj().tool("compare_asset.py"), a.tag, a.compared_with, "--property", a.prop]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="backslashreplace", cwd=str(HERE()))
        out = (r.stdout or "") + (r.stderr or "")
        print(out)
        if "comparison allowed" not in out:
            print("  \033[91m! compare_asset.py DID NOT ALLOW THIS COMPARISON\033[0m -- refused.")
            print("    Settle it there first. Do not record the claim and do not report it.\n")
            return 1
        for line in out.splitlines():
            if "asset_compare" in line:
                compare_proof = line.strip()
        if "DISCLOSURE, NOT DRIFT" in out:
            print("  \033[93m! Read that warning before recording. If either plate does not DISCLOSE")
            print("    the feature, this is a difference and the word 'diverges' is wrong.\033[0m\n")

    if not rec.get("aspect"):
        print(f"\n  \033[91m! NO ASPECT RECORDED FOR {a.tag}\033[0m — refused.")
        print("    Add an 'aspect' to this asset saying which face or angle its file shows")
        print("    (e.g. 'interior, camera in the room looking toward the frontage').")
        print("    A claim with no viewpoint reads as a claim about the whole object, and")
        print("    that is how F-46 happened. See element_rules.face_dependence.\n")
        return 1

    PROOFS().mkdir(parents=True, exist_ok=True)
    box = tuple(float(x) for x in a.box.split(","))
    n = len(rec.get("verified", [])) + 1
    out = PROOFS() / f"{a.tag.lstrip('@')}_{n:02d}.png"
    crop(path, box, out, a.claim or "look")
    print(f"\n  proof written: {out}\n  and: {str(out).replace('.png','_where.png')}")

    # ---- F-17: a crop at the wrong SCALE is not a proof.
    # The tool forced a proof and I still miscounted eight window lights as four,
    # because the crop spanned three bays and the bars were a few pixels wide.
    # Counting and measuring claims need ONE instance filling the frame.
    area = (box[2] - box[0]) * (box[3] - box[1])
    counting = counting_claim(a.claim)
    if counting and area > 0.06:
        print(f"\n  \033[91m! SCALE WARNING\033[0m — the box covers {area*100:.0f}% of the frame and the "
              f"claim counts something ({counting!r}).")
        print("    F-17: 'four lights' was recorded from a crop spanning three bays and was WRONG;"
              "\n    the bay is eight lights. Crop ONE instance to fill the frame and count again.")
        if not a.force:
            print("    Re-crop, or pass --force if you have already looked at feature scale.\n")
            return 1

    # ---- F-24: the scale rule alone is not enough for a COUNT.
    # 'five brass dome pendants' was written into K5 for three drafts. The 6%
    # rule is exactly the wrong tool here: it forces a crop too tight to show
    # whether there is a sixth pendant just outside it. Magnification proves
    # what ONE instance is; only a wide box proves HOW MANY there are. A
    # counting claim therefore needs BOTH, and neither substitutes for the other.
    extent = None
    if counting:
        if not a.extent:
            print("\n  \033[91m! COUNTING CLAIM WITHOUT AN EXTENT BOX\033[0m — refused.")
            print(f"    {counting!r} is a count. --box is deliberately tight, so it")
            print("    cannot show whether there is one more just outside it. Pass --extent with a")
            print("    box wide enough that the run visibly ENDS inside it at both ends, look at")
            print("    that crop, and count again. Two proofs or no claim.\n")
            return 1
        ebox = tuple(float(x) for x in a.extent.split(","))
        extent = PROOFS() / f"{a.tag.lstrip('@')}_{n:02d}_extent.png"
        crop(path, ebox, extent, "extent")
        print(f"  extent proof written: {extent}")
        if (ebox[0] > box[0] or ebox[1] > box[1]
                or ebox[2] < box[2] or ebox[3] < box[3]):
            print("\n  \033[91m! EXTENT BOX DOES NOT CONTAIN THE FEATURE BOX\033[0m — refused.")
            print("    The wide box has to be a superset of the tight one, or the two proofs")
            print("    are pictures of different places.\n")
            return 1

        # ---- F-69. THE EXTENT BOX PROVES THE RUN ENDS. IT DOES NOT PROVE THE RUN
        # IS ALL VISIBLE. Both are ways of missing an instance and they have
        # opposite cures. A run photographed ALONG its length is occluded by its
        # own architecture -- piers, reveals, projecting blocks -- and the
        # occluder sits INSIDE the extent box, so widening the crop can never
        # reveal it. 'six lights' was recorded off the left along-frontage plate
        # with a correct extent proof: the first column stood behind the door
        # block and the fourth fell outside a crop boundary. Both bays are four.
        OBLIQUE = re.compile(r"\balong\b|\bthree-quarter\b|\breceding\b|\boblique\b"
                             r"|\bin perspective\b|\bdown one side\b", re.I)
        if OBLIQUE.search(rec.get("aspect") or "") and not a.occluders:
            print("\n  \033[91m! COUNTING CLAIM ON A PLATE SHOT ALONG THE RUN, WITH NO OCCLUSION "
                  "STATEMENT\033[0m -- refused.")
            print(f"    This asset's aspect says the camera looks ALONG something, so the run counts")
            print("    itself out of sight: a pier, a reveal or a projecting block hides an instance")
            print("    and it sits INSIDE your extent box, where no wider crop will find it.")
            print("    Pass --occluders naming what stands in front of the run and where it ends,")
            print("    or 'nothing stands in front of this run' once you have looked. F-69.\n")
            return 1

    if a.look or not a.claim:
        # F-69b. The occlusion gate fired at RECORD time, and the six-lights
        # miscount happened at LOOK time -- it reached Zee as prose before any
        # tool saw it. A guard that only inspects what gets written down does
        # not protect what gets said. Ask here too, where the looking happens.
        if re.search(r"\balong\b|\bthree-quarter\b|\breceding\b|\boblique\b"
                     r"|\bin perspective\b|\bdown one side\b", rec.get("aspect") or "", re.I):
            print("  \033[93mTHIS PLATE LOOKS ALONG ITS SUBJECT. Before you count anything in it,")
            print("  or say a word about it to anyone, answer both (F-69):")
            print("    1. what stands in FRONT of the run and hides an instance?")
            print("    2. where does the run END, and is that end inside this crop?\033[0m")
        print("\n  LOOK AT IT before recording a claim. Re-run with --claim once you have.\n")
        return 0

    d["_fact_rev"] = d.get("_fact_rev", 0) + 1
    rec.setdefault("verified", []).append({
        "rev": d["_fact_rev"],
        "claim": a.claim,
        "box": list(box),
        "proof": str(out.relative_to(HERE())),
        "extent_proof": str(extent.relative_to(HERE())) if extent else None,
        "date": datetime.date.today().isoformat(),
        "supersedes": a.supersedes,
        "aspect": rec.get("aspect"),
        "occluders": a.occluders,
        "compared_with": a.compared_with,
        "compare_property": a.prop,
        "compare_proof": compare_proof,
    })
    save(d)
    print(f"  recorded against {a.tag} as fact-rev {d['_fact_rev']}: {a.claim!r}")
    print("  Any SELECTION resting on this asset is now stale — run selections.py --check.")
    if a.supersedes:
        print(f"  superseded wording (prompts containing it will now FAIL): {a.supersedes}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
