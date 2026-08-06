#!/usr/bin/env python3
"""
Edit inside ONE named prompt block, or refuse.

WHY THIS EXISTS
---------------
Twice in one session an edit landed in the wrong copy of the text:

  * the position and rail blocks written for the live K5 prompt went into the
    HISTORICAL k5-23 block, because `text.replace(old, new, 1)` hits the first
    occurrence in the file and the history sits above the live prompt;
  * a `two-thirds height` correction had to be applied to one of two identical
    paragraphs, and the wrong one was nearly patched.

Both were caught only by verifying the exported text afterwards. That is luck,
not process: the file holds every superseded version on purpose, so identical
sentences are the NORM here, and any whole-file string edit is a coin toss.

THE RULE
    Never edit a prompt by searching the whole file. Name the block, and let the
    tool refuse if the target is ambiguous or absent inside it.

Usage
  python3 patch_block.py --block "K5-start v5" --show          # print it
  python3 patch_block.py --block "K5-start v5" --old "..." --new "..."
  python3 patch_block.py --list                                # block names
  python3 patch_block.py --block "K5-start v5" --export OUT.txt

  FILE is OPTIONAL and comes first if you give it. Without it the block is
  looked up across every ledger the film declares in its `prompts` role.

FK-37 — WHY THE FILE IS OPTIONAL NOW
  Every other tool in this kit takes `--block "NAME"` and resolves the film
  itself. This one alone required a positional FILE, and the difference is
  invisible in a runbook full of the other form: the documented command was
  written as `patch_block.py --show "G3 v4"`, argparse bound "G3 v4" to `file`,
  and the tool died with a FileNotFoundError traceback on a path that was never
  a path. An interface that is unique among its siblings will be called the way
  the siblings are called.
"""
import argparse, hashlib, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

# For the side effect: stdout must not depend on the host locale (tools/_utf8.py).
import _utf8  # noqa: F401,E402
from lint_prompt import blocks


def fence_span(lines, title_pred):
    """Return (start_fence_idx, end_fence_idx, title) for the matching block."""
    title, spans = "(untitled)", []
    in_fence, start = False, None
    for i, line in enumerate(lines):
        h = re.match(r"^#{1,4}\s+(.*)", line)
        if h and not in_fence:
            title = h.group(1).strip()
        if line.strip().startswith("```"):
            if in_fence:
                spans.append((start, i, title))
            else:
                start = i
            in_fence = not in_fence
    hits = [s for s in spans if title_pred(s[2])]
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--block")
    ap.add_argument("--old")
    ap.add_argument("--new")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--export")
    a = ap.parse_args()

    if not a.block and not a.list:
        ap.error("--block is required (or --list)")

    def _read(path):
        """Refuse readably. A traceback is not a phase result -- the same rule
        verify.py is built on, and this file was the one place that broke it."""
        try:
            return path.read_text(encoding="utf-8").split("\n")
        except FileNotFoundError:
            print(f"\n  ! no such file: {str(path)!r}")
            print("    FILE is optional and comes FIRST. To name a block, use --block:")
            print(f'      python3 patch_block.py --block "{a.block or "NAME"}" --show\n')
            return None
        except (IsADirectoryError, PermissionError, UnicodeDecodeError) as ex:
            print(f"\n  ! cannot read {str(path)!r}: {type(ex).__name__}\n")
            return None

    if a.file:
        candidates = [pathlib.Path(a.file)]
    else:
        # Every ledger the film declares. The `prompts` role is plural on films
        # that keep their history in several files, and a block named in one of
        # four was previously unreachable without naming the file by hand.
        import _project as P  # FK-34: lazily, so `patch_block.py FILE ...` needs no film
        candidates = [f for f in P.file_list("prompts") if f.exists()]
        if not candidates:
            print("  the film declares no prompt ledger that exists")
            return 1

    if a.list:
        for c in candidates:
            if len(candidates) > 1:
                print(f"\n  --- {c.name}")
            ls = _read(c)
            if ls is None:
                return 1
            for _, _, t in fence_span(ls, lambda t: True):
                print("  " + t[:90])
        return 0

    # Find the block across every candidate, and REFUSE when several hold it --
    # the same rule this tool already applies within one file, applied across
    # the set. A block name that is ambiguous between ledgers is exactly the
    # condition that put two edits in historical blocks.
    found = []
    for c in candidates:
        ls = _read(c)
        if ls is None:
            return 1
        for h in fence_span(ls, lambda t: a.block.lower() in t.lower()):
            found.append((c, ls, h))
    if not found:
        where = ", ".join(c.name for c in candidates)
        print(f"  no block matching {a.block!r} in {where}")
        return 1
    if len({c for c, _, _ in found}) > 1:
        print(f"  {a.block!r} matches blocks in {len({c for c, _, _ in found})} ledgers — "
              f"REFUSING, name the file:")
        for c, _, (_, _, t) in found:
            print(f"    {c.name}: {t[:80]}")
        return 1
    p = found[0][0]
    lines = found[0][1]
    hits = [h for _, _, h in found]
    if len(hits) > 1:
        print(f"  {a.block!r} matches {len(hits)} blocks — REFUSING, be more specific:")
        for _, _, t in hits:
            print("    " + t[:90])
        return 1
    s, e, title = hits[0]
    body = "\n".join(lines[s + 1:e])

    # F-45. Two edits in this project landed in historical blocks. Every block
    # is now labelled, so REFUSE rather than trust the operator to read the
    # heading — the whole point of a marker is that a machine can act on it.
    # Scoped to EDITS: --show and --export must still work on dead blocks,
    # because reading the evidence is exactly how the ledger gets written.
    if a.old is not None or a.new is not None:
        # F-53. This scanned back a FIXED 12 lines from the fence and reported
        # UNMARKED on any block whose preamble was longer than that — G7 carries
        # its marker 14 lines up, behind a blocked-on note and an Elements line,
        # so a correctly-marked DRAFT was refused. A fixed window is a guess about
        # how much prose an author will write. Scan to the PREVIOUS HEADING, which
        # is the actual boundary of the block, and take the nearest marker inside it.
        status = "UNMARKED"
        for k in range(s, -1, -1):
            m = re.search(r"<!--\s*status:\s*(\w+)", lines[k])
            if m:
                status = m.group(1); break
            if lines[k].startswith("#") and k != s:
                break
        if status not in ("LIVE", "DRAFT"):
            print(f"  REFUSING to edit a {status} block: {title[:60]!r}")
            print("  Only LIVE and DRAFT blocks may be edited.")
            print("  `python3 staleness.py --list` shows which block is live for each role.")
            return 1


    if a.show:
        print(body)
        return 0

    if a.export:
        out = pathlib.Path(a.export)
        # Hash the bytes that are WRITTEN, not the source block they came from.
        # This hashed `body` (with its ** markers) while writing the stripped
        # text, so every sha reported all session identified a string that is
        # not in any file. A hash that names something other than the artefact
        # handed over is worse than no hash: it looks like verification.
        written = body.replace("**", "")
        out.write_text(written, encoding="utf-8")
        h = hashlib.sha256(written.encode()).hexdigest()[:12]
        print(f"  exported {title[:50]!r} -> {out}  ({len(body.split())} words, sha {h})")
        return 0

    if a.old is None or a.new is None:
        ap.error("--old and --new are both required")
    n = body.count(a.old)
    if n == 0:
        print(f"  {a.old[:70]!r} does NOT occur in {title[:50]!r} — refusing.")
        print("  (it may exist elsewhere in the file; that is exactly the trap this tool exists for)")
        return 1
    if n > 1:
        print(f"  {a.old[:70]!r} occurs {n}x inside the block — ambiguous, refusing.")
        return 1
    lines[s + 1:e] = body.replace(a.old, a.new).split("\n")
    p.write_text("\n".join(lines), encoding="utf-8")
    print(f"  patched {title[:60]!r} — 1 occurrence replaced, no other block touched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
