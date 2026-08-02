# Whole-catalog extractors — making the refresh loop cover every dataset

The central re-harvest (`.github/workflows/catalog-refresh.yml`) read-only clones the
estate, runs the shared `extractors/`, refreshes each dataset's per-repo shards, and
reassembles + reindexes behind the fail-closed percolation canary. Until now the loop
**only truly refreshed the regex dataset** — it was the one dataset with a real,
schema-matched per-repo extractor. The other datasets had either no extractor or a thin
"hook" whose v0 record schema did not match the committed monolith, so their output was
staged-and-dropped: the loop was *cosmetic* for them (it re-ran, but nothing they
committed ever changed).

This closes that gap. Every dataset below now has a **real per-repo extractor** that
emits records in the dataset's committed record schema, plus a **harvest assembler**
(`tools/assemble_dataset.py`, driven by `extractors/harvest_map.json`) that rebuilds the
dataset's primary file(s) from the refreshed shards.

## Contract (every extractor)

```
python3 extractors/extract_<dataset>.py <repo_path> <repo_name> [--out FILE]
```

Read-only, deterministic (a re-run on unchanged input is byte-identical), stdlib-only
(rdflib is the single exception, used by the ontologies extractor and already required).
Output is one JSONL record per asset, scoped to `<repo_name>`, matching the dataset's
`SCHEMA.md`. `extractors/harvest_map.json` binds each dataset → its extractor + how to
reassemble; `tools/assemble_dataset.py` reads it and, for a listed dataset, rebuilds the
named primary file(s) from `datasets/<ds>/<contrib_dir>/*.jsonl` — **fail-safe**: if no
shards exist yet, the committed primary files are left untouched (the loop is a no-op
until the extractor has run).

## Refresh coverage

### Self-refreshing (real per-repo extractor, wired into the loop)

| dataset | extractor | primary file(s) | merge | notes |
|---|---|---|---|---|
| `schemas-contracts` | `extract_schemas_contracts.py` | `contracts.jsonl` | single-owner | JSON-Schema / proto / avro / OpenAPI / SHACL / contract modules; consumers = in-repo `$ref`/import edges |
| `services-endpoints` | `extract_services_endpoints.py` | `services.jsonl` | single-owner | k8s Service/Ingress/Deployment/Rollout, ArgoCD App, docker-compose, gRPC, FastAPI/Express/OpenAPI routes |
| `ontologies` | `extract_ontologies.py` | `ontologies.jsonl` | single-owner | rdflib parse; triples/classes/properties/concepts + `owl:imports`; vendored-external trees skipped (kept in `third-party-vendored.jsonl`) |
| `adrs-docs` | `extract_adrs_docs.py` | `adrs.jsonl` + `docs.jsonl` | single-owner | ADR status/supersession lineage + signal-filtered key docs (routed by `adr.`/`doc.` id prefix) |
| `agents-manifests` | `extract_agents_manifests.py` | `agents.jsonl` | single-owner | subagents, blueprints, MCP servers, A2A cards, capability decls + the `connections` sub-graph and substrate refs |
| `rules-policies` | `extract_rules_policies.py` | `policies.jsonl` | single-owner | rego / kyverno / gatekeeper / rbac / shacl / gitleaks / json-schema gates / wallguard docs |
| `ci-workflows-tests` | `extract_ci_workflows_tests.py` | `ci-workflows.jsonl` + `tests.jsonl` | single-owner | Actions workflows (triggers/jobs/gating/fail-open signals) + test suites (routed by `wf-`/`ts-` id prefix) |
| `models` | `extract_models.py` | `models.jsonl` | union | provider/local model refs from routing/config; `used_by[]` unioned across repos; `runtime-model-digests.jsonl` preserved |
| `regex-operational-dataset` | `extract_regex.py` (pre-existing) | `regex-corpus.jsonl` | union | unchanged; the original live dataset |

`single-owner` = each record id is owned by exactly one repo, so assembly is
concat + dedup-by-id. `union` = the same id may recur across repos (e.g. one model used
by many), so its list fields (`used_by`) are unioned — the same semantics the regex
dataset uses.

### Central-rebuild (NOT a per-repo shard — documented, not wired)

| dataset | why it is not per-repo |
|---|---|
| `topic-vocabulary` | The product is **topic-model-derived** SKOS — LSA/LSI/LDA fitted over the *whole* estate corpus (see `topics.jsonl` `source: LSA`, the large `vocabulary.jsonl`, and `graphs/*.ttl`). A topic model is a global factorization, not a per-repo shard: the term–topic loadings only exist relative to the full document–term matrix, so re-fitting one repo at a time would change every other repo's topics. It stays a periodic **central rebuild**. A thin heading-level hook still runs to a staged artifact each loop (liveness only); it is deliberately *not* the topic-model product and is not committed. |
| `stemmer-policy` | A curated knowledge base of stemmer algorithms (Porter/Snowball/…) and per-domain assignment policy — estate-authored reference data, not harvested from repo source. No per-repo signal exists to extract. |

## Proving the loop is live (not cosmetic)

```
# clone a few public repos read-only, harvest, assemble, index, canary
python3 extractors/extract_<ds>.py <clone> <name> --out datasets/<ds>/contributions/<name>.jsonl
python3 tools/assemble_dataset.py --all        # rebuilds primary files from shards (harvest mode)
python3 tools/build_catalog_index.py           # re-ingest the READ half
python3 tools/verify_percolation.py            # FAIL-CLOSED canary — teeth both ways
```

The canary has teeth: a dataset that harvests to **zero** assets (a broken/empty
extractor) turns it red (`datasets present but contributed 0 assets`), so a refresh that
stops percolating never commits.

## Ids

`schemas-contracts`, `services-endpoints`, `ontologies`, `models`, and `ci-workflows-tests`
reproduce the central harvest's id formulas exactly (idempotent, no churn). `adrs-docs`,
`agents-manifests`, and `rules-policies` recompute deterministic ids that may differ from
the initial hand-seeded corpus; the first live harvest replaces those corpora in place.
