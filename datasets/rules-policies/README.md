# Estate Rules & Policies Inventory (`ds.rules-policies`)

A governed, catalog-registered inventory of the **rules and policies the SocioProphet estate
develops and defines** — policy-as-code, SHACL shapes, gates, guardrails, declared invariants,
and access controls — so that other agents can reuse them, trace their blast radius, and see
**which ones are actually enforced versus only declared.**

Seeded 2026-08-02 by a READ-ONLY harvest of **125 canonical first-party `~/dev` repos**
(derived checkouts, vendored/build trees, examples/tests, and third-party/pure-math repos excluded).

## Headline finding — declared vs enforced

**423 policies total. 185 enforced. 238 declared but NOT enforced.**

`enforced:false` is the **gap set**: policies the estate *declares* but for which nothing in CI, a
gate, or admission wiring demonstrably makes them fire. This is the same "has the contracts,
missing the gates" pattern tracked under the `sourceos-gate-gap` theme.

| kind | total | enforced | **declared-not-enforced** |
|---|---:|---:|---:|
| policy-as-code | 134 | 90 | **44** |
| gate | 116 | 47 | **69** |
| shacl | 55 | 8 | **47** |
| invariant | 70 | 0 | **70** |
| access | 34 | 29 | **5** |
| guardrail | 14 | 11 | **3** |
| **all** | **423** | **185** | **238** |

### Gap highlights (the list to close)

- **Policy-as-code that no CI/gate references** (declared only) — e.g.
  `human-digital-twin/.../opa/omega.rego` and `repair.rego`,
  `ontogenesis/.../rego/task_flow_policy_v0_4.rego`,
  `sociosphere/standards/qes/policies/provenance/required-provenance.rego`,
  `sourceos-spec/policies/skills/default-policy-pack.rego`,
  the `sourceos-continuum` cloudshell-hardened-pack Kyverno set
  (`disallow-latest`, `pod-security-baseline`), and
  `tritfabric/deploy/argo/gatekeeper/.../disallow_privileged.yaml`.
  These are real admission/authorization policies with **no wiring authority pointing at them**.
- **Every declared invariant is `enforced:false`** (70/70) — `INV-*` ids plus the named estate
  invariants **no-invisible-authority**, **lawful-learning**, **epistemic-level default
  (empty-evidence -> Speculative)**, and **fail-closed-gate**. They are asserted in prose/spec;
  whether a gate makes them bite is exactly the open question. (Contrast: SHACL/Kyverno enforcement
  *is* detected when a `pyshacl`/`kustomization` step names the shape/policy.)
- **SHACL shapes mostly unenforced** (47/55) — shape files exist, but only 8 are referenced by a
  validator step in CI.

## Contents
| File | What |
|---|---|
| `policies.jsonl` | **423** distinct policy/rule definitions; one record each; every reference site listed in `sources[]` (blast-radius edges). |
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `SCHEMA.md` | Record schema + the bipartite blast-radius model and query recipes. |

## Blast-radius / dependency tracing (how agents use it)
- **Who depends on policy X?** -> `sources[]` on its record (index 0 is the definition; the rest are references).
- **Highest-blast-radius policies** = highest `ref_count` (top today: SHACL `knowledge-context` 118,
  `adversarial-scenario` 87, `neurosymbolic-repo-graph` 91-class shapes; `guardrail_fabric` 75).
- **Gap sweep** -> filter `enforced:false`. A high-`ref_count` policy that is `enforced:false` is a
  prioritised remediation target: widely depended upon, but unproven at the gate.

## Governance
- **First-party policies are the point** and are included at full fidelity. No client/competitor
  marketing materials; vendored/build trees and pure-math repos are excluded (see `SCHEMA.md` hard rule).
- **`enforced` is evidence-based and fail-closed**: `true` only when a strict wiring authority
  (GitHub Actions, Makefile/justfile/Taskfile, pre-commit, kustomization/ArgoCD) references the policy.
  Validators/tests that merely exist do not count. Prose invariants default to declared.
- **Validate:** `python tools/validate_dataset_manifest.py datasets/rules-policies/manifest.json`
- `kind`, `engine`, and `enforced` are honest-but-heuristic curation seeds, not final governance labels.

## Expanding it
Add records to `policies.jsonl` (same schema, `id = pol-<sha1[0:10] of kind|name|repo/path>`), keep
client/competitor materials out, re-run the validator, and bump `manifest.json` `version`. When you
wire a declared policy into a gate, flip its `enforced` to `true` and add the wiring site to `sources[]`.

Part of the estate **asset-catalog program** (`prophet-core-catalog`), alongside
`ds.regex-operational-dataset`.
