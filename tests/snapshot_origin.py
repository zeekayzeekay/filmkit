#!/usr/bin/env python3
"""
SNAPSHOT A PROJECT'S OWN GUARD SCRIPTS, AND HASH THEM IN THE SAME BREATH.

    python tests/snapshot_origin.py <film-dir> <snapshot-dir>

`dual_run.py` refuses to run without a `_SHA256SUMS.txt` beside the scripts it is
comparing against. That refusal is FK-01: a transfer once reported success for
fifteen files and served six from a two-day-old snapshot, and an acceptance gate
run on stale sources certifies the kit against a film that no longer exists.

But requiring a manifest and providing no portable way to make one is half a
rule. `sha256sum` is not a Windows command, and this kit is meant to run there.

THE POINT OF DOING BOTH AT ONCE
-------------------------------
The hash must be taken **in the same operation that copies**, from the same read.
Hashing afterwards, as a second step, verifies that the copy matches the copy —
which is exactly the thing that was already true, and exactly the reassurance
that let six stale files through.

WHAT THIS IS FOR
----------------
Preserving the PRE-EXTRACTION state of a film's own tools, so the kit's claim to
reproduce them can be checked. Run it once, before migrating a film onto the kit,
and keep the snapshot.
"""
import hashlib, pathlib, sys

# The fourteen guard scripts a film carried before extraction, plus its facts
# file. Named rather than globbed: a glob would sweep up whatever else happens to
# be in the directory, and a snapshot that quietly includes a scratch file is a
# snapshot nobody can compare against later.
SCRIPTS = ["lint_prompt.py", "verify_asset.py", "compare_asset.py", "shotmap.py",
           "staleness.py", "preflight.py", "checklist.py", "guard_coverage.py",
           "crossshot.py", "selections.py", "patch_block.py", "frames_check.py",
           "measure.py", "stale_neighbours.py"]


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, dst = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
    if not src.is_dir():
        raise SystemExit(f"\n  ! {src} is not a directory\n")
    dst.mkdir(parents=True, exist_ok=True)

    wanted = list(SCRIPTS) + [f.name for f in sorted(src.glob("*_facts.json"))]
    lines, missing, n = [], [], 0
    for name in wanted:
        f = src / name
        if not f.exists():
            missing.append(name)
            continue
        data = f.read_bytes()                     # ONE read
        (dst / name).write_bytes(data)            # copied from it
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}")   # hashed from it
        n += 1

    (dst / "_SHA256SUMS.txt").write_text("\n".join(sorted(lines)) + "\n", encoding="utf-8")

    print(f"\n  snapshot of {src.name} -> {dst}")
    print(f"  {n} file(s) copied and hashed in one pass\n")
    for line in sorted(lines):
        print(f"    {line[:16]}…  {line.split('  ', 1)[1]}")
    if missing:
        print(f"\n  not present in {src.name}, and that may be correct:")
        for m in missing:
            print(f"    -- {m}")
        print("  A film that never had one of these simply never had it. But if you expected")
        print("  it, look now: an origin snapshot missing a script silently narrows every")
        print("  comparison made against it.")
    print(f"\n  Use it:  python tests/dual_run.py --origin-scripts {dst} --film {src}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
