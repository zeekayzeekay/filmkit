#!/usr/bin/env python3
"""
THE RECEIPT — the only thing that lets a generation fire.

    preflight goes fully green  ->  a receipt is written for THAT EXACT PROMPT
    a generation is attempted   ->  the gate demands the matching receipt

WHY IT IS KEYED ON THE PROMPT AND NOT ON TIME
---------------------------------------------
"preflight was run recently" is not a fact about the prompt about to be fired.
The origin project has already paid for that gap once: a prompt was fired that
did not match its own exported file, and the difference was caught by eye. F-37
exists because of it, and `check_fullread` already hashes the export to make an
attestation un-recyclable -- edit one word and the hash moves.

The receipt uses THE SAME SCHEME as that attestation, deliberately.
`check_fullread`'s own comment says it: *one artefact, one hash -- two schemes
for the same thing is a way to attest to nothing.* So this module owns the hash,
and both `preflight.py` and `gate.py` import it rather than each computing their
own.

WHAT A GREEN PREFLIGHT MEANS
----------------------------
Every phase PASS, including `full-read` and `manual` -- which is to say a person
has read the exported prompt end to end and signed for it. The automatic phases
alone are not enough: a gate that fired on those would pass a prompt nobody had
read, which is exactly the fault F-37 was written about.

WHAT THE RECEIPT CANNOT DO
--------------------------
It cannot know whether the prompt is any good. It says: this text, in this film,
at this fact revision, under this kit version, passed every gate, and a person
signed the read. Nothing more.
"""
import hashlib, json, pathlib, re

DIRNAME = ".filmkit/receipts"
STALE_AFTER_HOURS = 24


def normalise(text):
    """
    The bytes on disk and the bytes in a tool call are never quite the same:
    trailing spaces, CRLF, a stray blank line at the end. Hashing raw text would
    make the gate fail for reasons that have nothing to do with the prompt.

    Both sides normalise identically, and BOTH hashes are recorded so a mismatch
    can be diagnosed rather than merely refused.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.strip().split("\n")]
    return "\n".join(lines)


def digest(text):
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def raw_digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def short(h):
    return h[:12]


def path_for(film_dir, text):
    return pathlib.Path(film_dir) / DIRNAME / f"{short(digest(text))}.json"


def write(film_dir, text, *, block, fact_rev, kit_version, phases, stamp):
    """
    `stamp` is passed in rather than read from the clock, so that a caller in a
    replayed or recorded run controls it. A receipt whose own timestamp came from
    somewhere the caller cannot see is a receipt nobody can reproduce.
    """
    p = path_for(film_dir, text)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "_what": "Written by preflight on an ALL-GREEN run. The gate refuses any "
                 "generation whose prompt does not hash to this file's name.",
        "prompt_sha256": digest(text),
        "prompt_sha256_raw": raw_digest(text),
        "prompt_words": len(text.split()),
        "block": block,
        "fact_rev": fact_rev,
        "kit_version": kit_version,
        "phases": phases,
        "written_utc": stamp,
    }, indent=2), encoding="utf-8")
    return p


def read(film_dir, text):
    p = path_for(film_dir, text)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def age_hours(receipt, now_utc):
    """Hours between the receipt and `now_utc`, both ISO-8601 Z strings."""
    import datetime as _dt
    try:
        a = _dt.datetime.fromisoformat(receipt["written_utc"].replace("Z", "+00:00"))
        b = _dt.datetime.fromisoformat(now_utc.replace("Z", "+00:00"))
        return (b - a).total_seconds() / 3600.0
    except Exception:
        return None


def check(receipt, *, fact_rev, kit_version, now_utc):
    """
    Every reason this receipt does not authorise a fire, as a list. A gate that
    reports the first failure teaches you to fix one thing and try again; a gate
    that reports all of them lets you fix the situation.
    """
    bad = []
    if receipt is None:
        return ["no receipt for this exact prompt"]
    if receipt.get("fact_rev") != fact_rev:
        bad.append(f"receipt was written at fact_rev {receipt.get('fact_rev')}, "
                   f"the film is now at {fact_rev} — the facts moved under it")
    if receipt.get("kit_version") != kit_version:
        bad.append(f"receipt was written under kit {receipt.get('kit_version')}, "
                   f"running {kit_version}")
    failed = [k for k, v in (receipt.get("phases") or {}).items() if not v]
    if failed:
        bad.append(f"phases not green in that run: {', '.join(sorted(failed))}")
    if not (receipt.get("phases") or {}):
        bad.append("receipt records no phases at all")
    age = age_hours(receipt, now_utc)
    if age is None:
        bad.append("receipt has no readable timestamp")
    elif age > STALE_AFTER_HOURS:
        bad.append(f"receipt is {age:.0f}h old (limit {STALE_AFTER_HOURS}h)")
    return bad
