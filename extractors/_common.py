"""Shared, stdlib-only helpers for catalog contribution extractors.

Keep this dependency-free: the reusable CI workflow fetches `extractors/` from
this repo and runs it inside arbitrary caller repos with nothing but a stock
Python 3. No third-party imports here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Callable, Iterable, Iterator

# Directories that never carry first-party source worth cataloging.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", "target",
    ".next", ".nuxt", ".output", "coverage", ".turbo", ".cache", "vendor",
    "third_party", "third-party", ".terraform", ".idea", ".vscode",
    "site-packages", ".tox", ".gradle", "out",
}

# Hard cap so a pathological file can never wedge CI.
MAX_FILE_BYTES = 2_000_000


def iter_files(repo_path: str, exts: Iterable[str]) -> Iterator[str]:
    """Yield absolute paths of files under repo_path whose suffix is in exts.

    Deterministic order (sorted at every level) so downstream output is stable.
    """
    exts = {e.lower() for e in exts}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith(".git"))
        for name in sorted(files):
            _, ext = os.path.splitext(name)
            if ext.lower() in exts:
                yield os.path.join(root, name)


def read_text(path: str) -> str | None:
    """Best-effort UTF-8 read; skips huge or binary files. None on failure."""
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None
        with open(path, "r", encoding="utf-8", errors="strict") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def rel(repo_path: str, path: str) -> str:
    """Repo-relative POSIX path for a source location (stable across machines)."""
    return os.path.relpath(path, repo_path).replace(os.sep, "/")


def sha1_10(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def emit(records: list[dict], out_path: str | None) -> None:
    """Write records as JSONL (sorted by id) to out_path or stdout.

    Sorting + sort_keys makes the shard deterministic: identical repo -> identical bytes.
    """
    records = sorted(records, key=lambda r: r.get("id", ""))
    lines = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records]
    body = "\n".join(lines)
    if body:
        body += "\n"
    if out_path and out_path != "-":
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(body)
    else:
        sys.stdout.write(body)


def base_argparser(dataset: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=f"Extract the {dataset} contribution shard for one repo.",
    )
    p.add_argument("repo_path", help="Filesystem root of the repo to scan (read-only).")
    p.add_argument("repo_name", help="Logical repo name for sources[].repo (matches src.<repo>).")
    p.add_argument("--out", default="-", help="Output JSONL path; default stdout.")
    return p


def run(dataset: str, extract: Callable[[str, str], list[dict]]) -> int:
    args = base_argparser(dataset).parse_args()
    if not os.path.isdir(args.repo_path):
        sys.stderr.write(f"error: {args.repo_path} is not a directory\n")
        return 2
    records = extract(os.path.abspath(args.repo_path), args.repo_name)
    emit(records, args.out)
    return 0
