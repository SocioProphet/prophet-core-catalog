#!/usr/bin/env python3
"""Generalized per-repo sharding for ANY catalog dataset (not just regex).

The asset-catalog contribution model is "each repo owns its slice": a dataset is
an assembly of per-repo shards under `datasets/<ds>/contributions/<repo>.jsonl`.
`tools/assemble_dataset.py` already merges shards *back* into a corpus, but until
now only the regex dataset was ever decomposed into shards. This tool generalizes
the *decompose* direction: it fans a dataset's primary records out to
`contributions/<repo>.jsonl`, keyed on each record's `repo` (or, if absent, the
repo of its `sources[]`); records with no repo at all land in `_unsourced.jsonl`.

    python3 tools/shard_dataset.py datasets/models
    python3 tools/shard_dataset.py datasets/ci-workflows-tests datasets/models
    python3 tools/shard_dataset.py --all            # every datasets/*/ with a manifest

Design (lossless + byte-identical round-trip)
--------------------------------------------
* A record is assigned to exactly ONE owner shard (verbatim — never mutated), so
  decompose→assemble is a byte-identical round-trip. (The regex dataset fans a
  record across every source repo and re-merges with domain-specific union
  semantics; that lossy-then-merged path stays in assemble_dataset.py and is left
  untouched here.)
* Shard files hold the ORIGINAL record lines verbatim, sorted by id, so re-running
  on unchanged input is byte-identical (idempotent).
* A `contributions/_shard-manifest.json` records, per primary file, the record ids
  in their original order + a content hash. `tools/assemble_dataset.py` reads this
  manifest to reconstruct each primary file byte-for-byte from the shards, so the
  read-half index keeps seeing the exact same monolith it does today.

Primary files = every top-level `*.jsonl` in the dataset dir EXCEPT derived views
(corpus / regex-corpus / gbrg edges / glossary / vendored / remediations), which
are regenerated, not sharded.

Read-only w.r.t. the primary files, stdlib-only, deterministic. Fail-closed: after
writing, the round-trip is verified and the tool exits non-zero if any primary file
would not reconstruct byte-identically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MANIFEST_NAME = "_shard-manifest.json"

# Derived / non-primary top-level files: regenerated from the corpus, never sharded.
DERIVED = {
    "corpus.jsonl",
    "regex-corpus.jsonl",
    "gbrg-blast-radius.jsonl",
    "glossary.jsonl",
    "third-party-vendored.jsonl",
    "redos-remediations.jsonl",
}


def _owner_repo(rec: dict) -> str:
    """The single owner repo for a record: top-level `repo`, else the (min) repo
    across `sources[]`, else `_unsourced`."""
    repo = rec.get("repo")
    if isinstance(repo, str) and repo:
        return repo
    srcs = rec.get("sources")
    if isinstance(srcs, list):
        repos = [s.get("repo") for s in srcs if isinstance(s, dict) and s.get("repo")]
        if repos:
            return min(repos)
    return "_unsourced"


def _primary_files(ds_dir: Path) -> list[Path]:
    return [p for p in sorted(ds_dir.glob("*.jsonl")) if p.name not in DERIVED]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _read_raw_records(path: Path) -> list[tuple[str, str]]:
    """Return [(id, raw_line)] for a primary file, preserving original order.

    raw_line is the verbatim source line (no trailing newline) so reconstruction is
    byte-identical regardless of key order / separators the monolith was written with.
    """
    out: list[tuple[str, str]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            raise SystemExit(f"FAIL {path}:{i} invalid JSON: {e}")
        if not isinstance(rec, dict):
            raise SystemExit(f"FAIL {path}:{i} not a JSON object")
        rid = rec.get("id")
        if not rid:
            raise SystemExit(f"FAIL {path}:{i} record missing 'id' (cannot shard)")
        out.append((str(rid), line))
    return out


def _write_shards(contrib_dir: Path, shards: dict[str, list[tuple[str, str]]]) -> list[str]:
    """Write contributions/<repo>.jsonl (raw lines, sorted by id). Returns names written."""
    contrib_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for repo, items in shards.items():
        body = "\n".join(line for _id, line in sorted(items, key=lambda t: t[0]))
        if body:
            body += "\n"
        (contrib_dir / f"{repo}.jsonl").write_text(body, encoding="utf-8")
        written.append(f"{repo}.jsonl")
    return sorted(written)


def reconstruct(contrib_dir: Path) -> dict[str, str]:
    """Rebuild each primary file's text from the shards + manifest. Pure (no writes)."""
    manifest = json.loads((contrib_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    id_to_line: dict[str, str] = {}
    for shard in sorted(contrib_dir.glob("*.jsonl")):
        for line in shard.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rid = str(json.loads(line)["id"])
            id_to_line[rid] = line
    out: dict[str, str] = {}
    for fname, spec in manifest["primary_files"].items():
        lines = [id_to_line[str(rid)] for rid in spec["ids"]]
        body = "\n".join(lines)
        if body:
            body += "\n"
        out[fname] = body
    return out


def shard(ds_dir: Path, verify: bool = True) -> int:
    ds_dir = ds_dir.resolve()
    primaries = _primary_files(ds_dir)
    if not primaries:
        print(f"  {ds_dir.name}: no primary *.jsonl to shard (skipped)")
        return 0

    contrib_dir = ds_dir / "contributions"
    shards: dict[str, list[tuple[str, str]]] = {}
    manifest_primaries: dict[str, dict] = {}
    originals: dict[str, str] = {}

    for pf in primaries:
        recs = _read_raw_records(pf)
        originals[pf.name] = pf.read_text(encoding="utf-8")
        ordered_ids: list[str] = []
        for rid, line in recs:
            # build a throwaway dict only to read the repo key (cheap, records are small)
            repo = _owner_repo(json.loads(line))
            shards.setdefault(repo, []).append((rid, line))
            ordered_ids.append(rid)
        manifest_primaries[pf.name] = {"ids": ordered_ids, "sha256_16": _hash(originals[pf.name])}

    written = _write_shards(contrib_dir, shards)
    manifest = {
        "generated_by": "tools/shard_dataset.py",
        "dataset": ds_dir.name,
        "key": "repo|sources[].repo|_unsourced",
        "primary_files": manifest_primaries,
    }
    (contrib_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    n_records = sum(len(v) for v in shards.values())
    print(f"  {ds_dir.name}: sharded {n_records} record(s) from "
          f"{len(primaries)} primary file(s) -> {len(written)} shard(s)")

    if verify:
        rebuilt = reconstruct(contrib_dir)
        for fname, original in originals.items():
            if rebuilt.get(fname) != original:
                print(f"FAIL round-trip: {ds_dir.name}/{fname} does NOT reconstruct "
                      f"byte-identically from shards", file=sys.stderr)
                return 1
        print(f"    round-trip OK: {len(originals)} primary file(s) reconstruct byte-identically")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Shard a catalog dataset's primary records into per-repo contribution shards.")
    p.add_argument("dataset_dir", nargs="*", help="datasets/<name> dir(s).")
    p.add_argument("--all", action="store_true", help="shard every datasets/*/ with a manifest.")
    p.add_argument("--no-verify", action="store_true", help="skip the byte-identical round-trip check.")
    args = p.parse_args()
    targets = [Path(d) for d in args.dataset_dir]
    if args.all or not targets:
        targets = [m.parent for m in sorted(ROOT.glob("datasets/*/manifest.json"))]
    if not targets:
        print("no datasets found")
        return 0
    rc = 0
    for t in targets:
        rc |= shard(t, verify=not args.no_verify)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
