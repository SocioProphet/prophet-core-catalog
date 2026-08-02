# Estate Regex Operational Dataset (`ds.regex-operational-dataset`)

A governed, catalog-registered dataset of the SocioProphet estate's regular-expression
patterns, so that **other agents can reuse them, expand them, validate them, and trace
the blast radius of any use, misuse, or dependency.**

Seeded 2026-08-02 by a read-only harvest of 13 first-party `~/dev` repos.

## Contents
| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `contributions/<repo>.jsonl` | **Per-repo shards** — each repo owns its own slice, written by that repo's CI on merge to `main`. The source of truth. |
| `corpus.jsonl` | **2,308** distinct patterns; **generated** by assembling + merging the shards (`tools/assemble_dataset.py`). One record per pattern; identical patterns deduped, every usage site in `sources[]` (the blast-radius edges). Do not hand-edit. |
| `regex-corpus.jsonl` | Generated **alias** of `corpus.jsonl`, kept for back-compat. |
| `classifier-set.json` | 12 named classifiers (secret-detection, pii-detection, path-traversal, semver, …) grouping pattern ids. |
| `gbrg-blast-radius.jsonl` | **Generated** GBRG-ready mapping: each pattern as a `SemanticCell` (`kind: pattern`, `rx://<id>`) + one `imports` edge per usage site (`code://<repo>/<file> -> rx://<id>`). |
| `SCHEMA.md` | Record schema + the bipartite blast-radius model and misuse/dependency query recipes. |
| `PROVIDER-REFERENCE-NOTE.md` | Why first-party provider/model & leaked-key detector patterns (`provider_reference: true`, 41) are **included** — our own security/routing policy, not client materials. |

> **Shard layout (Lord Michael's "each repo updates its contribution on merge to
> main" directive).** Contributions live in `contributions/<repo>.jsonl`; the
> catalog-side `.github/workflows/assemble-catalog.yml` merges them into
> `corpus.jsonl` and rebuilds the derived views. See the repo-root
> `CONTRIBUTING-CATALOG.md` for the contract.

## Blast-radius / dependency tracing (how agents use it)
- **Who uses pattern X?** → `sources[]` on its corpus record, or all `imports` edges into `rx://<id>` in `gbrg-blast-radius.jsonl`.
- **Highest-blast-radius patterns** = highest `use_count` (top today: `\s+` 132; `\/$` 95; `^sha256:[a-f0-9]{64}$` 71 — the provenance/receipt shapes).
- **Misuse / risk sweep** → filter `risk_class: catastrophic` (secret-shaped) or `redos_suspect: true` (catastrophic-backtracking shapes; 11 flagged — see the ReDoS tracking issue).

## Governance
- **First-party provider refs are included** (`provider_reference: true`) as the estate's own security/routing policy — see `PROVIDER-REFERENCE-NOTE.md`. Competitor/client *marketing* materials remain excluded. The validator gates on JSONL validity + `id`/`pattern` presence.
- **Validate:** `python tools/validate_dataset_manifest.py datasets/regex-operational-dataset/manifest.json`
- `category` and `risk_class` are **curation seeds**, not final governance labels. Extraction is honest-but-heuristic (JS/TS `/…/` literals are ambiguous); a small residue may sit in `category: other`.

## Expanding it
Do **not** hand-edit `corpus.jsonl` / `regex-corpus.jsonl` — they are generated.
Add or update a repo's slice in `contributions/<repo>.jsonl` (same record schema,
`id = rx-<sha1[0:10] of pattern>`; keep client/competitor *marketing* materials
out — first-party provider/security patterns are fine, tag `provider_reference:
true`), then re-assemble and validate:

```bash
python3 tools/assemble_dataset.py datasets/regex-operational-dataset
python3 tools/validate_dataset_manifest.py datasets/regex-operational-dataset/manifest.json
```

In CI this happens automatically: a repo's own workflow regenerates its shard on
merge to `main` and `assemble-catalog.yml` reassembles the corpus. See the
repo-root `CONTRIBUTING-CATALOG.md`.
