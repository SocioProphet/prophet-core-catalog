# Estate ADRs & Key Docs Catalog (`ds.adrs-docs`)

A governed, catalog-registered inventory of the SocioProphet estate's **Architecture
Decision Records (ADRs)** and **key load-bearing docs**, so that other agents can **find
the decisions that govern the estate, trace what supersedes what, and see which repos
carry no recorded decisions at all.**

Seeded 2026-08-02 by a **read-only** markdown harvest of **149 first-party `~/dev` repos**.

## Contents
| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `adrs.jsonl` | **140** ADR records; one per decision record (see `SCHEMA.md`). |
| `docs.jsonl` | **1,000** key-doc records (READMEs + load-bearing design/spec/governance/rfc docs). |
| `README.md` | This overview + the still-present-supersessions and zero-ADR sweeps. |
| `SCHEMA.md` | Record schemas + harvest heuristics + query recipes. |

## ADRs at a glance
| Status | Count |
|---|---|
| accepted | 80 |
| proposed | 51 |
| superseded | 2 |
| deprecated | 0 |
| rejected | 0 |
| unknown (no parseable status line) | 7 |
| **total** | **140** |

**Repos with the most recorded decisions:** `sourceos-spec` (35), `socioprophet-standards-storage` (16),
`prophet-platform-standards` (11), `prophet-platform` (10), `agentplane` (8), `ProCybernetica` (6),
`gitea-sovereign` (6), `meshrush` (5).

## Key docs at a glance
| Kind | Count |
|---|---|
| spec | 355 |
| governance | 181 |
| design | 178 |
| readme | 169 |
| other | 114 |
| rfc | 3 |
| **total** | **1,000** |

## Governance sweeps (what this catalog surfaces)

### Superseded / deprecated ADRs still lying around
Decisions marked dead but still present in-tree — anyone reading the folder could still act on them:

| Repo | ADR | Path | Superseded by |
|---|---|---|---|
| `sourceos-spec` | 0001 | `docs/adr/0001-truth-surfaces-b11-delta.md` | ADR-0009 |
| `sourceos-spec` | 0001 | `docs/adr/0001-truth-surfaces-b11-delta-appendix-a-reuse-map.md` | ADR-0009 |

Both are the old `0001` "TruthSurface (B¹¹) / Δ-Surface" records, renumbered to **ADR-0009** to
resolve a duplicate-`0001` collision. They remain as tombstones — fine, but agents must follow
`superseded_by` and not treat them as live.

### Repos with ZERO ADRs
**119 of 149 first-party repos (80%) carry no recorded architecture decision at all** — only 30
repos have any ADR. Substantial repos (≥ 8 key docs but **no** ADR) where the absence is most
notable — decisions are being made but not recorded:

`policy-fabric` (41 docs), `openclaw` (41), `ontogenesis` (41), `tritrpc` (30), `Heller-Godel` (26),
`smart-tree` (20), `superconscious` (13), `contractforge` (12), `workstation-contracts` (11),
`memory-mesh` (11), `economic-prophet` (11), `source-os` (10), `Heller-Winters-Theorem` (10),
`alexandrian-academy` (8), `TurtleTerm` (8).

These are candidates for a backfill: a repo doing governance/policy work (`policy-fabric`,
`workstation-contracts`, `contractforge`) with zero ADRs is deciding things nowhere durable.

## How agents use it
- **Find the decision that governs X** → grep `adrs.jsonl` by `intent`/`title`, then read `path` in `repo`.
- **Is this decision still live?** → check `status`; if `superseded`/`deprecated`, follow `superseded_by`.
- **What supersedes / is superseded by ADR-N?** → `supersedes` / `superseded_by` fields.
- **Where are decisions NOT being recorded?** → repos absent from `adrs.jsonl` (see the zero-ADR sweep).
- **What are the load-bearing docs for a repo?** → filter `docs.jsonl` by `repo`; `kind` narrows to
  `governance` / `spec` / `design`.

## Governance / scope
- **First-party only.** Skipped `*.wt` worktrees, `_*` dirs, `node_modules`/vendored, `@`-pinned and
  `-main` embedded third-party snapshots (e.g. the ESIPFed `science-on-schema.org` decisions vendored
  under `gaia/cv/sources/`), and ADR **template** files. Excluded `AgenticaForge` / `agent-inbox`
  (third-party). No client / competitor materials.
- `status` is parsed from the ADR's own front-matter / `Status:` line / status table; `unknown` means
  the record carries no machine-readable status (honest, not a guess).
- The validator (`tools/validate_dataset_manifest.py`) gates on schema + JSONL validity + `id` presence,
  fail-closed when a data-bearing manifest ships no data file.

## Expanding it
Append records to `adrs.jsonl` / `docs.jsonl` (same schema), keeping the id stable
(`adr.<repo>.<number>` / `doc.<repo>.<slug>`), re-run
`python tools/validate_dataset_manifest.py datasets/adrs-docs/manifest.json`, and bump
`manifest.json` `version`. New repos need a `sources/src.<repo>.json`. Part of the
[Asset Catalog Program](../../docs/ASSET-CATALOG-PROGRAM.md) — the ADRs/docs asset class.
