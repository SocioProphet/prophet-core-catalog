# Estate Topic-Model Controlled Vocabulary + Glossary (`ds.topic-vocabulary`)

A governed, catalog-registered **controlled vocabulary** for the SocioProphet estate,
derived by topic modelling every first-party repo, plus a **glossary layer** (authored
definitions + linked terms) and **per-repo SKOS turtle graphs** so that other agents can
reuse the vocabulary, expand it, trace the blast radius of any term, and ingest it into the
DataHub business glossary.

Seeded 2026-08-02 by a read-only topic-model pass over **130** first-party `~/dev` repos
(19 more skipped as too-small — see below).

## Method — three sources, labelled by model

For each repo a one-doc-per-file corpus is built from code + docs
(`.py .ts .js .rs .go .md .rst .txt .yaml .yml .json`; lockfiles / `*.min.*` / files >200 KB /
`node_modules` / `dist` / `target` / vendored dirs skipped). Identifiers are split on
camelCase/snake_case, lowercased; stopwords + language keywords + ≤2-char tokens dropped.
Then, at **k=10 topics, top 15 terms/topic**:

| source | model | library |
|---|---|---|
| **LSA** | Truncated SVD on TF-IDF | scikit-learn `TruncatedSVD` |
| **LSI** | Latent Semantic Indexing on the TF-IDF corpus | gensim `LsiModel` |
| **LDA** | Latent Dirichlet Allocation on counts | scikit-learn `LatentDirichletAllocation` |

> **LSA ≡ LSI, honestly.** LSA and LSI are the *same* latent-semantic family — a truncated
> SVD of a term–document matrix. We produce **both**, under their own `source` labels, for
> completeness and cross-implementation comparison (sklearn dense SVD vs. gensim's streaming
> SVD over a `TfidfModel` corpus); expect their topics to be closely related, not independent
> evidence. LDA is the genuinely different (probabilistic, generative) model.

A repo's controlled vocabulary = the union of the top terms across its topics, each term
carrying `{topic_id, source, rank, weight}`.

## Combined vocabularies (two ways)

- **combined-additive** — the set-union of every repo's per-method vocabulary, each term
  annotated with the repos + methods it came from. This is the **blast-radius / provenance
  edge set** and lives in `graphs/estate-combined.ttl`.
- **combined-natural** — LSA/LSI/LDA re-run over the **whole-estate pooled corpus**; the
  naturally-derived estate topics/terms (`scope: combined-natural` in the JSONL).

## Contents

| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `vocabulary.jsonl` | **40,840** records, one per `(term, repo, source, scope)`. |
| `topics.jsonl` | **3,747** records, one per `(repo, source, topic_id)`: top terms (+ coherence slot). |
| `glossary.jsonl` | **7,724** glossary entries — **3,747 topics** (each with an authored definition + `narrower_terms` = member terms) and **3,977 terms** (each with a definition + `related_terms` + `repos` provenance). |
| `glossary/business_glossary.yml` | Native **DataHub business-glossary v1** file: one root node of the 3,977 distinct terms + one child node per repo holding its topic entries. Ingest with the `datahub-business-glossary` source. |
| `graphs/<repo>.ttl` | Per-repo SKOS `ConceptScheme` (130 files): concepts w/ `skos:prefLabel` + `skos:definition` + `dct:source`, topics as `skos:Collection`, and `skos:broader`/`skos:narrower`/`skos:related` links. |
| `graphs/estate-combined.ttl` | The combined-additive union scheme: each concept annotated with `tv:fromRepo` / `tv:fromMethod` (blast-radius provenance) + `skos:definition` + `skos:related`. |
| `SCHEMA.md` | Full record schemas + the SKOS/glossary model + query recipes. |

## Glossary layer (DataHub-grade)

Per the catalog's DataHub spine (`docs/DATAHUB_CATALOG_SPINE.md`), the vocabulary lands in the
**glossary with definitions and linked terms**, not just as raw vocab:

- **Topics are glossary nodes/terms** — each topic gets an authored one-sentence definition
  summarising its top terms, and `narrower_terms` = its member vocabulary.
- **Terms** — each distinct vocabulary term gets a concise definition. Top-of-topic
  (high-signal) terms get an authored sentence citing co-occurring siblings + repo provenance;
  long-tail terms use a contextual template. Definitions are model-derived (co-occurrence +
  provenance) and **curation seeds**, not final human-blessed governance labels.
- **Linked terms** = `related_terms` (co-topic siblings) + `broader` (its topic/scheme) +
  `narrower` (member terms). In turtle these are `skos:related` / `skos:broader` / `skos:narrower`.

The spine doc (`docs/DATAHUB_CATALOG_SPINE.md`) is conceptual and does **not** mandate a
specific glossary file format, so we emit the **standard DataHub business-glossary YAML**
(`version: 1`, `nodes[].terms[]` with `description`, `term_source: INTERNAL`, `related_terms`)
which DataHub ingests natively; `glossary.jsonl` + the SKOS turtle remain the source of truth.

## Blast-radius / provenance tracing (how agents use it)

- **Which repos use term X?** → `repos[]` on its `glossary.jsonl` term entry, or the
  `tv:fromRepo` / `rdfs:seeAlso` edges on its concept in `estate-combined.ttl`.
- **Which methods surfaced term X?** → `tv:fromMethod` (LSA/LSI/LDA) on the same concept, or
  `combined-additive` `weight` = number of repos it appeared in.
- **What is this repo *about*?** → its `topics.jsonl` rows / `graphs/<repo>.ttl` collections.
- **Cross-estate themes** → `scope: combined-natural` topics.

## Governance / hard rule

First-party terms are our own vocabulary and are **retained** — including provider/model names
that appear in **our** code (e.g. `anthropic`, `openai`, `aws`). **No client or competitor
*marketing* materials were ingested**: the corpus is exclusively first-party `~/dev` source,
and the two known third-party checkouts (`AgenticaForge`, `agent-inbox`) were excluded.

- **Validate:** `python tools/validate_dataset_manifest.py datasets/topic-vocabulary/manifest.json`
- **Every turtle parses** via `rdflib.Graph().parse` (all 131 graphs checked at build time).
- **Coherence** is left `null` in `topics.jsonl` for this seed (u_mass coherence needs the
  per-repo gensim corpora persisted; deferred to a curation pass — the field is present).

## Repos skipped (too small)

19 repos yielded <4 usable documents and were skipped (recorded, not failed):
`Heller-Dirac, Heller-Einstein, hodge-program-proof, homebrew-tap, hphd-zeta-mirror-lattice,
lattice-forge, m2-env-bootstrap, memorymesh, np-program, ns-program, prophet-core-infra,
prophet-core-ingest, prophet-core-libs, prophet-core-ops-brief, prophet-core-scaffolder,
prophet-domain-gaia-curation-vault, prophet-domain-gaia-ontology, prophet-sheaf-diff,
tritrpc-notes-archive`.

## Expanding it

Re-run the topic pass and append records (same schemas); keep client/competitor *marketing*
materials out (first-party provider names are fine); re-run the validator; bump `manifest.json`
`version`. Human curation should replace seed definitions with governance-blessed ones and set
`coherence`.
