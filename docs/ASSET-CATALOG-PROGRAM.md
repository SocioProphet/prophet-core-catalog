# Asset Catalog Program

**Goal:** every estate asset is registered in this catalog, kept fresh by CI on each merge to `main`, traceable for reuse / expansion / validation / blast-radius, and — where it is vocabulary — surfaced in the **glossary** with definitions and linked terms.

Backing store: DataHub (`docs/DATAHUB_CATALOG_SPINE.md`). Every dataset carries a manifest validating against `schemas/catalog.dataset.v0.1.json`, with a `README.md` + `SCHEMA.md`. The reference layout is `datasets/regex-operational-dataset/`, landing via PR #5 (not yet on `main` at time of writing) — new datasets mirror it.

## Asset classes (each = a catalog dataset)
| Dataset id | Asset class | Status |
|---|---|---|
| `ds.regex-operational-dataset` | Regex patterns + blast-radius edges (GBRG `kind:pattern`) | **Landed** (PR #5) |
| `ds.topic-vocabulary` | Controlled vocabulary by topic-model source (LSA / LSI / LDA), per-repo + combined-additive + combined-natural; per-repo SKOS turtle graphs; **glossary** (definitions + linked terms) | In progress |
| `ds.rules-policies` | Rules & policies (policy-as-code, SHACL, gates, guardrails, declared invariants); enforced-vs-declared | In progress |
| `ds.ci-workflows-tests` | CI configs, workflows, test suites; gating-vs-non-gating, zero-test repos | In progress |
| _future_ | schemas/contracts · ADRs/docs · ontologies/turtle graphs · models · services/endpoints · agents/manifests · secrets-inventory (refs only) | Roadmap — "all assets" |

The taxonomy is open: a new asset class = a new `datasets/<id>/` with a manifest. "All assets" is the north star, not a fixed list.

## Contribution model — CI-driven, per-repo shards
Cataloging is **not** a one-time central harvest. Each dataset is an assembly of per-repo shards:

```
datasets/<dataset>/contributions/<repo>.jsonl   # one shard per repo, owned by that repo
datasets/<dataset>/corpus.jsonl                  # assembled = concat(shards), built centrally
datasets/<dataset>/<derived...>                  # combined turtle, gbrg edges, glossary, etc.
```

- On merge to `main`, each repo's CI runs the shared extractors (single source of truth in `extractors/`) scoped to itself and updates **its own** `contributions/<repo>.jsonl` via a reusable workflow (`git-ops-standards/.github/workflows/catalog-contribute.yml`, `workflow_call`).
- The catalog's `assemble-catalog.yml` rebuilds `corpus.jsonl` + derived views + validates (fail-closed) on each contribution. It also auto-absorbs a seed monolith into shards, so the initial pull-harvest seed and the ongoing push-contribution converge.
- Cross-repo write needs a **GitHub App installation token minted in CI** (never a PAT — secrets minted in CI), scoped to contents+PRs on this repo only. The reusable workflow mints it per run from the `socioprophet-catalog-contributor` App. Org secrets: `CATALOG_APP_ID` + `CATALOG_APP_PRIVATE_KEY`.

## Glossary
Vocabulary terms and topics from `ds.topic-vocabulary` land in the **catalog glossary**: each topic and high-signal term becomes a glossary entry with an authored **definition** and **linked terms** (`skos:related` / `skos:broader` / `skos:narrower`), emitted both as SKOS turtle and in DataHub business-glossary form for native ingest.

## Blast radius
Every record lists its usage sites (`sources[]`), which are the blast-radius edges. Patterns project into GBRG as `SemanticCell kind:pattern` (`rx://<id>`) with `imports` edges (`sociosphere/gbrg` PR #522). The same edge model generalizes to other asset classes (a policy is `imports`-ed by the gates that reference it; a workflow by the repos that call it).

## Governance / hard rule
First-party assets are the point — **include** our own security/routing detectors, provider integration surface, policies, and vocabulary (provider names appearing in our own code are fine). **Exclude** client materials and competitor *marketing* materials (this scrubbed the seed deck: Palantir / BAAP / Liminal). The dataset validator (`tools/validate_dataset_manifest.py`) is fail-closed on schema + record integrity.

## Provenance to the estate's own principles
This program is [Lawful Learning](https://github.com/SocioProphet/socioprophet-seed-deck) applied to the estate's metadata: assets are declared (no invisible authority), carry provenance, and are traceable — the same discipline the platform sells.
