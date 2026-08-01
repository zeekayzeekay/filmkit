---
name: shot-script-coherence
description: Keep the shot script and the machine-readable shot map in agreement, in both directions, and check a prompt change against its neighbours. Use when adding or cutting a shot, when a shot's duration or content changes, or before firing anything whose neighbours were written earlier.
---

# Script and shots, both directions

## The two-way street

Production changes the script as often as the script changes production, so the two are
**compared**, never trusted:

- a shot in the script with **no row** in the shot map is invisible to every check in the kit
- a row in the map for a shot the script **dropped** is a build order for nothing

`shotmap.py` compares both directions and reports either as `uncovered`. Neither is a warning
you defer.

## Every shot row carries a load-bearing relationship

Not an inventory — a **relationship**. The one thing that decides whether a returned frame is
the right room at all:

> *the frontage is the FAR wall, the counter runs down the right toward it, and the door is at
> the LEFT END OF THE FRONTAGE, coplanar with the glazing bays. He crosses the room's depth,
> not its width.*

Test that before reading anything else in a returned frame. **An inventory of correct objects
passed eight checks while the door stood on the wrong wall** — every object present, every
object in the wrong relationship.

A row without one is refused by `shotmap`, because a shot with no stated relationship cannot be
reviewed, only inventoried.

## Every shot row carries a camera axis

And the axis must be covered by an attached plate, or a conditioning frame the row names. If
neither, you are not writing a prompt — you are building a plate.

## When a duration changes, everything downstream moves

A shot growing by two seconds re-derives every timecode after it. Do that arithmetic **before**
agreeing to the change, and put the new runtime in the same sentence as the agreement, so the
cost is visible when the decision is made rather than discovered later.

## Check the neighbours, not just the shot

```
python3 $FILMKIT/tools/crossshot.py <SHOT>
```

It prints each property across the previous shot, this one and the next, and marks what
CHANGES. Every marked property is either **deliberate and in the script**, or a continuity
fault. There is no third case.

## The sentences left standing

The most expensive class of fault is not the sentence you changed. It is the one you did not —
*"his shoulders are square to the window"*, still true of the old blocking, now false, sitting
inside a paragraph its author was editing around.

No rule reading the prompt alone can reach it, because it names no destination; it was merely
TRUE BECAUSE OF one. What is mechanical is **where** such a sentence lives:

```
python3 $FILMKIT/tools/stale_neighbours.py --old PREV.txt --new NEW.txt
```

It lists the survivors inside edited paragraphs. Reading them is a person's job.

## Reading the diff is not reading the prompt

Every fault found by reading a prompt end to end was found that way; every version that shipped
a fault had only its **diff** reviewed. Diff tools work, and they only ever show what changed —
and a stale sentence is by definition one that did not.

`preflight`'s full-read phase hashes the export and requires an attestation carrying that hash.
Edit one word and the hash moves and the attestation is void. It cannot be recycled, which is
the only property that makes it worth anything.

## Three questions no guard can ask for you

1. Does the prompt contradict the script for **this** shot?
2. Does anything the prompt changed invalidate a **neighbour's** text?
3. Does every `!` in the cross-shot report appear in the script as a **deliberate** change?
