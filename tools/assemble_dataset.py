#!/usr/bin/env python3
"""Assemble a catalog dataset from per-repo contribution shards.

Shard layout (the contract every estate repo writes into):

    datasets/<dataset>/contributions/<repo>.jsonl   # one shard per repo

This assembler concatenates+merges those shards into the canonical corpus and
rebuilds derived views. It is the reusable core that .github/workflows/
assemble-catalog.yml calls, so it also runs locally / by hand:

    python3 tools/assemble_dataset.py datasets/regex-operational-dataset
    python3 tools/assemble_dataset.py --all        # every datasets/*/

Behaviour
---------
1. If `contributions/*.jsonl` exist, they are the source of truth: read all,
   merge records that share an `id` (union sources, recompute use_count as
   len(sources) after dedup, union flags,
   OR the risk booleans, max risk_class), write `corpus.jsonl`.
2. AUTO-ABSORB: if there are NO shards yet but a pre-existing monolith
   (`corpus.jsonl` or the regex dataset's `regex-corpus.jsonl`) is present, it
   is split into `contributions/<repo>.jsonl` by each record's `sources[].repo`,
   then assembled. This migrates a legacy monolith to the shard layout once,
   losslessly.
3. Derived views are regenerated from the merged corpus: for the regex dataset,
   `gbrg-blast-radius.jsonl` (SemanticCell per pattern + one imports edge per
   source) and the `regex-corpus.jsonl` alias.

Deterministic: records sorted by id, sources sorted by (repo,file,line),
JSON emitted with sorted keys — re-running on unchanged shards is a no-op diff.

stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Per-dataset harvest wiring (extractors/harvest_map.json). Datasets listed there
# self-refresh: their PRIMARY file(s) are rebuilt from the per-repo contribution
# shards written by a real extractor. See _assemble_harvest + docs/CATALOG-EXTRACTORS.md.
HARVEST_MAP_PATH = ROOT / "extractors" / "harvest_map.json"


def _harvest_map() -> dict:
    try:
        return json.loads(HARVEST_MAP_PATH.read_text(encoding="utf-8")).get("datasets", {})
    except (OSError, json.JSONDecodeError):
        return {}


# Legacy monolith filenames that auto-absorb will consume, in priority order.
MONOLITH_NAMES = ["corpus.jsonl", "regex-corpus.jsonl"]

# Written by tools/shard_dataset.py when a dataset is decomposed with the
# generalized (lossless, single-owner) sharder. Its presence switches assemble
# from the regex union-merge path to a byte-identical primary-file reconstruction.
GENERAL_SHARD_MANIFEST = "_shard-manifest.json"

_RISK_ORDER = {"benign": 0, "sensitive": 1, "catastrophic": 2}


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"FAIL {path}:{i} invalid JSON: {e}")
    return out


def _write_jsonl(path: Path, records: list[dict]) -> None:
    lines = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records]
    body = "\n".join(lines)
    if body:
        body += "\n"
    path.write_text(body, encoding="utf-8")


def _merge(records: list[dict]) -> list[dict]:
    """Merge records sharing an id across shards into the canonical corpus."""
    agg: dict[str, dict] = {}
    for rec in records:
        rid = rec.get("id")
        if not rid:
            raise SystemExit(f"FAIL record missing id: {rec!r:.120}")
        cur = agg.get(rid)
        if cur is None:
            agg[rid] = json.loads(json.dumps(rec))  # deep copy
            # normalise: a shard may carry "sources": null / omit it entirely
            if not isinstance(agg[rid].get("sources"), list):
                agg[rid]["sources"] = []
            continue
        # union sources (dedup by repo/file/line); tolerate null/omitted sources
        seen = {(s.get("repo"), s.get("file"), s.get("line")) for s in cur["sources"]}
        for s in (rec.get("sources") or []):
            key = (s.get("repo"), s.get("file"), s.get("line"))
            if key not in seen:
                cur["sources"].append(s)
                seen.add(key)
        # union flags (tolerate null/omitted flags)
        cur["flags"] = "".join(sorted(set(cur.get("flags") or "") | set(rec.get("flags") or "")))
        # OR risk booleans, max risk_class
        cur["redos_suspect"] = bool(cur.get("redos_suspect")) or bool(rec.get("redos_suspect"))
        cur["provider_reference"] = bool(cur.get("provider_reference")) or bool(rec.get("provider_reference"))
        cur["competitor_clean"] = bool(cur.get("competitor_clean", True)) and bool(rec.get("competitor_clean", True))
        if _RISK_ORDER.get(rec.get("risk_class", "benign"), 0) > _RISK_ORDER.get(cur.get("risk_class", "benign"), 0):
            cur["risk_class"] = rec["risk_class"]
        # first non-empty intent / non-"other" category win
        if not cur.get("intent") and rec.get("intent"):
            cur["intent"] = rec["intent"]
        if cur.get("category", "other") == "other" and rec.get("category", "other") != "other":
            cur["category"] = rec["category"]
    # finalise: stable source order + recomputed use_count. Records that carry
    # no sources at all (e.g. manually-curated provider-reference seeds) keep
    # their declared use_count rather than being forced to 0.
    for rec in agg.values():
        rec["sources"].sort(key=lambda s: (s.get("repo", ""), s.get("file", ""), s.get("line", 0)))
        if rec["sources"]:
            rec["use_count"] = len(rec["sources"])
        else:
            rec.setdefault("use_count", 0)
    return sorted(agg.values(), key=lambda r: r["id"])


def _split_monolith(monolith: Path, contrib_dir: Path) -> None:
    """One-time migration: fan a legacy monolith out to contributions/<repo>.jsonl."""
    records = _read_jsonl(monolith)
    by_repo: dict[str, list[dict]] = {}
    for rec in records:
        srcs = rec.get("sources") or []
        if not srcs:
            # No provenance (e.g. hand-curated provider-reference seed): keep the
            # record verbatim in a repo-agnostic shard rather than invent a repo.
            shard_rec = json.loads(json.dumps(rec))
            shard_rec["sources"] = []
            by_repo.setdefault("_unsourced", []).append(shard_rec)
            continue
        repos: dict[str, list[dict]] = {}
        for s in srcs:
            repos.setdefault(s.get("repo", "_unsourced"), []).append(s)
        for repo, rsrcs in repos.items():
            shard_rec = json.loads(json.dumps(rec))
            shard_rec["sources"] = sorted(rsrcs, key=lambda s: (s.get("repo", ""), s.get("file", ""), s.get("line", 0)))
            shard_rec["use_count"] = len(rsrcs)
            by_repo.setdefault(repo, []).append(shard_rec)
    contrib_dir.mkdir(parents=True, exist_ok=True)
    for repo, recs in by_repo.items():
        _write_jsonl(contrib_dir / f"{repo}.jsonl", sorted(recs, key=lambda r: r["id"]))
    print(f"  absorbed {monolith.name} -> {len(by_repo)} shard(s): {', '.join(sorted(by_repo))}")


def _build_gbrg(corpus: list[dict], out: Path) -> None:
    """Regex dataset derived view: SemanticCell per pattern + imports edge per source."""
    rows: list[str] = []
    for rec in corpus:
        rows.append(json.dumps({
            "record_type": "SemanticCell",
            "kind": "pattern",
            "cell_id": f"rx://{rec['id']}",
            "intent": rec.get("intent", ""),
            "category": rec.get("category", "other"),
            "risk_class": rec.get("risk_class", "benign"),
            "provider_reference": bool(rec.get("provider_reference")),
            "redos_suspect": bool(rec.get("redos_suspect")),
            "use_count": rec.get("use_count", len(rec.get("sources", []))),
        }, ensure_ascii=False, sort_keys=True))
        for s in rec.get("sources", []):
            rows.append(json.dumps({
                "record_type": "GraphEdge",
                "kind": "imports",
                "from": f"code://{s.get('repo')}/{s.get('file')}",
                "to": f"rx://{rec['id']}",
                "line": s.get("line"),
            }, ensure_ascii=False, sort_keys=True))
    body = "\n".join(rows)
    if body:
        body += "\n"
    out.write_text(body, encoding="utf-8")


def _assemble_general(ds_dir: Path, contrib_dir: Path) -> None:
    """Generalized path: reconstruct each primary file byte-identically from the
    single-owner shards, using the manifest tools/shard_dataset.py wrote. Lossless
    round-trip — no domain-specific merge, no corpus.jsonl (the primary files ARE
    the corpus for these datasets)."""
    man = json.loads((contrib_dir / GENERAL_SHARD_MANIFEST).read_text(encoding="utf-8"))
    id_to_line: dict[str, str] = {}
    for shard in sorted(contrib_dir.glob("*.jsonl")):
        for line in shard.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            id_to_line[str(json.loads(line)["id"])] = line
    for fname, spec in man["primary_files"].items():
        lines = [id_to_line[str(rid)] for rid in spec["ids"]]
        body = "\n".join(lines)
        if body:
            body += "\n"
        (ds_dir / fname).write_text(body, encoding="utf-8")
    print(f"  reconstructed {len(man['primary_files'])} primary file(s) from "
          f"{len(id_to_line)} record(s) across single-owner shards")


def _merge_union(records: list[dict]) -> list[dict]:
    """Merge records sharing an id, unioning list fields (used_by/consumers) and
    keeping the first scalar value. Used by harvest datasets whose same id recurs
    across repos (e.g. one model referenced by many repos)."""
    agg: dict[str, dict] = {}
    for rec in records:
        rid = rec.get("id")
        if not rid:
            raise SystemExit(f"FAIL harvest record missing id: {rec!r:.120}")
        cur = agg.get(rid)
        if cur is None:
            agg[rid] = json.loads(json.dumps(rec))
            continue
        for key in ("used_by", "consumers", "imports", "endpoints", "sources"):
            if isinstance(cur.get(key), list) or isinstance(rec.get(key), list):
                merged = list(cur.get(key) or [])
                seen = {json.dumps(x, sort_keys=True) for x in merged}
                for x in (rec.get(key) or []):
                    k = json.dumps(x, sort_keys=True)
                    if k not in seen:
                        merged.append(x)
                        seen.add(k)
                # scalars stay sorted only when primitive
                cur[key] = sorted(merged) if merged and all(isinstance(x, str) for x in merged) else merged
        cur["governed"] = bool(cur.get("governed")) or bool(rec.get("governed"))
        cur["provider_reference"] = bool(cur.get("provider_reference")) or bool(rec.get("provider_reference"))
    return sorted(agg.values(), key=lambda r: r["id"])


def _assemble_harvest(ds_dir: Path, cfg: dict) -> None:
    """Rebuild a dataset's PRIMARY file(s) from the per-repo shards a real extractor
    wrote. Fail-SAFE: if no shards exist yet, the committed primary files are left
    exactly as-is (the loop is a no-op until the extractor has run)."""
    contrib_dir = ds_dir / cfg.get("contrib_dir", "contributions")
    shards = sorted(p for p in contrib_dir.glob("*.jsonl") if not p.name.startswith("_")) \
        if contrib_dir.exists() else []
    if not shards:
        print(f"  harvest: no shards under {contrib_dir.name}/ — primary file(s) left as committed")
        return
    records: list[dict] = []
    for shard in shards:
        records.extend(_read_jsonl(shard))
    mode = cfg.get("merge", "single-owner")
    total = 0
    for fname, spec in cfg.get("primary_files", {}).items():
        prefix = spec.get("id_prefix")
        sel = [r for r in records if (prefix is None or str(r.get("id", "")).startswith(prefix))]
        merged = _merge_union(sel) if mode == "union" else _dedup_single_owner(sel)
        _write_jsonl(ds_dir / fname, merged)
        total += len(merged)
        print(f"  harvest: wrote {fname}: {len(merged)} records ({mode})")
    print(f"  harvest: {total} record(s) from {len(shards)} shard(s); "
          f"preserved {cfg.get('preserve', [])}")


def _dedup_single_owner(records: list[dict]) -> list[dict]:
    """Each id owned by exactly one repo: keep the last occurrence, sort by id.
    A duplicate id across shards is a harvest bug, surfaced but not fatal."""
    seen: dict[str, dict] = {}
    dups = 0
    for rec in records:
        rid = rec.get("id")
        if not rid:
            raise SystemExit(f"FAIL harvest record missing id: {rec!r:.120}")
        if rid in seen:
            dups += 1
        seen[rid] = rec
    if dups:
        sys.stderr.write(f"[assemble] warning: {dups} duplicate id(s) across single-owner shards\n")
    return sorted(seen.values(), key=lambda r: r["id"])


def assemble(ds_dir: Path) -> None:
    ds_dir = ds_dir.resolve()
    manifest = json.loads((ds_dir / "manifest.json").read_text()) if (ds_dir / "manifest.json").exists() else {}
    ds_id = manifest.get("id", ds_dir.name)
    print(f"assembling {ds_dir.name} ({ds_id})")

    # Harvest datasets (real per-repo extractors) rebuild their named primary files
    # from shards — take that path first, before the regex/general shard logic.
    hcfg = _harvest_map().get(ds_dir.name)
    if hcfg:
        _assemble_harvest(ds_dir, hcfg)
        return

    contrib_dir = ds_dir / "contributions"

    # Generalized single-owner shards (tools/shard_dataset.py) reconstruct the
    # original primary files verbatim — take that path before the regex merge.
    if (contrib_dir / GENERAL_SHARD_MANIFEST).exists():
        _assemble_general(ds_dir, contrib_dir)
        return

    shards = sorted(contrib_dir.glob("*.jsonl")) if contrib_dir.exists() else []

    if not shards:
        # auto-absorb a legacy monolith, once.
        for name in MONOLITH_NAMES:
            mono = ds_dir / name
            if mono.exists() and mono.read_text().strip():
                _split_monolith(mono, contrib_dir)
                shards = sorted(contrib_dir.glob("*.jsonl"))
                break

    if not shards:
        print("  no contributions and no monolith to absorb — nothing to assemble")
        return

    records: list[dict] = []
    for shard in shards:
        records.extend(_read_jsonl(shard))
    corpus = _merge(records)

    _write_jsonl(ds_dir / "corpus.jsonl", corpus)
    print(f"  wrote corpus.jsonl: {len(corpus)} records from {len(shards)} shard(s)")

    is_regex = ds_id == "ds.regex-operational-dataset" or (ds_dir / "gbrg-blast-radius.jsonl").exists() \
        or (ds_dir / "regex-corpus.jsonl").exists()
    if is_regex:
        _write_jsonl(ds_dir / "regex-corpus.jsonl", corpus)  # generated alias
        _build_gbrg(corpus, ds_dir / "gbrg-blast-radius.jsonl")
        print("  regenerated regex-corpus.jsonl alias + gbrg-blast-radius.jsonl")


def main() -> int:
    p = argparse.ArgumentParser(description="Assemble catalog dataset(s) from contribution shards.")
    p.add_argument("dataset_dir", nargs="*", help="datasets/<name> dir(s); default with --all is all of them.")
    p.add_argument("--all", action="store_true", help="assemble every datasets/*/ under repo root.")
    args = p.parse_args()
    targets = [Path(d) for d in args.dataset_dir]
    if args.all or not targets:
        targets = [m.parent for m in sorted(ROOT.glob("datasets/*/manifest.json"))]
    if not targets:
        print("no datasets found")
        return 0
    for t in targets:
        assemble(t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
