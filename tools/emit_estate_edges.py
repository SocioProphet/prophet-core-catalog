#!/usr/bin/env python3
"""Emit cross-catalog dependency edges (P3) — real usage/consumer/import edges.

Turns the flat P2 inventory into a real DEPENDENCY graph so blast-radius traversals
go live. Reads the catalog's own inventory datasets and emits datasets/estate-graph/
estate-edges.ttl as cat:dependsOn edges between cat:EstateResource nodes:

  * models.jsonl    used_by[]   -> <consumer repo> cat:dependsOn <model>
  * services.jsonl  consumers[] -> <consumer>      cat:dependsOn <service>
  * ontologies.jsonl imports[]  -> <ontology>      cat:dependsOn <imported file>

Consumer/repo node IRIs use the same res:<slug> scheme as the P2 source nodes, so a
model used_by "noetica" JOINS the res:noetica node emitted from src.noetica — one graph.

All edges are cat:dependsOn (range cat:EstateResource) — SHACL-safe: no coercion into
cat:Model/cat:Infrastructure, which carry required fields these inventory records lack
(model refs here have no modelDigest; cat:Model typing awaits the model-store join).

Stdlib only. Deterministic (sorted).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "datasets"
OUT = DS / "estate-graph" / "estate-edges.ttl"

CAT = "https://socioprophet.github.io/ontogenesis/domains/estate-catalog#"
BASE = "https://catalog.socioprophet.ai/estate/"

PREFIXES = f"""@prefix cat:  <{CAT}> .
@prefix res:  <{BASE}resource/> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""


def slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "unknown"


def load(name: str) -> list[dict]:
    f = DS / name
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def emit() -> int:
    nodes: dict[str, tuple[str, str]] = {}   # slug -> (subject, label)
    edges: set[tuple[str, str]] = set()       # (from_slug, to_slug)

    def node(sl: str, subject: str, label: str) -> None:
        nodes.setdefault(sl, (subject, label))

    # models: used_by repo depends on the model
    for m in load("models/models.jsonl"):
        mid = m.get("id")
        if not mid:
            continue
        node(mid, "model", esc(m.get("name", mid)))
        for u in m.get("used_by") or []:
            us = slug(u)
            node(us, "repo", esc(u))
            edges.add((us, mid))

    # services: consumer depends on the service
    for s in load("services-endpoints/services.jsonl"):
        sid = s.get("id") or s.get("name")
        if not sid:
            continue
        node(sid, "service", esc(s.get("name", sid)))
        for c in s.get("consumers") or []:
            cs = slug(c)
            node(cs, "consumer", esc(c))
            edges.add((cs, sid))

    # ontologies: an ontology depends on the files it imports
    for o in load("ontologies/ontologies.jsonl"):
        oid = o.get("id")
        if not oid:
            continue
        node(oid, "ontology", esc(o.get("name", oid)))
        for imp in o.get("imports") or []:
            isl = slug(imp)
            node(isl, "ontology-file", esc(imp))
            edges.add((oid, isl))

    if not edges:
        print("ERR: no edges derived", file=sys.stderr)
        return 2

    lines = [PREFIXES, ""]
    for sl in sorted(nodes):
        subject, label = nodes[sl]
        lines.append(f"res:{sl} a cat:EstateResource ;")
        lines.append(f'  dct:subject "{subject}" ;')
        lines.append(f'  rdfs:label "{label}" .')
    lines.append("")
    for frm, to in sorted(edges):
        lines.append(f"res:{frm} cat:dependsOn res:{to} .")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: emitted {len(nodes)} nodes, {len(edges)} dependsOn edges -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(emit())
