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
import _project as P  # FK1: where the film is

PROOFS = P.DIR / "proofs"

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


def rim_chroma(arr, box):
    """Lit edges on a dark surround inside `box`, and what colour they are."""
    H, W, _ = arr.shape
    x0, y0, x1, y1 = int(box[0]*W), int(box[1]*H), int(box[2]*W), int(box[3]*H)
    p = arr[y0:y1, x0:x1].astype(np.float32)
    R, B, L = p[..., 0], p[..., 2], p.mean(2)
    nb = cv2.GaussianBlur(L, (21, 21), 0)
    lit = (L > nb + 8) & (nb < 95) & (L > 60)
    if lit.sum() < 200:
        return None
    return dict(area=100*float(lit.mean()), rb=float((R-B)[lit].mean()),
                lum=float(L[lit].mean()))


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
    PROOFS.mkdir(exist_ok=True)
    over = (arr * 0.30).astype(np.uint8)
    over[warm & ~rim] = (0, 110, 130)
    over[rim] = (255, 0, 200)
    p = Image.fromarray(over)
    ImageDraw.Draw(p).rectangle([W * x0, H * y0, W * x1, H * y1],
                                outline=(60, 255, 60), width=3)
    name = label or pathlib.Path(path).stem
    out = PROOFS / f"{name}_rimmask.png"
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--role", choices=["start", "end"])
    ap.add_argument("--pair", action="store_true")
    ap.add_argument("--expect", choices=["warmer", "cooler"], default="warmer")
    ap.add_argument("--video", action="store_true")
    a = ap.parse_args()

    if a.video:
        video_curve(a.images[0])
        return 0

    rs = [measure(p) for p in a.images]
    for r in rs:
        show(r)

    fail = []
    if a.role and len(rs) == 1:
        g = ROLE_GATES[a.role]
        print(f"\n  role={a.role}: {g['note']}")
        rc = rim_chroma(np.asarray(Image.open(a.images[0]).convert("RGB")), HEAD_BOX)
        if rc is None:
            fail.append("no lit edge found in the head box at all — is there a person in it?")
        else:
            print(f"    RIM CHROMA   area {rc['area']:.2f}%   R-B {rc['rb']:+.1f}   lum {rc['lum']:.1f}")
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
        sc = rim_chroma(np.asarray(Image.open(a.images[0]).convert("RGB")), HEAD_BOX)
        ec = rim_chroma(np.asarray(Image.open(a.images[1]).convert("RGB")), HEAD_BOX)
        print(f"\n  PAIR — rim colour on him   start R-B {sc['rb']:+6.1f}  →  end "
              f"{ec['rb']:+6.1f}    swing {ec['rb']-sc['rb']:+6.1f}   (need <= {-RIM_SWING_MIN:+.1f})")
        print(f"        rim brightness       {sc['lum']:6.1f}  →  {ec['lum']:6.1f}"
              f"    (must rise: he walks into the brighter end of the room)")
        print(f"        rim area             {sc['area']:6.2f}%  →  {ec['area']:6.2f}%")
        print(f"        room R-B             {s['rb_neutral']:+6.1f}  →  {e['rb_neutral']:+6.1f}"
              "    (the room swings cool too)")
        print(f"        golden-rim head-box  {s['rim_headbox_pct']:6.2f}%  →  "
              f"{e['rim_headbox_pct']:6.2f}%   (context only — NOT a gate, see F-28)")
        swing = ec["rb"] - sc["rb"]
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
    print("\n  \033[92mPASS\033[0m — now open the proof image. "
          "This tool's first version was wrong and only the proof revealed it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
