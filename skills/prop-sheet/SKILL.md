---
name: prop-sheet
description: Build prop reference sheets for objects a character touches, carries or looks at — the things that must match exactly across every shot. Use when creating a prop element, deciding whether a prop needs a sheet at all, or when a prop changes between cuts.
---

# Prop sheets

## Which props earn a sheet

A prop earns a sheet when it is **touched, carried, looked at, or planted for a later shot**.
Everything else is dressing, and dressing may drift.

That is not a judgement call each time — it is the tolerance table:

| MUST match exactly | MAY drift |
|---|---|
| the cup and its printed mark | background props out of focus |
| the phone | cup and saucer positions on other tables |
| anything a character touches or looks at | exact chair angles |
| anything the script plants for later | small dressing seen once |

A prop the camera lingers on is a prop the audience can count, measure and compare. A prop in
the back of a soft frame is not.

## The multi-panel product sheet

The useful shape is a studio sheet on plain grey, several panels:

- front elevation
- a three-quarter showing one specific edge — **say which edge**
- rear elevation
- any state the film needs (screen on, lid off, cup empty)

State the panel layout in the asset's `aspect`, panel by panel, because a claim recorded from
one panel is a claim about that panel and nothing else.

## The trap: a sheet carries the state it was drawn in

A phone sheet with a **lit** screen does not supply the dark slab that opens a shot. A cup
sheet with a lid on does not supply the lid off. If the film needs both states, the sheet needs
both panels — or the second state must be prompted and will drift.

And a product sheet's **lighting is a studio convention**. A stylised glow drawn standing up
off a screen is a render device, not how that object lights a room or a face. Write that into
the `aspect` so nobody reaches for the sheet as a light reference.

## Naming a fitting in order to exclude it

Do not. **The model renders what is named.** A prompt that said

> *the handle is on the street side and stays out of sight from in here*

returned a brass handle on the inside face. The enumeration before it had already done the
whole job:

> *This inside face carries green paint, glass and one brass letterplate, and the letterplate
> is the only metal on it.*

A closed list excludes by construction. This applies to handles, knobs, levers, push plates,
kickplates, latches, bolts, hinges and escutcheons — anything small, metal and nameable.

## Anchor objects

Every location plate records a **named anchor object** so later blocking is written against a
thing in the picture rather than against metres:

> *the door's brass letterplate — horizontal, at about hip height on the solid lower panel, and
> the one fixed feature of this wall whose height is known.*

Then blocking reads *"the palm lands a head above the letterplate"* rather than *"about 1.5 m
up"*, and the model has something to measure against.

## Registering one

```
python3 $FILMKIT/tools/verify_asset.py @cup --box 0.3,0.2,0.5,0.6 --look
python3 $FILMKIT/tools/verify_asset.py @cup --box ... --claim "..." --extent ...
```

Counting anything — lenses, buttons, panes, pendants — needs **both** a tight crop showing one
instance at feature scale **and** a wide box proving the run ends inside it. The 6% rule alone
forces a crop too tight to show whether there is one more just outside it.
