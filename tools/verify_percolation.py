#!/usr/bin/env python3
"""Fail-closed percolation canary — proves the catalog READ half actually works.

A control that cannot fail is suspect. This one CAN fail, and does, when the
catalog stops percolating: index missing/stale, a dataset not covered, an empty
glossary, or a canonical query that returns nothing. Wired into CI so a catalog
that reverts to write-only turns the build red.

Exit 0 only if the index is fresh, complete, and answerable.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / "catalog-index"
DATASETS = ROOT / "datasets"


def fail(msg):
    print(f"PERCOLATION FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    # 1. rebuild fresh so a stale index cannot pass
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_catalog_index.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"index build failed: {r.stderr.strip()}")

    idx = json.loads((IDX / "index.json").read_text())
    # 2. coverage: every dataset dir with a manifest must be indexed
    on_disk = {m.parent.name for m in DATASETS.glob("*/manifest.json")}
    indexed = {r["dataset"] for r in idx["registry"]}
    missing = on_disk - indexed
    if missing:
        fail(f"datasets not percolated into the index: {sorted(missing)}")

    # 3. non-empty content
    if idx["assets"] == 0:
        fail("index has 0 assets")
    if idx["glossary_terms"] == 0:
        fail("glossary did not percolate (0 terms) — vocabularies not answerable")
    if idx["edges"] == 0:
        fail("no blast-radius/lineage edges — dependency tracing not answerable")

    # 4. every dataset actually contributed at least one asset
    empty = [r["dataset"] for r in idx["registry"] if r["assets"] == 0]
    if empty:
        fail(f"datasets present but contributed 0 assets (not percolating): {empty}")

    # 5. canonical queries must return answers (not just be runnable)
    def q(*a):
        return subprocess.run([sys.executable, str(ROOT / "tools" / "catalog_query.py"), *a],
                              capture_output=True, text=True).stdout
    gloss = [json.loads(l) for l in (IDX / "glossary.jsonl").read_text().splitlines() if l.strip()]
    term = next((g["name"] for g in gloss if g.get("definition")), None)
    if not term or "no glossary entry" in q("define", term):
        fail("a known glossary term did not resolve to a definition")
    if "0 edge(s)" in q("who-uses", "prophet-mesh") and "0 edge(s)" in q("who-uses", "sociosphere"):
        fail("who-uses returned nothing for core repos — blast-radius not answerable")

    print(f"OK percolation: {idx['datasets']} datasets, {idx['assets']} assets, "
          f"{idx['glossary_terms']} glossary terms, {idx['edges']} edges — all answerable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
