#!/usr/bin/env python3
"""Validate the estate graph + run the P2 live-proof query.

Three checks over the emitted population (datasets/estate-graph/estate-graph.ttl),
against the VENDORED ontogenesis estate-catalog vocabulary + SHACL:

  1. parse    — the emitted graph is well-formed Turtle;
  2. conform  — every emitted instance SHACL-conforms to the binding vocabulary
                (real instances validated against the real TBox, not fixtures);
  3. reason   — a real cross-cutting SPARQL question is answered over the graph
                (the "reason over the estate, don't read every repo" proof).

Exit 0 iff parse + conform succeed and the reasoning query returns >0 rows.
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
VOCAB = ROOT / "vendor" / "ontogenesis" / "estate-catalog.ttl"
SHAPES = ROOT / "vendor" / "ontogenesis" / "estate-catalog.shacl.ttl"

# A real governance question: estate resources that are catalogued and active,
# grouped by accountable owner org — answerable from the graph without reading a repo.
PROOF_QUERY = """
PREFIX cat: <https://socioprophet.github.io/ontogenesis/domains/estate-catalog#>
SELECT ?owner (COUNT(?e) AS ?entries) WHERE {
  ?e a cat:CatalogEntry ; cat:owner ?owner ; cat:status "active" .
} GROUP BY ?owner ORDER BY DESC(?entries)
"""


def main() -> int:
    if not GRAPH.exists():
        print(f"ERR: {GRAPH} not found — run tools/emit_estate_graph.py first", file=sys.stderr)
        return 2

    # 1. parse (a malformed graph/vocab is a usage error, not a conformance verdict)
    data = Graph()
    try:
        data.parse(GRAPH, format="turtle")
        data.parse(VOCAB, format="turtle")
    except Exception as exc:  # rdflib raises various parser exceptions
        print(f"FAIL parse: {exc}", file=sys.stderr)
        return 2
    entries = len(list(data.query(
        "PREFIX cat: <https://socioprophet.github.io/ontogenesis/domains/estate-catalog#> "
        "SELECT ?e WHERE { ?e a cat:CatalogEntry }")))
    print(f"OK parse: {len(data)} triples, {entries} catalog entries")

    # 2. conform
    shapes = Graph()
    try:
        shapes.parse(SHAPES, format="turtle")
    except Exception as exc:
        print(f"FAIL parse: vendored shapes malformed: {exc}", file=sys.stderr)
        return 2
    conforms, _report, text = validate(
        data_graph=data, shacl_graph=shapes, inference="rdfs", abort_on_first=False, advanced=True
    )
    if not conforms:
        print("FAIL conform: emitted population does not satisfy the estate-catalog SHACL:", file=sys.stderr)
        print(text, file=sys.stderr)
        return 1
    print(f"OK conform: all {entries} entries satisfy the estate-catalog binding vocabulary")

    # 3. reason (live proof)
    rows = list(data.query(PROOF_QUERY))
    if not rows:
        print("FAIL reason: the proof query returned no rows", file=sys.stderr)
        return 1
    print("OK reason — active catalog entries by owner (top 5), answered over the graph:")
    for r in rows[:5]:
        print(f"    {str(r['owner']):40s} {int(r['entries'])}")
    print(f"    ... {len(rows)} owner org(s) total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
