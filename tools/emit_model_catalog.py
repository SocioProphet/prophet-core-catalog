#!/usr/bin/env python3
"""Emit cat:Model instances from real local model digests (gap-a remediation).

Reads datasets/models/runtime-model-digests.jsonl (real model-layer content digests
captured from the local ollama registry manifests) and emits
datasets/estate-graph/estate-models.ttl typing each as a cat:Model with its REAL
modelDigest and declared license. This finally satisfies the cat:Model SHACL
(modelDigest sha256 + license) with real data — the join the flat inventory lacked —
and lets the estate reason MIT/Apache-only over models it actually references.

Stdlib only. Deterministic.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "datasets" / "models" / "runtime-model-digests.jsonl"
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


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower()).strip("-") or "unknown"


def emit() -> int:
    if not SRC.exists():
        print(f"ERR: {SRC} not found", file=sys.stderr)
        return 2
    recs = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    lines = [PREFIXES, ""]
    n = 0
    for r in recs:
        digest = r.get("modelDigest", "")
        lic = r.get("license", "")
        if not DIGEST_RE.match(digest):
            print(f"ERR: {r.get('name')} has non-sha256 modelDigest {digest!r}", file=sys.stderr)
            return 2
        if not lic:
            print(f"ERR: {r.get('name')} has no license", file=sys.stderr)
            return 2
        iri = f"mdl-local-{slug(r.get('name', digest))}"
        lines.append(f"res:{iri} a cat:Model ;")
        lines.append(f'  cat:modelDigest "{digest}" ;')
        lines.append(f'  cat:license "{esc(lic)}" ;')
        lines.append(f'  rdfs:label "{esc(r.get("name", iri))}" ;')
        lines.append('  dct:subject "model" .')
        lines.append("")
        n += 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: emitted {n} cat:Model instances (real digests) -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(emit())
