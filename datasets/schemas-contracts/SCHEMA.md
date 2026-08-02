# Schemas & Contracts Catalog — Schema & Blast-Radius Model

Governed, catalog-ready inventory of the SocioProphet estate's **schemas and contracts**. Produced by a
READ-ONLY, file-type harvest of first-party source under `~/dev`. First-party only; duplicate working
copies and third-party trees are excluded (see README governance).

## Files

| file | contents |
|---|---|
| `contracts.jsonl` | one JSON object per contract file (record schema below) |
| `manifest.json` | catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`) |
| `README.md` | overview + blast-radius query recipes + unversioned/most-referenced surfaces |
| `SCHEMA.md` | this file |

## What counts as a contract (harvest scope)

| kind | matched by | `schema_id` source | `version` source |
|---|---|---|---|
| `json-schema` | `*.schema.json`, and `*.json` carrying `$schema` (JSON-Schema draft) or `$id` + a schema keyword | `$id` | `version`/`$version` field, else a `vN[.N[.N]]` token in `$id`/filename |
| `protobuf` | `*.proto` | `package` | `vN` token in package/filename |
| `avro` | `*.avsc` | `namespace.name` | — |
| `openapi` | `openapi*.{yaml,yml,json}`, `asyncapi*.{…}` | `info.title` | `info.version` |
| `shacl` | `*.shacl.ttl` | — | — |
| `other` | Zod/TypeBox/Pydantic contract modules under a `contracts/` dir or `*.contract.*`, that clearly DEFINE a contract | — | `vN` token in filename |

Extraction is honest-but-heuristic. `kind`, `intent`, and `version` are curation **seeds**, not final
governance labels.

## Record schema (`contracts.jsonl`)

```json
{
  "id": "ct-<sha1[0:12] of repo\\0path>",       // stable id; re-harvest is idempotent for unmoved files
  "name": "<basename of the contract file>",
  "kind": "json-schema|protobuf|shacl|openapi|avro|other",
  "repo": "<first-party ~/dev repo dir>",
  "path": "<path within repo>",
  "schema_id": "<$id / proto package / avro namespace.name / openapi title; empty if none>",
  "version": "<declared version; empty string when NONE is declared — a governance signal>",
  "consumers": [ "<repo>/<path>", ... ],         // files that $ref/import this contract (capped at 40)
  "consumer_count": <int>,                        // true in-degree (may exceed len(consumers))
  "intent": "<one-line: title/description/service/message; seed, may be empty>"
}
```

Field notes:
- **id** is a content-stable hash of `repo` + `path`, so re-harvest is idempotent for files that do not move.
- **version = `""`** means the contract declares NO version anywhere the harvester can see it — surfaced in
  the README as the primary remediation surface (silent-drift risk).
- **consumers** is **best-effort**: resolved by matching a contract's basename (and `$id`) against `$ref`
  values and `import` statements across the same first-party repo set. It is a **floor** on true blast
  radius (references by renamed alias or non-file `$id` may be missed). `consumer_count` is the full count;
  the stored `consumers[]` list is capped at 40 to keep the file sane.

## Blast-radius model

This inventory is a bipartite graph, catalog-ready and mappable onto GBRG
(Governed Blast-Radius Graph, `~/dev/sociosphere/gbrg`), exactly like `ds.regex-operational-dataset`.

```
node  (contract)  :  ct://<id>              — one per contract file (a corpus record)
node  (consumer)  :  code://<repo>/<file>   — a first-party file that $refs / imports it
edge  (uses)      :  code://<repo>/<file>  --uses-->  ct://<id>
```

- Each record's `consumers[]` **is** the edge set for that contract node; `consumer_count` is its in-degree
  = its blast radius.
- In GBRG terms the node type is `SemanticCell` (`kind: contract`, `cell_id: ct://<id>`) and each use is an
  `imports`-kind edge (`from` consumer DEPENDS-ON `to` contract), matching GBRG edge orientation.

### How other agents query it

- **Find / reuse**: filter `contracts.jsonl` by `kind` and `schema_id`; prefer the highest-`consumer_count`
  variant (most battle-tested). `jq 'select(.kind=="protobuf")' contracts.jsonl`.
- **Validate**: compile/validate each artifact under its engine — JSON Schema (draft in `$schema`),
  `protoc` for proto, Avro reader, an `openapi`/`asyncapi` linter, a SHACL engine for `*.shacl.ttl`.
- **Trace blast radius (misuse / dependency)**: given a contract `ct://<id>`, reverse-reachability over its
  `consumers[]` yields every file/repo that would break if the contract changes or is removed. Given a file,
  forward edges yield every governed contract it depends on.
- **Governance sweep**: `jq 'select(.version=="")' contracts.jsonl` = every contract with no declared
  version (unpinnable dependency); a high-`consumer_count` contract that is also unversioned is a prioritised
  remediation target.

## Hard rule (governance)

First-party assets are the point — our own schemas, event contracts, RPC surfaces, and policy envelopes are
**included**. **Excluded**: client materials, competitor marketing materials, duplicate working copies
(`*-chronos-superset`, `*-kairos-draft`, `prophet-platform` branch clones), and third-party trees
(`AgenticaForge`, `agent-inbox`). The validator (`tools/validate_dataset_manifest.py`) gates on schema +
JSONL validity and is fail-closed when a data-bearing manifest ships no data file;
`tools/validate_internal_ops_libraries.py` enforces that every `src.<repo>` in `sources` resolves.
