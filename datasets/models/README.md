# Estate ML/AI Models Catalog (`ds.models`)

A governed, catalog-registered inventory of the ML/AI **models** the SocioProphet estate
**routes to, runs, trains, or governs**, so that other agents can answer *which model is
used where* and **trace the blast radius** of any model deprecation, re-pricing, rate-limit,
outage, or governance action.

Seeded 2026-08-02 by a read-only harvest of first-party `~/dev` repos.

## Contents
| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `models.jsonl` | **52** distinct models; one record per model; every referencing repo listed in `used_by[]` (the blast-radius edges). |
| `SCHEMA.md` | Record schema + the bipartite blast-radius model and query recipes. |
| `PROVIDER-REFERENCE-NOTE.md` | Why third-party provider model ids in our routing/config are **included** (`provider_reference: true`). |

## By provider (52)
`qwen` 11 · `google` 11 · `meta` 5 · `openai` 5 · `socioprophet` 5 · `deepseek` 3 · `anthropic` 3 · `mistral` 3 · `nomic` 1 · `llava` 1 · `cognitivecomputations` 1 · `stability` 1 · `local` 1 · `sentence-transformers` 1

## By role (52)
`routing-target` 35 · `embedding` 5 · `fine-tuned` 4 · `judge` 3 · `governed` 3 · `other` 2

Primary sources: `model-router`'s `contracts/prophet-mesh/prophet-mesh-model-routing.v0.1.json`
(hosted routing families + task routes) and `prophet-mesh/specs/*` (the hosted frontier/balanced/
fast/open-private/specialist fleet); `noetica/prophet-mesh.manifest.json` (the local **ollama**
fleet: `nomic-embed-text`, `llama3.2`, `qwen2.5[-coder]`, `deepseek-r1`, `llava`, `dolphin3`);
`sourceos-model-carry` local-model profiles; `model-governance-ledger` `model://…` releases;
`noetica-impair` (`google/gemma-2-9b-it` + `gemma-scope` SAE); `embeddinglab` functional-model surface.

## Blast-radius / dependency tracing (how agents use it)
- **Who uses model X?** → `used_by[]` on its record.
- **Highest blast radius** = longest `used_by[]`: `gpt-5.5` (route + agents + installers), `nomic-embed-text`
  (6 repos incl. hellgraph/sherlock/systems-learning-loops — the semantic-similarity spine), `claude-sonnet-4.6`,
  `deepseek-r1:8b`, `google/gemma-2-9b-it` (impair + superconscious + procyber + platform).
- **Provider exposure** → group by `provider`; a provider outage/price change blast radius = union of `used_by[]`
  across its models. Losing `qwen`/`google` (11 each) is the widest hosted-provider exposure.
- **Trained/owned surface** → `provider:socioprophet` (`noetica-7b-verified-compute`, `noetica-graph`,
  `text-classifier`, fraud LGBM, embeddinglab deterministic-embedding) or `role:fine-tuned`.

## ⚠️ Governance gap (ungoverned models in production paths)
Only **9 of 52** models carry a governance entry (`governed:true`): the ledger `model://…` releases
(`text-classifier@2.4.0`, `local/small-language@0.1.0`, fraud `lgbm-risk-signal-v0`), the fine-tuned
`google/gemma-2-9b-it` + `gemma-scope` (weights-ref + superconscious registry), `noetica-7b-verified-compute`,
`noetica-graph`, the LoRA base `llama3.2:1b` (personal-tuning contract), and the `embeddinglab` functional
surface (`ledgerRequired`).

**43 models are ungoverned, and 42 of those sit directly in routing / production paths** — the entire
hosted-frontier fleet (`gpt-5.5`, `claude-opus-4.8`, `gemini-3.1-pro`, `mistral-large-3`, …), every guard/judge
model (`llama-guard-4`, `shieldgemma-2`, `qwen3-guard`), and the whole local ollama fleet
(`qwen2.5:7b`, `deepseek-r1:8b`, `llava:13b`, `nomic-embed-text`) are **routed to with no Model Governance
Ledger promotion entry**. `prophet-mesh` routing already declares the invariant `model_availability_is_not_authorization`
and requires ledger promotion evidence — but no such entry exists for these routing targets today. That is the
enforced-vs-declared gap this dataset surfaces.

- **Query it:** `jq -c 'select(.governed==false and (.role=="routing-target" or .role=="embedding" or .role=="judge"))' models.jsonl`

## Governance
- **First-party provider refs are included** (`provider_reference: true`) as the estate's own routing policy —
  see `PROVIDER-REFERENCE-NOTE.md`. Competitor/client *marketing* materials remain excluded.
- **Validate:** `make validate` (schema + referential integrity + JSONL validity), or
  `python tools/validate_dataset_manifest.py datasets/models/manifest.json`.
- `role` and `governed` are honest-but-heuristic curation seeds from a read-only harvest, not final
  governance labels; `used_by[]` are best-effort blast-radius edges.

## Expanding it
Add records to `models.jsonl` (same schema, `id = mdl-<sha1[0:10] of provider/name>`), keep client/competitor
*marketing* out (first-party provider refs are fine — tag `provider_reference: true`), re-run `make validate`,
bump `manifest.json` `version`. Part of the [Asset Catalog Program](../../docs/ASSET-CATALOG-PROGRAM.md)
("models" asset class).
