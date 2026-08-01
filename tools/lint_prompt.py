#!/usr/bin/env python3
"""
TARN prompt linter.

Mechanical pre-flight checks on Seedance prompt blocks. Catches the classes of
error that are regular enough to be caught by a machine, so review attention is
spent on the classes that are not.

Usage:  python3 lint_prompt.py TARN_STAGE3_PROMPTS.md
        python3 lint_prompt.py TARN_STAGE3_PROMPTS.md --block G3

Exit code 1 if any ERROR-level finding. WARN findings need a human decision.
"""
import re, sys, os, pathlib, json
import _project as P  # FK1: where the film is

# ---------------------------------------------------------------- PORTABILITY
# The engine holds no project content. Everything specific to a film — assets,
# geometry, continuity, tripwires, budgets, vocabulary — lives in ONE json file,
# chosen with --project or $PROMPTGUARD_PROJECT, defaulting to tarn_facts.json.
# A new scene needs new rows in that file; a new project needs a new copy of it.
# See PORTABILITY.md for the schema and what to change.
def _project_path():
    for i, a in enumerate(sys.argv):
        if a == "--project" and i + 1 < len(sys.argv):
            return pathlib.Path(sys.argv[i + 1])
    env = os.environ.get("PROMPTGUARD_PROJECT")
    if env:
        return pathlib.Path(env)
    return P.PATH

FACTS_PATH = _project_path()
FACTS = json.loads(FACTS_PATH.read_text(encoding="utf-8")) if FACTS_PATH.exists() else {}

def _cfg(key, default):
    """Project override for anything the engine would otherwise hard-code."""
    return FACTS.get("vocabulary", {}).get(key, default)

# Direction words. Finding them is easy; deciding whether each is load-bearing
# is not — so the linter surfaces them and points at the declared geometry.
DIRECTION = re.compile(
    r"\b(?:left|right|behind|in front of|near(?:er|est)?|far(?:ther|thest)?|"
    r"above|below|clockwise|anticlockwise|counter-?clockwise|upstage|downstage)\b", re.I)

# ---------------------------------------------------------------- rule tables

FOV_TABLE = set(_cfg('fov_table', [180, 107, 84, 63, 47, 29, 18, 12, 8]))

# WHO THE SHOT IS ABOUT. Four rules used to hard-code `@hero` and `he/his`,
# which made the engine silently wrong for any film whose lead is a woman, a
# pair, or a dog. A portability test against a second project file exposed it:
# the beat check reported every beat as heroless. Project data now.
PROTAGONIST = _cfg('protagonist', r"\bhe\b|\bhis\b|\bhim\b|@hero")
SECOND_PARTY = _cfg('second_party', r"@barista|\bher\b|\bshe\b")

# Lesson 1 — negations. The generator adds what you forbid.
NEGATION = re.compile(
    r"\b(?:no|not|never|nothing|none|neither|nor|without|cannot|can't|won't|"
    r"doesn'?t|does not|do not|don'?t|isn'?t|is not|aren'?t|are not|"
    r"wasn'?t|stays? clear of|free of|lacking|absent|avoid|refrain)\b",
    re.I)

# Sanctioned negations. Two kinds, both earn their place:
#   1. the @tarn_under device — scoping what a reference supplies. Proven here:
#      20 text-only candidates drifted, 4 with the exclusion clause landed.
#   2. the skill's own prescribed locks, which it says to write verbatim.
SANCTIONED_NEGATION = re.compile(
    r"(are|is) not in this frame|not in this frame|supplies .{0,80} only|"
    r"and nothing (else|of)|no drift mid-segment|"
    r"does not cut on its own|cuts only at", re.I)

# Lesson 4 — photographic abstractions the models do not act on.
# NB "stops" must be preceded by a number: "he stops mid-turn" is a verb.
BANNED_NUMERIC = re.compile(
    r"\b\d+(?:\.\d+)?\s*stops?\b|\b(?:two|three|four|one)\s+stops?\b|"
    r"\bf/\d|\bISO\s*\d|\bEV\b|"
    r"turn\s+(?:about\s+)?\d+\s*degrees|rotate\s+(?:about\s+)?\d+\s*degrees",
    re.I)

# No director / equipment names.
BANNED_NAMES = re.compile(
    r"\b(?:lubezki|deakins|fincher|kubrick|nolan|villeneuve|malick|"
    r"arri|alexa|red komodo|blackmagic|cooke|zeiss|panavision|imax)\b", re.I)

REQUIRED_BLOCKS = ["SCENE CONTEXT", "CAMERA", "LIGHTING", "POSITIVE LOCKS"]

# ---------------------------------------------------------------- consistency
# Five contradictions have shipped in these prompts. Every one was two
# statements about the SAME SUBJECT in different blocks, and every one was
# created by an edit that fixed one place and left the other. That is a lookup
# problem, not a judgement problem: group every sentence by what it talks
# about, print the groups, and the conflict is visible instead of 40 lines apart.

SUBJECTS = _cfg('subjects', None) or {
    "cup":        r"\bcup\b",
    "lid":        r"\blid\b",
    "his hands":  r"\b(?:his )?(?:hand|hands|thumb|fingers|grip)\b",
    "position":   r"\b(?:feet|stands?|standing|spot|mark|position|walks?)\b",
    "mouth":      r"\bmouth|jaw|lips\b",
    "eyes":       r"\beyes?|pupils?|gaze|squint",
    "the view":   r"\b(?:glass|glazing|window|view|panes?|frontage|outside)\b",
    "framing":    r"\b(?:framing|frame left|frame centre|fills?|filling|wider|widen)\b",
    "camera":     r"\bcamera|lens|tilt|arc|dolly|pull(?:s|ing)? back|static|locked off|pivot|widen\b",
    "the cut":    r"\bcut\b",
    "customers":  r"\bcustomers?|banquette|laptop|book\b",
    "colour":     r"\bcolour|color|white balance|kelvin|green|off-white|warm|cool\b",
    "counter":    r"\bcounter\b",
    "speech":     r"\bsays?|speaks?|spoken|silent|line\b",
    # "level" alone matched "water level" and "table height" — require it to be
    # about the frame, not a height. Found on G7/G10, both false positives.
    "horizon":    r"\bhorizon|holds? level|stays? level|level (?:frame|horizon|throughout)|\broll(?:s|ing)?\b|\bcant",
    "focus":      r"\bfocus|sharp|soft(?:er|ly)?|blur",
    "light":      r"\blight|lit|exposure|shadow|beam|bounce|sun\b",
}
# ^ the only table that is really about THIS film. Override it in
#   vocabulary.subjects for a project with different recurring nouns.

# Opposing terms. If two statements about one subject sit on opposite sides of
# any pair, that pair is surfaced for a human read. Low precision on purpose —
# the cost of a false flag is one glance; the cost of a miss has been five.
OPPOSITIONS = [
    # "closed?" matched the ADJECTIVE "close" — "a close group", "close to the
    # lens", "close enough to touch" — and produced six false CHECK items on one
    # prompt. Noise is not harmless: checks that cry wolf get skimmed, and a
    # skimmed check is how "0 errors" got reported on a prompt with 45 negations.
    (r"\bopens?\b|\bopened\b",            r"\bclosed\b|\bshut\b"),
    (r"keeps? hold|still holding|holding|takes its weight",
                                          r"sets? .{0,15}down|puts? .{0,10}down|lets? go|releas"),
    (r"\bwarm(?:ly)?\b", r"without warmth|no warmth|neither warm|coldness"),
    (r"\bvisible\b|\breads? around\b|\bstays? in frame\b",
                                          r"\bfilling everything\b|\bfills the whole\b|\bout of sight\b|\bhidden\b|\bnot visible\b"),
    (r"featureless|uniform|empty|no shape|nothing readable",
                                          r"hazy city|faint .{0,20}suggestion|structure|tonal variation|facade"),
    (r"\bfor all thirteen seconds\b|\bwhole shot\b|\bthroughout\b|\bwhole thirteen\b",
                                          r"\bat the cut\b|\bchanges only\b|\bwhole of segment\b|\bper segment\b"),
    (r"\blifts?\b|\braises?\b|\bbrings? it up\b", r"\blowers?\b|\bsets? it back\b"),
    (r"\bsilent\b|\bno words?\b|\bstays? silent\b", r"\bhe (?:says|speaks)\b"),
    (r"\blevel\b|\bholds? level\b",        r"\bdrifts?\b|\brolls?\b|\bcanted?\b|\btilted\b"),
    # "pulls back" must belong to the CAMERA — "the hand pulls back" is not a
    # camera move. Found on G10, false positive.
    (r"\bstatic\b|\blocked off\b|\bstays? locked\b",
     r"\barcs?\b|\bdoll(?:y|ies)\b|camera pulls? back|\btilts? up\b|curves around"),
]


# ------------------------------------------------------- timing coherence
# Trimming G3 from 13s to 12s left three stale numbers behind: "the whole of
# those five seconds", "those eight seconds", and a warm edge sized to "the last
# 1.5 seconds" of a segment that no longer had that length. A duration written
# out in prose has to agree with the structure declared elsewhere, and nothing
# was checking that.

WORDNUM = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


def timing_coherence(body, context=""):
    f, both = [], context + "\n" + body
    m = re.search(r"duration[^\d]{0,4}(\d+)", both, re.I)
    total = float(m.group(1)) if m else None

    cuts = sorted({float(x) for x in re.findall(r"(\d+(?:\.\d+)?)s\s*HARD CUT", body)} |
                  {float(x) for x in re.findall(r"cut[^.\n]{0,30}?at\s*(\d+(?:\.\d+)?)\s*s", body, re.I)})

    tcs = [(float(a), float(b)) for a, b in
           re.findall(r"(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)s", body)]
    span = max([b for _, b in tcs], default=None)

    if total and span and abs(span - total) > 0.01:
        f.append(("ERROR", "timing:span",
                  f"beats end at {span}s but duration is {total}s — they must match exactly, "
                  "there is no editor to trim with"))
    if total and cuts and max(cuts) >= total:
        f.append(("ERROR", "timing:cut", f"cut at {max(cuts)}s is at or past the {total}s end"))
    if len(set(cuts)) > 1:
        f.append(("ERROR", "timing:cut", f"cut time stated inconsistently: {sorted(set(cuts))}"))

    # segment lengths implied by the cut points
    allowed = set()
    if total:
        allowed.add(round(total, 2))
        bounds = [0.0] + cuts + [total]
        for a, b in zip(bounds, bounds[1:]):
            allowed.add(round(b - a, 2))

    if allowed:
        for m in re.finditer(r"\b([A-Za-z]+|\d+(?:\.\d+)?)[\s-]+seconds?\b", body):
            tok = m.group(1).lower()
            val = WORDNUM.get(tok, None)
            if val is None:
                try:
                    val = float(tok)
                except ValueError:
                    continue
            # only police spans that claim structure; short values are texture
            if val >= 3 and round(float(val), 2) not in allowed:
                f.append(("ERROR", "timing:stale-duration",
                          f"{m.group(0)!r} matches no segment. Real spans are "
                          f"{sorted(allowed)} — this is a leftover from an earlier cut "
                          f"or duration. …{body[max(0,m.start()-60):m.end()+40].strip()}…"))
    return f


# ------------------------------------------------ performance-lock budget
# Added 30 Jul after G3 v3. Every one of these rules is derived from a measured
# failure in a delivered clip, not from a principle. See TARN_FINDINGS.md.
#
# The project already knew the rule — "structural locks yes, performance locks
# no" — and then shipped a draft with MORE performance locks than the one it was
# fixing. Writing a lesson down does not enforce it. This does.
#
# TWO different counts, and they must not be confused — the first draft of this
# check mixed them up, which is the same unexamined-number fault the project
# keeps paying for:
#   BEAT LINES        = lines in ACTION that open "0.0-1.2s —". v1 had 8, v3 had 8.
#   TIMESTAMP MENTIONS = every "1.5s" anywhere. v1 had 20, v3 had 29.
# The second is the density signal; the first is the performance-locking signal.
#
#   draft      words   beat lines   timestamp mentions   negations   subject motion
#   v1  2,132       8          20            10           8.02
#   v2  3,075       ?          22            22            —
#   v3  3,680       8          29            45           4.43
#
# Correlation across three points is not proof, and two of v3's worst faults were
# NOT density faults. But every one of those 45 negations is a thing offered to
# the model (Lesson 1), and the 1.6s dead hold sat exactly in the one beat that
# gave the hero nothing to do.

BEAT = re.compile(r"^\s*(?:\*\*)?(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)s\s*[—-]", re.M)

# A hero clause that only says what he does NOT do. This is the exact shape of
# G3 v3's 2.2–3.0s beat, whose entire content for the hero was "He does not
# notice" — and which produced a measured 1.6 seconds of frozen cup.
HERO_NEGATED_ONLY = re.compile(
    r"\bhe\s+(?:does not|doesn'?t|will not|won'?t|makes no|takes no|gives no|"
    r"has no|shows no|stays unaware|remains unaware|notices nothing)\b", re.I)
HERO_ACTION = re.compile(
    r"\bhe\s+(?:takes?|lifts?|raises?|lowers?|brings?|turns?|walks?|steps?|sets?|"
    r"puts?|reaches?|drinks?|sips?|swallows?|drops?|carries?|crosses?|stops?|"
    r"begins?|starts?|comes?|holds?|looks?|glances?|leans?|straightens?|breathes?|"
    r"completes?|arrives?|moves?)\b|\bhis (?:hand|fingers|eyes|head|gaze) [a-z]+s\b", re.I)

NEGATION_BUDGET = _cfg('negation_budget', 15)   # v1 shipped 10 and acted well; v3 shipped 45
BEAT_BUDGET = _cfg('beat_budget', 10)           # ACTION beat lines. v1 and v3 both had 8; v4 has 7.
TIMESTAMP_BUDGET = _cfg('timestamp_budget', 24) # every timestamp mention. v1 20, v3 29.
MIN_BEAT = _cfg('min_beat_seconds', 1.0)        # sub-second beats produce pose-to-pose motion


def performance_budget(body):
    f = []
    lines = body.splitlines()

    beats = [(float(a), float(b), body.splitlines()[
        body[:m.start()].count("\n")]) for m, (a, b) in
        ((m, m.groups()) for m in BEAT.finditer(body))]

    for a, b, text in beats:
        if b - a < MIN_BEAT - 1e-9:
            f.append(("WARN", "beat-too-short",
                      f"{a}–{b}s is {b-a:.1f}s. Beats under {MIN_BEAT}s make the model hit "
                      "marks instead of acting. Merge it into its neighbour."))
        if HERO_NEGATED_ONLY.search(text) and not HERO_ACTION.search(text):
            f.append(("ERROR", "beat-without-action",
                      f"{a}–{b}s tells the hero what he does NOT do and gives him nothing "
                      "to do. G3 v3's 2.2–3.0s beat did exactly this and produced a "
                      "measured 1.6s of frozen cup. Give every beat a physical action or "
                      "fold it into the beat beside it."))
        if not re.search(PROTAGONIST, text, re.I):
            f.append(("WARN", "beat-without-hero",
                      f"{a}–{b}s assigns the hero nothing at all — check it is deliberate."))

    if len(beats) > BEAT_BUDGET:
        f.append(("ERROR", "beat-budget",
                  f"{len(beats)} timestamped beats, over the budget of {BEAT_BUDGET}. "
                  "v3 shipped 29 and measured 4.43 subject-motion against draft 1's 8.02. "
                  "Structural locks yes, performance locks no."))

    negs = 0
    for l in lines:
        if SANCTIONED_NEGATION.search(l):
            continue
        negs += len(NEGATION.findall(l))
    if negs > NEGATION_BUDGET:
        f.append(("ERROR", "negation-budget",
                  f"{negs} unsanctioned negations, over the budget of {NEGATION_BUDGET}. "
                  f"v1 shipped 10, v3 shipped 45. Lesson 1: the generator adds what you "
                  "forbid, and every one of these is an offer."))
    else:
        f.append(("INFO", "negations", f"{negs} unsanctioned (budget {NEGATION_BUDGET})"))
    stamps = len(re.findall(r"\d+(?:\.\d+)?\s*s\b", body))
    if stamps > TIMESTAMP_BUDGET:
        f.append(("WARN", "timestamp-density",
                  f"{stamps} timestamp mentions, over {TIMESTAMP_BUDGET}. v1 had 20 and "
                  "measured 8.02 subject-motion; v3 had 29 and measured 4.43."))
    f.append(("INFO", "beats", f"{len(beats)} ACTION beat lines (budget {BEAT_BUDGET}) · "
                               f"{stamps} timestamp mentions (budget {TIMESTAMP_BUDGET})"))
    f.append(("INFO", "words", str(len(body.split()))))
    return f


# ------------------------------------------- achievability of the end state
# G3 v3 locked "He stops turning at 7.0s and travels nowhere after it" while
# supplying an end_image in which his back is to camera — a pose he had not
# reached at 7.0s and could only reach by moving again. The model obeyed both:
# it stopped him, held, REVERSED him to face camera at 8.2s, and turned him away
# again. Four direction changes for one 90-degree turn.
#
# A "stops" lock and an end_image are not automatically in conflict — the camera
# may be doing the work — but the burden is on the prompt to say so.

STOPS_MOVING = re.compile(
    r"\b(?:stops?|ceases?|holds? still|comes? to rest|travels? nowhere|"
    r"stands? where he is)\b[^.\n]{0,60}?(?:at\s*)?(\d+(?:\.\d+)?)\s*s\b"
    r"|\bstops? (?:turning|moving|rotating|walking)\b"
    # F-27. The timestamp used to be mandatory on the first branch, because the
    # fault this rule was built from was "he stops turning AT 7.0s". G3 v4 then
    # wrote "comes to rest a single pace short of the glass ... and stands
    # there" with no time on it, and the rule was silent. The time was never the
    # fault; the stop was. A stop with no clock is worse, not better — nothing
    # even says when the pose is supposed to be reached.
    r"|\b(?:comes? to rest|stands? there|and stands\b|holds? still)\b", re.I)

# a terminal framing that is itself a MOVEMENT. Holding one of these is a freeze
# frame, not a held shot.
MOVING_POSE = re.compile(
    r"mid[- ]stride|heel (?:lifted|raised|clear)|weight (?:forward|over the leading)|"
    r"mid[- ]step|mid[- ]turn|leading (?:foot|knee)|one frame into the step", re.I)
STATIC_POSE = re.compile(
    r"comes? to rest|stands? there|standing still|holds? still|"
    r"stationary|at a standstill|travels? nowhere", re.I)
HOLD_TAIL = re.compile(
    r"hold(?:s|ing)?\s+(?:it\s+)?(?:for\s+)?(?:the\s+)?"
    r"(?:last|final)\s+(\d+(?:\.\d+)?)?\s*(?:second|s\b)", re.I)
ARC_WORDS = re.compile(r"\barcs?\b|\barcing\b|curves? around|orbits?|circles? (?:round|around)", re.I)


def achievability(body, context):
    f = []
    has_end = bool(re.search(r"end_image|end frame|supplied end image", body + context, re.I))
    for m in STOPS_MOVING.finditer(body):
        if has_end:
            f.append(("CHECK", "stop-vs-end-pose",
                      f"{m.group(0)!r} is a lock that stops the subject, and an end_image is "
                      "supplied. Confirm the end pose is ALREADY reached at that moment. "
                      "G3 v3 failed exactly here: he stopped at 7.0s, then had to move "
                      "again to reach the end frame, and reversed direction doing it."))
            break
    # ---------------------------------------------------------------- F-27
    # THE TERMINAL POSE MUST BE HOLDABLE.
    #
    # G3 v4 said he "comes to rest ... and stands there", and its own POSITIVE
    # LOCKS described the terminal framing as "mid-stride toward the glass",
    # settled at 11.0s and held to 12.0s. Both cannot happen. Either he freezes
    # with a heel off the floor for a whole second — which is the dead robotic
    # hold that was the first complaint about v3 — or he resolves to standing
    # and then has to move BACK into the stride to match the end frame, which is
    # the exact mechanism of v3's turn reversal at 8.2s.
    #
    # The older rule could not see this: it asked whether a stop lock and an
    # end_image coexist, never whether the stopped pose and the end pose are the
    # SAME pose. A contradiction between two descriptions of one moment is not a
    # scheduling problem, it is a physics one.
    # Scope BOTH halves to sentences that are about the ending. Unscoped, this
    # fired on G3 v4's 7.5–9.0s beat — "he completes the turn and comes to rest,
    # looking out" — which is a legitimate pause in the middle of a shot, paired
    # with a mid-stride description three paragraphs away. A rule that cannot
    # tell the terminal moment from any other moment is not about terminal pose.
    TERMINAL = re.compile(r"end[_ ]image|terminal framing|final framing|"
                          r"final frame|last frame|to the end\b|at 12\.0s", re.I)
    tail = " ".join(s for s in re.split(r"(?<=[.;])\s+|\n",
                                        re.sub(r"[*_`]+", "", body)) if TERMINAL.search(s))
    mp, sp = MOVING_POSE.search(tail), STATIC_POSE.search(tail)
    if mp and sp:
        f.append(("ERROR", "terminal-pose-unholdable",
                  f"the shot describes its ending as a MOVEMENT ({mp.group(0)!r}) and also as "
                  f"a REST ({sp.group(0)!r}). A mid-motion pose cannot be held: holding it is a "
                  "freeze, and resolving out of it means moving away from the end frame and "
                  "back. Decide which the last frame is, and say only that."))
    ht = HOLD_TAIL.search(tail)
    if mp and ht:
        f.append(("ERROR", "terminal-pose-unholdable",
                  f"the terminal framing is a movement ({mp.group(0)!r}) and the prompt holds it "
                  f"for the tail ({ht.group(0)!r}). Reach a moving end pose ON the final frame; "
                  "do not arrive early and sit in it."))

    if ARC_WORDS.search(body) and re.search(r"\bhe (?:turns?|begins? to turn)\b", body, re.I):
        f.append(("CHECK", "arc-plus-turn",
                  "the camera arcs AND the subject turns in the same segment. Measured on "
                  "G3 v3: the model split this into two moves with a visible seam. Prefer "
                  "one straight camera move and let the subject supply the change of angle."))
    return f


# ----------------------------------------------------- gate completeness
# k5-23 shipped with a warm rim on the hero although its own prompt ended
# "Nothing warm touches him". The claim was in the prompt; no gate measured it;
# the frame was selected on colour and composition alone; the fault propagated
# into a 54-credit clip. A prompt that asserts a measurable property of the light
# on a person must be gated on that property.

LIGHT_ON_PERSON = re.compile(
    r"(?:nothing warm touches|every edge (?:and rim )?on (?:him|@hero)|"
    r"warm (?:edge|rim|bounce)[^.\n]{0,60}(?:on|reaches?|lands? on) (?:him|his)|"
    r"rim (?:of his|on his)|the brightest edge)", re.I)


def gate_completeness(body, context, is_video):
    f = []
    if LIGHT_ON_PERSON.search(body):
        gates = context + "\n" + body
        if "frames_check" not in gates:
            f.append(("ERROR", "ungated-light-claim",
                      "this prompt makes a measurable claim about the light on a person but "
                      "no `frames_check.py` gate appears with it. k5-23 asserted 'Nothing "
                      "warm touches him', was never measured on it, scored 0.24 rim-on-dark "
                      "and cost a 54-credit generation."))
    return f


# ------------------------------------------------------------ measured locks
# K5-start v2 came back at R-B +4.5 against a +12.0 target — the same 7-point
# cold drift that got k5-gpt rejected. Cause: the colour paragraph was rewritten
# to fit the new negation budget, and it carried a note reading:
#
#   "Measured: this wording produced R-B +12.0 and +15.7 ... The earlier
#    version, which said 'cool, grey' and 'nothing warmer', produced +4.8 —
#    it pushed in the drift's own direction. DO NOT REVERT IT."
#
# The note was in the file, in bold, directly under the block. It was not read,
# because the edit was scoped to "reduce negations" and the negations in that
# paragraph were the thing that worked. Prose cannot defend itself.
#
# So: wording that has been measured gets an explicit machine-readable lock.
# Write `MEASURED-LOCK: <exact phrase>` in the prose around a block and the
# phrase must survive verbatim in the prompt body.

# Leading ">" and "*"/"-" are allowed: these lines live inside the blockquote
# that carries the reasoning, and the first version of this regex missed them
# entirely — a guard that silently matches nothing is the worst kind.
MEASURED_LOCK = re.compile(r"^[>\s*\-]*MEASURED-LOCK:\s*(.+?)\s*$", re.M)


def measured_locks(body, context):
    f = []
    for m in MEASURED_LOCK.finditer(context):
        phrase = m.group(1).strip().strip('"').strip("'")
        if phrase.lower() not in body.lower():
            f.append(("ERROR", "measured-wording-lost",
                      f"a MEASURED-LOCK phrase is no longer in the prompt: {phrase!r}. "
                      "This wording was kept because it was measured, not because it "
                      "reads well. Removing it cost K5-start v2 seven points of R-B and "
                      "one 7-credit generation."))
    return f


# words carrying no fact, so their presence must not count toward a paraphrase
# match. Keep this list SHORT: every word removed here is a word the superseded
# check can no longer see, and the failure mode of the check is silence.
STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "its", "it", "is", "are",
    "and", "or", "with", "that", "this", "there", "no", "not", "along", "by",
    "from", "for", "into", "one", "each", "runs", "run", "stands",
}


# ------------------------------------------------- LIGHT DIRECTION (F-47)
# A shadow thrown TOWARD the lens means the source is behind the SUBJECT.
# A shadow thrown AWAY from the lens means the source is behind the CAMERA.
# These are one fact stated two ways, and the inversion is not a matter of
# judgement -- it is arithmetic.
#
# On 31 Jul a review of @tarn_door wrote, in a single sentence:
#   "front-lit with a long shadow thrown toward the lens - sun behind camera"
# The evidence and the conclusion were opposites and sat four words apart. On
# the strength of it the plate was reported as lit backwards and a rebuild was
# recommended. The plate was correct; the reading was inverted. It is the same
# shape as F-14 -- a mechanism mistaken for a cause -- except here the mechanism
# refuted the cause in the same breath and nobody read the sentence twice.
#
# Scoped to a SENTENCE. Two spans may legitimately describe different moments;
# one sentence may not describe the sun in two places.
# NOTE it does NOT fire on backlit + shadows-toward-the-lens, which AGREE --
# that pairing is Shot 7's locked wording and a rule that flagged it would be
# a rule nobody could leave switched on.

SHADOW_TOWARD = re.compile(
    r"shadows?\b[^.]{0,70}?\b(?:toward|towards|into|at)\s+(?:the\s+)?"
    r"(?:lens|camera|viewer|foreground|bottom of (?:the )?frame)"
    r"|\b(?:toward|towards)\s+(?:the\s+)?(?:lens|camera)\b[^.]{0,50}?\bshadows?\b", re.I)
SHADOW_AWAY = re.compile(
    r"shadows?\b[^.]{0,70}?\b(?:away from|behind)\s+(?:the\s+)?(?:lens|camera)"
    r"|shadows?\b[^.]{0,70}?\b(?:into|toward|towards)\s+(?:the\s+)?"
    r"(?:background|distance|far wall|back of (?:the )?frame)", re.I)
FRONT_LIT = re.compile(
    r"\bfront-?lit\b|\bsun\s+(?:is\s+)?behind\s+(?:the\s+)?(?:camera|lens)\b"
    r"|\b(?:light|source)\s+(?:comes\s+|arrives\s+)?from\s+behind\s+(?:the\s+)?"
    r"(?:camera|lens)\b|\bsource\s+behind\s+(?:the\s+)?(?:camera|lens)\b", re.I)
BACK_LIT = re.compile(
    r"\bback-?lit\b|\bagainst the light\b|\brim-?lit\b"
    r"|\bsun\s+(?:is\s+)?(?:behind|beyond)\s+(?:it|him|her|them|the\s+"
    r"(?!camera\b|lens\b)\w+)|\bsource\s+behind\s+the\s+subject\b", re.I)


def light_direction(body):
    """F-47. Shadow direction and source position are ONE fact. Look it up in
    tarn_facts.json > geometry.lighting_inference; never re-derive it."""
    f = []
    for span in re.split(r"(?<=[.!?])\s+|\n\n", body):
        if len(span) > 700:
            continue
        if SHADOW_TOWARD.search(span) and FRONT_LIT.search(span):
            f.append(("ERROR", "light-direction-contradiction",
                      "a shadow thrown TOWARD the lens puts the source behind the SUBJECT, "
                      "which is backlight -- but this sentence also calls it front-lit or "
                      "puts the sun behind the camera. Those are opposites: "
                      f"{span.strip()[:150]!r}"))
        if SHADOW_AWAY.search(span) and BACK_LIT.search(span):
            f.append(("ERROR", "light-direction-contradiction",
                      "a shadow thrown AWAY from the lens puts the source behind the CAMERA, "
                      "which is front light -- but this sentence also calls it backlit. "
                      f"Those are opposites: {span.strip()[:150]!r}"))
    return f


# ------------------------------------------------- LOCATION METHOD (F-44)
# Three rules from Leera.md, each of which was on disk before the fault it
# would have prevented:
#
#   "hard visible rays usually slop"          -> F-28 cost two days of measurement
#                                                to establish that no beam enters
#   "a named anchor object for later          -> F-31/33; "one pace short of the
#    character placement"                        glazing" failed three times
#   "a declared 3/4-view default for depth"   -> the blogs say the same thing twice
#
# They apply to LOCATION prompts — a still that will become an @element — not to
# shot prompts, which have their own camera rules. A block counts as a location
# prompt when it names no protagonist and no timed beats.

HARD_RAYS = re.compile(
    r"\b(?:hard|visible|distinct|defined)\s+(?:sun\s*)?(?:rays?|beams?|shafts?)\b"
    r"|\bshafts? of (?:sun|light)\b|\bgod\s*rays?\b|\bsunbeams?\b", re.I)
ANCHOR_HINT = re.compile(
    r"\banchor\b|\bfor (?:later )?character placement\b"
    r"|\b(?:sofa|doorway|door|banner|counter|bench|table|stair|riser|pillar|column|gate)\b", re.I)
ANGLE_HINT = re.compile(r"3/4|three[- ]quarter|\bhead[- ]on\b|\d+\s*°|\d+\s*degree", re.I)


# ------------------------------------------------------- ROOM PLAN (F-58)
# Four previz frames of Shot 6B put the cafe door on a SIDE WALL, parallel to
# the counter. In the plate the door is IN the shopfront, at its left end,
# coplanar with the glazing bays and perpendicular to the counter. Two different
# models resolved the same gap the same wrong way, which makes it a property of
# the brief and not variance: the brief named the door, named the glazing bays,
# and never said they are one wall.
#
# This is F-15 in a second costume. There, four generations from byte-identical
# counter prose returned four different counter geometries. The lesson then was
# that PROSE CANNOT PIN A SHAPE and the fix was to pin to a selected frame. The
# same is true of a room's PLAN, and nothing in this linter was watching for it.
#
# Portable form, and this is the part that is not about TARN: a model builds the
# room before it builds the picture. Telling it what falls at the left of the
# FRAME says nothing about what is attached to what.
DOORWORD = re.compile(r"\bdoors?\b|\bdoorway\b|\bdoor's\b|\bdoor leaf\b", re.I)
FRONTWORD = re.compile(
    r"\bfrontage\b|\bshop\s?front\b|\bglazing bays?\b|\bglazed bays?\b"
    r"|\bmullion\b|\bstall riser\b", re.I)
PLAN_REL = re.compile(
    r"\bsame wall\b|\bone (?:single |continuous )?(?:wall|plane|run)\b|\bcoplanar\b"
    r"|\bin the same plane\b|\b(?:left|right|far|near) end of (?:the |that )?frontage\b"
    r"|\bset into the (?:frontage|shopfront)\b|\bpart of the (?:frontage|shopfront)\b"
    r"|\bwithin the (?:frontage|shopfront)\b|\bperpendicular to the counter\b"
    r"|\bthe door (?:is|sits|stands) (?:in|within|inside) the (?:frontage|shopfront)\b"
    r"|\bthe same wall as the (?:glazing|bays|frontage)\b", re.I)
FRAME_PLACEMENT = re.compile(
    r"\b(?:at|on|fills?|filling|occupy(?:ing|)|closes? off|stands? at|runs? along)\s+"
    r"(?:the\s+)?(?:extreme\s+)?(?:LEFT|RIGHT)(?:\s+(?:half|side|edge))?\s+of\s+"
    r"(?:the|this)\s+(?:frame|picture|shot)\b", re.I)


def room_plan(body):
    """F-58. A room's PLAN has to be stated as a relation between its features,
    not as two entries in a list of what falls where in the picture."""
    if TIGHT_FRAME.search(body):
        return []   # F-65: wide-shot rules do not apply to a frame with no room in it
    f = []
    if DOORWORD.search(body) and FRONTWORD.search(body) and not PLAN_REL.search(body):
        f.append(("ERROR", "room-plan-unpinned",
                  "this prompt names a DOOR and names the FRONTAGE or its GLAZING and never "
                  "says how the two stand to each other. Two different models both closed "
                  "that gap by moving the door onto a side wall (F-58). State the plan in "
                  "words the model can build from: the door is IN the frontage, at its left "
                  "end, coplanar with the glazing bays and perpendicular to the counter."))
    if len(FRAME_PLACEMENT.findall(body)) >= 2 and not PLAN_REL.search(body):
        f.append(("WARN", "plan-by-frame-only",
                  "two or more fixed features are placed by where they land IN THE FRAME and "
                  "no relationship between any two of them is stated in the room's own plan. "
                  "A frame position is a picture; the model builds the room first. Say what "
                  "is attached to what before saying where it falls."))
    return f


# F-60. LEFT AND RIGHT ARE NOT DEPTH.
# Both right-hand plate candidates put the door NEAR the lens with the glazing
# receding away from it -- a mirror of the left-hand plate rather than the
# opposite camera. The brief said the glazing "comes toward the lens along the
# RIGHT of the picture and ends in the green door, which stands right of centre",
# which places both of them on the same side and never says which one is CLOSER.
# On a wall running away from the camera, that is the only fact that decides the
# shot, and it was the one fact missing.
NEAREST = re.compile(
    r"(?:door|doors|glazing|bays?|frontage|shopfront)[^.]{0,80}?"
    r"\b(?:nearest|closest)\s+(?:the\s+lens|to\s+the\s+lens|to\s+camera|to\s+the\s+camera)\b"
    r"|\b(?:nearest|closest)\s+(?:the\s+lens|to\s+the\s+lens|to\s+camera|to\s+the\s+camera)\b"
    r"[^.]{0,80}?(?:door|doors|glazing|bays?|frontage|shopfront)", re.I | re.S)


def depth_order(body):
    """F-60. Two features of ONE receding wall, and no statement of which is nearer."""
    if TIGHT_FRAME.search(body):
        return []   # F-65: wide-shot rules do not apply to a frame with no room in it
    if not (DOORWORD.search(body) and FRONTWORD.search(body)):
        return []
    if NEAREST.search(body):
        return []
    return [("WARN", "depth-order-unstated",
             "the door and the glazing lie on ONE wall running away from the camera, and this "
             "prompt never says which of them is NEAREST THE LENS. Left and right do not settle "
             "it: both right-hand plate candidates put the door in the foreground and the bays "
             "receding behind it, which is the mirror of the other camera rather than the "
             "opposite one (F-60). Name the near end explicitly.")]


# F-61b. "CLOSES THE FAR END OF THAT WALL" BUILT A DOOR IN A DIFFERENT WALL.
# Both right-hand plate candidates put the door in the white brick wall across
# the back of the room. The brief said the door "closes the far end of that same
# wall" -- and a model reading that builds an END WALL and puts a door in it.
# Any phrasing that casts the door as the TERMINATION of a space rather than as
# an OPENING IN a named plane invites exactly that.
TERMINATING = re.compile(
    r"\b(?:closes?|closing|caps?|terminates?|ends?|seals?)\s+(?:off\s+)?(?:the\s+)?"
    r"(?:far\s+|other\s+|back\s+)?end\b"
    r"|\bat the (?:far |other |back )?end of the room\b|\bthe end wall\b"
    r"|\bacross the (?:far |back )?end\b", re.I)


def terminating_wall(body):
    """F-61b. A door described as closing an end gets built into a new end wall."""
    if TIGHT_FRAME.search(body):
        return []   # F-65: wide-shot rules do not apply to a frame with no room in it
    if not DOORWORD.search(body):
        return []
    m = TERMINATING.search(body)
    if not m:
        return []
    return [("WARN", "door-as-termination",
             f"{m.group(0)!r} casts the door as the END of a space. Two plate candidates read that "
             "as licence to build a wall across the back of the room and hang the door in it "
             "(F-61b). Describe the door as an OPENING IN a named plane instead - 'the last "
             "opening in the run of glazing, in the same plane as the bays' - never as the thing "
             "that closes, caps or terminates anything.")]


# F-65. A ROOM-PLAN FACT INSIDE A FRAME THAT HOLDS NO ROOM.
# Shot 6B's tight frame was asked for six times and came back MIRRORED every
# time. The cause was one phrase: "the door at the LEFT END OF THE FRONTAGE".
# In a wide plate that locates the door in the room. In a frame that contains
# no room it has no referent except the picture, so it reads as "the door is at
# the LEFT of the frame" -- and the whole composition mirrors to suit, taking
# the subject's profile and both hands with it.
#
# And the phrase was only there because the `door` tripwire, written from a
# WIDE-SHOT fault, demands the door's position be named. A wide-shot guard
# injected a wide-shot fact into a tight frame and flipped it.
TIGHT_FRAME = re.compile(
    r"\bbody of the room lies outside\b|\bno part of the room is in (?:this )?frame\b"
    r"|\bthe room holds no part of it\b|\btight enough that the (?:body of the )?room\b"
    r"|\bfills everything behind (?:him|her|them)\b", re.I)
ROOM_POSITION = re.compile(
    r"\b(?:left|right|far|near) end of (?:the |that )?(?:frontage|shopfront|run)\b"
    r"|\bcounter side\b|\bbanquette side\b|\bperpendicular to the counter\b"
    r"|\bcoplanar with the glazing bays\b|\bdown one side of the room\b", re.I)


def tight_frame(body):
    """F-65. In a frame with no room in it, a room-plan position is read as a
    FRAME position, and the picture mirrors to satisfy it."""
    if not TIGHT_FRAME.search(body):
        return []
    f = []
    for m in ROOM_POSITION.finditer(body):
        f.append(("ERROR", "room-position-in-tight-frame",
                  f"{m.group(0)!r} places something in the ROOM, and this frame declares that the "
                  "room is outside it. With no room to refer to, the model reads it as a position "
                  "in the PICTURE and mirrors the composition to satisfy it — subject, profile and "
                  "both hands with it (F-65). In a tight frame, pin handedness to the subject's own "
                  "body — which cheek, which ear, near hand and far hand — and delete the room."))
    return f


# F-66. NAMING AN ABSENT FITTING PUTS IT IN THE PICTURE.
# The 6B frame obeyed every other instruction and came back with a brass knob
# and escutcheon on the door's inside face. The prompt had said, correctly and
# positively, "this inside face carries green paint, glass and that one brass
# letterplate" -- and then added "the handle is on the street side and stays out
# of sight from in here." The enumeration was sufficient. The trailing clause
# named a handle, and a handle appeared.
FITTING = (r"handles?|knobs?|levers?|push[- ]plates?|kick[- ]?plates?|latch(?:es)?|bolts?"
           r"|hinges?|escutcheons?|letterboxe?s?")
ABSENCE = (r"out of sight|not visible|cannot be seen|can't be seen|is absent|are absent"
           r"|on the (?:street|other|far) side|stays? out of|hidden from|never seen|no \w+ here")
ABSENT_NAMED = re.compile(
    rf"\b(?:{FITTING})\b[^.]{{0,90}}?\b(?:{ABSENCE})\b"
    rf"|\b(?:{ABSENCE})\b[^.]{{0,90}}?\b(?:{FITTING})\b", re.I)


def absent_object(body):
    """F-66. A fitting named inside an absence clause is a fitting requested."""
    f = []
    for m in ABSENT_NAMED.finditer(body):
        f.append(("ERROR", "absent-object-named",
                  f"{m.group(0).strip()[:110]!r} names a fitting in order to say it is not there. "
                  "The model renders what is named: this exact clause put a brass knob and "
                  "escutcheon on the door's inside face in a frame that obeyed everything else "
                  "(F-66). Enumerate what the surface DOES carry and stop — 'green paint, glass "
                  "and one brass letterplate, and the letterplate is the only metal on it'."))
    return f


def location_method(title, body, facts):
    """Leera's rules, for location stills only."""
    if not re.search(r"\blocation\b|\bplate\b|\bestablish", title, re.I):
        return []
    f = []
    if HARD_RAYS.search(body):
        f.append(("WARN", "location:hard-rays",
                  "hard visible rays in a location still. Leera: 'soft sources for interiors — "
                  "hard visible rays usually slop.' This project spent two days measuring "
                  "@cafe_sun to establish that no beam enters the room (F-28); the rule was "
                  "on disk the whole time."))
    if not ANCHOR_HINT.search(body):
        f.append(("WARN", "location:no-anchor",
                  "no named anchor object. Leera asks for one — a sofa, a doorway, a banner — "
                  "so a character can later be placed against a thing rather than at a "
                  "distance. 'One pace short of the glazing' failed three generations; "
                  "'no floor between his foot and the door' worked first try (F-31/33)."))
    if not ANGLE_HINT.search(body):
        f.append(("WARN", "location:no-angle",
                  "no camera angle stated. Leera's default is a declared 3/4 view, and both "
                  "house blogs say the same thing: a 3/4 angle adds depth, which gives the "
                  "camera something to hold onto when it moves."))
    return f


# ------------------------------------------------- ASSET ECONOMY (F-40)
# A conditioning frame is not one image. K6 cost 14 prompt versions and 11
# generations, and every edit afterwards had to keep the frame and the video
# prompt in agreement. That is the real price, and it is only worth paying when
# a state CHANGES INSIDE the shot and no element can carry the change —
# elements are global to a generation, so anything that must look different at
# the start and the end is invisible to them.
#
# The rule is not "do not use frames". It is "say why", once, in the facts file,
# before building one.

FRAME_USE = re.compile(r"\bstart[_ ]image\b|\bend[_ ]image\b|supplied (?:start|end) image", re.I)


def frame_justified(title, body, context, facts):
    """Every conditioning frame names WHICH shot earned it, and why.

    The first version of this rule only checked that the project file had an
    asset_economy section at all — which every project would, one minute after
    reading the docs. It was unprovable and it asked for nothing. Asking per
    shot is both the discipline that matters and a thing a fixture can trigger.
    """
    econ = facts.get("asset_economy", {})
    if not FRAME_USE.search(body + "\n" + context):
        return []
    justified = econ.get("frames_justified", {})
    key = next((k for k in justified if re.search(rf"\b{re.escape(k)}\b", title, re.I)), None)
    if key:
        return []
    return [("ERROR", "frame-unjustified",
             f"this prompt uses a conditioning frame and no entry in "
             f"asset_economy.frames_justified matches {title[:40]!r}. A frame costs many "
             "generations and couples every later edit to it — K6 cost 14 prompt versions "
             "and 11 images. Name the shot and say what state changes inside it that an "
             "element cannot carry, or use elements only.")]


# --------------------------------------------------- RELEASED BUT LOCKED (F-36)
# Twice now the body of a prompt has RETIRED a requirement and POSITIVE LOCKS
# has gone on demanding it:
#   body  "It does NOT have to sit under the letterplate ... those two cannot
#          both be satisfied and the cup's HAND wins"
#   locks "the top of that lid sitting just BELOW the door's brass letterplate"
# and earlier, FRAMING corrected to "WELL LEFT" while LOCKS still said "a little
# left of frame centre". POSITIVE LOCKS is the most authoritative block in the
# prompt, so a stale requirement there outranks the correction that replaced it
# — the letterplate lock is what put the cup in the wrong hand in k6-9.
#
# The pattern is narrow enough to match: the body says a thing is NOT required,
# and the locks assert it anyway.

RELEASE = re.compile(
    r"\b(?:does not|doesn't|need not|does NOT) have to\b\s*(?P<what>[^.\u2014]{5,60})"
    r"|\bit is not required (?:that|to)\b\s*(?P<what2>[^.\u2014]{5,60})", re.I)


def released_but_locked(body):
    f = []
    flat = re.sub(r"[*_`]+", "", body)
    m = re.search(r"^POSITIVE LOCKS\b(.*)$", flat, re.M | re.S)
    if not m:
        return f
    locks = m.group(1).lower()
    for r in RELEASE.finditer(flat[:m.start()]):
        what = (r.group("what") or r.group("what2") or "").strip().lower()
        keys = [w for w in re.findall(r"[a-z]{4,}", what) if w not in STOPWORDS]
        if len(keys) < 2:
            continue
        # The release and the lock rarely use the same preposition: here the body
        # said "under the letterplate" and LOCKS said "BELOW the door's brass
        # letterplate". Requiring two shared words missed it. So one DISTINCTIVE
        # word is enough — a noun long enough to be specific to this prompt —
        # and short words still need two.
        hit = [k for k in keys if k in locks]
        if hit and (max(len(k) for k in hit) >= 8 or len(hit) >= 2):
            f.append(("ERROR", "released-but-locked",
                      f"the body says it does not have to {what!r}, and POSITIVE LOCKS still "
                      f"asserts it ({', '.join(hit)}). LOCKS is the most authoritative block "
                      "here, so a stale requirement in it beats the correction that replaced "
                      "it — this is what put the cup in the wrong hand in k6-9."))
    return f


# ------------------------------------------------ CONTESTED DESTINATION (F-31)
# The same trick as contested-position, applied to the other role a noun plays.
# When K6's destination moved from the middle of the glazing to the door, nine
# sentences kept describing the old one. Three of them named it outright:
#     "the distance between him and the GLASS is closed by HIM WALKING"
#     "he should be nearer the GLASS"
#     "the GLASS is the next thing he would touch"
# while others said "one pace short of the DOOR". A shot has ONE destination.
# Index by that role and two of them cannot both be it.
#
# Note what this does NOT reach: "his shoulders square to the window" and "a
# little left of the centre" were also stale, and neither names a destination.
# They are CONSEQUENCES of the old one. See F-31 for why that class stays manual.

DEST_FRAME = re.compile(
    r"(?:one pace short of|a pace short of|short of|toward[s]?|up to|nearer|closer to"
    r"|distance between him and|next thing he would touch\b[^.]{0,4})"
    r"\s+(?:the|that|its)?\s*([a-z]+)", re.I)
# frontage/wall are SUPERSETS containing both door and glazing, so they conflict
# with nothing and are not counted.
DEST_GROUPS = {"glass": "the glazing", "glazing": "the glazing", "window": "the glazing",
               "panes": "the glazing", "door": "the door", "doorway": "the door",
               "counter": "the counter", "riser": "the stall riser"}


def contested_destination(body):
    seen = {}
    for m in DEST_FRAME.finditer(re.sub(r"[*_`]+", "", body)):
        g = DEST_GROUPS.get(m.group(1).lower())
        if g:
            seen.setdefault(g, m.group(0).strip()[:70])
    if len(seen) > 1:
        return [("CHECK", "contested-destination",
                 f"the shot is given {len(seen)} different destinations: "
                 + " / ".join(f"{k} ({v!r})" for k, v in seen.items())
                 + ". A walk has one end point. When a destination changes, every sentence "
                   "that named the old one has to be retired, and there is no list of those "
                   "— which is how nine of them survived into K6 v9.")]
    return []


# --------------------------------------------------- CONTESTED POSITION (F-30)
# K6 v9 said, four sentences apart:
#     "The green door ... fills the frame directly behind him ... its solid
#      green lower panel behind his legs"
#     "The green panelled stall riser fills the frame directly behind his legs"
# Two objects, one place. The linter reported 0 errors, because this is not a
# vocabulary opposition — door and stall riser are not antonyms, they are both
# correct nouns for this room. What is wrong is that only one thing can be
# immediately behind a man's legs.
#
# It happened the ordinary way: the destination changed from the glazing to the
# door, the new sentence was written, and the old one was left standing. The
# consistency checker groups by SUBJECT, so it filed these under "the view" and
# "counter" and never compared them. Group by PLACE instead.

# Only IMMEDIATE-CONTACT anchors are exclusive. Plenty of things may be loosely
# "behind him" — the room, the tables, the warm half of the picture — and the
# first version of this rule flagged all four of them. What cannot be shared is
# a place touching the body: directly behind him, behind his legs, beside his
# hip. Tight anchors only, and CHECK rather than ERROR, because the reading is
# a human's.
TIGHT_ANCHOR = re.compile(
    r"(?:(?:directly|immediately)\s+(?:behind|in front of)\s+him"
    r"|(?:behind|beside|against|under)\s+his\s+"
    r"(?:legs|leg|shoulder|shoulders|hip|hips|knees|back|heels))", re.I)


def contested_position(body):
    f, claims = [], {}
    flat = re.sub(r"[*_`]+", "", body)
    for m in TIGHT_ANCHOR.finditer(flat):
        place = " ".join(m.group(0).lower().split())
        before = flat[max(0, m.start()-90):m.start()]
        # the head noun is the last plausible noun phrase before the anchor
        n = re.findall(r"\b(?:the|its|a)\s+([a-z][a-z' ]{2,32}?)\s*(?:,|$|\bfills?\b|\bstands?\b|\bruns?\b|\bsits?\b|\bis\b)", before, re.I)
        subj = " ".join(n[-1].lower().split()) if n else before.strip()[-34:]
        claims.setdefault(place, {})[subj] = m.group(0)
    for place, subs in claims.items():
        if len(subs) > 1:
            f.append(("CHECK", "contested-position",
                      f"{len(subs)} different things are each placed {place}: "
                      + " / ".join(repr(s) for s in subs)
                      + ". Only one object can touch a given part of a body. This is the "
                        "residue a changed destination leaves behind, and the consistency "
                        "checker cannot see it — it groups by SUBJECT, and these nouns are "
                        "not opposites, they are both correct names for things in this room."))
    return f


# ------------------------------------------------- SKILL CONFORMANCE (F-29)
# These encode rules that live in the installed `higgsfield-seedance-prompt`
# skill and that this linter had no equivalent for. They were missed for the
# same reason four asset facts were missed: the rules were transcribed into
# TARN_STAGE3_APPROACH.md on 29 Jul and every check since was written against
# the TRANSCRIPTION. A second-hand copy of a rulebook is an asset claim like any
# other, and it had never been checked against the source.

# Match BOTH reference forms in use here. The first version of this regex only
# matched "@tag — description", which is what G3 uses. K5 and K6 open their
# reference lines "@cafe_sun supplies this room …" — so the check found ZERO
# references in two of the three live prompts and would never have fired on
# them at any length. A guard that is silent on two thirds of the corpus
# reports clean and means nothing; found within a minute of first use.
REF_LINE = re.compile(r"^@([A-Za-z0-9_\-]+)\s*(?:[—\-:]\s*|supplies\s+)(.+)$", re.M)
ENVIRONMENT_TAGS = set(FACTS.get("element_rules", {}).get("environment_tags", []))
REF_WORD_BUDGET = _cfg("reference_word_budget", 60)

def skill_conformance(body, is_video):
    f = []

    # 1. "Keep the character description minimal — long appearance text conflicts
    #    with the image and DEGRADES it." The skill's template is one line:
    #    age + role/build + state + unique features + action-critical details.
    #    This is a stated degradation mechanism, not a style preference, and it
    #    is a live candidate for why detailed staging kept being ignored.
    for tag, desc in REF_LINE.findall(body):
        n = len(desc.split())
        if "@" + tag in ENVIRONMENT_TAGS:
            continue          # the skill states this rule for CHARACTER refs only
        if n > REF_WORD_BUDGET:
            f.append(("WARN", "reference-block-length",
                      f"@{tag}'s description is {n} words, over {REF_WORD_BUDGET}. The skill: "
                      "'keep the character description minimal — long appearance text conflicts "
                      "with the image and degrades it.' State only what the image cannot carry: "
                      "small text, logos, colour, action-critical detail."))

    # 2. "Atmosphere in percent / metres", and it should build in steps across
    #    shots. Every TARN prompt says 'fine dust motes hang in the bright air'
    #    with no quantity anywhere.
    for m in re.finditer(r"[^.\n]{0,80}\b(dust|motes|haze|fog|mist|smoke|vapour|vapor)\b[^.\n]{0,80}",
                         body, re.I):
        if not re.search(r"\d+\s*(?:%|per ?cent|m\b|metres?|meters?)", m.group(0), re.I):
            f.append(("WARN", "atmosphere-unquantified",
                      f"'{m.group(1)}' with no density or depth figure — the skill asks for "
                      f"'fog density 40%' or 'haze visible at 15 meters depth', not an adjective: "
                      f"…{m.group(0).strip()[:70]}…"))
            break

    # 3. Timecode format. The skill writes '0.0s to 1.0s — …' and 'HARD CUT' on
    #    its own line. TARN writes '0.0–1.2s —'. Probably harmless; unverified,
    #    which is the point — an undeclared deviation from a stated format.
    if is_video and re.search(r"^\s*\d+\.\d+\s*[–-]\s*\d+\.\d+\s*s\s*—", body, re.M):
        f.append(("WARN", "timecode-format",
                  "beats are written '0.0–1.2s —'; the skill's stated format is "
                  "'0.0s to 1.2s — …'. Deviating may be fine, but it has never been tested."))
    return f


# ---------------------------------------------------- asset claim verification
# THE FAULT CLASS THIS SESSION'S WORST MISS BELONGED TO.
#
# Every check before this one reads the PROMPT. None of them can tell you the
# prompt is faithfully repeating a false fact. On 30 Jul four claims in the
# element-truth document turned out to be wrong about @cafe_int:
#
#   "one continuous horizontal glazing bar at two-thirds height"
#        -> each bay is FOUR lights: one vertical bar AND one horizontal bar
#   "a broad brass strip along its base"
#        -> the brass runs along the TOP of the front, under the wood
#   "deep green PANELLED front"
#        -> the counter front is plain flat green; the stall riser is the panelled one
#   "There is no door in this plate"
#        -> there is a door at the left end of the frontage, and Shot 7 exits through it
#
# Those four were copied verbatim into every K5 prompt for two days. Five frames
# were generated against them. The linter reported 0 errors every time, because
# a false fact stated consistently is internally consistent.
#
# The only cure is evidence: a claim about an asset must be traceable to somebody
# having opened the file and looked, with a proof crop written to disk and a date.
# So the asset ledger stores claims WITH proofs, and this check enforces that
# anything a prompt asserts about an element is backed by one.

def asset_claims(body, facts):
    f, assets = [], facts.get("assets", {})
    if not assets:
        return f
    tags = set(re.findall(r"@[A-Za-z0-9_\-]+", body))
    for tag in sorted(tags):
        rec = assets.get(tag)
        if rec is None:
            f.append(("WARN", "asset-unknown",
                      f"{tag} is used but has no entry in the asset ledger. Every element a "
                      "prompt describes should have one, so its claims can be checked "
                      "against the file rather than against memory."))
            continue
        verified = rec.get("verified", [])
        if not verified:
            f.append(("ERROR", "asset-unverified",
                      f"{tag} has no verified observations. Its description has never been "
                      "checked against the image. Four such claims about @cafe_int were "
                      "wrong for two days and cost five generations. Run "
                      f"`python3 verify_asset.py {tag} --claim ... --box ...` first."))
            continue
        # a claim recorded without a proof crop is an assertion, not an observation
        for v in verified:
            if not v.get("proof"):
                f.append(("ERROR", "asset-claim-unproven",
                          f"{tag}: claim {v.get('claim','?')!r} has no proof crop. "
                          "A claim with no image behind it is how the element-truth "
                          "document acquired four false facts."))
    # ---------------------------------------------------------------- F-25
    # RETIRED WORDING IS CHECKED AGAINST THE WHOLE LEDGER, NOT THE TAGS NAMED.
    #
    # This check used to live inside the per-tag loop above and use a literal
    # substring test. K6-end v4 shipped "brass base strip" and the guard was
    # silent, for TWO independent reasons, either of which alone was fatal:
    #
    #   1. K6 names @cafe_sun and never @cafe_int, and the retired wording
    #      "broad brass strip along its base" was recorded against @cafe_int.
    #      So the loop never opened the list that would have caught it. But the
    #      counter is ONE OBJECT that appears in both plates: a fact retired
    #      about the world does not stop being retired when a prompt cites a
    #      different photograph of the same room.
    #   2. Even in range it would have missed, because the only string it could
    #      recognise was a verbatim copy of the retired sentence — the one form
    #      a rewrite never takes. A false fact survives precisely BY being
    #      paraphrased.
    #
    # So: every retired claim in the ledger, against every prompt, matched on
    # content words co-occurring in one sentence in any order.
    low = body.lower()
    # Strip markdown emphasis BEFORE splitting into sentences. Without this the
    # splitter sees "...moulded capitals.**" — the character before the space is
    # an asterisk, not a full stop — and silently runs the whole POSITIVE LOCKS
    # paragraph together as one "sentence". Co-occurrence tests then match words
    # from opposite ends of a 200-word block and report contradictions that are
    # two correct sentences sitting near each other. Every emphatic block in
    # this project is bolded, so the failure landed exactly on the text that
    # matters most.
    sentences = re.split(r"(?<=[.;])\s+|\n", re.sub(r"[*_`]+", "", low))
    for tag, rec in sorted(assets.items()):
        for v in rec.get("verified", []):
            if v.get("retracted"):
                continue
            for wrong in v.get("supersedes", []):
                if wrong.lower() in low:
                    f.append(("ERROR", "asset-claim-superseded",
                              f"the prompt states {wrong!r} verbatim, which was checked "
                              f"against {tag} and found WRONG on {v.get('date','?')}. "
                              f"The verified claim is: {v.get('claim')!r}."))

            # ---- the paraphrase, which is the form the fault actually takes.
            #
            # My first fix here was a bag-of-words score over the retired
            # wording: fire if ~70% of its content words land in one sentence.
            # It fired on NINE correct sentences in K5, because a correction
            # necessarily reuses most of the retired claim's vocabulary — the
            # true sentence "the broad brass strip runs along the TOP" shares
            # broad/brass/strip with the false "broad brass strip along its
            # base". The words the two share are the SUBJECT; the word that
            # carries the falsity is the one that can be absent. No threshold
            # separates them, and a looser one only trades silence for noise.
            #
            # So the discriminator is not inferable and must be WRITTEN DOWN
            # when the fact is retired: the token groups that, co-occurring in
            # one sentence, make the statement false. Every group must hit.
            for c in v.get("contradicts", []):
                pats, why = c["all"], c.get("why", "")
                for s in sentences:
                    if all(re.search(p, s, re.I) for p in pats):
                        f.append(("ERROR", "asset-claim-superseded",
                                  f"{tag}: {why or 'retired fact restated'} — "
                                  f"{' + '.join(pats)} co-occur in: {s.strip()[:130]!r}. "
                                  f"Verified: {v.get('claim')!r}"))
                        break
    return f


# ------------------------------------------------------------ scope conflict
# K5 v2a carried these two sentences twenty lines apart:
#
#   "the whole figure sits at one COLD temperature from crown to hem"
#   "nothing in the frame is COOLER, bluer ... than @cafe_int already is"
#
# They cannot both hold. The second covers every pixel including him, so it
# overrules the first, and the warm rim came back: head-box 0.05 -> 0.60.
#
# The existing consistency checker missed it because it groups by SUBJECT and
# these sit in different groups — one is "light", one is "colour". The fault is
# not two statements about one subject; it is a statement about EVERYTHING
# silently overruling a statement about ONE THING. That is a scope conflict, and
# it needs its own check.
#
# General shape, worth stating because it will recur outside colour: a global
# quantifier plus a property, and a local exception to that property, are a
# contradiction unless the global explicitly excludes the local.

# The polarity matters, not the vocabulary. "nothing in the frame is cooler"
# FORBIDS coolness everywhere; "the figure sits at one cold temperature" ASSERTS
# it locally. The first version of this check compared which temperature words
# each sentence contained, and the global sentence happened to contain both
# ("grey ... faint warm cast ... nothing is cooler"), so it scored as the same
# side and was skipped. Compare prohibition against assertion instead.

GLOBAL_PROHIBITION = re.compile(
    r"\b(?:nothing|no part|nowhere|none)\b[^.]{0,60}?\b(?:in|of)\s+the\s+"
    r"(?:frame|picture|shot|image)\b[^.]{0,80}?\bis\b\s*(?P<props>[^.]{0,90})", re.I)
LOCAL_SUBJECT = re.compile(r"\b(?:on him|on his|@hero|the man\b|his skin|his face|his hair|"
                           r"the (?:whole )?figure|every edge (?:and rim )?on)\b", re.I)
PROPERTY = re.compile(r"\b(cool(?:er)?|cold(?:er)?|blue(?:r)?|warm(?:er)?|"
                      r"bright(?:er)?|dark(?:er)?|saturated|grey|gray)\b", re.I)

# cool-family words are interchangeable for this purpose: forbidding "cooler"
# forbids "cold" and "grey" on a person just as effectively.
FAMILY = {"cool": "cool", "cooler": "cool", "cold": "cool", "colder": "cool",
          "blue": "cool", "bluer": "cool", "grey": "cool", "gray": "cool",
          "warm": "warm", "warmer": "warm",
          "bright": "bright", "brighter": "bright",
          "dark": "dark", "darker": "dark", "saturated": "saturated"}


def scope_conflict(body):
    f = []
    sents = sentences(body)
    for gi, gs in sents:
        m = GLOBAL_PROHIBITION.search(gs)
        if not m:
            continue
        forbidden = {FAMILY.get(w.lower()) for w in PROPERTY.findall(m.group("props"))}
        forbidden.discard(None)
        if not forbidden:
            continue
        for li, ls in sents:
            if li == gi or not LOCAL_SUBJECT.search(ls):
                continue
            asserted = {FAMILY.get(w.lower()) for w in PROPERTY.findall(ls)}
            clash = forbidden & asserted
            if clash:
                f.append(("ERROR", "scope-conflict",
                          f"a WHOLE-FRAME prohibition on {'/'.join(sorted(clash))} sits "
                          "opposite a claim asserting it about the PERSON. The global "
                          "sentence covers every pixel including him, so it wins:\n"
                          f"        GLOBAL L{gi}: {gs[:150]}\n"
                          f"        LOCAL  L{li}: {ls[:150]}\n"
                          "        K5 v2a shipped exactly this pair and the warm rim came "
                          "back — head-box rim-on-dark 0.05 -> 0.60. Attribute the property "
                          "to NAMED SURFACES and give the person an explicit value of their "
                          "own, rather than forbidding it frame-wide."))
                return f      # one report is enough; they share one cause
    return f


# ---------------------------------------------------------------- cost check
# TARN_HANDOFF and TARN_BUILD_PLAN both price a 12s draft at 42 credits, which is
# the 720p FAST rate. TARN_STAGE3_PROMPTS mandates 720p STD for every draft. The
# real cost of ver3 was 54. Three numbers for one job, in three live documents.

def cost_check(title, body, context):
    f = []
    both = title + "\n" + context
    pricing = (FACTS.get("pricing") or {}).get("per_second", {})
    if not pricing:
        return f
    dur = re.search(r"duration\s*(\d+)", both, re.I) or re.search(r"\b(\d+)s\b", title)
    res = re.search(r"\b(720p|1080p|4K)\b", both)
    mode = re.search(r"mode:\s*(std|fast)", both, re.I)
    claimed = re.search(r"(\d+)\s*cr\b", title)
    if dur and res and mode:
        key = f"{res.group(1)} {mode.group(1).lower()}"
        rate = pricing.get(key)
        if rate:
            real = float(dur.group(1)) * rate
            f.append(("INFO", "cost", f"{dur.group(1)}s at {key} = {real:.0f} credits"))
            if claimed and abs(float(claimed.group(1)) - real) > 1:
                f.append(("ERROR", "cost-mismatch",
                          f"heading says {claimed.group(1)} cr but {dur.group(1)}s at {key} "
                          f"is {real:.0f} cr. The 42-credit figure in the handoff and the "
                          "build plan is the 720p FAST rate; the settings here mandate std."))
    return f


# --------------------------------------------------- sibling conformance
# Every fault of the last three rounds was in the lines just edited, and every
# one was a NEW paragraph failing to do what its neighbours already did:
#   @cup_prop restored without the "…are not in this frame" clause its three
#   siblings all carry; the printed mark described twice in one paragraph.
# Whole-document scans dilute attention across 300 lines when the risk sits in
# five. So: group paragraphs that do the SAME JOB and flag any one missing a
# feature that most of its siblings have. This is the check that maps to how
# the mistakes are actually being made.

ELEMENT_FEATURES = {
    "exclusion clause (the @tarn_under device)": r"not in this (frame|shot)|are not in",
    "identity or invariance assertion":          r"100%\s*(?:matches|that of)|identical (?:in every frame|for the whole)|holds .{0,40}(?:every frame|whole shot)|stays identical|exactly that",
}


def sibling_conformance(body):
    f = []
    m = re.search(r"ACTIVE REFERENCES\n(.*?)(?=\n[A-Z][A-Z /]{3,}\n)", body, re.S)
    if not m:
        return f
    paras = [p.strip() for p in m.group(1).split("\n") if p.strip().startswith("@")]
    if len(paras) < 2:
        return f
    for label, pat in ELEMENT_FEATURES.items():
        rx = re.compile(pat, re.I)
        has = [p for p in paras if rx.search(p)]
        lacks = [p for p in paras if not rx.search(p)]
        if has and lacks and len(has) >= len(paras) / 2:
            for p in lacks:
                f.append(("ERROR", "sibling-conformance",
                          f"{p.split(' ')[0]} has no {label}, but "
                          f"{len(has)} of {len(paras)} element paragraphs do. "
                          "A reference restored or rewritten in isolation is the "
                          "commonest fault on this project."))
    # duplicated content inside one paragraph
    for p in paras:
        STOP = set("the a an and or of in on at to its it is are with for that this "
                   "as by from be been which their his her every all no not".split())
        chunks = [c.strip().lower() for c in re.split(r"[.;]", p) if len(c.strip()) > 45]
        for i, a in enumerate(chunks):
            for b in chunks[i + 1:]:
                sa = {w.strip('",') for w in a.split()} - STOP
                sb = {w.strip('",') for w in b.split()} - STOP
                if len(sa & sb) >= 8:
                    f.append(("WARN", "sibling-conformance",
                              f"{p.split(' ')[0]} says the same thing twice — "
                              f"~{len(sa & sb)} shared words between two clauses. "
                              "Say each important thing once."))
                    break
            else:
                continue
            break
    return f


def sentences(body):
    out = []
    for i, line in enumerate(body.splitlines(), 1):
        s = line.strip()
        if not s or s.isupper():
            continue
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z@*])", s):
            if len(part) > 12:
                out.append((i, part.strip()))
    return out


def consistency(body):
    """Group statements by subject; surface opposing pairs. Returns findings."""
    sents = sentences(body)
    groups = {}
    for subj, pat in SUBJECTS.items():
        p = re.compile(pat, re.I)
        hits = [(i, s) for i, s in sents if p.search(s)]
        if len(hits) > 1:
            groups[subj] = hits
    f = []
    # Repeated acquisition of one object. "lifts it clear" ... "picks it up off
    # the counter" are not opposites, so no antonym pair catches them — but you
    # cannot take hold of the same thing twice without letting go in between.
    ACQUIRE = re.compile(r"closes? around|takes? (?:its weight|hold)|picks? .{0,12}up|"
                         r"lifts? .{0,15}(?:clear|off)", re.I)
    for subj in ("cup", "his hands"):
        hits = groups.get(subj, [])
        acq = [(i, s) for i, s in hits if ACQUIRE.search(s)]
        if len(acq) > 1:
            f.append(("CHECK", f"consistency:{subj} re-acquired",
                      f"{len(acq)} separate statements take hold of it — you cannot "
                      "pick up the same object twice without setting it down between:\n"
                      + "".join(f"        L{i}: {s[:150]}\n" for i, s in acq)))
    for subj, hits in groups.items():
        for a, b in OPPOSITIONS:
            ra, rb = re.compile(a, re.I), re.compile(b, re.I)
            side_a = [(i, s) for i, s in hits if ra.search(s)]
            side_b = [(i, s) for i, s in hits if rb.search(s)]
            # Two people doing opposite things is not a contradiction — she lets
            # go, he takes hold. Drop the pair if the two sides belong to
            # different actors. This was the dominant false positive.
            def actor(ss):
                txt = " ".join(s for _, s in ss).lower()
                her = len(re.findall(SECOND_PARTY, txt, re.I))
                his = len(re.findall(PROTAGONIST, txt, re.I))
                return "her" if her > his else ("his" if his > her else "?")
            if side_a and side_b and actor(side_a) != actor(side_b) \
               and "?" not in (actor(side_a), actor(side_b)):
                continue
            if side_a and side_b:
                f.append(("CHECK", f"consistency:{subj}",
                          "opposing statements about the same subject — read both:\n"
                          + "".join(f"        L{i}: {s[:150]}\n" for i, s in side_a[:2])
                          + "        ---- vs ----\n"
                          + "".join(f"        L{i}: {s[:150]}\n" for i, s in side_b[:2])))
    return groups, f

# ---------------------------------------------------------------- extraction

def blocks(md_text):
    """Yield (title, prompt_body, context) per fenced block.

    `context` is the prose around the fence — the change-log tables, the settings
    line, the notes, the Gates. It is not sent to the model, but it DESCRIBES the
    prompt, so a stale row there ("the cup never reaching his mouth" after a sip
    was added) is a live contradiction for whoever reads it next. Consistency and
    timing checks see it; the block-structure rules do not.

    Context is the prose on BOTH sides of the fence, up to the next heading. It
    used to be the prose before it only — which meant the Gates line, which is
    always written after the block, was invisible to every context check. The
    gate-completeness check could not see the gate it was asking for.
    """
    title, out = "(untitled)", []
    in_fence, buf, pre = False, [], []
    pending = None          # a finished block still collecting its trailing prose
    for line in md_text.splitlines():
        h = re.match(r"^#{1,3}\s+(.*)", line)
        if h and not in_fence:
            if pending:
                out.append(pending); pending = None
            title = h.group(1).strip(); pre = []
        if line.strip().startswith("```"):
            if in_fence:
                if pending:
                    out.append(pending)
                pending = (title, "\n".join(buf), "\n".join(pre))
                buf = []; pre = []
            in_fence = not in_fence
            continue
        if in_fence:
            buf.append(line)
        else:
            pre.append(line)
            if pending:     # trailing prose belongs to the block just closed
                pending = (pending[0], pending[1], pending[2] + "\n" + line)
    if pending:
        out.append(pending)
    return out

# ---------------------------------------------------------------- checks

def lint(title, body, context=""):
    f = []                                    # (level, rule, detail)
    lines = body.splitlines()

    # -- structure. Video and image prompts have different shapes; a video
    #    prompt is the one that has time in it.
    is_video = bool(re.search(r"FORMAT MODE|HARD CUT|\d+\.\d+\s*[–-]\s*\d+\.\d+s", body))
    first = next((l.strip() for l in lines if l.strip()), "")
    if is_video:
        if not first.startswith("SCENE CONTEXT"):
            f.append(("ERROR", "no-style-prefix",
                      f"prompt must open on SCENE CONTEXT, opens on {first[:40]!r}"))
        need = REQUIRED_BLOCKS
    else:
        need = ["FRAMING", "THE LIGHT", "POSITIVE LOCKS"]
        f.append(("INFO", "mode", "image prompt — video block rules skipped"))
    for b in need:
        if b not in body:
            f.append(("ERROR", "missing-block", f"{b} block absent"))

    f += room_plan(body)
    f += depth_order(body)
    f += terminating_wall(body)
    f += tight_frame(body)
    f += absent_object(body)

    # -- Lesson 1, negations
    for i, l in enumerate(lines, 1):
        if SANCTIONED_NEGATION.search(l):
            continue
        for m in NEGATION.finditer(l):
            f.append(("WARN", "negation",
                      f"L{i}: {m.group(0)!r} in …{l[max(0,m.start()-45):m.end()+45].strip()}…"))

    # -- Lesson 4, un-actionable numbers
    for i, l in enumerate(lines, 1):
        for m in BANNED_NUMERIC.finditer(l):
            f.append(("ERROR", "abstract-number",
                      f"L{i}: {m.group(0)!r} — describe the outcome instead"))

    # -- banned names
    for i, l in enumerate(lines, 1):
        for m in BANNED_NAMES.finditer(l):
            f.append(("ERROR", "banned-name", f"L{i}: {m.group(0)!r}"))

    # -- FOV must come from the anchor table
    for i, l in enumerate(lines, 1):
        for m in re.finditer(r"(\d+)\s*°|(\d+)\s*degree field", l):
            v = int(m.group(1) or m.group(2))
            if v not in FOV_TABLE:
                f.append(("ERROR", "fov-off-table",
                          f"L{i}: {v}° is not an anchor-table value {sorted(FOV_TABLE)}"))

    # -- speeds need units
    for i, l in enumerate(lines, 1):
        if re.search(r"\b(?:slowly|quickly|fast|slow)\b", l, re.I) and "km/h" not in l:
            if re.search(r"\bcamera\b|\bdoll(y|ies)\b|\barc\b|\bpush(es)?\b|\bpull", l, re.I):
                f.append(("WARN", "unitless-speed",
                          f"L{i}: camera speed without km/h — …{l.strip()[:70]}…"))

    # -- timecode arithmetic
    tcs = [(float(a), float(b)) for a, b in
           re.findall(r"(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)s", body)]
    if tcs:
        span_end = max(b for _, b in tcs)
        m = re.search(r"duration\s*(\d+)", body, re.I)
        for (a, b) in tcs:
            if b < a:
                f.append(("ERROR", "timecode", f"reversed range {a}–{b}s"))
        gaps = sorted(tcs)
        for (a1, b1), (a2, b2) in zip(gaps, gaps[1:]):
            if a2 > b1 + 0.001 and a2 - b1 > 0.01 and (a1, b1) != (a2, b2):
                f.append(("WARN", "timecode-gap",
                          f"uncovered {b1}s → {a2}s"))
        f.append(("INFO", "timecode-span", f"beats cover 0 → {span_end}s"))

    # -- @tags used
    tags = sorted(set(re.findall(r"@[A-Za-z0-9_\-]+", body)))
    f.append(("INFO", "tags", ", ".join(tags) if tags else "none"))

    # -- multishot hygiene
    if "HARD CUT" in body or "multishot" in body.lower():
        if "no drift mid-segment" not in body:
            f.append(("WARN", "multishot", "missing 'no drift mid-segment'"))
        if "does not cut on its own" not in body:
            f.append(("WARN", "multishot", "missing the self-cutting lock"))

    # -- LENS 3: tripwires. A ruling written in one document, enforced against
    #    text written in another. Keyword trigger on a semantic rule.
    for tw in FACTS.get("tripwires", []):
        pat, ctx = re.compile(tw["pattern"], re.I), re.compile(tw["context"], re.I)
        # A tripwire with "requires" fires only when the disambiguator is ABSENT.
        # Requiring the right phrasing beats forbidding the wrong one — the same
        # reason prompts are written positively. Regex cannot see "both of them
        # are on it", but it can see whether "opposite her" was said.
        req = re.compile(tw["requires"], re.I) if tw.get("requires") else None
        if req and req.search(body):
            continue
        for i, l in enumerate(lines, 1):
            if pat.search(l) and (ctx.pattern == "." or ctx.search(body)):
                f.append(("ERROR", "tripwire",
                          f"L{i}: {pat.search(l).group(0)!r} — {tw['ruling']}"))
                break   # one report per rule is enough

    # -- ELEMENT SCOPE. Elements are global to a generation, never time-scoped.
    er = FACTS.get("element_rules", {})
    envs = [t for t in set(re.findall(r"@[A-Za-z0-9_\-]+", body))
            if t in er.get("environment_tags", [])]
    if len(envs) > er.get("max_environment_tags", 99):
        f.append(("ERROR", "element-scope",
                  f"{len(envs)} environment elements ({', '.join(sorted(envs))}) — {er['ruling']}"))

    # -- LOCK COVERAGE. A structural feature named in the body must be locked.
    locks = body.split("POSITIVE LOCKS")[-1] if "POSITIVE LOCKS" in body else ""
    for trigger, required in er.get("locks_must_mention", {}).items():
        if trigger.startswith("_"):
            continue
        if re.search(trigger, body, re.I) and not re.search(required, locks, re.I):
            f.append(("ERROR", "lock-coverage",
                      f"body mentions {trigger!r} but POSITIVE LOCKS never secures "
                      f"{required!r} — {er['locks_must_mention']['_why']}"))

    # -- IMAGE-PROMPT RULES. Learned from the K5 / K6 batches.
    if not is_video:
        if not re.search(r"16:9|landscape rectangle|wider than it is tall", body, re.I):
            f.append(("ERROR", "aspect-in-body",
                      "image prompt does not state 16:9 in its text. K5 came back "
                      "portrait 3:4 despite the UI setting — say it in the prompt too."))
        if not re.search(r"colour of th\w+ room|white balance|kelvin|does not shift|"
                         r"colour .{0,20}fixed", body, re.I):
            f.append(("WARN", "colour-lock",
                      "no white-balance / colour lock. Room colour temperature drifted "
                      "between K5 generations. State the sources in Kelvin and describe "
                      "what each surface reads as."))
        if re.search(r"counter|bar top|table|worktop", body, re.I) and \
           not re.search(r"\bacross it\b|\balong it\b|square on", body, re.I):
            f.append(("WARN", "camera-axis",
                      "a long object is in frame but the camera axis is not stated as "
                      "across or along it — the difference changes the shot completely."))

    # -- VIDEO-PROMPT RULE. Frame-relative positions drift once the camera moves.
    if is_video:
        for i, l in enumerate(lines, 1):
            for m in re.finditer(r"\b(?:at|to|in|on) (?:the )?frame (?:left|right|centre|center)\b"
                                 r"|\b(?:down|along) the (?:left|right) side\b", l, re.I):
                near = l.lower()
                if "terminal" in near or "end state" in near or "final framing" in near:
                    continue
                f.append(("WARN", "frame-relative-in-video",
                          f"L{i}: {m.group(0)!r} — safe in a still, drifts in a video. "
                          "Anchor to a named object or make it a terminal state."))

    # -- LENS 5: invertible directions. Every one is a bit the model may flip.
    dirs = {}
    for i, l in enumerate(lines, 1):
        for m in DIRECTION.finditer(l):
            dirs.setdefault(m.group(0).lower(), []).append(i)
    if dirs:
        summary = ", ".join(f"{k}×{len(v)}" for k, v in sorted(dirs.items()))
        f.append(("WARN", "direction-audit",
                  f"{sum(len(v) for v in dirs.values())} direction words — {summary}. "
                  "Each must be load-bearing or deleted. Look them up in "
                  "tarn_facts.json > geometry; never re-derive them."))

    # -- sibling conformance: a rewritten paragraph must do what its neighbours do.
    f += sibling_conformance(body)

    # -- added 30 Jul, all from measured failures in G3 v3. See TARN_FINDINGS.md.
    if is_video:
        f += performance_budget(body)
        f += achievability(body, context)
    f += gate_completeness(body, context, is_video)
    f += asset_claims(body, FACTS)
    f += skill_conformance(body, is_video)
    f += contested_position(body)
    f += contested_destination(body)
    f += released_but_locked(body)
    f += frame_justified(title, body, context, FACTS)
    f += light_direction(body)
    f += location_method(title, body, FACTS)
    f += scope_conflict(body)
    f += measured_locks(body, context)
    f += cost_check(title, body, context)

    # -- timing coherence: durations in prose must match the declared structure.
    f += timing_coherence(body, context)

    # -- LENS 4: internal contradiction. Includes the surrounding prose, because
    #    a change-log row that describes the prompt can go stale against it.
    groups, cons = consistency(body + "\n" + context)
    f += cons
    f.append(("INFO", "subjects",
              ", ".join(f"{k}({len(v)})" for k, v in sorted(groups.items(),
                                                            key=lambda kv: -len(kv[1])))))

    # -- LENS 6: continuity. Read the matrix, do not recall it.
    shots = sorted({int(s) for s in re.findall(r"SHOTS?\s+(\d+)", title.upper())} |
                   {int(s) for s in re.findall(r"\b(\d+)\s*\+\s*(?=\d)", title)})
    shots += [int(s) for s in re.findall(r"\+\s*(\d+)", title)]
    cont = FACTS.get("continuity", {})
    for s in sorted(set(shots)):
        row = cont.get(str(s))
        if row:
            f.append(("INFO", f"continuity shot {s}",
                      "wardrobe=%s | cup=%s | phone=%s | city=%s | cafe=%s | score=%s | horizon=%s" % tuple(row)))
    return f


def dump_subject(text, only, subject):
    """Print every statement about one subject, across all blocks. Use this
    after any edit: read the whole group, not the line you changed."""
    for title, body, _ in blocks(text):
        if only and only.lower() not in title.lower():
            continue
        pat = SUBJECTS.get(subject)
        if not pat:
            print(f"unknown subject. known: {', '.join(SUBJECTS)}"); return
        p = re.compile(pat, re.I)
        hits = [(i, s) for i, s in sentences(body) if p.search(s)]
        print(f"\n{'='*72}\n{title}  —  every statement about '{subject}'\n{'='*72}")
        for i, s in hits:
            print(f"  L{i:>4}  {s}")


def main():
    args = [a for a in sys.argv[1:]]
    if "--project" in args:
        i = args.index("--project"); del args[i:i + 2]
    path = pathlib.Path(args[0])
    only = sys.argv[sys.argv.index("--block") + 1] if "--block" in sys.argv else None
    text = path.read_text(encoding="utf-8")
    if "--subject" in sys.argv:
        dump_subject(text, only, sys.argv[sys.argv.index("--subject") + 1])
        return
    worst = 0
    for title, body, context in blocks(text):
        if only and only.lower() not in title.lower():
            continue
        findings = lint(title, body, context)
        errs = [x for x in findings if x[0] == "ERROR"]
        warns = [x for x in findings if x[0] == "WARN"]
        checks = [x for x in findings if x[0] == "CHECK"]
        print(f"\n{'='*72}\n{title}\n{'='*72}")
        print(f"  {len(errs)} error · {len(warns)} warn · {len(checks)} consistency-check")
        for lvl, rule, detail in findings:
            if lvl == "INFO":
                print(f"    · {rule}: {detail}")
        for lvl, rule, detail in findings:
            if lvl == "CHECK":
                print(f"  [{lvl}] {rule}: {detail}")
        for lvl, rule, detail in findings:
            if lvl not in ("INFO", "CHECK"):
                print(f"  [{lvl}] {rule}: {detail}")
        worst = max(worst, 1 if errs else 0)
    print("\n  After ANY edit, run:  lint_prompt.py FILE --block X --subject <name>")
    print("  Read the whole subject group. Five shipped contradictions were all")
    print("  created by fixing one place and leaving the other.\n")
    sys.exit(worst)


if __name__ == "__main__":
    main()
