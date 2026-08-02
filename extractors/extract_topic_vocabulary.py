#!/usr/bin/env python3
"""topic-vocabulary extractor (ds.topic-vocabulary) — HOOK/thin.

Emits ONE repo's contribution shard: the repo's declared topic vocabulary —
Markdown headings from README/docs — so the catalog can build an estate-wide
concept index (which repo talks about what) without any embedding dependency.

    python3 extractors/extract_topic_vocabulary.py <repo_path> <repo_name> [--out FILE]

Record schema (v0):

    {"id": "topic-<sha1[:10]>",           # stable per normalized term
     "term": "<heading text>",
     "level": <int>,                       # markdown heading depth 1..6
     "sources": [{"repo","file","line"}],  # every heading occurrence
     "use_count": <int>,
     "provider_reference": false}

Same-term headings across files/repos collapse to one record (like the regex
`id`), so the catalog-side assembler merges them across repo shards.

Read-only, stdlib-only, deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_10, run  # noqa: E402

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_NORM = re.compile(r"[^a-z0-9]+")
_STOP = {"the", "a", "an", "of", "and", "to", "for", "with", "in", "on"}


def _normalize(term: str) -> str:
    return _NORM.sub(" ", term.lower()).strip()


def extract(repo_path: str, repo_name: str) -> list[dict]:
    agg: dict[str, dict] = {}
    for path in iter_files(repo_path, {".md", ".markdown"}):
        text = read_text(path)
        if text is None:
            continue
        relpath = rel(repo_path, path)
        in_fence = False
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = _HEADING.match(line)
            if not m:
                continue
            level = len(m.group(1))
            term = m.group(2).strip()
            norm = _normalize(term)
            if not norm or norm in _STOP or len(norm) < 2:
                continue
            tid = "topic-" + sha1_10(norm)
            src = {"repo": repo_name, "file": relpath, "line": lineno}
            rec = agg.get(tid)
            if rec is None:
                agg[tid] = {
                    "id": tid,
                    "term": term,
                    "level": level,
                    "sources": [src],
                    "use_count": 1,
                    "provider_reference": False,
                }
            else:
                rec["sources"].append(src)
                rec["use_count"] += 1
                rec["level"] = min(rec["level"], level)
    for rec in agg.values():
        rec["sources"].sort(key=lambda s: (s["repo"], s["file"], s["line"]))
    return sorted(agg.values(), key=lambda r: r["id"])


if __name__ == "__main__":
    raise SystemExit(run("topic-vocabulary", extract))
