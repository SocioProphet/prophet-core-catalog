# Stemmer / Tokenizer / Vocabulary Policy — Schema & Resolution Model

Governed, catalog-ready policy for text normalization across the SocioProphet estate.
Two files: a catalog of AVAILABLE normalizers (`stemmers.jsonl`) and an ASSIGNMENT of the
right ones to each repo/domain (`assignment-policy.jsonl`). First-party + open standards only;
licensed terminologies are pointers, never vendored (see hard rule below).

## Files

| file | contents |
|---|---|
| `stemmers.jsonl` | one JSON object per AVAILABLE normalizer/tokenizer/vocabulary (record schema below) |
| `assignment-policy.jsonl` | one JSON object per repo (`scope:"repo"`) and per domain (`scope:"domain"`) |
| `manifest.json` | catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`) |
| `SCHEMA.md` | this file |

## Record schema — `stemmers.jsonl`

```json
{
  "id": "stem.snowball",
  "name": "Snowball (Porter2) stemmer",
  "kind": "stemmer|lemmatizer|tokenizer|vocabulary",
  "family": "porter|snowball|lancaster|krovetz|spacy-lemma|code-identifier|domain-terminology",
  "languages": ["en", "fr", "..."],
  "best_for_domains": ["health", "legal", "..."],
  "notes": "<when to use / caveats>",
  "license": "<SPDX-ish or license note; POINTER-ONLY for licensed terminologies>",
  "resource_ref": "<URL or first-party:// pointer — content is NOT vendored>"
}
```

Field notes:
- **kind** — `stemmer` (suffix-stripping to a stem), `lemmatizer` (dictionary lemma),
  `tokenizer` (segmentation only, no stemming), `vocabulary` (controlled terminology / term list).
- **family** — algorithm/source family. `code-identifier` also covers the Unicode-word and no-op
  tokenizers (segmentation-only normalizers); `domain-terminology` covers all controlled vocabularies.
- **languages** — `"code"` = source code; `"multi"` = language-agnostic; otherwise ISO 639-1.
- **resource_ref / license** — for **licensed** terminologies (SNOMED CT, UMLS) this is a **pointer**
  and the license note is load-bearing: the terminology content is never stored in this repo.

Catalog contents (13): stemmers `stem.porter`, `stem.snowball`, `stem.lancaster`, `stem.krovetz`;
`stem.none` (identity); lemmatizer `lemma.spacy`; tokenizers `tok.code-identifier`, `tok.unicode-word`;
vocabularies `vocab.snomed-ct`, `vocab.mesh`, `vocab.umls`, `vocab.legal-terms`, `vocab.finance-terms`.

## Record schema — `assignment-policy.jsonl`

```json
{
  "id": "sp.repo.prophet-health",            // sp.repo.<repo> | sp.domain.<domain>
  "scope": "repo|domain",
  "target": "<repo name | domain name>",
  "domain": "health|legal|finance|code|security|ontology|general",
  "stemmer": "<id in stemmers.jsonl>",        // stem.* or lemma.* ; stem.none = no stemming
  "tokenizer": "<id in stemmers.jsonl>",       // prose tokenizer (tok.unicode-word default)
  "code_tokenizer": "<id in stemmers.jsonl>",  // tokenizer for source/config files (tok.code-identifier)
  "vocabulary": "<id in stemmers.jsonl | null>",// controlled vocabulary, or null
  "rationale": "<why this domain gets this policy>"
}
```

Field notes:
- **scope / target** — resolution is repo-first: use the `scope:"repo"` record for `target==<repo>`;
  otherwise fall back to the `scope:"domain"` record for the repo's `domain`. Every repo record's
  `domain` has a matching domain fallback.
- **stemmer / tokenizer / code_tokenizer / vocabulary** — every value is an `id` in `stemmers.jsonl`
  (`vocabulary` may be `null`). `code_tokenizer` is applied to source/config/workflow files;
  `tokenizer` to prose/docs.
- **domain** — inferred read-only from the repo README; a curation seed, not a final label.

### Health invariant (hard, enforced by the manifest quality gate)

For every record with `domain == "health"`:
`stemmer == "stem.snowball"` **and** `vocabulary == "vocab.snomed-ct"` **and**
`code_tokenizer == "tok.code-identifier"`. This encodes Lord Michael's rule
(`prophet-health` → Snowball + SNOMED CT + code-identifier tokenizer for code files) and holds for
the `health` domain fallback and every health repo (`prophet-health`, `human-digital-twin`).

## Code-identifier tokenizer (`tok.code-identifier`) spec

Splits programming identifiers into normalized subtokens, with **no linguistic stemming**:
1. split on non-alphanumeric separators: `_` (snake), `-` (kebab), `.`/`/`/`::` (paths), whitespace;
2. split camelCase / PascalCase boundaries: `lower|Upper` and acronym run `HTTPServer` → `HTTP` + `Server`;
3. split letter↔digit boundaries: `utf8`→`utf`,`8`; `v2`→`v`,`2`;
4. lowercase; drop empty tokens; **preserve literals otherwise** (keys, symbols, CVE ids, `sk-ant-…`).

Use it as `code_tokenizer` in every policy so source, config, workflow and log corpora keep their
token literals; never stem code tokens (`stem.none` for code/security domains).

## Resolution / query recipes (how other assets consume it)

- **Normalize a repo's text** — resolve the repo's assignment; tokenize prose with `tokenizer`,
  code with `code_tokenizer`; apply `stemmer`; map surface terms to `vocabulary` concept ids.
- **`ds.topic-vocabulary`** — MUST tokenize/stem each repo per this policy **before** fitting
  LSA/LSI/LDA, so per-repo and combined vocabularies are mergeable (see README).
- **Glossary** — a term's surface variants are its stemmed/lemmatized forms under its repo's policy;
  health/legal/finance entries carry `vocabulary` concept ids as `skos:exactMatch`.
- **Blast radius** — an assignment's `target`/`sources[]` are the edges: changing a normalizer or a
  domain default reaches every repo whose policy references it; a vocabulary change reaches every
  health/legal/finance corpus that normalizes against it.

## Hard rule (governance)

First-party assets and **open** standards (Snowball, Porter, Lancaster, Krovetz, spaCy, MeSH,
Unicode UAX-29) are referenced directly. **Licensed terminologies (SNOMED CT, UMLS) are captured as
a pointer + license note ONLY — their content is never vendored** (SNOMED CT requires a SNOMED
International Affiliate License; UMLS a UMLS Metathesaurus License). Legal/finance term lists are
first-party, assembled from public-domain / permissively-licensed sources (eCFR/GPO, EuroVoc,
FASB US-GAAP). No client materials and no competitor marketing materials. The dataset validator
(`tools/validate_dataset_manifest.py`) is fail-closed on schema + record integrity.
