# Feedback Loops & Asset Lifecycles (`ds.feedback-loops`)

The estate's own **feedback loops** and **asset lifecycles**, captured as queryable catalog
records — **dogfooding**: we run our own governance primitives (provenance, blast-radius,
epistemicLevel, fail-closed gates, supersession-not-retraction) on our own process and metadata,
not just on customer workloads.

## Contents
| file | contents |
|---|---|
| `feedback-loops.jsonl` | one record per loop: `{id, name, kind, trigger, steps[], feedback_signal, closes_when, recorded_in[], dogfood, status, related_datasets[]}` |
| `lifecycles.jsonl` | one record per asset class: `{id, asset_class, states[], transition_guard, recorded_in[], dogfood}` |
| `manifest.json` | catalog manifest (validates `schemas/catalog.dataset.v0.1.json`) |
| `SCHEMA.md` | record schema |

Narrative: [`docs/FEEDBACK-LOOPS-AND-LIFECYCLES.md`](../../docs/FEEDBACK-LOOPS-AND-LIFECYCLES.md).

## The loops (8)
`catalog-contribution` · `pre-merge-gate` · `gap→remediation` · `conformance` · `vocabulary→glossary` · `blast-radius` · `vendor-freshness` · `assumption-reconciliation`.

Every loop names its **feedback signal** (what closes it) and **`recorded_in`** (the PRs/issues/files
that are the evidence it ran) — so a loop that never fires is detectable, per the estate rule
*"control that cannot fail = suspect."*

## Asset lifecycles (5)
schema/contract · ADR · vendored-artifact · pattern/policy/vocabulary · classification/verdict — each with
its states, its **transition guard**, and where it's recorded.

## Why it's here
A feedback loop that isn't recorded can't be audited, and an asset whose lifecycle isn't declared
drifts silently. Capturing them as catalog records makes each loop and lifecycle **traceable and
falsifiable** — the same standard the platform sells. `status` values (`live`, `partial`,
`live-pending-token`) are honest about which loops are fully closed.
