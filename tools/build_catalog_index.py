#!/usr/bin/env python3
"""Build the queryable catalog index — the READ half of the asset catalog.

Ingests every dataset's records + the glossary + blast-radius edges into a single
unified, queryable index under catalog-index/. This is what makes the catalog
*percolate*: details/docs/vocabularies written by the harvest become answerable
("who uses X", "define Y", "blast-radius of Z") instead of sitting write-only in git.

Deterministic, stdlib-only. Outputs:
  catalog-index/assets.jsonl    one node per asset across ALL datasets
  catalog-index/glossary.jsonl  terms + definitions + linked terms
  catalog-index/edges.jsonl     blast-radius / lineage edges (asset -> site/consumer)
  catalog-index/index.json      registry + coverage + counts (the manifest of the index)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"
OUT = ROOT / "catalog-index"

# Files that are NOT primary asset records for a dataset (aliases / edges / glossary
# / shards), handled specially or skipped to avoid double counting.
SKIP_FILES = {
    "regex-corpus.jsonl",       # alias of corpus.jsonl
    "gbrg-blast-radius.jsonl",  # edges, ingested separately
    "glossary.jsonl",           # glossary, ingested separately
    "third-party-vendored.jsonl",
    "redos-remediations.jsonl",
}


def _name(rec: dict, ds: str, i: int) -> str:
    for k in ("name", "term", "title", "id", "cell_id"):
        v = rec.get(k)
        if isinstance(v, str) and v:
            return v
    return f"{ds}:{i}"


def _kind(rec: dict, ds: str) -> str:
    for k in ("kind", "category", "role", "asset_class", "record_type"):
        v = rec.get(k)
        if isinstance(v, str) and v:
            return v
    return ds


def _repo(rec: dict):
    if isinstance(rec.get("repo"), str):
        return rec["repo"]
    srcs = rec.get("sources")
    if isinstance(srcs, list) and srcs and isinstance(srcs[0], dict):
        return srcs[0].get("repo")
    return None


def _edges_from(asset_id: str, ds: str, rec: dict):
    out = []
    for s in (rec.get("sources") or []):
        if isinstance(s, dict) and s.get("repo"):
            out.append({"from": asset_id, "rel": "used_at", "to": f"{s.get('repo')}/{s.get('file','')}",
                        "line": s.get("line"), "dataset": ds})
    for key, rel in (("consumers", "consumed_by"), ("used_by", "used_by"), ("imports", "imports"),
                     ("narrower_terms", "narrower"), ("related_terms", "related")):
        for c in (rec.get(key) or []):
            if isinstance(c, str) and c:
                out.append({"from": asset_id, "rel": rel, "to": c, "dataset": ds})
    conn = rec.get("connections")
    if isinstance(conn, dict):
        for slot, items in conn.items():
            for it in (items or []):
                if isinstance(it, str) and it:
                    out.append({"from": asset_id, "rel": f"connects:{slot}", "to": it, "dataset": ds})
    return out


def build() -> int:
    OUT.mkdir(exist_ok=True)
    assets, glossary, edges = [], [], []
    registry = []
    manifests = sorted(DATASETS.glob("*/manifest.json"))
    if not manifests:
        print("ERR: no dataset manifests found", file=sys.stderr)
        return 2

    for m in manifests:
        ds = m.parent.name
        man = json.loads(m.read_text(encoding="utf-8"))
        ds_assets = 0
        for jf in sorted(m.parent.glob("*.jsonl")):
            if jf.name in SKIP_FILES:
                continue
            for i, line in enumerate(jf.read_text(encoding="utf-8").splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                aid = rec.get("id") or f"{ds}:{jf.stem}:{i}"
                nm = _name(rec, ds, i)
                kd = _kind(rec, ds)
                rp = _repo(rec)
                intent = rec.get("intent") or rec.get("definition") or rec.get("description")
                # compact searchable field: structured fields + high-value list fields
                # (capabilities, tags, endpoints, terms) flattened — not the full blob.
                extra = []
                for k in ("declared_capabilities", "tags", "endpoints", "terms", "verbs",
                          "provider", "role", "status", "engine"):
                    v = rec.get(k)
                    if isinstance(v, list):
                        extra += [str(x) for x in v if isinstance(x, (str, int))]
                    elif isinstance(v, (str, int)):
                        extra.append(str(v))
                node = {
                    "asset_id": aid, "dataset": ds, "name": nm, "kind": kd,
                    "repo": rp, "path": rec.get("path"), "intent": intent,
                    "search": " ".join(str(x) for x in ([nm, kd, rp, rec.get("path"), intent, aid] + extra) if x).lower()[:800],
                }
                assets.append(node)
                edges.extend(_edges_from(aid, ds, rec))
                ds_assets += 1
        # glossary
        gf = m.parent / "glossary.jsonl"
        if gf.exists():
            for line in gf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    g = json.loads(line)
                except json.JSONDecodeError:
                    continue
                glossary.append({"id": g.get("id"), "name": g.get("name"), "kind": g.get("kind"),
                                 "definition": g.get("definition"), "source": g.get("source"),
                                 "related_terms": g.get("related_terms") or [],
                                 "narrower_terms": g.get("narrower_terms") or [],
                                 "repos": g.get("repos") or []})
        # gbrg blast-radius edges
        bf = m.parent / "gbrg-blast-radius.jsonl"
        if bf.exists():
            for line in bf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("record_type") == "GraphEdge":
                    edges.append({"from": e.get("from"), "rel": e.get("kind", "imports"),
                                  "to": e.get("to"), "line": e.get("line"), "dataset": ds})
        registry.append({"dataset": ds, "id": man.get("id"), "version": man.get("version"),
                         "assets": ds_assets, "sources": len(man.get("sources", []))})

    # write
    for name, rows in (("assets.jsonl", assets), ("glossary.jsonl", glossary), ("edges.jsonl", edges)):
        with open(OUT / name, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    index = {"generated_by": "tools/build_catalog_index.py", "datasets": len(registry),
             "assets": len(assets), "glossary_terms": len(glossary), "edges": len(edges),
             "registry": registry}
    (OUT / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"OK: indexed {len(assets)} assets, {len(glossary)} glossary terms, "
          f"{len(edges)} edges across {len(registry)} datasets -> {OUT}/")
    return 0


if __name__ == "__main__":
    sys.exit(build())
