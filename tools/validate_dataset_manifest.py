#!/usr/bin/env python3
"""Validate catalog dataset manifests against schemas/catalog.dataset.v0.1.json.

Also runs dataset-local quality checks so a manifest cannot claim conformance it
does not have (fail-closed): corpus JSONL must parse line-by-line, and every record
must carry a stable `id` and a `pattern`. First-party provider references (e.g. a
model-router allow-list or a leaked-key detector like `sk-ant-…`) are PERMITTED as
the estate's own security/routing policy — they are not client materials. Mirrors
tools/validate_wallguard_catalog_visibility.py.

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
    fmt = man.get("schema", {}).get("format")
    jsonl_files = sorted(ds_dir.glob("*.jsonl"))
    has_data = bool(jsonl_files) or any(ds_dir.glob("*.ttl")) or any(ds_dir.glob("*.yml"))
    # fail-closed: a data-bearing manifest that ships no data file must NOT pass silently.
    if fmt in {"document", "table", "mixed", "graph", "timeseries", "vector", "raster"} and not has_data:
        errs.append(f"{ds_dir.name}: manifest declares format '{fmt}' but no data file "
                    f"(*.jsonl / *.ttl / *.yml) is present next to it")
    # id/pattern integrity applies to the regex corpus shape; JSONL parse validity to all.
    corpus_names = {"regex-corpus.jsonl", "corpus.jsonl"}
    for jf in jsonl_files:
        for i, line in enumerate(jf.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errs.append(f"{jf.name}:{i} invalid JSON ({e})")
                continue
            if jf.name in corpus_names and (not rec.get("id") or not rec.get("pattern")):
                errs.append(f"{jf.name}:{i} record missing id/pattern")
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
