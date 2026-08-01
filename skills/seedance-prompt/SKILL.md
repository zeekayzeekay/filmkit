---
name: seedance-prompt
description: Write a Seedance 2.0 prompt for a shot in a film — block order, lens choice, beat timing, element attachment, and the phrasing rules that stop the model rendering what you told it to avoid. Use before writing any Seedance prompt, and before editing one.
---

# Writing a Seedance prompt

A prompt is not a description of a scene. It is **an instruction to a model that renders what
is named**, including what you name in order to exclude.

## Before the first word

```
python3 $FILMKIT/tools/shotmap.py          # what does this shot need, and what supplies it?
python3 $FILMKIT/tools/verify_asset.py --audit
```

If `shotmap` says the camera axis is covered by no attached plate, **you are not writing a
prompt yet — you are building a plate.** See the `location-plate` skill.

## Deconstruct before you compose

Six slots. Mark each **explicit**, **implied** or **missing** in the brief you were given:

| slot | the question |
|---|---|
| subject | who or what is this shot about — one, not three |
| action | what physically changes between the first frame and the last |
| setting | which plate holds it, and on which axis |
| light | direction, quality, colour temperature, and what it lands on |
| camera | framing and lens, and whether the camera moves |
| constraints | what must match a neighbouring shot |

**Missing slots are where drift enters.** A slot you did not decide is one the model decides,
differently, every time. Fill them, then write.

## Block order

```
SCENE CONTEXT      one paragraph: where, when, who, what is about to happen
LOCATION MAP       foreground / midground / background, as layers
CAMERA             framing, lens in degrees, movement or "static"
ACTION             a timed beat table
LIGHTING           sources, direction, what each one lands on
POSITIVE LOCKS     the closed list of what must not change
```

`SCENE CONTEXT`, `CAMERA`, `LIGHTING` and `POSITIVE LOCKS` are required. A prompt missing one
of them fails the lint.

## Lens

Choose from the anchor set, in degrees of horizontal field of view:

```
180   107   84   63   47   29   18   12   8
```

A value off this list is a value the model interpolates. State it as
`Medium shot at 47 degrees`, never as a focal length, never as an f-stop. Photographic
abstractions — stops, ISO, EV, "shot on Alexa", director names — are not acted on and are
refused by the lint.

## Beats

A beat table with a physical action in every row:

```
| 0.0s to 1.2s | He sets the cup down; his shoulders drop. |
| 1.2s to 3.0s | The camera holds. Wind moves the grass behind him. |
```

A beat with a state and no action is a beat the model renders as a freeze. One measured
example ran 1.6 seconds of a motionless cup because the row said *"the cup sits on the table"*.

## The phrasing rule that costs the most

**A prohibition is a description with a minus sign in front, and the minus sign is the least
reliable token in the prompt.** Measured, four times in one day:

| written | rendered |
|---|---|
| *put no door anywhere except…* | extra doors |
| *every other wall carries no door* | a door in another wall |
| *no hard-edged cast shadow shapes* | a hard beam |
| *the handle stays out of sight from in here* | a brass handle |

Instead, **enumerate what the surface does carry and close the list**:

> *This inside face carries green paint, glass and one brass letterplate, and the letterplate
> is the only metal on it.*

A closed list excludes by construction and names nothing that should be absent.

## Say each important thing once

A fact repeated in two blocks is a fact that can be edited in one of them. Five shipped
contradictions were all created by fixing one place and leaving the other. Put each fact in
the block that owns it, and refer to it nowhere else.

## Elements

Elements are **global to the generation**. They condition every frame, not a span.

- **One environment element**, and only one. Two states of one room cannot both be attached —
  the second appears in frame 1 and destroys any reveal.
- An element carries **an axis**, not just materials. If the shot is photographed off that
  axis, the model drops either the room or the subject.
- A frame built to be a `start_image` or `end_image` is **never** registered as an element.
  Global means its finished pose appears in frame 1.

## Handedness

**A frame is handed by what is in it.** Wide: the room does it — the door is at the left end
of the frontage, the counter runs down the right. Tight: only the subject's own body can —
which cheek is toward the lens, which ear, which shoulder is nearer, near hand versus far hand.

**Pin handedness to whatever the frame actually contains, and delete the other entirely.** A
room-plan fact inside a frame with no room in it has no referent except the picture, and will
be read as a statement about the *frame* — which mirrors the whole composition.

## Before it fires

```
python3 $FILMKIT/tools/preflight.py --block "<BLOCK>" --record RUN.md --export OUT.txt
```

No partial pass. The receipt that authorises a generation is written only when every phase is
green **including the items only a person can answer** — and the gate refuses any call whose
prompt does not hash to that receipt.
