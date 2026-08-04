# Estate Classification Admissibility & Trust Grading — schema

One row per estate. The row answers **"which of this estate's six classification fingerprint
layers can actually be trusted, and how much classification confidence has it earned?"**

This ships *before* any classification does. It is derivable from the catalog and the data
alone — no glossary, no calibration — which makes it the honest day-one deliverable for a
customer who has neither.

## Fields

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | `adm-<hash>` |
| `estate` | string | estate URN |
| `generated_at` | string | ISO-8601 |
| `cold_start_phase` | int 0–4 | 0 = catalog-derived bootstrap; 4 = steady state |
| `layers` | array | all **six**, always — see below |
| `admissible_count` | int 0–6 | derived |
| `degraded_count` | int 0–6 | derived; admissible but on a fallback channel |
| `n_eff` | float | effective number of *independent* layers |
| `n_eff_floor` | float | floor required for `POS` |
| `pos_available` | bool | whether positive classification is reachable at all |
| `grade` | enum `A`–`F` | **recomputed**, never carried from the source document |
| `grade_note` | string | why this estate got this grade |

### `layers[]`

| Field | Type | Notes |
| --- | --- | --- |
| `layer` | enum | `L1-ontodt-type`, `L2-ontodq-profile`, `L3-business-glossary`, `L4-operational-semantics`, `L5-table-topic`, `L6-schema-key-graph` |
| `admissible` | bool | |
| `reason` | enum or null | required when `admissible` is false; closed set, so causes aggregate across estates |
| `degraded` | bool | admissible but on a fallback channel — L4 without query logs, L6 on inferred inclusion dependencies |

**All six layers appear in every row.** An omitted layer is indistinguishable from an
admissible one, which is exactly the silent averaging this dataset exists to prevent.

## Grading

```
A  6 admissible, none degraded, n_eff >= floor        full stack, quorum earned
B  6 admissible, some degraded, n_eff >= floor        full stack on partial channels
C  4-5 admissible, n_eff >= floor                     quorum holds on a reduced stack
D  4-5 admissible, n_eff <  floor                     layers present but not independent
F  <= 3 admissible                                    below any meaningful quorum
```

`n_eff` is the participation ratio of the layer covariance spectrum, **not** a count of
contributing layers and **not** the Herfindahl index. Two perfectly correlated layers give
`H = 0.5` — apparently healthy — while supplying one layer's worth of information. Since
L3–L4 are correlated (both track glossary maturity) and L5 depends on L3 (it is a bag of L3
labels), **expect `n_eff < 6` on every real estate.**

A cold-start estate grading `F` is the correct answer, not a bug. Most estates engage
without a maintained glossary — if they had one they would not need this system — so `D`/`F`
at phase 0 is the normal starting state and the grade is what makes the gap visible.

Same principle as the country coverage grading in the Data Catalogue: the map is
deliberately not uniformly green.
