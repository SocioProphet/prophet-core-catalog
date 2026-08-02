#!/usr/bin/env python3
"""Validate catalog dataset manifests against schemas/catalog.dataset.v0.1.json.

Also runs dataset-local quality checks so a manifest cannot claim conformance it
does not have (fail-closed): corpus JSONL must parse line-by-line, and a public
corpus must be competitor_clean. Mirrors tools/validate_wallguard_catalog_visibility.py.

Usage: python tools/validate_dataset_manifest.py [datasets/<name>/manifest.json ...]
       (no args -> validate every datasets/*/manifest.json)
"""
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "catalog.dataset.v0.1.json").read_text())


def check(manifest_path: Path) -> list[str]:
    errs: list[str] = []
    man = json.loads(manifest_path.read_text())
    try:
        jsonschema.validate(man, SCHEMA)
    except jsonschema.ValidationError as e:
        errs.append(f"schema: {e.message}")
        return errs

    ds_dir = manifest_path.parent
    corpus = ds_dir / "regex-corpus.jsonl"
    public = man.get("access", {}).get("visibility") == "public"
    if corpus.exists():
        for i, line in enumerate(corpus.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errs.append(f"{corpus.name}:{i} invalid JSON ({e})")
                continue
            if public and rec.get("competitor_clean") is not True:
                errs.append(f"{corpus.name}:{i} public dataset but competitor_clean != true ({rec.get('id')})")
    return errs


def main() -> int:
    targets = [Path(a) for a in sys.argv[1:]] or sorted(ROOT.glob("datasets/*/manifest.json"))
    if not targets:
        print("no dataset manifests found")
        return 0
    failed = 0
    for t in targets:
        errs = check(t)
        if errs:
            failed += 1
            print(f"FAIL {t}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"OK   {t}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
