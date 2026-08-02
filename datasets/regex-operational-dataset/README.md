# Estate Regex Operational Dataset (`ds.regex-operational-dataset`)

A governed, catalog-registered dataset of the SocioProphet estate's regular-expression
patterns, so that **other agents can reuse them, expand them, validate them, and trace
the blast radius of any use, misuse, or dependency.**

Seeded 2026-08-02 by a read-only harvest of 13 first-party `~/dev` repos.

## Contents
| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `regex-corpus.jsonl` | **2,308** distinct patterns; one record per pattern; identical patterns deduped, with every usage site listed in `sources[]` (these are the blast-radius edges). |
| `classifier-set.json` | 12 named classifiers (secret-detection, pii-detection, path-traversal, semver, …) grouping pattern ids. |
| `gbrg-blast-radius.jsonl` | GBRG-ready mapping: each pattern as a `SemanticCell` (`kind: pattern`, `rx://<id>`) + one `imports` edge per usage site (`code://<repo>/<file> -> rx://<id>`). |
| `SCHEMA.md` | Record schema + the bipartite blast-radius model and misuse/dependency query recipes. |
| `PROVIDER-REFERENCE-NOTE.md` | Why first-party provider/model & leaked-key detector patterns (`provider_reference: true`, 41) are **included** — our own security/routing policy, not client materials. |

## Blast-radius / dependency tracing (how agents use it)
- **Who uses pattern X?** → `sources[]` on its corpus record, or all `imports` edges into `rx://<id>` in `gbrg-blast-radius.jsonl`.
- **Highest-blast-radius patterns** = highest `use_count` (top today: `\s+` 132; `\/$` 95; `^sha256:[a-f0-9]{64}$` 71 — the provenance/receipt shapes).
- **Misuse / risk sweep** → filter `risk_class: catastrophic` (secret-shaped) or `redos_suspect: true` (catastrophic-backtracking shapes; 11 flagged — see the ReDoS tracking issue #6 and the remediation file below).

## ReDoS remediation (issue #6)
- **Worklist:** `redos-remediations.jsonl` — one record per flagged pattern: `{id, original, hardened, rationale, sites:[{repo,file,line}], status}`. This catalog delivers the **verified hardened patterns + the exact usage sites**; the actual source edits land in the owning repos via their own PRs.
- **Status:** all 11 `status: "proposed"`. Empirical timing (CPython `re` + V8) shows **none exhibit exponential catastrophic backtracking** — every flagged shape has a *disjoint separator* (literal `.`, `\s`/`[ \t]` vs. a word class) or uses the Friedl unrolled quote matcher `(?:[^"\\]|\\.)*`, so decomposition is unambiguous and backtracking is already linear (worst adversarial case ~4 ms on 60 KB). They are true-positives on *shape* but **unbounded**, which still trips static scanners and leaves worst-case work uncapped.
- **Fix strategy:** bound each pattern — keep the `^…$` anchors, add per-token length caps (`{1,N}`), cap repetition counts, replace `\s` with `[ \t]` where line-local, and use possessive/atomic runs where the engine supports it (Python 3.11+). Every hardened pattern was verified to (a) still match its intended inputs and (b) drop worst-case adversarial time to sub-millisecond. **None required escalation.**

## Governance
- **First-party provider refs are included** (`provider_reference: true`) as the estate's own security/routing policy — see `PROVIDER-REFERENCE-NOTE.md`. Competitor/client *marketing* materials remain excluded. The validator gates on JSONL validity + `id`/`pattern` presence.
- **Validate:** `python tools/validate_dataset_manifest.py datasets/regex-operational-dataset/manifest.json`
- `category` and `risk_class` are **curation seeds**, not final governance labels. Extraction is honest-but-heuristic (JS/TS `/…/` literals are ambiguous); a small residue may sit in `category: other`.

## Expanding it
Add records to `regex-corpus.jsonl` (same schema, `id = rx-<sha1[0:10] of pattern>`), keep client/competitor *marketing* materials out (first-party provider/security patterns are fine — tag `provider_reference: true`), re-run the validator, bump `manifest.json` `version`.
