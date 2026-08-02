#!/usr/bin/env python3
"""ci-workflows-tests extractor (ds.ci-workflows-tests) — HOOK/thin.

Emits ONE repo's contribution shard: the repo's CI surface — GitHub Actions
workflows and their jobs, plus a rollup of the repo's test files — so the
catalog can reason about which gates each repo actually runs and where its
tests live (feeds the estate-ci-health / gate-gap audits).

    python3 extractors/extract_ci_workflows_tests.py <repo_path> <repo_name> [--out FILE]

Record schema (v0, stable enough to build on; refine as consumers appear):

    {"id": "ci-<sha1[:10]>",              # stable per (repo, kind, key)
     "kind": "workflow" | "test-suite",
     "name": "<workflow name | test dir>",
     "triggers": ["push", "pull_request", ...],   # workflow only
     "jobs": ["build", "validate", ...],           # workflow only
     "test_count": <int>,                          # test-suite only
     "sources": [{"repo","file","line"}],
     "provider_reference": false}

Read-only, stdlib-only, deterministic. YAML is parsed with a deliberately small
line-scanner (no PyYAML dependency) — good enough for on/jobs/name keys.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_10, run  # noqa: E402

TEST_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".rs", ".go"}
_TEST_NAME = re.compile(r"(^|[._-])(test|spec)([._-]|$)|(^|/)tests?/", re.IGNORECASE)
_TOP_KEY = re.compile(r"^([A-Za-z_][\w-]*):")
_LIST_ITEM = re.compile(r"^\s*-\s*([A-Za-z_][\w./-]*)")
# job/trigger scanning is a heuristic line-scan; these keys are structural noise
# that must never be reported as a job name or a trigger.
_NOISE = {
    "runs-on", "steps", "needs", "if", "name", "uses", "with", "env",
    "permissions", "strategy", "matrix", "outputs", "container", "services",
    "defaults", "concurrency", "timeout-minutes", "continue-on-error",
    "branches", "tags", "paths", "types", "branches-ignore", "paths-ignore",
    "tags-ignore", "inputs", "secrets", "cron",
}


def _parse_workflow(text: str) -> tuple[str, list[str], list[str]]:
    """Return (name, triggers, jobs) from a minimal line scan of an Actions YAML."""
    name, triggers, jobs = "", [], []
    lines = text.splitlines()
    section = None
    for ln in lines:
        m = _TOP_KEY.match(ln)
        if m:
            key = m.group(1)
            section = key if key in ("on", "jobs") else None
            if key == "name":
                after = ln.split(":", 1)[1].strip().strip("'\"")
                if after:
                    name = after
            if key == "on":
                inline = ln.split(":", 1)[1].strip().lstrip("[").rstrip("]")
                for t in re.split(r"[,\s]+", inline):
                    t = t.strip().strip("'\"")
                    if t:
                        triggers.append(t)
            continue
        if section == "on":
            m2 = re.match(r"^\s{1,4}([A-Za-z_][\w-]*):", ln)
            li = _LIST_ITEM.match(ln)
            if m2:
                triggers.append(m2.group(1))
            elif li:
                triggers.append(li.group(1))
        elif section == "jobs":
            m2 = re.match(r"^\s{1,4}([A-Za-z_][\w-]*):", ln)
            if m2:
                jobs.append(m2.group(1))
    triggers = sorted(t for t in set(triggers) if t not in _NOISE)
    jobs = sorted(j for j in set(jobs) if j not in _NOISE)
    return name, triggers, jobs


def extract(repo_path: str, repo_name: str) -> list[dict]:
    records: list[dict] = []
    # 1) workflows
    wf_dir = os.path.join(repo_path, ".github", "workflows")
    if os.path.isdir(wf_dir):
        for path in iter_files(wf_dir, {".yml", ".yaml"}):
            text = read_text(path)
            if text is None:
                continue
            relpath = rel(repo_path, path)
            name, triggers, jobs = _parse_workflow(text)
            records.append({
                "id": "ci-" + sha1_10(f"{repo_name}\x00workflow\x00{relpath}"),
                "kind": "workflow",
                "name": name or Path(relpath).stem,
                "triggers": triggers,
                "jobs": jobs,
                "sources": [{"repo": repo_name, "file": relpath, "line": 1}],
                "provider_reference": False,
            })
    # 2) test-suite rollup, one record per directory that holds test files
    test_dirs: dict[str, int] = {}
    for path in iter_files(repo_path, TEST_EXTS):
        relpath = rel(repo_path, path)
        if _TEST_NAME.search(relpath):
            d = str(Path(relpath).parent)
            test_dirs[d] = test_dirs.get(d, 0) + 1
    for d, count in test_dirs.items():
        records.append({
            "id": "ci-" + sha1_10(f"{repo_name}\x00test-suite\x00{d}"),
            "kind": "test-suite",
            "name": d,
            "test_count": count,
            "sources": [{"repo": repo_name, "file": d, "line": 0}],
            "provider_reference": False,
        })
    records.sort(key=lambda r: r["id"])
    return records


if __name__ == "__main__":
    raise SystemExit(run("ci-workflows-tests", extract))
