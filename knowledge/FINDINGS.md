# FILMKIT — general findings

Faults that have cost something, and that survive the portability test: their fixture
still fires with every project proper noun stripped.

**A finding is not closed until it has a guard and a fixture.**

Each entry carries a metadata block, from which `checklist.py` derives the review
checklist — so the checklist cannot drift from the ledger.

```
<!-- guard: automatic|manual   scope: prompt|asset|frames|process|delivery
     ask: the question a reviewer must answer in writing -->
```

Populated by `bin/filmkit-promote`. Nothing is hand-added here.

---

## F-69 · I COUNTED WHAT THE FRAME DISCLOSED AND CALLED IT WHAT THE ROOM HAS

<!-- guard: automatic  scope: build/verify
     ask: is this run photographed ALONG its length — and if so, what is standing in front of it? -->

**Cost:** one wrong verified claim, live for eleven minutes, retracted by Zee in two sentences. It would have cost a re-roll of an accepted plate if he had agreed with me.

I registered the left along-frontage plate and reported a divergence: *"its first and third bays read three columns by two rows, six lights each, while only the middle bay reads four by two."* I had the master open beside it, I cropped at 1:1, and I put it in front of Zee as a fault. **Every bay is four columns by two rows.** Bay one reads three because **the projecting door block stands in front of its first column**. Bay three reads three because **my crop boundary cut its fourth**.

**Three counting guards already existed and not one of them could have caught this.**

| finding | the cure it installed | why it is useless here |
|---|---|---|
| F-17 | crop ONE instance to fill the frame | I did. The instance was correct. |
| F-24 | plus a WIDE box proving the run ENDS inside it | I did. It did end inside it. |
| F-61 | never count off a downscale | I did not. Every crop was 1:1. |

All three treat a miscount as **a framing problem**, and all three cure it by **moving the crop boundary**. This miscount was not at the boundary. **The thing hiding the column was in the middle of the extent crop, in focus, at full resolution, and I looked straight at it.**

**The mechanism, and it is the whole finding.** A run photographed **along** its length is occluded by its own architecture. Piers, reveals, mullions and projecting blocks are *part of* the run, so they stand between the lens and their own neighbours. Widening the crop cannot help — **the occluder is inside it.** An oblique count is therefore a count of what the frame **discloses**, and disclosure and existence are different numbers.

**And there is a tell I ignored.** The plate's own `aspect` field, which I wrote, says *"looking ALONG the frontage."* The word was sitting in the ledger row while I counted.

**The near-miss underneath it.** `asset_economy` puts *"counts of things a viewer might count"* in **SHOULD match**, so I recorded the divergence instead of proposing a re-roll. That tolerance table is the only reason this cost nothing. **A guard I did not have was covered by a rule about what is worth fixing — which is luck, not method.**

**Guard.** `--occluders` on `verify_asset.py`: a counting claim on a plate whose `aspect` says the camera looks **along / three-quarter / receding / oblique / down one side** is refused unless the claim names what stands in front of the run and where it actually ends. *"Nothing stands in front of this run"* is an acceptable answer and it is only acceptable after looking. Stored on the claim beside the two proof crops. Fired and confirmed.

**The transferable rule.** *Extent proves the run ends. Occlusion proves the run is all there. They are different proofs and a wide crop only ever supplies the first.*

**What is not encoded:** nothing detects an occluder automatically. The gate forces the question and records the answer; it cannot tell whether the answer is true, and it does not fire on a plate whose `aspect` happens not to use one of those six words.

---

*Copied from a film's ledger on 2026-08-01 by `filmkit-promote`, which checked that its `ask:` names no proper noun of that film and that it carries a transferable rule. The EVIDENCE travels with it deliberately — one film's specifics are the reason the rule exists, and a rule without its reason gets switched off. The finding also stays in that film's own ledger; this is a copy, not a move.*

---

## F-71 · THE FACE TAXONOMY ASKED WHICH FACE AND NEVER ASKED WHICH END

<!-- guard: automatic  scope: build/verify
     ask: is this feature fixed to one edge or one end of the subject — and does each plate actually DISCLOSE it? -->

**Cost:** folded into F-70. The knob argument had no vocabulary, so it was settled by eye.

`element_rules.face_dependence` sorted every property into three buckets — `one_face_only`, `both_faces`, `independent_of_face` — and **all three ask the same question: which face?** That was the right question on 31 Jul, when the two plates were an interior and a street elevation.

**On 1 Aug both plates were the same face.** Two interiors of one door. They disagreed about a brass knob, and the taxonomy had nothing to say, so `compare_asset.py` returned *"property not in the taxonomy"* — correctly — and I stopped using it and reasoned in prose instead. **A refusal I could not resolve became a reason not to use the tool at all**, which is the same shape as F-67: a guard whose only legal fix is unavailable trains you to route around it.

**The missing bucket.** The two plates are shot from **opposite ends of one wall**. A fitting on a vertical stile is square to the lens from the near end and swallowed by its own stile from the far one — and neither plate can establish which stile is the lock stile. The side-by-side, once the bucket existed and the tool would draw it, shows the two crops are not even looking at the same part of the leaf.

**Guard.** New bucket `same_face_disclosure_varies`, holding *door furniture on a stile*, *anything fixed to one end of a long run*, and *the near face of any projecting pier* — that last one is the pier that hid the bay column in F-69, so both of today's mistakes now live in one taxonomy entry with one reason. `compare_asset.py` reads the fourth bucket and stamps the comparison **DISCLOSURE, NOT DRIFT**: a difference here may be called drift only if **both** plates visibly disclose the feature.

**The transferable rule.** *Ask which face. Then ask which end. A difference in what is disclosed is not a difference in what is there.*

**What is not encoded:** nothing measures whether a plate discloses a feature — the tool states the rule and draws the two crops side by side, and the reading is still a person's.

---

*Copied from a film's ledger on 2026-08-01 by `filmkit-promote`, which checked that its `ask:` names no proper noun of that film and that it carries a transferable rule. The EVIDENCE travels with it deliberately — one film's specifics are the reason the rule exists, and a rule without its reason gets switched off. The finding also stays in that film's own ledger; this is a copy, not a move.*
