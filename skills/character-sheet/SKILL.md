---
name: character-sheet
description: Build character reference sheets that hold identity across a whole film — one face per sheet, panel discipline, and what a studio sheet can and cannot govern. Use when creating or reviewing a character element, or when a character's face or wardrobe drifts between shots.
---

# Character sheets

## One face per sheet

A sheet showing two views of a face the model reads as two faces. Every panel must be the
**same person**, and the sheet must be checked for it — not assumed. `verify_asset --audit`
tells you which sheets have never been checked against the image at all.

## A sheet is a viewpoint, not an object

Every asset carries an `aspect` saying which face or angle its file shows, and a claim without
one is refused. This is not bookkeeping. Seven properties of one door were once reported as
drift, and five of them were the two **faces** of one door — compared by eye, across
viewpoints, with no proof written.

For a character sheet the aspect is usually *"studio, frontal portrait panel"*, and that
sentence is doing real work: it says the sheet governs **identity**, and does not govern how
this person is lit in a room.

## What a studio sheet CANNOT govern

- **Light.** A four-panel product sheet's lighting is a studio device. One phone sheet's
  fourth panel draws the screen's output as an opaque rectangular sheet of light standing up
  off the glass — a render convention, not how a phone lights a face. Using it as a light
  reference imports the convention.
- **State.** A sheet carries the state it was drawn in. A phone sheet with a lit screen does
  not supply the dark slab that opens a shot; that must be prompted.
- **Scale in a room.** A portrait panel says nothing about how tall this person reads against
  a counter.

Write those exclusions into the `aspect` itself, where anyone reading the row will see them.

## What MUST match exactly

Faces. Wardrobe. Anything a character touches or looks at. Anything the script plants for a
later shot. The direction light comes from. The room's colour temperature.

## What MAY drift, and re-rolling for it is waste

Background props out of focus. Exact chair angles. How many people are on the street beyond the
glass. Small dressing that appears once and never again.

**The test:** will a viewer at 24fps, watching once, on a phone, notice it? If no, it is not a
fault, it is a difference. Write the difference down and move on.

## Deriving a second sheet

A second sheet of the same character — different wardrobe, different age, a bare-shouldered
variant — is a **derived** asset and follows the same rule as a derived location angle: build
it image-to-image from the first, never fresh from prose. Two fresh generations of one face
will not agree, and the disagreement is invisible until the two shots are cut together.

For anything with an **asymmetric identity mark** — a scar, a barnacle pattern, a tattoo — the
derivation is not optional. An asymmetric pattern generated twice is two different creatures.

## Registering one

```
python3 $FILMKIT/tools/verify_asset.py @name --box x0,y0,x1,y1 --look      # crop it and OPEN it
python3 $FILMKIT/tools/verify_asset.py @name --box ... --claim "..."       # then record
```

A claim about an asset is only a claim if somebody opened the file, looked at the region, and
left the crop on disk. Four false facts about one location survived a "full visual audit", a
dozen reviews and five generations, because they were written from prose.

**Counting claims need two proofs**: one instance filling the frame, *and* a wide box showing
the run ends inside it. Magnification proves what one instance is; only the wide box proves how
many there are.
