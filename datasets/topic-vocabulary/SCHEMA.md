# Topic-Vocabulary Dataset — Schema, SKOS & Glossary Model

Governed, catalog-ready controlled vocabulary of the SocioProphet estate, produced by a
READ-ONLY topic-model pass (LSA / LSI / LDA) over first-party source under `~/dev`.
First-party only (see hard rule below).

## Files

| file | contents |
|---|---|
| `vocabulary.jsonl` | one record per `(term, repo, source, scope)` |
| `topics.jsonl` | one record per `(repo, source, topic_id)` |
| `glossary.jsonl` | one record per glossary entry (`kind: topic` or `term`) |
| `glossary/business_glossary.yml` | DataHub business-glossary v1 (native ingest) |
| `graphs/<repo>.ttl` | per-repo SKOS ConceptScheme |
| `graphs/estate-combined.ttl` | combined-additive union SKOS ConceptScheme |

## `vocabulary.jsonl`

```json
{
  "id": "tv-<sha1(scope|repo|source|term)[:12]>",
  "term": "<vocabulary term>",
  "repo": "<repo>|__union__|__estate__",
  "source": "LSA|LSI|LDA",
  "scope": "repo|combined-additive|combined-natural",
  "topic_id": <int|null>,        // null for combined-additive
  "rank": <int|null>,            // 0-based position within the topic; null for combined-additive
  "weight": <float|int>          // model weight (repo/natural); repo-count for combined-additive
}
```

- **scope=repo** — one record per `(term, repo, source)`, collapsed to the topic where the term
  had maximum |weight|.
- **scope=combined-additive** — one record per `(term, source)`, `repo="__union__"`,
  `weight` = number of repos the `(term, source)` pair appeared in.
- **scope=combined-natural** — LSA/LSI/LDA over the whole-estate pooled corpus, `repo="__estate__"`.

## `topics.jsonl`

```json
{
  "repo": "<repo>|__estate__",
  "source": "LSA|LSI|LDA",
  "topic_id": <int>,
  "scope": "repo|combined-natural",
  "top_terms": ["...", ...],     // ordered by weight, up to 15
  "coherence": <float|null>      // u_mass slot; null in this seed
}
```

## `glossary.jsonl`

```json
{
  "id": "gt-...",
  "name": "<term> | '<repo> · <source> topic <k>'",
  "kind": "topic|term",
  "definition": "<authored/contextual one-sentence definition>",
  "source": "LSA|LSI|LDA|combined-natural|combined-additive",
  "node": "urn:sp:topic-vocabulary:<scheme>",   // parent topic/scheme
  "related_terms": ["...", ...],                 // co-topic siblings (linked terms)
  "narrower_terms": ["...", ...],                // topics: member terms; terms: []
  "repos": ["...", ...]                          // provenance / blast-radius
}
```

- **Topic entries** (`kind: topic`) — `source` is the deriving model for repo topics, or
  `combined-natural` for estate topics; `narrower_terms` = member vocabulary; `definition`
  summarises the top terms.
- **Term entries** (`kind: term`) — one per distinct term; `source: combined-additive` (the
  union view); `node` = its home topic's scheme; `related_terms` = home-topic siblings;
  `repos` = every repo the term appears in.

## SKOS model (per-repo turtle)

```
skos:ConceptScheme   :  <CAT>/<repo>                         — one per repo
skos:Concept (topic) :  <CAT>/<repo>#<source>-topic-<k>      — also a skos:Collection
skos:Concept (term)  :  <CAT>/<repo>#<source>-<term>
```

Each term concept carries `skos:prefLabel`, `skos:definition`, `skos:inScheme`,
`dct:source` (LSA/LSI/LDA), `skos:broader` → its topic, and `skos:related` → co-topic
siblings. Each topic carries `skos:narrower` / `skos:member` → its terms and `skos:definition`.
`CAT = https://catalog.socioprophet.ai/topic-vocabulary/`.

### `estate-combined.ttl` (combined-additive union)

One `skos:ConceptScheme`; each distinct term is a `skos:Concept` with `skos:definition`,
`skos:related` (siblings), and the **provenance edge set**:

```
<concept> tv:fromMethod "LSA"|"LSI"|"LDA" .     # dct:source mirror
<concept> tv:fromRepo   "<repo>" .              # every repo it came from
<concept> rdfs:seeAlso  <CAT>/<repo> .          # link to that repo's scheme
```

`tv: = <CAT>ns#`. In blast-radius terms, `tv:fromRepo` fan-out from a term concept is the set
of repos that would be affected if that term/concept changes meaning or is removed.

## Query recipes

- **Reuse**: filter `vocabulary.jsonl` by `repo` + `source`; take highest-|`weight`| terms.
- **Glossary lookup**: `glossary.jsonl` by `name` → `definition`, `related_terms`, `repos`.
- **Blast radius of a term**: `glossary.jsonl` `repos[]`, or `estate-combined.ttl`
  `tv:fromRepo` / `rdfs:seeAlso` edges from the concept.
- **Cross-estate themes**: `topics.jsonl` `scope: combined-natural`.
- **DataHub**: ingest `glossary/business_glossary.yml` via the `datahub-business-glossary` source.

## Hard rule

The corpus is exclusively first-party `~/dev` source. First-party provider/model names in our
own code (`anthropic`, `openai`, `aws`, …) are **retained** as our vocabulary. **No client or
competitor marketing materials** were ingested; third-party checkouts (`AgenticaForge`,
`agent-inbox`) were excluded. `definition`, and the topic/term groupings, are curation seeds,
not final governance labels.
