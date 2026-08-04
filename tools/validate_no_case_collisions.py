#!/usr/bin/env python3
"""Refuse any two tracked paths that differ only by case.

Git is case-sensitive; macOS (APFS) and Windows are not. When both `Noetica.jsonl` and
`noetica.jsonl` are tracked, only one can exist on disk, so checkout writes both blobs to the
same file and the last one wins. Git then reports the loser as modified — permanently. The
working tree can never be clean, `git checkout -- <path>` cannot fix it, and every unrelated
PR opened on a Mac carries a spurious multi-thousand-line diff that looks like the author
rewrote a dataset they never touched.

That is not a cosmetic problem here. This catalog shards `contributions/<repo>.jsonl` by each
record's `sources[].repo`, so a case-variant filename means a case-variant REPO NAME, and the
estate graph starts believing one repo is two. Blast-radius edges split, source attributions
split, and both halves look plausible.

Checks the index rather than the filesystem, since a case-insensitive filesystem is precisely
what hides the collision.
"""
from __future__ import annotations

import collections
import json
import subprocess
import sys


def tracked_paths() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True, check=True).stdout
    return [p for p in out.split("\0") if p]


def collisions(paths: list[str]) -> dict[str, list[str]]:
    by_lower: dict[str, list[str]] = collections.defaultdict(list)
    for p in paths:
        by_lower[p.lower()].append(p)
    return {k: sorted(v) for k, v in by_lower.items() if len(v) > 1}


def main() -> int:
    paths = tracked_paths()
    found = collisions(paths)

    # Prove the check bites before trusting a pass from it: a synthetic pair that differs only
    # by case must be caught. A collision detector only ever run against a clean tree is
    # indistinguishable from `return 0`.
    probe = ["a/B.txt", "a/b.txt", "a/c.txt"]
    if list(collisions(probe)) != ["a/b.txt"]:
        print("FAIL: self-test — the collision detector did not catch a known case-variant pair",
              file=sys.stderr)
        return 1
    if collisions(["a/b.txt", "a/c.txt"]):
        print("FAIL: self-test — the collision detector fired on distinct paths", file=sys.stderr)
        return 1

    for _, variants in sorted(found.items()):
        print(f"FAIL: paths differ only by case — only one can exist on a case-insensitive "
              f"filesystem: {variants}", file=sys.stderr)
        print("      Pick the canonical casing, merge the contents, then drop the other with "
              "`git update-index --force-remove <path>`.", file=sys.stderr)

    ok = not found
    print(json.dumps({"ok": ok, "tracked": len(paths), "collisions": len(found),
                      "selfTest": "detector proven to bite"}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
