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

# Legacy monolith filenames that auto-absorb will consume, in priority order.
MONOLITH_NAMES = ["corpus.jsonl", "regex-corpus.jsonl"]

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


def assemble(ds_dir: Path) -> None:
    ds_dir = ds_dir.resolve()
    manifest = json.loads((ds_dir / "manifest.json").read_text()) if (ds_dir / "manifest.json").exists() else {}
    ds_id = manifest.get("id", ds_dir.name)
    print(f"assembling {ds_dir.name} ({ds_id})")

    contrib_dir = ds_dir / "contributions"
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
