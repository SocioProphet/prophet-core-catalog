#!/usr/bin/env python3
"""Validate the estate graph + run the live-proof reasoning queries.

Over the emitted population (estate-graph.ttl) + dependency edges (estate-edges.ttl),
against the VENDORED ontogenesis estate-catalog vocabulary + SHACL:

  1. parse    — the emitted graph is well-formed Turtle;
  2. conform  — every instance SHACL-conforms to the binding vocabulary (real
                instances vs the real TBox, not fixtures);
  3. reason   — real questions answered over the graph, including BLAST RADIUS
                (transitive cat:dependsOn) — the point of the graph: reason over
                the estate, don't read every repo.

Exit codes: 0 = ok; 1 = conformance/reason failure; 2 = usage/parse error.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from rdflib import Graph
    from pyshacl import validate
except ImportError as exc:  # pragma: no cover
    print(f"ERR: missing dependency ({exc}); pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "datasets" / "estate-graph" / "estate-graph.ttl"
EDGES = ROOT / "datasets" / "estate-graph" / "estate-edges.ttl"
MODELS = ROOT / "datasets" / "estate-graph" / "estate-models.ttl"
VOCAB = ROOT / "vendor" / "ontogenesis" / "estate-catalog.ttl"
SHAPES = ROOT / "vendor" / "ontogenesis" / "estate-catalog.shacl.ttl"

CAT = "PREFIX cat: <https://socioprophet.github.io/ontogenesis/domains/estate-catalog#>\n"

# Blast radius: resources whose removal breaks the most (direct dependents).
BLAST_QUERY = CAT + """
SELECT ?target (COUNT(?src) AS ?dependents) WHERE {
  ?src cat:dependsOn ?target .
} GROUP BY ?target ORDER BY DESC(?dependents) LIMIT 5
"""

# Transitive blast radius of a specific node (multi-hop cat:dependsOn+).
TRANSITIVE = CAT + "SELECT (COUNT(DISTINCT ?r) AS ?n) WHERE { ?r cat:dependsOn+ %s . }"

# Governance: cat:Models whose license is NOT MIT/Apache-2.0 (the estate rule).
LICENSE_QUERY = CAT + """
SELECT ?m ?license WHERE {
  ?m a cat:Model ; cat:license ?license .
  FILTER(?license != "MIT" && ?license != "Apache-2.0")
} ORDER BY ?m
"""


def main() -> int:
    for f in (GRAPH, EDGES, MODELS):
        if not f.exists():
            print(f"ERR: {f} not found — run 'make estate-graph' first", file=sys.stderr)
            return 2

    data = Graph()
    try:
        data.parse(GRAPH, format="turtle")
        data.parse(EDGES, format="turtle")
        data.parse(MODELS, format="turtle")
        data.parse(VOCAB, format="turtle")
    except Exception as exc:
        print(f"FAIL parse: {exc}", file=sys.stderr)
        return 2
    entries = len(list(data.query(CAT + "SELECT ?e WHERE { ?e a cat:CatalogEntry }")))
    edges = len(list(data.query(CAT + "SELECT ?s ?t WHERE { ?s cat:dependsOn ?t }")))
    models = len(list(data.query(CAT + "SELECT ?m WHERE { ?m a cat:Model }")))
    print(f"OK parse: {len(data)} triples, {entries} catalog entries, {edges} dependsOn edges, {models} models")

    shapes = Graph()
    try:
        shapes.parse(SHAPES, format="turtle")
    except Exception as exc:
        print(f"FAIL parse: vendored shapes malformed: {exc}", file=sys.stderr)
        return 2
    conforms, _r, text = validate(
        data_graph=data, shacl_graph=shapes, inference="rdfs", abort_on_first=False, advanced=True
    )
    if not conforms:
        print("FAIL conform:\n" + text, file=sys.stderr)
        return 1
    print(f"OK conform: {entries} entries + {edges} edges satisfy the estate-catalog vocabulary")

    blast = list(data.query(BLAST_QUERY))
    if not blast:
        print("FAIL reason: blast-radius query returned no rows", file=sys.stderr)
        return 1
    print("OK reason — highest blast radius (most-depended-on resources):")
    for r in blast:
        iri = str(r["target"]).rsplit("/", 1)[-1]
        print(f"    {iri:28s} {int(r['dependents'])} direct dependents")

    # Transitive blast radius of the #1 node — the "if this breaks, what breaks" answer.
    top = str(blast[0]["target"])
    trows = list(data.query(TRANSITIVE % f"<{top}>"))
    n = int(trows[0]["n"]) if trows else 0
    print(f"OK reason — transitive blast radius of {top.rsplit('/', 1)[-1]} "
          f"= {n} resource(s) depend on it (multi-hop cat:dependsOn+)")

    # Governance: which catalogued models violate the MIT/Apache-only rule?
    bad = list(data.query(LICENSE_QUERY))
    print(f"OK reason — MIT/Apache-only check: {models} cat:Model(s), "
          f"{len(bad)} NOT MIT/Apache (flagged over the graph):")
    for r in bad:
        print(f"    {str(r['m']).rsplit('/', 1)[-1]:28s} {str(r['license'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
