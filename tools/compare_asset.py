#!/usr/bin/env python3
"""
Compare two assets on a shared invariant -- and refuse when the two views
cannot support the comparison.

WHY THIS EXISTS (F-46)
----------------------
`element_rules.one_element_per_angle` has required since 31 Jul that every
derived plate be "verified against the master on the shared invariants before it
is registered." Nothing implemented that. It was done by eye, and on 31 Jul the
eye reported SEVEN mismatches between @tarn_door and @cafe_int's door:

    pull handle · brass kickplate · no panelled reveal · green drifted
    · lit backwards · no water in the plate · one light instead of four

Only the LAST one was real. The others were the two FACES of one door: an
outward-opening egress door is pulled from the street and pushed from inside, so
a street-face handle and kickplate are correct, and a freestanding leaf in a
meadow cannot have an interior reveal. The colour read dark because the face was
backlit. On the strength of that reading a rebuild was recommended and a good
plate was called broken.

The crop was at the right SCALE (F-17) and of the right OBJECT (F-16). It was of
the wrong FACE, and no rule in this kit had a word for that.

THE RULE
    An observation carries the viewpoint it was made from. Two observations may
    be compared only on a property that is visible and identical from BOTH. A
    difference in a face-specific fitting across differing aspects is not
    evidence of drift; it is evidence of two faces.

The taxonomy is DATA, in tarn_facts.json > element_rules.face_dependence, so it
is extended by editing facts rather than code -- and so the reason travels with
the rule (F-42: a rule without its reason gets switched off).

Usage
  python3 compare_asset.py @tarn_door @cafe_int --property "pull handle"
  python3 compare_asset.py @tarn_door @cafe_int --property "light count" \
      --box-a 0.33,0.02,0.50,0.80 --box-b 0.14,0.17,0.36,0.60
  python3 compare_asset.py --audit          # which assets have no aspect
"""
import argparse, json, pathlib, re, sys
from PIL import Image
import _project as P  # FK1: where the film is

HERE = P.DIR
FACTS = P.PATH
PROOFS = HERE / "proofs" / "asset_compare"
R, G, Y, X = "\033[91m", "\033[92m", "\033[93m", "\033[0m"


def classify(prop, fd):
    prop_l = prop.lower().strip()
    # F-71. The fourth bucket. The three below all ask WHICH FACE; this one asks
    # WHICH END, and it is the one the knob argument needed and did not have.
    for bucket in ("one_face_only", "both_faces", "independent_of_face",
                   "same_face_disclosure_varies"):
        for key, why in fd.get(bucket, {}).items():
            if key.startswith("_"):
                continue
            if key.lower() in prop_l or prop_l in key.lower():
                return bucket, key, why
    return None, None, None


def side_by_side(pa, ba, pb, bb, out):
    ims = []
    for path, box in ((pa, ba), (pb, bb)):
        im = Image.open(path).convert("RGB")
        W, H = im.size
        if box:
            x0, y0, x1, y1 = box
            im = im.crop((int(W * x0), int(H * y0), int(W * x1), int(H * y1)))
        h = 900
        ims.append(im.resize((max(1, int(im.size[0] * h / im.size[1])), h), Image.LANCZOS))
    cv = Image.new("RGB", (sum(i.size[0] for i in ims) + 30, 900), (18, 18, 18))
    x = 0
    for i in ims:
        cv.paste(i, (x, 0)); x += i.size[0] + 30
    PROOFS.mkdir(parents=True, exist_ok=True)
    cv.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a", nargs="?"); ap.add_argument("b", nargs="?")
    ap.add_argument("--property", help="the invariant being compared")
    ap.add_argument("--box-a"); ap.add_argument("--box-b")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="compare anyway, having stated in the run record why the "
                         "property is visible from both faces")
    x = ap.parse_args()

    d = json.loads(FACTS.read_text(encoding="utf-8"))
    assets = d.get("assets", {})
    fd = d.get("element_rules", {}).get("face_dependence", {})

    if x.audit:
        print("\n  asset viewpoints\n")
        for t, rec in sorted(assets.items()):
            asp = rec.get("aspect")
            print(f"  {'ok ' if asp else '!! '}{t:26s} {asp or 'NO ASPECT RECORDED'}")
        bad = [t for t, r in assets.items() if not r.get("aspect")]
        print(f"\n  {len(bad)} asset(s) cannot be compared safely.\n" if bad
              else "\n  Every asset knows which way it is facing.\n")
        return 1 if bad else 0

    if not (x.a and x.b and x.property):
        ap.error("give two asset tags and --property, or --audit")
    for t in (x.a, x.b):
        if t not in assets:
            print(f"  unknown asset {t}"); return 1
    aa, ab = assets[x.a].get("aspect"), assets[x.b].get("aspect")
    if not aa or not ab:
        print(f"\n  {R}! ASPECT NOT RECORDED{X} — refused.")
        print(f"    {x.a}: {aa or 'MISSING'}\n    {x.b}: {ab or 'MISSING'}")
        print("    An observation with no viewpoint cannot be compared to anything.\n")
        return 1

    bucket, key, why = classify(x.property, fd)
    print(f"\n  {x.a}\n    aspect: {aa}\n  {x.b}\n    aspect: {ab}\n")
    same_face = aa.split(",")[0].strip().lower() == ab.split(",")[0].strip().lower()

    if bucket is None:
        print(f"  {Y}? PROPERTY NOT IN THE TAXONOMY{X} — {x.property!r} is not listed in")
        print("    element_rules.face_dependence. Decide which bucket it belongs in and add")
        print("    it there WITH ITS REASON before comparing. Guessing is what F-46 was.\n")
        return 1

    print(f"  property {x.property!r} -> {bucket} ({key})\n    {why}\n")

    if bucket == "same_face_disclosure_varies":
        print("  \033[93m! DISCLOSURE, NOT DRIFT\033[0m — this property is fixed to one edge or one "
              "end of the\n    subject, so an oblique view can hide it behind its own geometry. "
              "A difference\n    here may be called DRIFT only if BOTH plates visibly DISCLOSE the "
              "feature. If\n    either does not, it is a difference: record it with the reason and "
              "move on (F-71).\n")

    if bucket == "one_face_only" and not same_face:
        print(f"  {R}! CROSS-FACE COMPARISON REFUSED{X}")
        print(f"    {key!r} exists on one face only, and these two observations are of")
        print("    different faces. A difference here is NOT drift — it is two faces.")
        print("    This is exactly the reading that called a correct @tarn_door broken.\n")
        return 1

    if bucket == "independent_of_face" and "paint colour" in (key or "") and not same_face:
        print(f"  {Y}! COLOUR ACROSS DIFFERENT LIGHT{X} — proceed only if both faces are")
        print("    lit comparably. A backlit face reads darker and cooler and that is not a")
        print("    colour drift. See geometry.lighting_inference.\n")
        if not x.force:
            return 1

    ba = tuple(float(v) for v in x.box_a.split(",")) if x.box_a else None
    bb = tuple(float(v) for v in x.box_b.split(",")) if x.box_b else None
    fa, fb = HERE / assets[x.a]["file"], HERE / assets[x.b]["file"]
    if not (fa.exists() and fb.exists()):
        print(f"  {R}file missing{X}: {fa if not fa.exists() else fb}\n"); return 1
    slug = re.sub(r"\W+", "-", f"{x.a}-{x.b}-{x.property}").strip("-").lower()
    out = side_by_side(fa, ba, fb, bb, PROOFS / f"{slug}.png")
    print(f"  {G}comparison allowed{X} — side-by-side written:\n    {out}")
    print("\n  NOW OPEN IT. The tool has established that the comparison is legitimate.")
    print("  Whether the two agree is still a person's reading, and it is the only part")
    print("  of this that was ever the hard bit.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
