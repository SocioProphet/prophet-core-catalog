#!/usr/bin/env python3
"""Ingest the SourceOS governance vocabulary into the catalog glossary (prophet-ontology wiring).

The sourceos-spec GlossaryTerm contract + its governed alignment promotion (draft->approved) produce
the estate's GOVERNANCE vocabulary (release-gate, attestation, epistemic-level, governed-loop, ...).
This generator lifts those approved terms into a first-class catalog dataset so build_catalog_index
aggregates them into catalog-index/glossary.jsonl alongside the LSA/LSI/LDA topic vocabulary — the
governance words become searchable, edge-linked catalog terms (kind: "governance").

Mirrors the ontogenesis generator pattern: edit the generator / the seed, not glossary.jsonl.

    python3 tools/ingest_srcos_glossary.py           # regenerate datasets/sourceos-glossary/glossary.jsonl
    python3 tools/ingest_srcos_glossary.py --check    # fail if it is stale vs the seed
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "datasets" / "sourceos-glossary"
SEED = DS / "seed"
OUT = DS / "glossary.jsonl"


def load_terms() -> list[dict]:
    terms = {}
    for f in sorted(glob.glob(str(SEED / "*.json"))):
        doc = json.loads(Path(f).read_text(encoding="utf-8"))
        if doc.get("type") != "GlossaryTerm" or not str(doc.get("id", "")).startswith("urn:srcos:glossary:"):
            continue
        if doc.get("status") != "approved":
            continue  # only APPROVED governance terms regulate state — drafts don't reach the catalog
        if not str(doc.get("name", "")).strip() or not str(doc.get("definition", "")).strip():
            raise SystemExit(f"REFUSED {doc.get('id')}: empty name/definition")
        terms[doc["id"]] = doc
    return list(terms.values())


def to_glossary_row(term: dict) -> dict:
    slug = term["id"].split(":")[-1]
    related = [t.split(":")[-1] for t in
               (r.get("target", "") for r in term.get("relations", []))
               if t.startswith("urn:srcos:glossary:")]
    return {
        "id": f"gt-srcos-{slug}",
        "name": term["name"],
        "kind": "governance",
        "definition": term["definition"],
        "source": "sourceos-spec",
        "related_terms": sorted(set(related)),
        "narrower_terms": [],
        "repos": ["sourceos-spec"],
    }


def render(terms: list[dict]) -> str:
    rows = sorted((to_glossary_row(t) for t in terms), key=lambda r: r["id"])
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    terms = load_terms()
    if not terms:
        print("no approved GlossaryTerm seed found", file=sys.stderr)
        return 1
    jsonl = render(terms)
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != jsonl:
            print(f"STALE: {OUT} does not match `ingest_srcos_glossary.py`; regenerate.", file=sys.stderr)
            return 1
        print(f"OK: {OUT} up to date ({len(terms)} governance terms)")
        return 0
    OUT.write_text(jsonl, encoding="utf-8")
    print(f"wrote {OUT} ({len(terms)} governance terms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
