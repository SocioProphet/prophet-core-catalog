#!/usr/bin/env python3
"""ci-workflows-tests extractor (ds.ci-workflows-tests).

Emits ONE repo's contribution shard covering BOTH primary files of the dataset:
GitHub Actions workflows (`wf-*` ids -> datasets/ci-workflows-tests/ci-workflows.jsonl)
and the repo's test suites (`ts-*` ids -> datasets/ci-workflows-tests/tests.jsonl), in
the SAME record schemas as those files (see SCHEMA.md). The two families are told apart
by id prefix (`wf-` / `ts-`), which is how the harvest assembler routes them back.

    python3 extractors/extract_ci_workflows_tests.py <repo_path> <repo_name> [--out FILE]

`wf id = wf-<sha1[:10] of repo/path>`; `ts id = ts-<sha1[:10] of repo|path|framework>`
— both stable, idempotent, byte-compatible with the central harvest. YAML is read with
a small stdlib line scanner (no PyYAML). Read-only, deterministic.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_hex, run  # noqa: E402

_TOP_KEY = re.compile(r"^([A-Za-z_][\w-]*):")
_NOISE = {
    "runs-on", "steps", "needs", "if", "name", "uses", "with", "env", "permissions",
    "strategy", "matrix", "outputs", "container", "services", "defaults", "concurrency",
    "timeout-minutes", "continue-on-error", "branches", "tags", "paths", "types",
    "branches-ignore", "paths-ignore", "tags-ignore", "inputs", "secrets", "cron",
}
_FAIL_OPEN = [
    (re.compile(r"continue-on-error:\s*true"), "continue-on-error:true"),
    (re.compile(r"\|\|\s*true"), "|| true"),
    (re.compile(r"\bexit\s+0\b"), "exit 0"),
    (re.compile(r"\|\|\s*echo"), "|| echo (swallow)"),
]

_TEST_FRAMEWORKS = {
    "pytest": (re.compile(r"(^|/)(test_[^/]+\.py|conftest\.py)$"), "test_*.py / conftest.py"),
    "jest-vitest": (re.compile(r"\.(test|spec)\.(t|j)sx?$"), "*.test.ts / *.spec.js"),
    "cargo": (re.compile(r"(^|/)tests?/.+\.rs$|(^|/)[^/]+\.rs$"), "rust #[test]"),
    "go": (re.compile(r"_test\.go$"), "*_test.go"),
}


def _parse_workflow(text: str):
    name, triggers, jobs = "", [], []
    section = None
    for ln in text.splitlines():
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
                triggers += [t.strip().strip("'\"") for t in re.split(r"[,\s]+", inline) if t.strip()]
            continue
        if section == "on":
            m2 = re.match(r"^\s{1,4}([A-Za-z_][\w-]*):", ln)
            li = re.match(r"^\s*-\s*([A-Za-z_][\w./-]*)", ln)
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


def _workflow_records(repo, repo_path) -> list[dict]:
    out = []
    wf_dir = os.path.join(repo_path, ".github", "workflows")
    if not os.path.isdir(wf_dir):
        return out
    for path in iter_files(wf_dir, {".yml", ".yaml"}):
        text = read_text(path)
        if text is None:
            continue
        relpath = rel(repo_path, path)
        name, triggers, jobs = _parse_workflow(text)
        fail_open = sorted({label for rx, label in _FAIL_OPEN if rx.search(text)})
        gating = bool(jobs) and any(t in ("pull_request", "push", "merge_group") for t in triggers)
        out.append({
            "id": "wf-" + sha1_hex(f"{repo}/{relpath}", 10),
            "repo": repo, "path": relpath, "type": "github-actions",
            "name": name or Path(relpath).stem, "triggers": triggers, "jobs": jobs,
            "gating": gating, "fail_open_signals": fail_open, "last_status": None,
        })
    return out


def _test_records(repo, repo_path) -> list[dict]:
    # group test files by (framework, containing dir); tested_target = that dir's leaf.
    groups: dict[tuple[str, str], list[str]] = {}
    for path in iter_files(repo_path, {".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go"}):
        relpath = rel(repo_path, path)
        for fw, (rx, _desc) in _TEST_FRAMEWORKS.items():
            if fw == "cargo":
                if not relpath.endswith(".rs"):
                    continue
                # a .rs file counts as a test suite if it is under a tests/ dir OR
                # actually declares #[test] / #[tokio::test] (not just mentions it).
                under_tests = "/tests/" in ("/" + relpath) or relpath.startswith("tests/")
                if not under_tests:
                    txt = read_text(path)
                    if not txt or ("#[test]" not in txt and "#[tokio::test]" not in txt):
                        continue
            elif not rx.search(relpath):
                continue
            d = str(Path(relpath).parent)
            groups.setdefault((fw, d), []).append(relpath)
            break
    out = []
    for (fw, d), files in groups.items():
        tested = Path(d).name or Path(d).parent.name or repo
        # crude test_count: count test functions/cases across the group's files
        count = 0
        for f in files:
            txt = read_text(os.path.join(repo_path, f))
            if not txt:
                continue
            if fw == "pytest":
                count += len(re.findall(r"^\s*def\s+test_\w+", txt, re.MULTILINE))
            elif fw == "jest-vitest":
                count += len(re.findall(r"\b(it|test)\s*\(", txt))
            elif fw == "cargo":
                count += len(re.findall(r"#\[(?:tokio::)?test\]", txt))
            elif fw == "go":
                count += len(re.findall(r"^func\s+Test\w+", txt, re.MULTILINE))
        out.append({
            "id": "ts-" + sha1_hex(f"{repo}|{d}|{fw}", 10),
            "repo": repo, "path": d, "framework": fw,
            "test_count": count, "file_count": len(files), "tested_target": tested,
        })
    return out


def extract(repo_path: str, repo_name: str) -> list[dict]:
    records = _workflow_records(repo_name, repo_path) + _test_records(repo_name, repo_path)
    return sorted(records, key=lambda r: r["id"])


if __name__ == "__main__":
    raise SystemExit(run("ci-workflows-tests", extract))
