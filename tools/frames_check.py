#!/usr/bin/env python3
"""
TARN conditioning-frame check, with mandatory proof.

WHY THIS EXISTS — the fault it is built to make impossible
---------------------------------------------------------
G3 v3 (`cde23ba5`) was fired with `k5-23` as start_image and `k6-2_MS` as
end_image. The prompt said a warm edge builds along the back of his neck from
2.2s. It never built — because it was already there in frame 0, and it was
already there because the start frame had it baked in.

    k5-23    rim-on-dark 0.24%      ver3 @ 0.04s   0.23%   <- inherited
    k6-2_MS  rim-on-dark 0.05%      ver3 @ 2.2s    0.17%
                                    ver3 @ 4.0s    0.08%   <- declining, not building

`k5-23` failed its own prompt, whose LIGHT block ends "Nothing warm touches him"
— a negation, buried at the end of a paragraph, against Lesson 2. Nothing gated
it. It cost a 54-credit generation.

THE RULE THIS TOOL ENFORCES
    A property the prompt says CHANGES across a shot must differ between the two
    conditioning frames, in the direction the prompt claims, by a margin big
    enough to survive the model. Measure both frames. Never one.

WHY THE OBVIOUS METRIC IS WRONG — read this before changing the mask
--------------------------------------------------------------------
The first version of this file used a plain "warm and bright" mask. The proof
image showed it was lighting up his FACE AND HANDS. Skin is red-over-green-over-
blue and bright, so a warm-pixel mask is largely a skin detector, and any shot
where the hero turns his back reads as "the light left him" when nothing of the
kind happened. That mask said ver3's light collapsed from 1.0% to 0.11% at 9s;
almost all of that was his face leaving frame.

This is the failure `measure.py` exists to prevent, reproduced inside the tool
written to prevent it. It was caught only by opening the proof image.

So the metric here is RIM-ON-DARK: warm pixels whose local neighbourhood is dark
(21px box mean luminance < 95). A rim rides the edge of hair, a shoulder, a
jacket — dark things. A lit face sits in a bright field and is excluded. On the
same four keyframes this separates cleanly:

    k5-23 warm 1.06 -> rim 0.24     k6-1     warm 0.41 -> rim 0.19
    k5-2  warm 0.55 -> rim 0.22     k6-2_MS  warm 0.29 -> rim 0.05

Room-wide warmth is a SEPARATE question and gets its own number (`rb_neutral`),
because "the room swung cool" and "no warm bounce reached him" are different
findings with different fixes.

Usage
  python3 frames_check.py IMAGE --role start
  python3 frames_check.py START END --pair --expect warmer
  python3 frames_check.py CLIP.mp4 --video
"""
import argparse, pathlib, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw
import _utf8  # noqa: F401  — the stream hardening, which _project used to bring

# FK-34. _project IS IMPORTED LAZILY, INSIDE THE FUNCTIONS THAT NEED A FILM.
#
# It used to be `import _project as P` at module scope with `PROOFS = P.DIR /
# "proofs"` under it, so the module could not load outside a film -- and
# `--selftest`, which builds its own throwaway film for its subprocesses and
# needs none itself, died before reaching its first case. `verify.py` ran it
# with cwd=film, inside a section headed "SELFTESTS THAT NEED NO FILM", so the
# one harness that would have caught it was configured not to.
#
# `bin/filmkit-promote` already carries this pattern with a comment explaining
# it. I did not follow it here.
_PROOFS = None


def proofs():
    """The film's proofs directory, resolved on FIRST USE rather than at import."""
    global _PROOFS
    if _PROOFS is None:
        import _project as P  # FK1: where the film is
        _PROOFS = P.DIR / "proofs"
    return _PROOFS

# Thresholds measured on the four G3 keyframes and on draft 1, whose opening
# carries no rim at all (0.03). Sources in TARN_FINDINGS.md, finding F-01.
# The START gate moved from frame-wide to HEAD-BOX on 30 Jul, and the reason is
# written here rather than quietly applied — a gate changed without a stated
# reason is finding F-07 all over again.
#
# k5-24 came back at 0.18 frame-wide (over the old 0.10 ceiling) but 0.05 in the
# head box. The proof image settles it: the counted rim is almost entirely the
# BRASS COUNTER END FACE, which the prompt explicitly requires as "a wide band of
# dull warm metal", plus the pendant bulbs. Both are meant to be warm. Gating on
# the whole frame therefore fails a frame for containing the props it was asked
# to contain.
#
# The claim being tested is "no warm light on the man", so the measurement must
# be on the man. Head-box only. Frame-wide is still reported, as context.
#
#   k5-23  head-box 0.53   FAIL      k6-2_MS  head-box 0.04   FAIL
#   k5-24  head-box 0.05   PASS      k6-3     head-box 0.15   PASS
# START CEILING RAISED 0.10 -> 0.30 on Zee's call, 30 Jul, and the reason matters.
# 0.10 came from k5-24, the ONLY frame ever to reach it — and k5-24 turned out to
# be asset-wrong and colder overall (R-B +4.5) than the room should be. A ceiling
# derived from one unrepresentative frame is the four-table gate all over again.
#
# @cafe_int has LIT TUNGSTEN PENDANTS overhead. Overhead tungsten putting a modest
# warm glow on someone's hair is physically CORRECT, not a fault. What is a fault
# is a strong rim, and the numbers separate cleanly:
#
#   too warm:  k5-23 0.53   k5-26 0.52   k5-28 0.45
#   honest:    k5-29 0.22   k5-24 0.05
#
# So the ceiling is 0.30, and the load-bearing test moves to the PAIR: the end
# must exceed the start by 0.10, measured on him. A start at 0.22 is fine provided
# the end reaches ~0.32.
ROLE_GATES = {
    # The GOLDEN-rim measure survives for the start frame only, and only as a
    # warning. Its job there is real: catch tungsten or an early warm edge
    # spilling onto a man who is supposed to be cold. k5-23 0.53 and k5-28 0.45
    # are genuine faults on it.
    "start": dict(warm_soft_max=0.30, rim_rb_min=0.0,
                  note="grey morning. The rim on him must be WARM-LEANING (rim R-B >= 0): "
                       "tungsten room, no sky on him yet. k5-29 +7.6 and k5-30 +3.5 pass. "
                       "The golden-rim area is a warning only — 0.30 catches k5-23 (0.53) "
                       "and k5-28 (0.45); k5-30's 0.36 is tungsten on the crown of his hair, "
                       "which is physically correct."),
    # The end gate used to be head_min=0.32 on that same golden measure. It was
    # UNSATISFIABLE and is gone. See F-28 below: @cafe_sun's own light source
    # measures R-B +1.7 and its near-glass surfaces are the COOLEST in the room.
    "end":   dict(rim_rb_max=-10.0,
                  note="mountain light. The rim on him must be COOL (rim R-B <= -10): near the "
                       "glass this room is lit by open sky, which is bright and blue-leaning. "
                       "k6-3 -15.4, k6-4 -15.1, k6-5 -20.0 all pass. Nothing here is gated on "
                       "warmth, because there is no warm light at that end of the room."),
}
MIN_PAIR_DELTA = 0.10          # percentage points of rim-on-dark

HEAD_BOX = (0.20, 0.02, 0.55, 0.50)   # generous; catches a person, does not segment one


# ---------------------------------------------------------------- F-28
# THE RIM'S COLOUR IS THE MEASUREMENT. ITS WARMTH IS AN ASSUMPTION.
#
# `masks()` below tests (R-B)>45 AND R>G+12 — a GOLDEN rim. That was derived for
# the START frame, where the fault to catch was tungsten spilling onto a man who
# is supposed to be cold, and it is right for that job.
#
# It was then reused unchanged as the END gate, on the assumption that the end
# light is the same colour as the light being rejected. It is not. Measured on
# @cafe_sun itself:
#
#     the sunlit grass slope, i.e. THE SOURCE      R-B  +1.7   G-B  +2.4
#     white brick over the frontage                R-B -20.9   (bright, 216)
#     mosaic floor: near the glass  R-B +13.8  ->  nearest camera  R-B +22.4
#
# The source is neutral, the near-glass surfaces are the COOLEST and brightest
# in the room, and warmth increases with distance FROM the window. The sun is
# high and behind the building, so what floods the near-glass zone is open sky.
# There is no warm pool by the glazing to stand in.
#
# So the end gate demanded R-B>45 from a light measuring R-B +1.7. It was not a
# hard gate, it was an unsatisfiable one, and k6-3 0.15 / k6-4 0.04 / k6-5 0.06
# were never measuring the payoff — they were measuring stray tungsten and skin.
# This is F-02 again: a mask that cannot see the thing it is pointed at.
#
# Measure the rim WITHOUT assuming a colour, then read its colour off:
#
#     frame     rim area   rim R-B          frame     rim area   rim R-B
#     k5-29       1.51%      +7.6            k6-3       3.22%     -15.4
#     k5-30       1.64%      +3.5            k6-4       2.82%     -15.1
#                                            k6-5       2.52%     -20.0
#
# The transition is large, clean and correctly signed — it just runs WARM to
# COOL, which is what this room does. Gate the SWING, not the warmth.

RIM_SWING_MIN = 15.0     # k5-30 -> k6-5 is -23.5. Two start frames differ by 4.1.

# FK-30. WHICH BOX THAT NUMBER WAS DERIVED ON, because it is not a property of
# the light -- it is a property of the light AND the region it was read from.
# Every reading behind RIM_SWING_MIN was taken on HEAD_BOX, and FK-29 showed
# what HEAD_BOX contains at the window end: a shopfront. So a swing measured
# inside a subject box CANNOT be compared with it. Doing so compares two
# different quantities and calls the difference a verdict, which is the exact
# fault this project keeps paying for.
RIM_SWING_DERIVED_ON = "the default head box"

# FK-27. The direction is NOT the caller's to choose, and `--expect` used to
# accept it as though it were — then read it nowhere. The operator ran the
# documented command with `--expect warmer`, this gate measured a swing of
# -24.3 against a threshold requiring <= -15.0, and printed PASS. He asked for
# one direction and was certified green on its opposite, with no line of output
# naming which one had been tested.
#
# The direction is a MEASURED property of the room (the table above, and F-28):
# there is no golden light at the window end, so a warm-swing gate here is not
# merely wrong, it is unsatisfiable. The flag therefore stays — it documents the
# assumption and gives a caller somewhere to disagree — but it can only AGREE or
# REFUSE. It can never redirect, and it can never be silently discarded.
GATE_DIRECTION = "cooler"


def rim_chroma(arr, box, proof_name=None):
    """Lit edges on a dark surround inside `box`, and what colour they are.

    FK-28 — AND THIS ONE HAS A PROOF NOW, BECAUSE IT IS THE NUMBER THAT GATES.

    `measure()` writes `<name>_rimmask.png` and it draws `masks()`: the GOLDEN
    rim, the metric the pair block itself labels "context only — NOT a gate, see
    F-28". The number the pair gate actually decides on is this one, and it had
    no proof image at all. So the tool ended every run with "PASS — now open the
    proof image", and the picture it sent you to was of a different mask.

    That is F-02 — *a mask that cannot see the thing it is pointed at* — inside
    the tool written to prevent it, for the second time. The docstring above
    records the first. The difference is that the first was a wrong mask and
    this was a missing picture, which is harder to notice, because the operator
    does what he was told, looks at a real proof, and reports honestly on it.

    What the picture must show, and why it is coloured this way: this mask is
    COLOUR-AGNOSTIC by design (F-28 — gate the swing, not the warmth), so it
    will happily count a bright window edge against a dark mullion. Painting
    warm-leaning and cool-leaning lit pixels differently is the only way to see
    whether the R-B being reported came off a person or off the architecture.
    """
    H, W, _ = arr.shape
    x0, y0, x1, y1 = int(box[0]*W), int(box[1]*H), int(box[2]*W), int(box[3]*H)
    p = arr[y0:y1, x0:x1].astype(np.float32)
    R, B, L = p[..., 0], p[..., 2], p.mean(2)
    nb = cv2.GaussianBlur(L, (21, 21), 0)
    lit = (L > nb + 8) & (nb < 95) & (L > 60)
    if lit.sum() < 200:
        return None
    # FK-29. HOW FAR THE COUNTED PIXELS ARE SPREAD, reported and NOT gated.
    # A rim on a person is a compact thing in one part of the box. A glazing
    # grid runs edge to edge. On this film's end frame the counted mask spanned
    # essentially every column of the crop, which is a window and not a man --
    # and the tool called its mean "rim colour on him". No threshold is set
    # here, because I have no corpus to set one from and inventing a number is
    # how the old end gate came to demand R-B>45 from a light measuring +1.7.
    # This is a number for a person to read next to a picture.
    # FK-33. THE MEAN WAS SUMMARISING TWO POPULATIONS.
    #
    # Measured off the operator's own proof overlay, 6 Aug, inside a box drawn
    # round the man: the counted pixels are not one rim with one colour. They
    # are a WARM rim on his hair, from the room's own light above and behind
    # him, and a COOL edge along his shoulders, from the window. Two lights, two
    # parts of one man. A single mean R-B falls between them and describes
    # NEITHER -- and it made the film's own LIGHT block and POSITIVE LOCKS read
    # as a contradiction when both were true of different parts of the frame.
    #
    # So the two populations are reported separately, always, with their shares.
    # No threshold decides when to say so, because a threshold is the thing I
    # keep inventing and having to retract (FK-29, FK-30). The numbers are
    # printed; the reader sees whether it is bimodal.
    rb_px = (R - B)
    warm = lit & (rb_px >= 0)
    cool = lit & (rb_px < 0)
    n = float(lit.sum())
    # WHERE each population sits, as a fraction of the box's width. This is a
    # SPATIAL PROXY and is labelled as one: in the origin film's end frame the
    # cool pixels are the door stiles and glazing bars at both edges of the box
    # while the man is in the middle. It is not a subject test -- FK-30 is the
    # finding about a positional number whose helper line claimed more than it
    # measured, and this one says what it is.
    bw = lit.shape[1]
    def _cx(m):
        return float(np.where(m)[1].mean()) / max(bw - 1, 1) if m.any() else float("nan")
    def _edge(m):
        if not m.any():
            return float("nan")
        c = np.where(m)[1]
        return 100.0 * float(((c < bw / 3) | (c > 2 * bw / 3)).mean())
    res = dict(area=100*float(lit.mean()), rb=float(rb_px[lit].mean()),
               lum=float(L[lit].mean()),
               span_x=100*float((lit.any(axis=0)).mean()),
               span_y=100*float((lit.any(axis=1)).mean()),
               warm_pct=100*float(warm.sum())/n, cool_pct=100*float(cool.sum())/n,
               rb_warm=float(rb_px[warm].mean()) if warm.any() else float("nan"),
               rb_cool=float(rb_px[cool].mean()) if cool.any() else float("nan"),
               warm_cx=_cx(warm), cool_cx=_cx(cool),
               warm_edge=_edge(warm), cool_edge=_edge(cool))
    if proof_name:
        _p = proofs()
        _p.mkdir(exist_ok=True)
        over = (arr * 0.30).astype(np.uint8)
        sub = over[y0:y1, x0:x1]
        rb_px = (R - B)
        sub[lit & (rb_px >= 0)] = (255, 150, 0)      # warm-leaning, counted
        sub[lit & (rb_px < 0)] = (0, 150, 255)       # cool-leaning, counted
        over[y0:y1, x0:x1] = sub
        im = Image.fromarray(over)
        ImageDraw.Draw(im).rectangle([x0, y0, x1, y1], outline=(60, 255, 60), width=3)
        out = _p / f"{proof_name}_rimchroma.png"
        im.save(out)
        res["proof"] = str(out)
    return res


def masks(arr):
    """Return (warm, rim_on_dark). See the docstring for why the second exists."""
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    warm = ((R - B) > 45) & (R > G + 12) & (L > 110)
    neighbourhood = cv2.blur(L, (21, 21))
    return warm, warm & (neighbourhood < 95)


def neutral_rb(arr):
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    sat = arr.max(axis=2) - arr.min(axis=2)
    m = (sat < 26) & (L > 70) & (L < 200)
    if m.sum() < 500:
        return float("nan"), 0
    return float(R[m].mean() - B[m].mean()), int(m.sum())


def load(path, width=640):
    im = Image.open(path).convert("RGB")
    im = im.resize((width, max(1, int(width * im.size[1] / im.size[0]))), Image.LANCZOS)
    return im, np.asarray(im).astype(np.float32)


def measure(path, label=None):
    im, arr = load(path)
    W, H = im.size
    warm, rim = masks(arr)
    x0, y0, x1, y1 = HEAD_BOX
    rbox = rim[int(H * y0):int(H * y1), int(W * x0):int(W * x1)]
    rb, npx = neutral_rb(arr)
    L = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    res = dict(path=str(path),
               warm_pct=100 * warm.mean(),
               rim_pct=100 * rim.mean(),
               rim_headbox_pct=100 * rbox.mean(),
               skin_share=100 * (warm.sum() - rim.sum()) / max(warm.sum(), 1),
               rb_neutral=rb, neutral_px=npx, lum_mean=float(L.mean()))
    # PROOF — magenta is the rim actually counted, dim cyan is what was DISCARDED
    # as skin or bright-field. Seeing the discard is the whole point.
    _p = proofs()
    _p.mkdir(exist_ok=True)
    over = (arr * 0.30).astype(np.uint8)
    over[warm & ~rim] = (0, 110, 130)
    over[rim] = (255, 0, 200)
    p = Image.fromarray(over)
    ImageDraw.Draw(p).rectangle([W * x0, H * y0, W * x1, H * y1],
                                outline=(60, 255, 60), width=3)
    name = label or pathlib.Path(path).stem
    out = _p / f"{name}_rimmask.png"
    p.save(out)
    res["proof"] = str(out)
    return res


def show(r):
    print(f"\n  {pathlib.Path(r['path']).name}")
    print(f"    RIM-ON-DARK  frame {r['rim_pct']:5.2f}%   head-box {r['rim_headbox_pct']:5.2f}%")
    print(f"    (raw warm {r['warm_pct']:5.2f}%, of which {r['skin_share']:.0f}% discarded as "
          f"skin / bright field — magenta is counted, cyan is discarded)")
    print(f"    R-B neutral {r['rb_neutral']:+6.1f} on {r['neutral_px']/1000:.0f}k px"
          f"   ·  mean lum {r['lum_mean']:5.1f}")
    print(f"    proof: {r['proof']}")


def video_curve(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    i, rows = 0, []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        a = cv2.cvtColor(cv2.resize(f, (640, 360)), cv2.COLOR_BGR2RGB).astype(np.float32)
        _, rim = masks(a)
        R, G, B = a[..., 0], a[..., 1], a[..., 2]
        L = 0.2126 * R + 0.7152 * G + 0.0722 * B
        sat = a.max(axis=2) - a.min(axis=2)
        m = (sat < 26) & (L > 70) & (L < 200)
        rb = float(R[m].mean() - B[m].mean()) if m.sum() > 500 else float("nan")
        rows.append((i / fps, 100 * rim.mean(), float(L.mean()), rb))
        i += 1
    cap.release()
    a = np.array(rows)
    print(f"\n  {pathlib.Path(path).name} — rim-on-dark %, frame luminance, room R-B\n")
    for j in range(0, len(a), max(1, int(fps / 2))):
        print(f"    {a[j,0]:5.2f}s  rim {a[j,1]:5.2f}%  lum {a[j,2]:5.1f}  R-B {a[j,3]:+6.1f}  "
              + "+" * int(a[j, 1] * 40))
    print("\n    Read the ROOM luminance and R-B alongside the rim. A rim number that "
          "\n    falls while the subject turns away is a framing artefact, not a light change.")
    return a


def selftest():
    """FK-27 — `--expect` may agree or refuse. It may never be ignored.

    The fault this replaces: the flag was declared, printed in the usage block,
    passed by the operator as `warmer`, and read nowhere. The gate tested a COOL
    swing, measured -24.3 against a threshold of <= -15.0, and printed PASS.

    Case 3 is the one that matters and it is the discrimination control: the
    refusal must arrive on paths that DO NOT EXIST. A tool that opens the images
    first and argues afterwards has already put numbers on the screen answering
    a question nobody asked, and the numbers are the part people remember.
    """
    import json, subprocess, tempfile
    ok = True
    print("\n  FK-27/28/29 — the flag agrees or refuses · the gated mask has a proof ·\n"
          "                the verdict names its scope\n")
    wrong = "warmer" if GATE_DIRECTION == "cooler" else "cooler"
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d)
        # A film, because `_project` refuses to resolve without one — and the
        # FIRST version of this selftest ran without it, so every subprocess
        # died at import with "no film found", four cases failed for a reason
        # that had nothing to do with the rule, and the fifth PASSED because its
        # assertion was "REFUSED not in output" and a crash contains no such
        # word. A negative assertion passes on a process that never started.
        (p / "film_facts.json").write_text(json.dumps({
            "_fact_rev": 1, "assets": {}, "selections": {},
            "_files": {"prompts": "P.md", "findings": "F.md", "script": "S.md",
                       "selftest": "G.md", "checklist": "C.md", "run_record": "R.md",
                       "workflow": "W.md", "live_docs": [], "regression_globs": []}}),
            encoding="utf-8")
        # two frames that differ, so the runs that get PAST the direction guard
        # have something real to measure and cannot pass by reading nothing
        # The lit edges must land inside HEAD_BOX and there must be enough of
        # them: rim_chroma returns None under 200 lit pixels, and a rim is only
        # "lit" where it exceeds its own 21px neighbourhood by 8 — so one broad
        # stripe raises its own surround and mostly cancels itself. Several thin
        # ones do not. A first attempt at 8px x 50 produced 50 lit pixels and
        # None; these produce ~1100.
        for name, rim in (("a.png", (215, 165, 110)), ("b.png", (110, 160, 220))):
            arr = np.full((200, 200, 3), 18, dtype=np.uint8)
            for i in range(3):
                arr[6:101, 60 + i * 10:64 + i * 10] = rim
            Image.fromarray(arr).save(p / name)
        # FK-33. A frame carrying BOTH populations, which is the whole case the
        # split exists for -- warm stripes and cool stripes in one box, so the
        # mean lands between them and describes neither. Without this the split
        # would be tested only on frames where one share is 100% and the other
        # is 0, which is the arrangement that cannot tell a split from a mean.
        arr = np.full((200, 200, 3), 18, dtype=np.uint8)
        for i in range(3):
            arr[6:101, 60 + i * 10:64 + i * 10] = (215, 165, 110)
        for i in range(3):
            arr[6:101, 100 + i * 10:104 + i * 10] = (110, 160, 220)
        Image.fromarray(arr).save(p / "mixed.png")

        def run(args):
            r = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve())] + args,
                               capture_output=True, text=True, encoding="utf-8",
                               errors="backslashreplace", cwd=str(p), timeout=180)
            return r.stdout + r.stderr, r.returncode

        cases = [
            (f"--expect {wrong} is REFUSED, not obeyed and not ignored",
             [str(p / "a.png"), str(p / "b.png"), "--pair", "--expect", wrong],
             lambda o, rc: "REFUSED" in o and rc == 2),
            (f"--expect {GATE_DIRECTION} agrees and the run proceeds",
             [str(p / "a.png"), str(p / "b.png"), "--pair", "--expect", GATE_DIRECTION],
             lambda o, rc: "REFUSED" not in o and "rim colour IN BOX" in o),
            ("the refusal arrives BEFORE the images are opened",
             [str(p / "nope.png"), str(p / "gone.png"), "--pair", "--expect", wrong],
             lambda o, rc: "REFUSED" in o and rc == 2 and "rim colour IN BOX" not in o),
            ("default auto runs, and says which direction it gated",
             [str(p / "a.png"), str(p / "b.png"), "--pair"],
             lambda o, rc: f"gating a {GATE_DIRECTION.upper()} swing" in o),
            # Without this one the whole set would pass on a tool that refused
            # everything, which is the cheapest way to look strict.
            ("...and a non-pair run is not refused for a direction it never gates",
             [str(p / "a.png")],
             lambda o, rc: "REFUSED" not in o),
            # FK-28. The gated mask must write its OWN proof, and the run must
            # send the operator to it rather than to the golden-rim picture that
            # decides nothing.
            ("the gated mask writes a proof, and the run names it",
             [str(p / "a.png"), str(p / "b.png"), "--pair"],
             lambda o, rc: "_rimchroma" in o and (p / "proofs" / "a_rimchroma.png").exists()
                           and (p / "proofs" / "b_rimchroma.png").exists()),
            # FK-29. The verdict must name its scope, and the box must be
            # nameable. The pair below is the whole point: the SAME command
            # says something different about what it measured depending on
            # whether anybody told it where the subject is.
            ("with no --subject the verdict says it measured a REGION, not a person",
             [str(p / "a.png"), str(p / "b.png"), "--pair"],
             # NB: assert on the SCOPE block, which prints on FAIL as well as
             # on PASS. The first version of this case also required the words
             # from the PASS line, so it failed on a run that was FAILING for an
             # unrelated reason -- a test that only holds when everything else
             # is green tells you nothing on the day you need it.
             lambda o, rc: "SCOPE: the DEFAULT head box" in o
                           and "about a REGION and not" in o),
            ("with --subject it says so, and drops the warning",
             [str(p / "a.png"), str(p / "b.png"), "--pair",
              "--subject", "0.25,0.02,0.45,0.55"],
             lambda o, rc: "SCOPE: the DEFAULT" not in o),
            ("--subject actually moves the box, it is not decoration",
             [str(p / "a.png"), str(p / "b.png"), "--pair",
              "--subject", "0.25,0.02,0.45,0.55"],
             lambda o, rc: "30% x  90%" in o),
            ("a reversed --subject box is refused, not silently normalised",
             [str(p / "a.png"), str(p / "b.png"), "--pair", "--subject", "0.9,0.1,0.2,0.5"],
             lambda o, rc: "must be X0,Y0,X1,Y1" in o and rc == 2),
            ("the wrong NUMBER of --subject boxes is refused",
             [str(p / "a.png"), str(p / "b.png"), "--pair",
              "--subject", "0.2,0.1,0.4,0.5", "--subject", "0.2,0.1,0.4,0.5",
              "--subject", "0.2,0.1,0.4,0.5"],
             lambda o, rc: "Give one per image" in o and rc == 2),
            ("...and one box for all images is allowed",
             [str(p / "a.png"), str(p / "b.png"), "--pair", "--subject", "0.25,0.02,0.45,0.55"],
             lambda o, rc: rc == 3 and "Give one per image" not in o),
            # FK-30. A subject-box run must REFUSE a verdict, because the
            # threshold it would be judged against was derived on a different
            # region. The control below is the one that matters: the SAME
            # frames with no --subject must still reach a real verdict, or this
            # rule is just "refuse whenever anything is specified".
            ("a subject-box run refuses a verdict and says why",
             [str(p / "a.png"), str(p / "b.png"), "--pair", "--subject", "0.25,0.02,0.45,0.55"],
             lambda o, rc: "UNCALIBRATED — no verdict" in o and rc == 3),
            ("...and the same frames with no --subject still reach one",
             [str(p / "a.png"), str(p / "b.png"), "--pair"],
             lambda o, rc: "UNCALIBRATED" not in o and rc in (0, 1)),
            # FK-33. The mean was summarising two populations. On the origin
            # film that is a warm rim on his hair and a cool edge on his
            # shoulders -- two lights, two parts of one man -- and averaging
            # them made the film's LIGHT block and POSITIVE LOCKS read as a
            # contradiction when both were true.
            ("a frame with two populations reports BOTH, not just their mean",
             [str(p / "mixed.png"), str(p / "b.png"), "--pair"],
             lambda o, rc: "THE SPLIT" in o and "warm-leaning" in o and "cool-leaning" in o),
            # The one that matters: a 75/25 frame must READ 75/25. Without it
            # the split is only ever exercised on frames where one share is 100
            # and the other 0 -- the arrangement in which a split and a mean are
            # indistinguishable.
            ("...and a 75/25 frame reads 75/25, with both means kept apart",
             [str(p / "mixed.png"), str(p / "b.png"), "--pair"],
             lambda o, rc: "75% at R-B +105.0" in o and "25% at R-B -110.0" in o),
            # The control: on a frame that genuinely has ONE population, saying
            # so is the informative answer, and an empty population must print
            # as a dash rather than nan -- a nan in a report reads as a broken
            # tool rather than as an absence.
            ("a single-population frame says 100/0, and the empty side is a dash not nan",
             [str(p / "a.png"), str(p / "b.png"), "--pair"],
             lambda o, rc: "100% at R-B +105.0" in o and "0% at R-B      —" in o),
            ("...and that proof is a DIFFERENT file from the golden-rim one",
             [str(p / "a.png"), str(p / "b.png"), "--pair"],
             lambda o, rc: (p / "proofs" / "a_rimmask.png").exists()
                           and (p / "proofs" / "a_rimmask.png").read_bytes()
                               != (p / "proofs" / "a_rimchroma.png").read_bytes()),
        ]
        for name, args, want in cases:
            out, rc = run(args)
            good = "Traceback" not in out and want(out, rc)
            ok &= good
            print(f"  {'ok ' if good else '!! '}{name}")
            if not good:
                for line in out.strip().splitlines()[-4:]:
                    print(f"       {line[:100]}")

    print()
    print("  \033[92mNo faults of any known class.\033[0m" if ok else "  \033[91mFAILED.\033[0m")
    print("  NOT tested: whether GATE_DIRECTION is the RIGHT direction for your room. That")
    print("  is a measurement, it is recorded under F-28, and it is not a command-line flag.\n")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="*")
    ap.add_argument("--selftest", action="store_true",
                    help="FK-27: prove --expect can only agree or refuse, never be ignored")
    ap.add_argument("--role", choices=["start", "end"])
    ap.add_argument("--pair", action="store_true")
    ap.add_argument("--expect", choices=["warmer", "cooler", "auto"], default="auto",
                    help="the direction you believe the rim colour moves. Default auto = "
                         "the direction this gate was derived for. Naming the other one is "
                         "refused, not silently ignored.")
    ap.add_argument("--subject", action="append", default=None, metavar="X0,Y0,X1,Y1",
                    help="normalised box holding the SUBJECT in this frame, one per image "
                         "in order. The default head box is fixed and the subject is not: "
                         "a man twelve feet from the lens occupies a tenth of it, and the "
                         "rest is room. FK-29.")
    ap.add_argument("--video", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.images:
        ap.error("no images given")

    # Refuse BEFORE measuring. A tool that measures first and then argues has
    # already spent the operator's attention on numbers answering a question he
    # did not ask, and the numbers are the part people remember.
    if a.expect not in ("auto", GATE_DIRECTION):
        print(f"\n  REFUSED — you passed --expect {a.expect}, and the pair gate here tests a "
              f"{GATE_DIRECTION.upper()} swing in the rim's colour.")
        print(f"  That direction is not a setting. It was measured off this room's own frames "
              f"and\n  recorded under F-28: there is no golden light at the window end, so a "
              f"{a.expect}\n  gate is not merely the wrong test, it is one nothing could pass.")
        print("\n  If you believe the light really does run the other way, that is a finding "
              "about\n  the room and it changes GATE_DIRECTION. It does not change this run.\n")
        return 2

    if a.video:
        video_curve(a.images[0])
        return 0

    def box_for(i):
        if not a.subject:
            return HEAD_BOX, False
        if len(a.subject) not in (1, len(a.images)):
            ap.error(f"--subject given {len(a.subject)} time(s) for {len(a.images)} image(s). "
                     f"Give one per image, in order, or exactly one for all of them.")
        spec = a.subject[i] if len(a.subject) > 1 else a.subject[0]
        try:
            v = tuple(float(x) for x in spec.split(","))
        except ValueError:
            ap.error(f"--subject {spec!r} is not four numbers separated by commas")
        if len(v) != 4 or not all(0.0 <= x <= 1.0 for x in v) or v[0] >= v[2] or v[1] >= v[3]:
            ap.error(f"--subject {spec!r} must be X0,Y0,X1,Y1 as fractions of the frame, "
                     f"with X0<X1 and Y0<Y1")
        return v, True

    rs = [measure(p) for p in a.images]
    for r in rs:
        show(r)

    fail = []
    if a.role and len(rs) == 1:
        g = ROLE_GATES[a.role]
        print(f"\n  role={a.role}: {g['note']}")
        _box, _given = box_for(0)
        rc = rim_chroma(np.asarray(Image.open(a.images[0]).convert("RGB")), _box,
                        proof_name=pathlib.Path(a.images[0]).stem)
        if rc is None:
            fail.append("no lit edge found in the head box at all — is there a person in it?")
        else:
            print(f"    RIM CHROMA   area {rc['area']:.2f}%   R-B {rc['rb']:+.1f}   lum {rc['lum']:.1f}")
            print(f"    proof: {rc['proof']}   (orange = warm-leaning, blue = cool-leaning)")
            if "rim_rb_min" in g and rc["rb"] < g["rim_rb_min"]:
                fail.append(f"rim R-B {rc['rb']:+.1f} is below {g['rim_rb_min']:+.1f} — the light "
                            "on him is already cool, so the change has happened before the shot starts")
            if "rim_rb_max" in g and rc["rb"] > g["rim_rb_max"]:
                fail.append(f"rim R-B {rc['rb']:+.1f} is above {g['rim_rb_max']:+.1f} — the sky light "
                            "has not reached him; he is still carrying the room's own tungsten")
        if "warm_soft_max" in g and rs[0]["rim_headbox_pct"] > g["warm_soft_max"]:
            print(f"    note: golden-rim area {rs[0]['rim_headbox_pct']:.2f}% is over "
                  f"{g['warm_soft_max']}% — check the mask proof that it is hair, not a window edge")

    if a.pair and len(rs) == 2:
        s, e = rs
        # HEAD-BOX, not frame-wide. Frame-wide rim is dominated by the BRASS
        # fittings, whose visible area changes with framing — k6-4's 0.33 is
        # almost entirely the counter strip, with 0.04 on the man. Comparing
        # frame-wide numbers across two different framings compares brass to
        # brass. The claim under test is "the light on HIM rises", so measure him.
        d = e["rim_headbox_pct"] - s["rim_headbox_pct"]
        # The pair is now gated on the SWING IN THE RIM'S COLOUR, not on how much
        # golden light lands on him. See F-28: there is no golden light at the
        # window end of this room, so the old delta could only ever be negative.
        _sbox, _sgiven = box_for(0)
        _ebox, _egiven = box_for(1)
        sc = rim_chroma(np.asarray(Image.open(a.images[0]).convert("RGB")), _sbox,
                        proof_name=pathlib.Path(a.images[0]).stem)
        ec = rim_chroma(np.asarray(Image.open(a.images[1]).convert("RGB")), _ebox,
                        proof_name=pathlib.Path(a.images[1]).stem)
        # Name the direction in words, not only as the sign of a threshold. The
        # operator who typed `--expect warmer` read "(need <= -15.0)" and PASS
        # in the same block and had no reason to connect them.
        print(f"\n  PAIR — gating a {GATE_DIRECTION.upper()} swing"
              + (f", as you asked" if a.expect == GATE_DIRECTION else " (F-28; --expect auto)"))
        # The --role path has always tested this and the --pair path never did,
        # so a pair with no detectable lit edge died with a TypeError instead of
        # saying what was wrong. A traceback is not a finding: it tells the
        # operator the tool is broken when what happened is that his frame has
        # no rim in the head box, which is itself the answer.
        if sc is None or ec is None:
            which = ", ".join(n for n, v in (("start", sc), ("end", ec)) if v is None)
            print(f"\n  \033[91mFAIL\033[0m\n    ! no lit edge found in the head box of the "
                  f"{which} frame. Either there is nobody in it, or the light on him is flat "
                  f"enough that this gate has nothing to measure — open the rim proof and see "
                  f"which.")
            return 1
        print(f"        rim colour IN BOX    start R-B {sc['rb']:+6.1f}  →  end "
              f"{ec['rb']:+6.1f}    swing {ec['rb']-sc['rb']:+6.1f}   (need <= {-RIM_SWING_MIN:+.1f})")
        # FK-33. THE SPLIT, ALWAYS -- because the line above is a mean over two
        # populations and on this film it falls between them and describes
        # neither. Read this block before the line above it.
        # An empty population is a real answer -- "no cool pixels at all" is the
        # most informative thing this block can say -- so it prints as a dash
        # rather than nan. A nan in a report reads as a broken tool.
        def _n(v, w=6, d=1, suf=""):
            return f"{'—':>{w}}" if v != v else f"{v:+{w}.{d}f}{suf}"

        def _p(v, w=9):
            return f"{'—':>{w}}" if v != v else f"{v:{w}.0f}"

        print(f"\n        THE SPLIT — the line above is the mean of these two:")
        print(f"                              {'start':>22s}   {'end':>22s}")
        print(f"          warm-leaning   {_p(sc['warm_pct'])}% at R-B {_n(sc['rb_warm'])}"
              f"   {_p(ec['warm_pct'])}% at R-B {_n(ec['rb_warm'])}")
        print(f"          cool-leaning   {_p(sc['cool_pct'])}% at R-B {_n(sc['rb_cool'])}"
              f"   {_p(ec['cool_pct'])}% at R-B {_n(ec['rb_cool'])}")
        print(f"          warm sits at x {_n(sc['warm_cx'], 8, 2)}    {_n(ec['warm_cx'], 20, 2)}"
              f"   (0 = left of box, 1 = right)")
        print(f"          cool sits at x {_n(sc['cool_cx'], 8, 2)}    {_n(ec['cool_cx'], 20, 2)}")
        print(f"          in outer 1/3   warm {_p(sc['warm_edge'], 3)}% cool "
              f"{_p(sc['cool_edge'], 3)}%      warm {_p(ec['warm_edge'], 3)}% cool "
              f"{_p(ec['cool_edge'], 3)}%")
        # FK-35. THE SENTENCE THAT USED TO BE HERE WAS WRONG, and it was wrong
        # one commit after FK-30, which is the finding about a positional number
        # whose helper line claimed more than it measured. It said "the
        # architecture tends to the edges and the person to the middle".
        #
        # A RIM RIDES THE SILHOUETTE, AND IN A TIGHT BOX THE SILHOUETTE IS THE
        # EDGE. So a perfect subject box, containing nothing but a person,
        # reports most of its counted pixels in the outer thirds -- for the same
        # reason a box full of glazing does. The number cannot separate them and
        # no arrangement of it can. Reported because the distribution is worth
        # seeing; explained as what it is, which is not a subject test and not a
        # proxy for one either.
        print(f"          (DISTRIBUTION ONLY. This cannot tell a rim at the box edge from")
        print(f"           architecture at the box edge, because a rim rides the silhouette")
        print(f"           and in a tight box the silhouette IS the edge. Only the proof")
        print(f"           answers which — that is what the proof is for.)")
        print(f"\n        Two lights on two parts of one subject are not a contradiction and")
        print(f"        their mean is not a description. If both shares are large, the number")
        print(f"        on the line above is between them and belongs to neither.")
        print(f"        rim brightness       {sc['lum']:6.1f}  →  {ec['lum']:6.1f}"
              f"    (must rise: he walks into the brighter end of the room)")
        print(f"        rim area             {sc['area']:6.2f}%  →  {ec['area']:6.2f}%")
        # FK-29. HOW WIDE THE COUNTED MASK IS SPREAD ACROSS ITS OWN BOX.
        # Reported, never gated -- see rim_chroma.
        #
        # FK-32. THIS COMMENT USED TO CARRY A MEASUREMENT I NEVER TOOK. It said
        # "on the origin film's end frame this read 99% / 97%", written before
        # the feature had ever run on that film. The real numbers, when it did:
        #
        #     default box   80% x 92%  ->  100% x 75%
        #     subject box  100% x 95%  ->   94% x 98%
        #
        # A fabricated number in a source comment is worse than one in a message
        # -- a message is read once and a comment is inherited by whoever
        # changes this next, as though it were evidence. And it is the same
        # fault the film's own F-61 exists for: a counting claim stated without
        # the crop. Third time in one session that I have written a figure I had
        # not measured.
        #
        # The real numbers also make FK-30's point better than my invention did:
        # spread barely separates a box full of glazing from a box round a man.
        print(f"        mask spread          {sc['span_x']:5.0f}% x {sc['span_y']:3.0f}%  →  "
              f"{ec['span_x']:5.0f}% x {ec['span_y']:3.0f}%  of the box's columns x rows")
        # FK-30. THE LINE THAT USED TO BE HERE SAID "near 100% is
        # architecture". It was wrong, and its own first real run showed it: a
        # box drawn TIGHT around a man reads ~100% too, because his head fills
        # the top and his shoulders fill the width. Spread measures how well the
        # box FITS its contents, not what the contents are. A number whose name
        # asserts more than it measures is the whole of FK-29, reproduced by me
        # one commit later while writing the fix for it.
        # FK-35, third instance. This caption was corrected once already (FK-30)
        # and still ended "high spread in a LOOSE box means architecture" --
        # another statement of what the number USUALLY MEANS rather than what it
        # is computed from. A loose box round a person also spreads. Say the
        # computation; the proof says the meaning.
        print(f"                             (DISTRIBUTION ONLY, not a gate and not a subject"
              f"\n                              test. It is the share of the box's columns and "
              f"rows holding\n                              at least one counted pixel, and "
              f"nothing more.)")
        print(f"        room R-B             {s['rb_neutral']:+6.1f}  →  {e['rb_neutral']:+6.1f}"
              "    (the room swings cool too)")
        print(f"        golden-rim head-box  {s['rim_headbox_pct']:6.2f}%  →  "
              f"{e['rim_headbox_pct']:6.2f}%   (context only — NOT a gate, see F-28)")
        # FK-28. THE PROOF FOR THE NUMBER THAT DECIDES, named separately from
        # the _rimmask proof, which draws the metric on the line above it — the
        # one this block says is not a gate. "Open the proof image" was pointing
        # at the wrong picture on every run this tool has ever made.
        print(f"\n        PROOF OF THE GATED MASK — open these two, not the _rimmask pair:")
        for _c in (sc, ec):
            print(f"          {_c['proof']}")
        print(f"        orange = warm-leaning pixel, blue = cool-leaning, and the R-B above is")
        print(f"        their mean. A rim is THIN: head-box area is {sc['area']:.2f}% and "
              f"{ec['area']:.2f}% here.")
        print(f"        If the colour is on glazing bars or brass rather than on hair, a")
        print(f"        shoulder or a jacket edge, this gate is measuring the room, not the man.")
        if not (_sgiven and _egiven):
            # FK-29. The verdict must not imply something nobody established.
            # This box is FIXED and the subject is not: in the origin film's end
            # frame the hero is twelve feet from the lens and occupies about a
            # tenth of it, and the other nine tenths are a window onto a lake.
            # The tool cannot find him. It can refuse to pretend it did.
            print(f"\n        \033[93mSCOPE: the DEFAULT head box\033[0m {HEAD_BOX}. Nothing has "
                  f"established that\n        it contains only the subject, so the numbers above "
                  f"are about a REGION and not\n        about a person. Name him and they become "
                  f"about him:\n          --subject X0,Y0,X1,Y1  (one per image, in order, "
                  f"fractions of the frame)")
        swing = ec["rb"] - sc["rb"]
        # FK-30. A THRESHOLD IS NOT A PROPERTY OF THE LIGHT. It is a property of
        # the light AND the region it was read from. Every reading behind
        # RIM_SWING_MIN was taken on the default head box, and FK-29 established
        # what that box holds at the window end of this room: a shopfront. So a
        # swing measured inside a SUBJECT box cannot be judged against it.
        #
        # Doing it anyway would have handed over a FAIL that is exactly as
        # unfounded as the PASS that started all of this -- same tool, same
        # frames, opposite verdict, neither of them evidence. Refuse the verdict
        # and say what would restore it.
        if _sgiven or _egiven:
            print(f"\n  \033[93mUNCALIBRATED — no verdict\033[0m")
            print(f"    You measured inside a subject box. The swing threshold "
                  f"({-RIM_SWING_MIN:+.1f}) was\n    derived on {RIM_SWING_DERIVED_ON}, which is "
                  f"a different region, so comparing the\n    two would compare two different "
                  f"quantities and print the difference as a\n    verdict. The measurement above "
                  f"is real. The threshold does not apply to it.")
            print(f"\n    Observed: swing {swing:+.1f}, rim brightness "
                  f"{sc['lum']:.0f} → {ec['lum']:.0f}.")
            print(f"    To get a verdict back, re-derive the threshold from subject-box readings")
            print(f"    across the candidate frames, then set RIM_SWING_MIN and "
                  f"RIM_SWING_DERIVED_ON\n    together — they are one fact and they move as one.\n")
            return 3
        if swing > -RIM_SWING_MIN:
            fail.append(f"rim colour swing {swing:+.1f} is weaker than {-RIM_SWING_MIN:+.1f}. "
                        "Two start frames differ by 4.1, so this is not noise — the light on "
                        "him has not changed enough between the frames Seedance interpolates.")
        if ec["lum"] <= sc["lum"]:
            fail.append(f"the rim on him gets DARKER ({sc['lum']:.0f} → {ec['lum']:.0f}). "
                        "He is walking toward the brightest part of the room; if the light on "
                        "him falls, he has not gone anywhere.")

    if fail:
        print("\n  \033[91mFAIL\033[0m")
        for x in fail:
            print(f"    ! {x}")
        return 1
    # FK-28. This line used to say "the proof image", singular, on a run that
    # writes two DIFFERENT masks — and the operator reasonably opened the one
    # named in the per-frame block, which draws the metric this tool demotes to
    # context-only three lines above. Name the one that decided.
    _scope = ("over the subject box you supplied" if (a.subject and a.pair)
              else "over the DEFAULT head box — a region, not a person" if a.pair
              else "")
    print(f"\n  \033[92mPASS\033[0m {_scope}".rstrip() + " — now open the "
          "\033[1m_rimchroma\033[0m proof, which is the "
          "mask this\n  verdict was computed from. The _rimmask pair is the golden-rim metric "
          "and it\n  gates nothing. This tool's first version was wrong about its mask and only "
          "a\n  proof revealed it; the second version was right about the mask and pointed at "
          "the\n  wrong picture.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
