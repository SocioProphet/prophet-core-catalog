#!/usr/bin/env python3
"""rules-policies extractor (ds.rules-policies).

Emits ONE repo's contribution shard: one record per machine-readable GOVERNANCE
surface in <repo_path> — OPA/Rego, Kyverno/Gatekeeper policy-as-code, k8s RBAC,
SHACL shape graphs, gitleaks secret rulesets, JSON-Schema gates, WallGuard
information-barrier docs, and custom gate scripts — in the SAME record schema as
`datasets/rules-policies/policies.jsonl` (see SCHEMA.md).

    python3 extractors/extract_rules_policies.py <repo_path> <repo_name> [--out FILE]

`id = pol-<sha1[:10] of repo\\0path>` — stable + idempotent per policy file. (This
recomputes ids deterministically; they may differ from the hand-seeded corpus, which
the harvest replaces on the first live run.) Read-only, stdlib-only, deterministic.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_hex, run  # noqa: E402

_ENFORCING = {"rego", "kyverno", "gatekeeper", "gitleaks", "rbac", "shacl"}


def _first_line(text: str) -> str:
    for ln in text.splitlines():
        s = ln.strip()
        if s:
            return s[:120]
    return ""


def _classify(relpath: str, text: str):
    """Return (name, kind, engine, intent) or None."""
    name = Path(relpath).stem
    low = relpath.lower()
    base = os.path.basename(low)

    if low.endswith(".rego"):
        decisions = re.findall(r"^\s*(allow|deny|violation|warn)\b", text, re.MULTILINE)
        intent = _first_line(text)
        if decisions:
            intent += " | decisions: " + ", ".join(sorted(set(decisions)))
        return name, "policy-as-code", "rego", intent[:200]

    if low.endswith(".shacl.ttl") or ("sh:NodeShape" in text and low.endswith(".ttl")):
        shapes = re.findall(r"(\w+)\s+a\s+sh:NodeShape", text)
        n = text.count("sh:NodeShape")
        intent = f"{n} SHACL NodeShape(s)"
        if shapes:
            intent += "; targets: " + ", ".join(sorted(set(shapes))[:5])
        return name, "shacl", "shacl", intent[:200]

    if low.endswith((".yaml", ".yml")):
        if "kyverno.io" in text or re.search(r"kind:\s*ClusterPolicy|kind:\s*Policy\b", text):
            title = re.search(r"policies\.kyverno\.io/title:\s*(.+)", text)
            return name, "policy-as-code", "kyverno", (title.group(1).strip() if title else "Kyverno policy")[:200]
        if "ConstraintTemplate" in text or "gatekeeper" in low or "constraints.gatekeeper.sh" in text:
            return name, "policy-as-code", "gatekeeper", _first_line(text)[:200]
        if re.search(r"kind:\s*(Cluster)?Role(Binding)?\b", text):
            k = re.search(r"kind:\s*(\w+)", text)
            return name, "access", "rbac", f"RBAC {k.group(1) if k else 'Role'}"
        if "gitleaks" in low:
            return name, "gate", "gitleaks", "Secret-scanning ruleset (gitleaks)"

    if base.endswith(".gitleaks.toml") or base == ".gitleaks.toml" or base == "gitleaks.toml":
        return name, "gate", "gitleaks", "Secret-scanning ruleset (gitleaks)"

    if base.endswith(".schema.json") and ("gate" in base or "policy" in base or "guard" in base):
        return name, "gate", "json-schema", _first_line(text)[:200]

    if low.endswith(".md") and ("wallguard" in low or "information-barrier" in low
                                or "information_barrier" in low or "WallGuard" in text):
        return name, "access", "wallguard", "WallGuard visibility/access control"

    if (("gate" in base or "guard" in base) and low.endswith((".py", ".sh"))
            and (low.startswith("scripts/") or "/scripts/" in ("/" + low) or "/ci/" in ("/" + low))):
        return name, "gate", "custom", _first_line(text)[:200]

    return None


def extract(repo_path: str, repo_name: str) -> list[dict]:
    records: list[dict] = []
    for path in iter_files(repo_path, {".rego", ".ttl", ".yaml", ".yml", ".toml", ".json", ".md", ".py", ".sh"}):
        relpath = rel(repo_path, path)
        text = read_text(path)
        if text is None:
            continue
        got = _classify(relpath, text)
        if not got:
            continue
        name, kind, engine, intent = got
        records.append({
            "id": "pol-" + sha1_hex(f"{repo_name}\x00{relpath}", 10),
            "name": name, "kind": kind, "engine": engine,
            "repo": repo_name, "path": relpath, "line": 1,
            "intent": intent, "enforced": engine in _ENFORCING, "ref_count": 0,
            "sources": [{"repo": repo_name, "file": relpath, "line": 1}],
        })
    records.sort(key=lambda r: r["id"])
    return records


if __name__ == "__main__":
    raise SystemExit(run("rules-policies", extract))
