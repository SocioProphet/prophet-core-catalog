# Estate Stemmer / Tokenizer / Vocabulary Assignment Policy (`ds.stemmer-policy`)

A governed, catalog-registered dataset that answers one question for every estate corpus:
**which normalization do we apply to this text, and why?** It pairs (a) a catalog of the
*available* stemmers / lemmatizers / tokenizers / controlled vocabularies with (b) a per-repo
and per-domain **assignment** of the right normalizer + vocabulary for the right domain — so the
estate uses the right normalization for the right domain instead of a single global default.

Authored 2026-08-02. Domains inferred read-only from each first-party `~/dev` repo's README.

> **Lord Michael's rule, encoded:** `prophet-health` / any health-domain repo →
> **Snowball** stemmer + **SNOMED CT** vocabulary + **code-identifier** tokenizer for code files.

## Contents
| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `stemmers.jsonl` | **13** available normalizers — one record per option: `{id, name, kind, family, languages[], best_for_domains[], notes, license, resource_ref}`. Stemmers (Porter, Snowball/Porter2, Lancaster, Krovetz), a spaCy lemmatizer, tokenizers (code-identifier camel/snake split; Unicode word), a no-op normalizer, and controlled vocabularies (SNOMED CT, MeSH, UMLS, legal, finance). |
| `assignment-policy.jsonl` | **128** assignments — 7 per-domain fallbacks + **121** per-repo records: `{id, scope, target, domain, stemmer, tokenizer, code_tokenizer, vocabulary, rationale}`. |
| `SCHEMA.md` | Record schemas, the code-identifier splitter spec, and the resolution / query recipes. |

## How to resolve a policy (how agents use it)
1. **Look up the repo** in `assignment-policy.jsonl` (`scope: "repo"`, `target: "<repo>"`).
2. Fall back to its **domain** record (`scope: "domain"`) if the repo is not listed.
3. Apply `tokenizer` to prose and `code_tokenizer` to source/config files, then `stemmer`
   (or lemmatizer), then normalize surface terms against `vocabulary` (if non-null) by
   resolving each id in `stemmers.jsonl`.

Example — `prophet-health`:
```json
{"stemmer":"stem.snowball","tokenizer":"tok.unicode-word",
 "code_tokenizer":"tok.code-identifier","vocabulary":"vocab.snomed-ct"}
```
Clinical narrative is Unicode-word tokenized then Snowball-stemmed; surface terms are mapped to
SNOMED CT **concept ids** against a licensed local terminology server (SNOMED CT content is
**never vendored** here — pointer + license note only); code files use the code-identifier tokenizer.

## Domain defaults
| Domain | stemmer | tokenizer (prose / code) | vocabulary |
|---|---|---|---|
| **health** | `stem.snowball` | `tok.unicode-word` / `tok.code-identifier` | `vocab.snomed-ct` (MeSH/UMLS complements) |
| **legal / regulatory / compliance** | `stem.snowball` | `tok.unicode-word` / `tok.code-identifier` | `vocab.legal-terms` |
| **finance / markets** | `stem.snowball` | `tok.unicode-word` / `tok.code-identifier` | `vocab.finance-terms` |
| **code / dev-tooling** | `stem.none` (no linguistic stemming) | `tok.code-identifier` / `tok.code-identifier` | — |
| **security** | `stem.none` | `tok.code-identifier` / `tok.code-identifier` | — |
| **ontology / knowledge / NLP** | `stem.snowball` (`lemma.spacy` for entity/relation extraction) | `tok.unicode-word` / `tok.code-identifier` | — |
| **general / platform** | `stem.snowball` | `tok.unicode-word` / `tok.code-identifier` | — |

## How this feeds `ds.topic-vocabulary` and the glossary
This dataset is the **normalization contract upstream of topic modeling.** `ds.topic-vocabulary`
builds controlled vocabularies per topic-model source (LSA / LSI / LDA) per repo; those models
are only comparable if every repo's text is tokenized and stemmed the **same way its domain
dictates**. So the topic-vocabulary extractor MUST resolve `ds.stemmer-policy` for each repo and
tokenize/stem with the assigned `tokenizer`/`code_tokenizer`/`stemmer` **before** fitting the
model — a health repo's terms are Snowball-stemmed and SNOMED-normalized, a code repo's are
identifier-split and left unstemmed. Consistent normalization is what makes the per-repo,
combined-additive and combined-natural vocabularies mergeable.

Downstream, the **catalog glossary** (see `docs/ASSET-CATALOG-PROGRAM.md` → Glossary) inherits the
same policy: a glossary entry's surface forms are the stemmed/lemmatized variants under its repo's
policy, and health/legal/finance glossary terms carry their `vocabulary` concept ids
(`skos:exactMatch` to SNOMED CT / legal / finance concepts) so linked terms
(`skos:related` / `broader` / `narrower`) align across repos.

## Governance
- **First-party + open standards only.** Snowball, Porter, Lancaster, Krovetz, spaCy, MeSH are
  open/free and referenced directly. **Licensed terminologies (SNOMED CT, UMLS) are POINTERS +
  license notes only — their content is never vendored** (SNOMED CT needs a SNOMED International
  Affiliate License; UMLS needs a UMLS Metathesaurus License). Legal/finance term lists are
  first-party, assembled from public-domain / permissively-licensed sources. No client or
  competitor marketing materials.
- **Validate:** `python tools/validate_dataset_manifest.py datasets/stemmer-policy/manifest.json`
- `domain` is an inference from each repo's README and is a **curation seed**, not a final label;
  refine a repo's assignment by editing its record, not the domain fallback.

## Expanding it
- **New normalizer/vocabulary:** add a record to `stemmers.jsonl` (`id` = `stem.*` / `lemma.*` /
  `tok.*` / `vocab.*`); for any licensed terminology capture a **pointer + license note only**,
  never the content; re-run the validator; bump `manifest.json` `version`.
- **New repo / re-classification:** add or edit a `scope: "repo"` record in
  `assignment-policy.jsonl`; keep the health rule intact (health → `stem.snowball` +
  `vocab.snomed-ct` + `tok.code-identifier`); re-run the validator.
