# Estate Ontologies & RDF Graph Inventory (`ds.ontologies`)

A governed, catalog-registered inventory of the SocioProphet estate's **formal ontologies
and RDF/turtle graphs** — OWL / RDFS / SKOS / SHACL vocabularies, plus JSON-LD contexts and
`n3`/`rdf` graphs — so that **other agents can find and reuse the estate's formal vocabularies
and trace their use (import blast-radius).**

Seeded 2026-08-02 by a read-only `rdflib` harvest of **21 first-party `~/dev` repos**.

This catalogs the **hand-authored formal vocabularies**. The *topic-model-derived* SKOS lives
in [`ds.topic-vocabulary`](../topic-vocabulary/) and is cross-referenced (via
`upstream_datasets`), **not** duplicated here.

## Contents
| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `ontologies.jsonl` | **360** first-party graph files; one record per file with triple/class/property/skos counts, `base_iri`, `owl:imports` edges (blast-radius), and a `parses` boolean. |
| `third-party-vendored.jsonl` | **8** vendored EXTERNAL ontology source dirs (347 files) — recorded for provenance, **not** ingested as ours. |
| `SCHEMA.md` | Record schema + the import blast-radius model and query recipes. |

## By the numbers (first-party)
- **360** graphs · **44,026** triples · **1,007** classes · **1,349** properties · **27** SKOS concepts.
- By kind: **owl 133** · **jsonld 103** · **shacl 60** · **rdf 49** · **rdfs 9** · **skos 6**.
- By repo: **ontogenesis 256** (the estate's BFO-style upper/middle/lower/domain ontology +
  SHACL shapes + external alignments), socioprophet-standards-knowledge 21, sociosphere 18,
  sourceos-spec 18, agent_descriptors 10, orion-field-intelligence 6, tritfabric 6,
  prophet-platform 4, systems-learning-loops 4, prophet-domain-gaia-ontology 3, and 11 more.
- **348 / 360 parse** cleanly via `rdflib`; **12 do not** (see gaps below).

## Parse-failure gaps (the remediation queue)
Twelve graphs do **not** load standalone under `rdflib`. They are recorded honestly with
`parses:false` and their exception in `parse_error`, in three groups:

**A — dead / unreachable remote `@context` (6, all `ontogenesis`)** — JSON-LD examples whose
published `@context` URL 404s or is otherwise unresolvable offline:
`catalog/civic_stack_registry.jsonld`, `catalog/registry.jsonld`,
`examples/civic-org-service-stack.example.jsonld`,
`examples/smart-home-privacy-nursery.example.jsonld`,
`examples/sovereign-device-orchestration-demo.jsonld`,
`examples/valueflows-governed-task-flow-demo.jsonld`. *Fix: vendor/pin the context, or point at a live URL.*

**B — invalid Turtle: `/` in a prefixed local name (5, all `sociosphere`)** — `repo:Org/repo`
and `ss:role/component` are not legal Turtle prefixed names (the `/` must be escaped or the
term written as a full IRI). This breaks `rdflib` across the neurosymbolic-repo-graph fixtures
**and the main ontology itself**:
`ontologies/sociosphere.ttl` (the real ontology — a genuine bug),
`registry/neurosymbolic-repo-graph-reasoner/valid.active-spine-inference.ttl` (named *valid* yet
does not parse — a genuine bug), plus `diagnostic.stale-pin.ttl`,
`invalid.missing-boundary.ttl`, `invalid.policy-denied-shacl-pass.ttl`.
*Fix: escape `\/` or use `<https://github.com/Org/repo>` full IRIs.*

**C — intentional negative fixture (1)** — `tritfabric/fabric/packs/rdf-to-shir/fixtures/invalid.ttl`
is a deliberately malformed test input; failure here is expected.

## Blast radius — largest & most-imported (how agents trace use)
- **Highest-blast-radius ontology** = most `owl:imports` in-edges. Top target:
  `…/ontogenesis/Upper/upper-core.ttl` — imported **64×**. Change it and 64 estate graphs are
  affected. Next: `catalog/registry.ttl` (17×), `Domains/party-identity.ttl` (10×),
  `Platform/platform.ttl` (9×), `Domains/cyber.ttl` / `Middle/semantic-mapping.ttl` /
  `Domains/business_core.ttl` (8× each).
- **Largest single graphs** (triples): `ontogenesis/Domains/knowledge-commons-canon.ttl`
  **21,496**, `ontogenesis/generated/socioprophet-surfaces.ttl` 459,
  `ontogenesis/catalog/registry.ttl` 434, `ontogenesis/Platform/SocioProphet.ttl` 274
  (41 classes / 39 properties — the densest hand-authored class model).
- **Most-importing graphs** (out-degree): `ontogenesis/Alignments/seven-model-stack.ttl` (13),
  `Alignments/sector-domains.ttl` (11), `prophet/prophet_cli.ttl` (9) — the alignment layer
  that stitches domains to the upper ontology and to external standards.
- Query recipes and the full GBRG mapping are in `SCHEMA.md`.

## Third-party vendored (recorded, NOT ours)
`third-party-vendored.jsonl` lists **8** external ontology source dirs (347 files) vendored
into first-party repos, for provenance only — their triples are **not** attributed to the estate:
ESIPFed **SWEET** (234 files, gaia-world-model), **environmental-exposure-ontology** (59),
ESIPFed **science-on-schema.org** (44), gene-ontology **obographs** (4), **BCO-DMO** Ocean-Data
(3), and **KBpedia KKO** (3 copies across `hellgraph`, `prophet-platform` owl-reasoner, and
`prophet-sheaf-hellgraph`). `gaia-world-model`'s graph corpus is **entirely** vendored external
CV sources — it authored no first-party graphs.

## Governance
- **First-party only.** Worktree/superset clones, `dist/`/`build/` mirrors, and language envs
  are skipped so a graph is never double-counted; `AgenticaForge`/`agent-inbox` (estate
  boundary) excluded. See `SCHEMA.md` → *Governance / scope*.
- **Cross-reference, don't duplicate.** Derived topic-model SKOS is `ds.topic-vocabulary`.
- **Validate:** `make validate` (schema + referential integrity of every `src.<repo>`), and
  `python tools/validate_dataset_manifest.py datasets/ontologies/manifest.json` (JSONL validity).

## Expanding it
Add records to `ontologies.jsonl` (`id = onto-<sha1[0:12] of repo/path>`), keep vendored
external ontologies in `third-party-vendored.jsonl` (not ingested), re-run the harvest/validator,
and bump `manifest.json` `version`. Program context: `docs/ASSET-CATALOG-PROGRAM.md`.
