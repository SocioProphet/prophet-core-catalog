# Estate Schemas & Contracts Catalog (`ds.schemas-contracts`)

A governed, catalog-registered inventory of the SocioProphet estate's **schemas and contracts**, so that
**agents can find, reuse, validate, and trace the blast radius of every contract** in the estate.

Seeded 2026-08-02 by a READ-ONLY, file-type harvest of **90 first-party `~/dev` repos**.

## Contents
| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `contracts.jsonl` | **2328** contract records; one per contract file. Each carries `consumers[]` — the files that `$ref`/import it = its blast-radius edges. |
| `SCHEMA.md` | Record schema + the blast-radius model and reuse/misuse/dependency query recipes. |

## Coverage by kind
| kind | count |
|---|---|
| json-schema | 2240 |
| avro | 48 |
| protobuf | 17 |
| openapi | 15 (OpenAPI + AsyncAPI API-description contracts) |
| other | 8 (Zod/TypeBox/Pydantic contract modules under `contracts/`) |

## Blast-radius / dependency tracing (how agents use it)
- **Who uses contract X?** → its `consumers[]` array (capped at 40; `consumer_count` is the true in-degree). Every element is one `code → contract` edge.
- **Highest-blast-radius contracts** (change these and the most breaks):

| consumers | contract | `$id` / package |
|---|---|---|
| 30 | `SCOPE-D/config/schemas/proof-artifact.schema.json` | `https://socioprophet.org/schemas/scope-d-proof-artifact.schema.json` |
| 29 | `prophet-platform/schemas/proof-artifact.schema.json` | `https://schemas.socioprophet.ai/prophet-platform/proof-artifact.schema.json` |
| 22 | `ProCybernetica/schemas/claim.schema.json` | `https://schemas.socioprophet.org/procybernetica/claim.schema.json` |
| 22 | `economic-prophet/schemas/vdt_profile.schema.json` | `—` |
| 22 | `socioprophet-standards-knowledge/schemas/jsonschema/core/claim.schema.json` | `socioprophet://schemas/knowledge/core/claim.schema.json` |
| 20 | `SourceOS/caps/semantic-search-bi/schemas/evidence_event.schema.json` | `—` |
| 20 | `sherlock-search/caps/search-backend-graph/schemas/evidence_event.schema.json` | `—` |
| 20 | `sherlock-search/caps/semantic-search-bi/schemas/evidence_event.schema.json` | `—` |
| 20 | `sherlock-search/caps/search-backend-lexical/schemas/evidence_event.schema.json` | `—` |
| 20 | `sherlock-search/caps/search-backend-vector/schemas/evidence_event.schema.json` | `—` |

- **Reuse**: filter by `kind` + `schema_id`; prefer the highest-`consumer_count` variant (most battle-tested).
- **Validation**: compile/validate each artifact under its engine (JSON Schema draft, `protoc`, Avro, `openapi` linter, SHACL).

## Governance — unversioned contracts (remediation surface)
**1052 of 2328 contracts (45.2%) declare NO version** (`version: ""`) — no `$id` version token, no `version`/`info.version` field. These are the silent-drift risk: a consumer cannot pin what it depends on. They are the first curation target. Query: `jq 'select(.version=="")' contracts.jsonl`.

## Contracts by repo (top 15)
| repo | contracts |
|---|---|
| `sourceos-spec` | 354 |
| `prophet-platform` | 314 |
| `SCOPE-D` | 133 |
| `sociosphere` | 129 |
| `agentplane` | 125 |
| `ProCybernetica` | 121 |
| `socioprophet-standards-storage` | 115 |
| `gaia-world-model` | 62 |
| `superconscious` | 57 |
| `socioprophet-standards-knowledge` | 55 |
| `exodus` | 48 |
| `sherlock-search` | 39 |
| `Noetica` | 35 |
| `semantic-serdes` | 35 |
| `prophet-workspace` | 34 |

## Governance
- **First-party only.** Duplicate working copies (`*-chronos-superset`, `*-kairos-draft`, `prophet-platform` branch clones) and third-party trees (`AgenticaForge`, `agent-inbox`) are excluded. No client/competitor materials.
- **Validate:** `python3 tools/validate_dataset_manifest.py datasets/schemas-contracts/manifest.json` (schema + JSONL validity, fail-closed) and `python3 tools/validate_internal_ops_libraries.py` (every `src.<repo>` in `sources` resolves).
- `kind`, `intent`, and `version` are honest-but-heuristic **seeds** for curation, not final governance labels. `consumers[]` is best-effort (basename/`$id` reference matching), a floor on true blast radius.

## Expanding it
Add records to `contracts.jsonl` (same schema), keep client/competitor materials out, re-run the validator, bump `manifest.json` `version`. This mirrors the reference layout `datasets/regex-operational-dataset/` and the program in `docs/ASSET-CATALOG-PROGRAM.md`.
