#!/usr/bin/env python3
"""
TARN region measurement, with mandatory proof.

WHY THIS EXISTS
Three separate wrong conclusions on this project came from measuring a region
that was never visually verified:

  1. skyline peak detection — crop boxes were off the mountains entirely,
     returned zero peaks, and the correlation came back NaN
  2. "green joinery" colour boxes — the @cafe_int box was sitting on a blown
     window (17% of it above luminance 250) and reported as joinery
  3. "glass" white-balance mask — caught white brick and subway tile, which
     inverted the conclusion and produced the claim "the panes are not blown,
     so they are fine" when the panes were in fact perfectly uniform

The failure is always the same shape: the numbers look plausible, so the mask is
never checked. The habit that has worked every time is matched-scale crops
viewed side by side.

So this tool does two things no amount of discipline reliably does:
  * it ALWAYS writes a proof image of exactly what was measured, and prints the
    path, so numbers and evidence arrive together
  * it reports the mask's own COMPOSITION — how much of it is green, near-white,
    dark, skin-toned — so a contaminated mask announces itself

Usage
  python3 measure.py IMAGE --box 0.33,0.24,0.55,0.34 --label glass
  python3 measure.py IMAGE --mask neutral --label wb
  python3 measure.py A.png B.png --box 0.33,0.24,0.55,0.34 --label glass --stack

--stack writes ONE image with each crop resampled to a common width and stacked
vertically. That is the matched-scale comparison, and it is the only form in
which two frames of different sizes should ever be compared.
"""
import argparse, pathlib, sys
import numpy as np
from PIL import Image, ImageDraw
import _project as P  # FK1: where the film is

PROOFS = P.DIR / "proofs"


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def composition(px):
    """What is actually in this mask? A contaminated mask shows a mixed profile."""
    R, G, B = px[:, 0], px[:, 1], px[:, 2]
    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    sat = px.max(axis=1) - px.min(axis=1)
    n = max(len(px), 1)
    return {
        "greenish (joinery?)": 100 * ((G > R + 6) & (G > B + 4)).sum() / n,
        "near-white >248":     100 * (L > 248).sum() / n,
        "bright 200-248":      100 * ((L > 200) & (L <= 248)).sum() / n,
        "mid 70-200":          100 * ((L >= 70) & (L <= 200)).sum() / n,
        "dark <70":            100 * (L < 70).sum() / n,
        "saturated >40":       100 * (sat > 40).sum() / n,
        "skin-ish":            100 * ((R > G + 12) & (G > B + 4) & (L > 60) & (L < 220)).sum() / n,
    }


def report(label, px, extra=""):
    R, G, B = px[:, 0], px[:, 1], px[:, 2]
    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    print(f"\n  {label}{extra}   n={len(px)/1e3:.0f}k px")
    print(f"    RGB=({R.mean():6.1f},{G.mean():6.1f},{B.mean():6.1f})   "
          f"R-B={R.mean()-B.mean():+6.1f}")
    print(f"    lum  p5={np.percentile(L,5):5.1f}  p50={np.percentile(L,50):5.1f}  "
          f"p95={np.percentile(L,95):5.1f}  SD={L.std():5.1f}  %>248={(L>248).mean()*100:5.1f}")
    comp = composition(px)
    print("    composition: " + " · ".join(f"{k} {v:.0f}%" for k, v in comp.items() if v >= 1))
    # contamination heuristics — the checks that would have caught all three failures
    warn = []
    if comp["greenish (joinery?)"] > 12 and "glass" in label.lower():
        warn.append("mask is >12% green — joinery is in it, this is not glass")
    if comp["near-white >248"] > 12 and "joinery" in label.lower():
        warn.append("mask is >12% near-white — a blown window is in it, not joinery")
    if comp["skin-ish"] > 10 and ("counter" in label.lower() or "board" in label.lower()):
        warn.append("mask is >10% skin-toned — a hand is in it")
    spread = [v for v in (comp["dark <70"], comp["mid 70-200"],
                          comp["bright 200-248"], comp["near-white >248"]) if v > 20]
    if len(spread) >= 3:
        warn.append("tone spread across 3+ bands — the mask is probably straddling "
                    "several materials rather than sampling one")
    for w in warn:
        print(f"    \033[93m! CONTAMINATION: {w}\033[0m")
    return comp


def crop_box(im, box):
    W, H = im.size
    x0, y0, x1, y1 = box
    return im.crop((int(W * x0), int(H * y0), int(W * x1), int(H * y1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--box", help="x0,y0,x1,y1 as fractions of frame")
    ap.add_argument("--mask", choices=["neutral", "all"], help="rule-based mask")
    ap.add_argument("--label", default="region")
    ap.add_argument("--stack", action="store_true",
                    help="write one matched-scale stacked comparison")
    a = ap.parse_args()
    PROOFS.mkdir(exist_ok=True)
    box = tuple(float(v) for v in a.box.split(",")) if a.box else None
    crops = []

    for path in a.images:
        im = Image.open(path).convert("RGB")
        name = pathlib.Path(path).stem
        if box:
            c = crop_box(im, box)
            arr = np.asarray(c).astype(np.float32).reshape(-1, 3)
            report(f"{name} · {a.label}", arr, f"  box={box}  crop={c.size}")
            crops.append((name, c))
            # proof 1: the crop itself.  proof 2: the box drawn on the whole frame
            c.save(PROOFS / f"{name}_{a.label}_crop.png")
            full = im.copy(); d = ImageDraw.Draw(full); W, H = full.size
            d.rectangle([box[0]*W, box[1]*H, box[2]*W, box[3]*H], outline=(255, 40, 40),
                        width=max(3, W // 300))
            full.thumbnail((1100, 1100)); full.save(PROOFS / f"{name}_{a.label}_where.png")
        else:
            arr = np.asarray(im).astype(np.float32)
            L = lum(arr)
            if a.mask == "neutral":
                sat = arr.max(axis=2) - arr.min(axis=2)
                m = (sat < 26) & (L > 70) & (L < 200)
            else:
                m = np.ones_like(L, bool)
            report(f"{name} · {a.label} (mask={a.mask})", arr[m])
            # proof: the mask, painted magenta over a dimmed frame
            over = (arr * 0.35).astype(np.uint8)
            over[m] = (255, 0, 200)
            p = Image.fromarray(over); p.thumbnail((1100, 1100))
            p.save(PROOFS / f"{name}_{a.label}_mask.png")

    if a.stack and len(crops) > 1:
        Wt = 950
        rs = [c.resize((Wt, int(Wt * c.size[1] / c.size[0])), Image.LANCZOS) for _, c in crops]
        out = Image.new("RGB", (Wt, sum(r.size[1] for r in rs) + 10 * (len(rs) - 1)), (15, 15, 15))
        y = 0
        for r in rs:
            out.paste(r, (0, y)); y += r.size[1] + 10
        out.save(PROOFS / f"STACK_{a.label}.png")

    print(f"\n  PROOF WRITTEN to {PROOFS}/ — open it before quoting any number above.")
    print("  An unviewed mask has produced three wrong conclusions on this project.\n")


if __name__ == "__main__":
    main()
