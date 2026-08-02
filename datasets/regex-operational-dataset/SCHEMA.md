# REGEX Operational Dataset — Schema & Blast-Radius Model

Governed, catalog-ready seed of the SocioProphet estate's REGEX corpus. Produced by a
READ-ONLY harvest of first-party source under `~/dev`. First-party provider/security
patterns are included (see policy below).

## Files

| file | contents |
|---|---|
| `regex-corpus.jsonl` | one JSON object per DISTINCT pattern (record schema below) |
| `classifier-set.json` | named classifiers grouping pattern ids + descriptions |
| `gbrg-blast-radius.jsonl` | GBRG projection: `SemanticCell kind:pattern` + `imports` edges per usage site |
| `manifest.json` | catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`) |
| `README.md` | dataset overview + blast-radius query recipes |
| `PROVIDER-REFERENCE-NOTE.md` | why first-party provider/model & leaked-key detectors are included |
| `SCHEMA.md` | this file |

## Record schema (`regex-corpus.jsonl`)

```json
{
  "id": "rx-<sha1[0:10] of raw pattern>",
  "pattern": "<raw regex source, decoded from the host literal>",
  "flags": "<i/m/s/... union across sites; empty if none>",
  "lang": "python|js|ts|rust|jsonschema|yaml",   // dominant language among sources
  "intent": "<one-line: what it matches; seed field, may be empty pending curation>",
  "category": "secret|pii|url|identifier|version|path|validation|classifier|other",
  "sources": [ {"repo": "<repo>", "file": "<path within repo>", "line": <int>} ],
  "use_count": <int>,                    // total usage sites == len(sources) after dedup
  "risk_class": "catastrophic|sensitive|benign",
  "redos_suspect": <bool>,               // nested-quantifier / catastrophic-backtracking shape
  "competitor_clean": true,              // true; competitor/client MARKETING materials are excluded
  "provider_reference": <bool>           // true when the pattern/site references a provider we integrate (first-party, allowed)
}
```

Field notes:
- **id** is a stable content hash of the raw pattern, so the same regex in N repos collapses to ONE record whose `sources[]` lists every site. Re-harvest is idempotent for unchanged patterns.
- **flags** is the union of flags observed across sites (JS `/…/i` etc.).
- **category** and **risk_class** are keyword-heuristic SEEDS for curation, not final governance labels.
- **risk_class** rubric: `catastrophic` = secret/credential detectors, command-injection and destructive-command detectors, path-escape guards; `sensitive` = PII and path locators; `benign` = version/identifier/generic structural validators.
- **redos_suspect** = `true` when the pattern contains `(…+)+`, `(…*)*`, `(.*)*`, `(?:…+)+`, `(\S+)+`, or an alternation group under an outer quantifier — shapes prone to catastrophic backtracking.

## Hard rule (governance)

Excluded: competitor/client **marketing** materials (this scrubbed the seed deck — Palantir,
BAAP, Liminal). **Included** (first-party policy, `provider_reference: true`): our own
security/routing patterns, including leaked-key detectors (`sk-ant-…`, `sk-proj-…`,
`ANTHROPIC_API_KEY`) and model-router allow-lists — these are the estate's own policies, not
competitor materials (no clients today). See `PROVIDER-REFERENCE-NOTE.md` for the decision and
the client-onboarding escape hatch (split an `organization`/`restricted` variant then). The
validator (`tools/validate_dataset_manifest.py`) gates on schema + JSONL validity + `id`/`pattern`
presence, and is fail-closed when a data-bearing manifest ships no data file.

## Blast-radius model

This corpus is a bipartite graph, catalog-ready and directly mappable onto GBRG
(Governed Blast-Radius Graph, `~/dev/sociosphere/gbrg`).

```
node  (pattern)   :  rx://<id>              — one per distinct regex (a corpus record)
node  (usage site):  code://<repo>/<file>   — a first-party source location
edge  (uses)      :  code://<repo>/<file>  --uses-->  rx://<id>
```

- Each record's `sources[]` array **is** the edge set for that pattern node: every element is one
  `code → rx` "uses" edge. `use_count` is the pattern node's in-degree = its blast radius.
- In GBRG terms the node type is `SemanticCell` (`contracts/semantic-cell.schema.json`); there is
  no native pattern node, so patterns map as `SemanticCell`-adjacent nodes (`kind: pattern`,
  `cell_id: rx://<id>`) and each use is an `imports`-kind edge (`from` code cell DEPENDS-ON `to`
  pattern), matching GBRG edge orientation in `contracts/graph-edge.schema.json`.

### How other agents query it

- **Reuse**: filter `regex-corpus.jsonl` by `category` / `classifier-set.json` membership; take the
  highest-`use_count` member (most battle-tested).
- **Expansion**: add new sites by appending to a record's `sources[]` and incrementing `use_count`;
  add new patterns as new records (id = sha1 of raw pattern).
- **Validation**: compile each `pattern` under its `lang` engine; assert `redos_suspect:false` for
  any user-input-facing use; enforce `risk_class` policy at the gate.
- **Misuse / dependency tracing (blast radius)**: given a pattern `rx://<id>`, reverse-reachability
  over its `sources[]` yields every file/repo that would break or leak if the pattern changes or is
  removed. Given a file, forward edges yield every governed pattern it depends on. A secret-detector
  with high `use_count` and a `redos_suspect:true` sibling is a prioritised remediation target.
```
```
