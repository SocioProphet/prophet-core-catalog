# Feedback Loops & Lifecycles — Dogfooding

**Thesis:** SocioProphet applies its own primitives to itself. The platform sells
provenance, calibrated uncertainty (`epistemicLevel`), no-invisible-authority,
blast-radius traceability, fail-closed gates, and supersession-not-retraction. This
document records where we run each of those **on our own process and metadata** — so the
dogfooding is auditable, not asserted. Machine-readable companion: `ds.feedback-loops`.

## The loops

| Loop | Trigger | Feedback signal | Recorded in |
|---|---|---|---|
| **Catalog contribution** | repo merges to main | stale/changed shard | `assemble-catalog.yml`, `catalog-contribute.yml`, prophet-mesh#21 |
| **Pre-merge gate** | PR opened | Copilot + CI findings | every PR review; conformance report |
| **Gap → remediation** | harvest/audit finds a gap | gap count in a dataset | prophet-core-catalog#6, sociosphere#527, procyber#118/#119 |
| **Conformance** | invariant audit | conformance matrix | `LAWFUL-LEARNING-CONFORMANCE.md`, standards-storage#97 |
| **Vocabulary → glossary** | corpus change | vocab/glossary coverage | `ds.topic-vocabulary`, `ds.stemmer-policy` |
| **Blast-radius** | any asset use/change | edge set per asset | `gbrg-blast-radius.jsonl`, sociosphere#522 |
| **Vendor-freshness** | upstream advances | `staleConsumerCount` | sociosphere vendor-freshness plane, #525, prophet-platform#1222 |
| **Assumption reconciliation** | any asserted claim | synthetic/escalated count | `deck-assumptions.reconciled.json`, `ESCALATIONS.md` |

Each loop names the signal that closes it. A loop whose `recorded_in` is empty or unresolvable is a
**never-fired control** — suspect by the estate's own rule.

## The lifecycles

- **Schema/contract:** authored → versioned (`$id`+version) → cataloged → consumed (`$ref`) → superseded. *Guard:* the ProofArtifact singleton check blocks unversioned forks (standards-storage#98).
- **ADR:** proposed → accepted → superseded/deprecated/rejected. *Guard:* `supersedes`/`superseded_by` lineage (`ds.adrs-docs`).
- **Vendored artifact:** vendored → current → stale → re-vendored. *Guard:* `track-latest` freshness policy; the graph records staleness rather than hiding it.
- **Pattern/policy/vocabulary:** harvested → cataloged → validated → consumed → expanded/deprecated. *Guard:* fail-closed validator + provenance.
- **Classification/verdict:** candidate → confirmed/contested → **superseded, not retracted** (append-only).

## How this closes on itself

This document and `ds.feedback-loops` are themselves catalog assets: they carry provenance
(`sources[]`), validate through the same fail-closed gate, and will be kept fresh by the same
contribution loop they describe. The catalog catalogs its own governance — which is the point.

The **catalog-contribution** loop mints its token in CI from the estate's shared ops App (the
already-provisioned `GH_OPS_APP_ID` / `GH_OPS_APP_PRIVATE_KEY` org secrets, gated by
`vars.GH_OPS_APP_CONFIGURED`) — no catalog-specific secret and no per-consumer operator action.
It is `live-pending-token` only in that it stays inert (green) until the shared App is
configured estate-wide and granted `contents` + `pull_requests` write; that one-time permission
grant on the existing org App is the sole human step (GitHub does not expose App-permission
management to CI/WIF identities). Recorded honestly here rather than reported as fully closed.
