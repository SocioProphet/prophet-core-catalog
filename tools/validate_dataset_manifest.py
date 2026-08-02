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
    # Every record needs a stable `id`; regex-dataset records additionally need a
    # `pattern` (fail-closed so a manifest can't claim conformance it lacks).
    needs_pattern = man.get("id") == "ds.regex-operational-dataset"
    # Validate the canonical corpus.jsonl (shard-assembled), the regex-corpus.jsonl
    # alias, and every per-repo contribution shard, so a bad shard fails the gate
    # before assembly ever runs.
    corpus_files = [ds_dir / "corpus.jsonl", ds_dir / "regex-corpus.jsonl"]
    corpus_files += sorted((ds_dir / "contributions").glob("*.jsonl"))
    for corpus in corpus_files:
        if not corpus.exists():
            continue
        rel_name = corpus.relative_to(ds_dir).as_posix()
        for i, line in enumerate(corpus.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errs.append(f"{rel_name}:{i} invalid JSON ({e})")
                continue
            if not rec.get("id"):
                errs.append(f"{rel_name}:{i} record missing id")
            elif needs_pattern and not rec.get("pattern"):
                errs.append(f"{rel_name}:{i} record missing pattern")
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
