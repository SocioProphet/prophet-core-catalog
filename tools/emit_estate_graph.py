#!/usr/bin/env python3
"""Emit the estate graph (P2 population) — real catalog sources -> typed RDF ABox.

Reads every sources/src.*.json manifest and emits datasets/estate-graph/estate-graph.ttl:
each source becomes a cat:CatalogEntry (typed by the ontogenesis estate-catalog binding
vocabulary, which is KKO-grounded) describing a cat:EstateResource. This is the
population layer the estate-catalog TBox (ontogenesis #131) was built to type — turning
"read every repo" into "reason over one graph".

Stdlib only (matches the extractor ethos): TTL is emitted as text. Validation +
SPARQL live-proof is a separate step (tools/validate_estate_graph.py).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"
OUT = ROOT / "datasets" / "estate-graph" / "estate-graph.ttl"

CAT = "https://socioprophet.github.io/ontogenesis/domains/estate-catalog#"
BASE = "https://catalog.socioprophet.ai/estate/"

PREFIXES = f"""@prefix cat:  <{CAT}> .
@prefix ent:  <{BASE}entry/> .
@prefix res:  <{BASE}resource/> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def org_of(provider: str) -> str:
    # provider is "Org/repo"; the accountable owner is the org.
    return provider.split("/", 1)[0] if provider else "unknown"


def slug(src_id: str) -> str:
    # src.agent-machine -> agent-machine (local name after the src. prefix)
    return src_id[4:] if src_id.startswith("src.") else src_id


def emit() -> int:
    files = sorted(SOURCES.glob("src.*.json"))
    if not files:
        print("ERR: no sources/src.*.json found", file=sys.stderr)
        return 2

    lines = [PREFIXES, ""]
    n = 0
    for f in files:
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERR parsing {f.name}: {exc}", file=sys.stderr)
            return 2
        sid = s.get("id", "")
        if not sid:
            continue
        name = esc(s.get("name", sid))
        provider = s.get("provider", "")
        owner = esc(org_of(provider))
        domain = esc(s.get("domain", "unknown"))
        prov = s.get("provenance", {}) or {}
        canonical = esc(prov.get("canonical_url", ""))
        lic = (s.get("license", {}) or {}).get("class", "unknown")
        local = slug(sid)

        # The governed catalog RECORD.
        lines.append(f"ent:{local} a cat:CatalogEntry ;")
        lines.append(f'  cat:catalogId "{esc(sid)}" ;')
        lines.append(f'  cat:owner "{owner}" ;')
        lines.append('  cat:status "active" ;')
        lines.append(f'  dct:title "{name}" ;')
        if canonical:
            lines.append(f'  cat:provenanceRef "{canonical}" ;')
        lines.append(f'  dct:license "{esc(lic)}" ;')
        lines.append(f"  cat:describes res:{local} .")
        # The estate RESOURCE the record is about.
        lines.append(f"res:{local} a cat:EstateResource ;")
        lines.append(f'  dct:subject "{domain}" ;')
        lines.append(f'  rdfs:label "{name}" .')
        lines.append("")
        n += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: emitted {n} catalog entries -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(emit())
