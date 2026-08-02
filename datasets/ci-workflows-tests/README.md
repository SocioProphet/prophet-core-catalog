# Estate CI / Workflows / Tests Inventory (`ds.ci-workflows-tests`)

A governed, catalog-registered inventory of the SocioProphet estate's **CI assets** and
**test suites**, so that other agents can **reason about where merges are actually gated,
where CI can fail open, and which repos ship with no automated proof at all** — a
blast-radius / risk view of the estate's quality controls.

Seeded 2026-08-02 by a READ-ONLY harvest of **149 first-party `~/dev` repos**. Part of the
prophet-core-catalog asset-catalog program (sibling to `ds.regex-operational-dataset`).

## Contents
| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `ci-workflows.jsonl` | **741** CI assets — GitHub Actions workflows, Makefile CI target-sets, `.gitlab-ci.yml`, `justfile`, `Taskfile`. One record per asset. |
| `tests.jsonl` | **401** test suites — one record per `(repo, directory, framework)` group, with an approximate `test_count`. |
| `SCHEMA.md` | Record schemas + the bipartite blast-radius / risk model and query recipes. |

## Headline numbers (harvest 2026-08-02)
| Metric | Value |
|---|---|
| First-party repos scanned | 149 |
| CI assets | 741 — 641 GitHub Actions, 99 Makefile-CI, 1 other (Taskfile) |
| GitHub Actions **gating** (fire on `pull_request`/`merge_group`) | 579 |
| GitHub Actions **NOT gating** (push/schedule/dispatch only) | 62 |
| Test suites | 401 (156 vitest/jest, 133 pytest, 100 cargo, 12 go-test) |
| Test declarations counted (approx) | ~17,700 |
| Repos with tests | 68 |
| **Repos with ZERO tests** | **81** |
| Repos running GitHub Actions but with **zero tests** | 46 |

## Risk / blast-radius views (why this dataset exists)

### 1. Repos with ZERO tests (81) — change ships with no automated proof
`Heller-Dirac`, `Heller-Einstein`, `HolographMe`, `SociOS-Linux__cloudshell-fog`, `agent-machine`, `agentos-spine`, `agentos-starter`, `api-contracts`, `cairnpath-mesh`, `contractforge`, `delivery-excellence`, `delivery-excellence-automation`, `delivery-excellence-boards`, `delivery-excellence-bounties`, `delivery-excellence-innersource`, `embeddinglab`, `enhancements`, `functional-model-surfaces`, `graphbrain-contract`, `graphlab`, `hellgraph-bench`, `hodge-program-proof`, `holmes`, `holmes-fix-search-wiring`, `homebrew-prophet`, `homebrew-tap`, `hphd-zeta-mirror-lattice`, `hyperswarm-agent-composable-cluster-scaleup`, `imagelab`, `lattice-forge`, `m2-env-bootstrap`, `memorymesh`, `new-hope`, `newhope-slash-topics-integration`, `nix-openclaw`, `nlplab`, `np-program`, `ns-program`, `ocrlab`, `orion-field-intelligence`, `profit-mpcc`, `prophet-cli`, `prophet-core-catalog`, `prophet-core-contracts`, `prophet-core-infra`, `prophet-core-ingest`, `prophet-core-ledger`, `prophet-core-libs`, `prophet-core-ops-brief`, `prophet-core-policy`, `prophet-core-query`, `prophet-core-scaffolder`, `prophet-domain-gaia-curation-vault`, `prophet-domain-gaia-ontology`, `prophet-health`, `prophet-platform-standards`, `prophet-sheaf-diff`, `prophet-workspace`, `regis-entity-graph`, `semantic-serdes`, `shortcut-overlay`, `slash-topics`, `socioprophet-agent-standards`, `socioprophet-docs-main`, `socioprophet-dotgithub`, `socioprophet-seed-deck`, `socioprophet-standards-storage`, `socioprophet-web`, `socios-ignition`, `socioslinux-web`, `sourceos-a2a-mcp-bootstrap`, `sourceos-build`, `sourceos-model-carry`, `sourceos-spec`, `sourceos-working-spine`, `speechlab`, `timeserieslab`, `translationlab`, `tritrpc-notes-archive`, `videolab`, `workspace-inventory`

> Some are intentionally test-free (docs, homebrew taps, seed decks, standards/contract
> repos). Others (`prophet-cli`, `prophet-health`, `prophet-workspace`, most `prophet-core-*`,
> `socioprophet-web`) are code repos where zero tests is a genuine gap. `zero tests` here
> means "no test files matched the pytest/vitest/jest/cargo/go patterns", not a judgment on
> whether tests are warranted.

### 2. GitHub Actions workflows that do NOT gate merges (62)
These fire only on `push` / `schedule` / `workflow_dispatch` — they never block a PR. Heaviest:
`BearBrowser` (8), `TurtleTerm` (5), `memory-mesh` (5), `sociosphere` (5), `ontogenesis` (4),
`prophet-platform` (4), `source-os` (4), `Noetica` (3), `socioprophet-dotgithub` (3). Many are
legitimately non-gating (nightly builds, release/publish, benchmarks) — the value is being able
to *tell them apart from* a check someone believed was blocking merges but isn't.

### 3. Repos with GitHub Actions but NO gating workflow at all (2)
`api-contracts`, `socioprophet-dotgithub` — CI exists but nothing runs on `pull_request`, so a
change can merge without any workflow executing.

### 4. Fail-open ≡ no-gate candidates (23)
Gating workflows that carry a source-visible fail-open pattern (`continue-on-error: true` or an
`if: always()` guard that can report success despite an upstream failure) — e.g.
`Noetica/validate.yml`, `ProCybernetica/ci.yml`, `agent-machine/validate.yml`,
`prophet-platform/validate-target-diagnostics.yml`, several `SCOPE-D` monitors,
`BearBrowser` nightly DMG/Linux. A green check that can pass while the underlying step fails is,
for gate purposes, no gate. Query: `gating == true && fail_open_signals != []`.

### 5. Highest test mass (widest coverage-loss blast radius)
`openclaw` (~6,900), `prophet-platform` (~3,000), `Noetica` (~1,780), `socioprophet` (~560),
`hellgraph` (~490), `smart-tree` (~420), `sociosphere` (~370), `TurtleTerm` (~360),
`Heller-Winters-Theorem` (~340), `agentplane` (~340), `ProCybernetica` (~340).

## Governance
- **First-party only.** Third-party `AgenticaForge` and `agent-inbox` are excluded per the
  estate boundary; no client/competitor materials are present.
- **`gating`, `fail_open_signals`, `test_count` are curation/risk SEEDS, not final governance
  labels.** `gating` is a *source-derived candidate-required-check* signal; it does not read
  GitHub branch-protection required-status-checks (invisible from source). `test_count` is a
  static occurrence count, not a runtime collection. `last_status` is populated for a 16-repo
  active-org sample only; `null` means **not queried**, not "never ran".
- **Validate:** `python tools/validate_dataset_manifest.py datasets/ci-workflows-tests/manifest.json`

## Expanding it
Re-run the harvest (idempotent — ids are content hashes of `repo/path` and `repo|dir|framework`),
append/replace records, keep third-party and client/competitor materials out, re-run the
validator, and bump `manifest.json` `version`. To turn `last_status` from a sample into full
coverage, extend the `gh run list` pass across all org repos (rate-limit permitting).
