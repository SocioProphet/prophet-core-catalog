#!/usr/bin/env python3
"""Type the estate's referenced models as cat:Model with real digests (gap-a).

Joins the model records the estate actually references (datasets/models/models.jsonl —
the same IDs that repos `cat:dependsOn` in estate-edges.ttl) to the real model-layer
content digests + licenses captured from the local ollama registry manifests
(datasets/models/runtime-model-digests.jsonl). Where a referenced model's name matches a
captured digest, it emits `a cat:Model ; cat:modelDigest ; cat:license` ONTO the same
res:<id> IRI the dependency edges point at — so the governance check (MIT/Apache-only)
covers the models the estate really depends on, not a parallel node set.

Models with no local digest (hosted APIs like gpt-*/claude-*/gemini-*, or sizes not present
locally) are left as `cat:EstateResource` references — honest: there is no content digest
for them here.

Stdlib only. Deterministic (sorted by id).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIGESTS = ROOT / "datasets" / "models" / "runtime-model-digests.jsonl"
MODELS = ROOT / "datasets" / "models" / "models.jsonl"
OUT = ROOT / "datasets" / "estate-graph" / "estate-models.ttl"

CAT = "https://socioprophet.github.io/ontogenesis/domains/estate-catalog#"
BASE = "https://catalog.socioprophet.ai/estate/"
PREFIXES = f"""@prefix cat:  <{CAT}> .
@prefix res:  <{BASE}resource/> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""
DIGEST_RE = re.compile(r"^sha256:[a-fA-F0-9]{64}$")


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def load(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def emit() -> int:
    if not (DIGESTS.exists() and MODELS.exists()):
        print("ERR: missing datasets/models/{runtime-model-digests,models}.jsonl", file=sys.stderr)
        return 2

    by_name: dict[str, dict] = {}
    by_family: dict[str, list[dict]] = {}
    for d in load(DIGESTS):
        by_name[d["name"]] = d
        by_family.setdefault(d["name"].split(":")[0], []).append(d)

    def lookup(name: str) -> dict | None:
        if name in by_name:
            return by_name[name]
        if f"{name}:latest" in by_name:
            return by_name[f"{name}:latest"]
        fam = by_family.get(name.split(":")[0], [])
        return fam[0] if len(fam) == 1 else None

    # join referenced models -> real digest/license, keyed by the edge-node id
    typed: dict[str, dict] = {}
    for m in load(MODELS):
        mid, name = m.get("id"), m.get("name")
        if not mid or not name:
            continue
        d = lookup(name)
        if not d:
            continue
        if not DIGEST_RE.match(d.get("modelDigest", "")) or not d.get("license"):
            continue
        typed.setdefault(mid, {"name": name, "digest": d["modelDigest"], "license": d["license"]})

    if not typed:
        print("ERR: no referenced model joined to a real digest", file=sys.stderr)
        return 2

    lines = [PREFIXES, ""]
    for mid in sorted(typed):
        t = typed[mid]
        lines.append(f"res:{mid} a cat:Model ;")
        lines.append(f'  cat:modelDigest "{t["digest"]}" ;')
        lines.append(f'  cat:license "{esc(t["license"])}" ;')
        lines.append(f'  rdfs:label "{esc(t["name"])}" ;')
        lines.append('  dct:subject "model" .')
        lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: typed {len(typed)} referenced models as cat:Model (real digests) -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(emit())
