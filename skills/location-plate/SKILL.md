---
name: location-plate
description: Build and register the location plates a film shoots against — masters, derived angles, and the axis rule. Use when a shot needs a camera angle no existing plate covers, when deciding whether to build a plate or change the shot, or when comparing two plates for drift.
---

# Location plates

## One element per CAMERA ANGLE, not per room

Prose cannot pin a shape. Four generations from byte-identical counter prose returned four
different geometries. An image can pin it — which is why a location is not one element but one
per angle you shoot on.

## Masters declare themselves

A plate that **originates** an axis carries `is_master` as a sentence saying which axis it
originates and what derives from it. Not a boolean: *"has no provenance"* and *"is the
provenance"* are opposite states that look identical to anything reading `derived_from`, and a
bare `true` is how a derived plate gets quietly promoted to silence a gate.

## A derived angle is DERIVED, not described

Build it **image-to-image with the master passed as an input image**, and let the prompt
describe **the camera move**, not the room.

Attaching the master as an *element* is not the same thing. An element conditions a render; an
input image constrains geometry. Measured in one afternoon, same room:

| method | attempts | result |
|---|---|---|
| image-to-image from the master | 1 | landed |
| text-to-image, master attached as element | 3 | door on a side wall · a new wall across the back · an L-shaped room with glazing on two walls |

**And the chain matters, not the last step.** A prose-invented room becomes a certified
derivation the moment somebody edits it once. If any step says `text-to-image`, the plate needs
a recorded `derivation_exemption` naming **who** checked it against the master, **when**, on
**which invariants**, and — because a tight frame cannot show a room — **which invariants it
could not show**.

## When derivation is impossible

These models do not do novel view synthesis. They will not re-photograph a scene from
somewhere else. When the master cannot be turned into the angle you need:

1. re-photograph by prose, accepting it is a new plate with a new provenance, **or**
2. **change the shot** so the angle is not needed

Option 2 is usually cheaper and is almost never considered. Six previz frames were spent
before somebody asked whether the shot had to be that wide.

## A tight frame has no room in it

A wide plate is located by the room. A tight one is not located at all — and a room-plan
sentence inside it has no referent except the picture, so it reads as a statement about the
FRAME and mirrors the composition to suit.

If the frame declares the room is outside it, **delete every room-plan fact from the prompt.**
The guards that demand a door's position were written from wide-shot faults and stand down
here, deliberately.

## Comparing two plates — never by eye

`compare_asset.py` exists because seven "mismatches" between two plates were read off two crops
by eye and five were imaginary.

```
python3 $FILMKIT/tools/compare_asset.py @plate @master --property "the shared invariant" \
    --box-a x0,y0,x1,y1 --box-b x0,y0,x1,y1
```

It asks two questions a person skips:

- **Which face?** A street handle is not missing from an interior view.
- **Which end?** A knob on a stile is not missing from a plate shot from the far end of the
  same wall — it is behind its own stile. Same face, different disclosure.

If the property is not in the taxonomy, the tool refuses, and **that refusal is the work**:
decide which bucket it belongs in and write the reason. The next person inherits it.

## Counting anything in a plate shot ALONG its subject

Two proofs are not enough. The extent box proves the run **ends** inside the crop; it does not
prove the run is **all visible**. A frontage photographed along its length is occluded by its
own piers and reveals — and the occluder sits inside the extent crop, where no wider box will
find it.

Before counting, answer both:

1. what stands in **front** of the run and hides an instance?
2. where does the run **end**, and is that end inside this crop?

And do the looking **through the tool**. An ad-hoc crop in a scratch script writes no
whole-frame view, asks no questions, and is how "six lights" got said out loud about a bay that
has eight.
