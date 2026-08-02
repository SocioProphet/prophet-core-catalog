# Models Catalog — Schema & Blast-Radius Model

Governed, catalog-ready inventory of the ML/AI **models** the SocioProphet estate
routes to, runs, trains, or governs. Produced by a READ-ONLY harvest of first-party
source under `~/dev` (2026-08-02). First-party provider model references are included
(see `PROVIDER-REFERENCE-NOTE.md`).

## Files

| file | contents |
|---|---|
| `models.jsonl` | one JSON object per distinct model (record schema below) |
| `manifest.json` | catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`) |
| `README.md` | dataset overview, provider/role rollups, governance-gap surfacing, query recipes |
| `PROVIDER-REFERENCE-NOTE.md` | why third-party provider model ids in our routing/config are included |
| `SCHEMA.md` | this file |

## Record schema (`models.jsonl`)

```json
{
  "id": "mdl-<sha1[0:10] of provider/name>",
  "name": "<model id / name as it appears in our config (e.g. qwen2.5:7b, claude-opus-4.8, google/gemma-2-9b-it)>",
  "provider": "openai|anthropic|google|mistral|meta|qwen|deepseek|nomic|stability|sentence-transformers|socioprophet|local|...",
  "role": "routing-target|embedding|fine-tuned|judge|governed|other",
  "repo": "<first-party repo where the model is declared/harvested>",
  "path": "<path within repo of the declaring config/code>",
  "used_by": ["<repo/service referencing it>"],   // blast-radius edges
  "governed": true,                                 // has a model-governance-ledger / weights_manifest / functional-service governance entry
  "provider_reference": true,                       // model id belongs to a third-party provider we integrate (first-party ref, included)
  "intent": "<one-line: what it is / what it is used for>"
}
```

Field notes:
- **id** is a stable content hash of `provider/name`, so the same model referenced across N repos collapses to ONE record whose `used_by[]` lists every referencing repo/service.
- **role** rubric:
  - `routing-target` — a model the router/mesh dispatches work to (hosted or local ollama fleet).
  - `embedding` — a text/vector embedding model.
  - `fine-tuned` — a model the estate trains, adapts (LoRA), or studies as a base (e.g. `google/gemma-2-9b-it` in noetica-impair, `noetica-7b`).
  - `judge` — a safety-classifier / guard / eval model (Llama Guard, ShieldGemma, qwen3-guard).
  - `governed` — a `model://…` release whose lifecycle is tracked in the Model Governance Ledger.
  - `other` — reranker, SAE/interpretability artifact, or otherwise non-inference asset.
- **provider** `socioprophet` = a first-party trained/owned model; `local` = an unbranded local release; otherwise the upstream provider.
- **governed** is `true` only when a governance entry exists (Model Governance Ledger `model://` release, `weights://` manifest ref, or an `embeddinglab` functional-service with `ledgerRequired`). Absence is the governance signal the README surfaces.
- **provider_reference** is `true` for third-party provider model ids appearing in our own routing/config — these are FIRST-PARTY provider references, included at full fidelity (see `PROVIDER-REFERENCE-NOTE.md`).

## Hard rule (governance)

Included: first-party models the estate owns/trains, **and** third-party provider model
ids that appear in our own routing tables / configs (`provider_reference: true`) — same
policy as `ds.regex-operational-dataset`. Excluded: competitor/client **marketing**
materials. The validator (`tools/validate_dataset_manifest.py` + `tools/validate_internal_ops_libraries.py`)
gates on schema + JSONL validity + source referential integrity, and is fail-closed when
a data-bearing manifest ships no data file.

## Blast-radius model

This inventory is a bipartite graph, catalog-ready and mappable onto GBRG
(Governed Blast-Radius Graph, `~/dev/sociosphere/gbrg`).

```
node  (model)      :  mdl://<id>             — one per distinct model (a corpus record)
node  (consumer)   :  code://<repo>          — a first-party repo/service that references it
edge  (uses)       :  code://<repo>  --uses-->  mdl://<id>
```

- Each record's `used_by[]` array **is** the edge set for that model node: every element is one
  `code → mdl` "uses" edge. Its length is the model node's in-degree = its blast radius.
- Given a model `mdl://<id>`, reverse-reachability over `used_by[]` yields every repo/service that
  would break or need re-routing if the model is deprecated, re-priced, rate-limited, or pulled.
- Given a repo, forward edges yield every model it depends on (its provider exposure surface).

### How other agents query it

- **Which model is used where?** → `used_by[]` on the model's record.
- **Highest-blast-radius models** = longest `used_by[]` (today: `gpt-5.5`, `nomic-embed-text`,
  `claude-sonnet-4.6`, `deepseek-r1:8b`).
- **Governance gap** → filter `governed:false` AND `role in {routing-target,embedding,judge}` — models
  in production routing paths with no Model Governance Ledger entry.
- **Provider exposure** → group by `provider`; a provider outage/price change blast radius = union of
  `used_by[]` across its models.
- **Trained/owned surface** → filter `provider:socioprophet` or `role:fine-tuned`.
