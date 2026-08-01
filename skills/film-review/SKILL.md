---
name: film-review
description: Review a returned generation or a candidate frame — what order to test things in, which mismatches are faults and which are differences, and how to report a finding without inventing one. Use when a generation comes back, when judging a candidate frame, or when about to tell someone something is wrong.
---

# Reviewing what came back

## Test ONE thing first, and test the load-bearing thing

Read the shot's **load-bearing relationship** before anything else. If the room is wrong, every
observation about the light in it is an observation about the wrong room.

Reviewing in the wrong order costs whole rounds: a frame was called *correct* two paragraphs
after the same report noted that both candidates had folded the door onto a return wall.

## A returned frame is graded on relationships, not inventory

Present-and-correct objects in wrong relationships pass an inventory and fail the film. Ask:

- is the load-bearing relationship intact?
- is the camera on the axis the shot declares?
- is the handedness right — which cheek, which hand, which shoulder is nearer?
- does anything the script plants for later survive?

## Not every mismatch is a fault

| MUST match exactly | SHOULD match | MAY drift |
|---|---|---|
| faces · wardrobe · the cup and its mark · the phone | furniture layout in the plane of focus | background props out of focus |
| anything touched or looked at | counts of things a viewer might count | exact chair angles |
| anything planted for later | architecture the camera moves past slowly | how many people are on the street |
| light direction · room colour temperature | | dressing seen once and never again |

**The test:** will a viewer at 24fps, watching once, on a phone, notice it? If no, it is a
difference. Write it down and move on. Chasing MAY-drift items spends generations on things
nobody will read.

## A divergence is COMPARED, never noticed

The sentence *"this plate diverges from the master"* is the most expensive sentence available.
It has been wrong or meaningless six times across two days, and every one was produced the same
way: two crops open on a screen, and a person reading them.

Run `compare_asset.py` **before the word leaves your mouth.** Ask which face, then ask which
end. A difference in what a plate **discloses** is not a difference in what is **there**.

## Counting

Never off a downscale. Never off an oblique view without asking what stands in front of the
run. A bay reported as six lights had eight — one column behind a projecting pier, one outside
a crop boundary — with a correct extent proof attached.

## Reporting

**Report "no faults of any known class". Never "clean".** And name what is not encoded — the
things this pass could not have checked, and why.

"Clean" is a claim about everything. "No faults of any known class" is a claim about the
classes you have. The difference is the whole of what you do not know, and stating it is what
lets the next person aim.

## When something IS wrong

A fault that cost something becomes a finding, and **a finding is not closed until it has a
guard and a fixture.** If it cannot be automated it becomes a `manual` checklist item with a
written question, and preflight will not pass without an answer. Never leave it as a paragraph
and assume that is enough.

If the lesson is general rather than about this film:

```
python3 $FILMKIT/bin/filmkit-promote <FINDING-ID>
```

which runs the portability test, demands a neutral fixture, and records why anything is
refused.

## Two habits no script can hold

- **After writing any gate, ask which existing rows can no longer satisfy it — and check.**
  Three separate guards in this kit turned out to be unsatisfiable by an entire class of asset,
  and a guard that cannot be satisfied does not get fixed. It gets routed around, invisibly.
- **Verify the thing that has to survive the trip**, not the thing in front of you. The
  delivered file, not the working copy. A clean directory, not the one where your own outputs
  already sit. The process, not the pure function.
