#!/usr/bin/env python3
"""rules-policies extractor (ds.rules-policies) — HOOK/thin.

Emits ONE repo's contribution shard: the repo's machine-readable governance
surface — OPA/Rego policies, `*.rules.yaml` / `policy*.y*ml`, CODEOWNERS, and
git-ops control registries (controls.yaml) — so the catalog can enumerate which
rules each repo declares and enforce cross-repo consistency.

    python3 extractors/extract_rules_policies.py <repo_path> <repo_name> [--out FILE]

Record schema (v0):

    {"id": "pol-<sha1[:10]>",             # stable per (repo, file)
     "kind": "rego" | "policy-yaml" | "codeowners" | "controls-registry",
     "name": "<file stem>",
     "sources": [{"repo","file","line"}],
     "provider_reference": false}

Read-only, stdlib-only, deterministic. Thin by design: it inventories policy
FILES today; a later revision can descend into individual rules.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_10, run  # noqa: E402


def _kind(relpath: str) -> str | None:
    name = os.path.basename(relpath).lower()
    if relpath.endswith(".rego"):
        return "rego"
    if name == "codeowners" or relpath.upper().endswith("/CODEOWNERS"):
        return "codeowners"
    if name in ("controls.yaml", "controls.yml"):
        return "controls-registry"
    if (("policy" in name or "policies" in name or name.endswith(".rules.yaml")
         or name.endswith(".rules.yml")) and (name.endswith((".yaml", ".yml")))):
        return "policy-yaml"
    return None


def extract(repo_path: str, repo_name: str) -> list[dict]:
    records: list[dict] = []
    for path in iter_files(repo_path, {".rego", ".yaml", ".yml", ""}):
        relpath = rel(repo_path, path)
        kind = _kind(relpath)
        if not kind:
            continue
        if read_text(path) is None and kind != "codeowners":
            continue
        records.append({
            "id": "pol-" + sha1_10(f"{repo_name}\x00{relpath}"),
            "kind": kind,
            "name": Path(relpath).stem or Path(relpath).name,
            "sources": [{"repo": repo_name, "file": relpath, "line": 1}],
            "provider_reference": False,
        })
    records.sort(key=lambda r: r["id"])
    return records


if __name__ == "__main__":
    raise SystemExit(run("rules-policies", extract))
