# Estate Classification Admissibility & Trust Grading

**Which of an estate's six classification fingerprint layers can actually be trusted — and
how much classification confidence it has therefore earned.**

One row per estate, graded A–F, with the grade **recomputed** from the estate's own
measurements rather than carried from the source document.

## Why this is a dataset and not a footnote

The six-layer classifier (`SP-FPRINT-STACK-001`, contracted in `sourceos-spec`) assigns a
business data class to a column from six independent metadata layers. Those layers **fail
independently**, and on any given estate several of them are simply unusable:

| Layer | Fails when |
| --- | --- |
| L1 OntoDT type | everything declared `VARCHAR` |
| L2 OntoDQ profile | table empty or newly seeded (**anti**-correlated with L1) |
| L3 Business glossary | glossary stale or absent |
| L4 Operational semantics | no query-log access |
| L5 Table topic | junk-drawer staging table, or an active drift flag |
| L6 Schema / key graph | constraints never declared in DDL |

The alternative to reporting this is **silently averaging over unreliable layers**, which
produces a confident number with nothing behind it. So per-layer admissibility is a primary
output of the classifier, alongside the classification — and it ships *first*, because it
needs no glossary and no calibration.

## The grade is meant to be low at first

```
A  6 admissible, none degraded, n_eff >= floor
B  6 admissible, some degraded, n_eff >= floor
C  4-5 admissible, n_eff >= floor
D  4-5 admissible, n_eff <  floor
F  <= 3 admissible
```

A cold-start estate grading **D** or **F** is the correct answer. L3 and L4 are exactly what
a customer lacks when they engage — a customer with a maintained glossary would not need
this system — so their absence is the normal starting state, and the grade is what makes
that visible instead of papering over it.

The seed row (Berger Foods, cold-start phase 0) grades **D**: four layers admissible, two of
them degraded, `n_eff` 3.6 against a floor of 4.0. The layers that are present are not
independent enough to license a positive classification, so the honest outputs on that
estate today are `ZERO` and `NEG` only.

Same principle as the country coverage grading in the Data Catalogue: the map is
deliberately not uniformly green.

## `n_eff`, not layer count, and not Herfindahl

`n_eff` is the participation ratio of the layer covariance spectrum — the **effective number
of independent layers**. The Herfindahl index measures concentration of *magnitude* instead:
two perfectly correlated layers contributing equally give `H = 0.5`, which looks healthy
while supplying one layer's worth of information. H catches "one layer dominates"; it does
not catch "my layers are secretly the same layer", which is the failure that matters here.

L3–L4 are correlated (both track glossary maturity) and L5 depends on L3 (it is a bag of L3
labels), so **`n_eff < 6` on every real estate**.

## Refresh

```bash
python3 tools/grade_classification_admissibility.py emit --spec-dir ~/dev/sourceos-spec
```

```bash
python3 tools/grade_classification_admissibility.py validate
```

`validate` runs in CI. It recomputes every committed grade from that row's own layer states
and `n_eff`, fails on drift, and separately exercises the grading function across all five
bands — a grading function only ever run on one estate is a constant with extra steps.

Upstream contract: `sourceos-spec` `schemas/EstateAdmissibilityReport.json`,
`specs/fingerprint-stack.md`.
