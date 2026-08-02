#!/usr/bin/env python3
"""Query the catalog index — proves the catalog percolates (content comes back out).

Usage:
  catalog_query.py stats
  catalog_query.py search <text>
  catalog_query.py define <term>
  catalog_query.py who-uses <repo-or-asset-substring>
  catalog_query.py blast-radius <asset_id>
  catalog_query.py dataset <dataset-name>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

IDX = Path(__file__).resolve().parents[1] / "catalog-index"


def _load(name):
    p = IDX / name
    if not p.exists():
        sys.exit(f"ERR: {p} missing — run tools/build_catalog_index.py first")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    if cmd == "stats":
        print(json.dumps(json.loads((IDX / "index.json").read_text())["registry"], indent=2))
        return 0
    if cmd == "search":
        q = " ".join(args).lower()
        hits = [a for a in _load("assets.jsonl") if q in a.get("search", "")]
        print(f"{len(hits)} hit(s) for {q!r}:")
        for a in hits[:25]:
            print(f"  [{a['dataset']}] {a['name']}  ({a.get('kind')})  {a.get('repo') or ''} {a.get('path') or ''}")
        return 0
    if cmd == "define":
        q = " ".join(args).lower()
        gl = [g for g in _load("glossary.jsonl") if q in (g.get("name") or "").lower()]
        if not gl:
            print(f"no glossary entry matching {q!r}"); return 1
        for g in gl[:10]:
            print(f"* {g['name']} ({g.get('kind')}): {g.get('definition')}")
            if g.get("related_terms"):
                print(f"    related: {', '.join(g['related_terms'][:8])}")
            if g.get("narrower_terms"):
                print(f"    narrower: {', '.join(g['narrower_terms'][:8])}")
        return 0
    if cmd == "who-uses":
        q = " ".join(args).lower()
        es = [e for e in _load("edges.jsonl") if q in (e.get("to") or "").lower() or q in (e.get("from") or "").lower()]
        print(f"{len(es)} edge(s) matching {q!r}:")
        for e in es[:30]:
            print(f"  {e.get('from')} --{e.get('rel')}--> {e.get('to')}" + (f":{e['line']}" if e.get('line') else ""))
        return 0
    if cmd == "blast-radius":
        aid = args[0] if args else ""
        es = [e for e in _load("edges.jsonl") if e.get("from") == aid or e.get("to") == aid]
        print(f"blast radius of {aid}: {len(es)} edge(s)")
        for e in es[:40]:
            print(f"  {e.get('from')} --{e.get('rel')}--> {e.get('to')}" + (f":{e['line']}" if e.get('line') else ""))
        return 0
    if cmd == "dataset":
        ds = args[0] if args else ""
        rows = [a for a in _load("assets.jsonl") if a["dataset"] == ds]
        print(f"{len(rows)} asset(s) in {ds}:")
        for a in rows[:25]:
            print(f"  {a['name']}  ({a.get('kind')})  {a.get('repo') or ''}")
        return 0
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
