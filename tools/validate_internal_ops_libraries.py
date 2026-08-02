#!/usr/bin/env python3
"""Validate internal-operations library / vendored-IP catalog entries.

Every third-party library the estate depends on is cataloged here as a
``catalog.source`` (where it comes from, its license) plus a ``catalog.dataset``
under ``datasets/internal-operations/`` (the governed, versioned asset the estate
consumes). This validator:

1. schema-validates every source and dataset manifest,
2. checks referential integrity (each dataset's ``sources`` resolve), and
3. enforces the estate license policy for vendored libraries: an
   ``ds.internal_ops.libraries.*`` dataset may only depend on a source whose
   license class is permissive (``open`` / ``public-domain`` / ``permissive``) —
   i.e. no copyleft/restricted IP is silently vendored.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCHEMA = ROOT / "schemas" / "catalog.source.v0.1.json"
DATASET_SCHEMA = ROOT / "schemas" / "catalog.dataset.v0.1.json"
SOURCES_DIR = ROOT / "sources"
DATASETS_DIR = ROOT / "datasets"

LIBRARY_PREFIX = "ds.internal_ops.libraries."
PERMISSIVE_CLASSES = {"open", "public-domain", "permissive"}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_schema(instance: dict, schema: dict, *, label: str) -> list[str]:
    validator = Draft202012Validator(schema)
    problems: list[str] = []
    for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        problems.append(f"{label}: {location}: {error.message}")
    return problems


def main() -> int:
    problems: list[str] = []

    source_schema = load_json(SOURCE_SCHEMA)
    dataset_schema = load_json(DATASET_SCHEMA)

    def rel(path: Path) -> str:
        return str(path.relative_to(ROOT))

    sources: dict[str, dict] = {}
    for path in sorted(SOURCES_DIR.glob("*.json")) if SOURCES_DIR.exists() else []:
        record = load_json(path)
        label = rel(path)
        problems += check_schema(record, source_schema, label=label)
        sid = record.get("id", label)
        if sid in sources:
            # Fail closed: a duplicate id would otherwise overwrite the earlier
            # record and make referential/license checks run against the wrong one.
            problems.append(f"{label}: duplicate source id '{sid}'")
        else:
            sources[sid] = record

    datasets: list[tuple[str, dict]] = []
    if DATASETS_DIR.exists():
        # Only ``datasets/<name>/manifest.json`` files are dataset manifests.
        # Data payloads (classifier sets, corpora, etc.) also live under a
        # dataset directory as ``*.json`` but must NOT be schema-validated as
        # manifests, so match the manifest filename explicitly.
        for path in sorted(DATASETS_DIR.glob("*/manifest.json")):
            record = load_json(path)
            label = rel(path)
            problems += check_schema(record, dataset_schema, label=label)
            datasets.append((label, record))

    # Semantic checks.
    for label, record in datasets:
        for src_id in record.get("sources", []):
            src = sources.get(src_id)
            if src is None:
                problems.append(f"{label}: references unknown source '{src_id}'")
                continue
            if record.get("id", "").startswith(LIBRARY_PREFIX):
                lic = src.get("license", {}).get("class")
                if lic not in PERMISSIVE_CLASSES:
                    problems.append(
                        f"{label}: vendored library depends on source '{src_id}' "
                        f"with non-permissive license class '{lic}' "
                        f"(allowed: {sorted(PERMISSIVE_CLASSES)})"
                    )

    if problems:
        print("Internal-ops library catalog validation FAILED:", file=sys.stderr)
        for line in problems:
            print(f" - {line}", file=sys.stderr)
        return 1

    print(
        f"OK: validated {len(sources)} source(s) and {len(datasets)} dataset(s); "
        "vendored libraries are permissively licensed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
