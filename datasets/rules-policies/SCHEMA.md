# Rules & Policies Inventory — Schema & Blast-Radius Model

Governed, catalog-ready inventory of the rules and policies the SocioProphet estate
**develops and defines**. Produced by a READ-ONLY harvest of first-party source under
`~/dev`. Competitor/client-clean (see hard rule below).

## Files

| file | contents |
|---|---|
| `policies.jsonl` | one JSON object per DISTINCT policy/rule definition (record schema below) |
| `manifest.json` | catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`) |
| `SCHEMA.md` | this file |
| `README.md` | overview + the **declared-but-NOT-enforced** gap set |

## Record schema (`policies.jsonl`)

```json
{
  "id": "pol-<sha1[0:10] of kind|name|repo/path>",
  "name": "<policy/rule name: rego package, kyverno metadata.name, shape stem, INV-id, invariant slug, file stem>",
  "kind": "policy-as-code | shacl | gate | guardrail | invariant | access",
  "engine": "rego | kyverno | gatekeeper | admission | shacl | json-schema | rbac | wallguard | gitleaks | custom",
  "repo": "<first-party repo the policy is DEFINED in>",
  "path": "<path within repo>",
  "line": <int>,
  "intent": "<one line: what the policy asserts/enforces>",
  "enforced": <bool>,           // wired into CI / a gate / admission — see rubric
  "ref_count": <int>,           // total external reference sites (blast radius in-degree)
  "sources": [ {"repo": "<repo>", "file": "<path>", "line": <int>} ]  // definition site first, then references
}
```

### Field notes

- **id** is a stable content hash, so re-harvest is idempotent for unchanged definitions.
- **kind** taxonomy:
  - `policy-as-code` — OPA/rego, Kyverno `ClusterPolicy`, Gatekeeper `ConstraintTemplate`,
    Kubernetes `ValidatingAdmissionPolicy`/`NetworkPolicy`, and named `*.policy.*` definitions.
  - `shacl` — a `*.ttl` / `*.shacl.ttl` file declaring `sh:NodeShape`s (one record per file;
    `intent` reports shape count + target classes).
  - `gate` — CI/governance gate configs and gate schemas (`*-gate*`, conformance configs,
    `.gitleaks*` secret-scan rulesets).
  - `guardrail` — guardrail-fabric policy modules and `*guardrail*` packs/configs.
  - `invariant` — declared invariants: `INV-*` ids, plus named estate invariants
    (no-invisible-authority, lawful-learning, epistemic-level default, fail-closed).
  - `access` — WallGuard visibility/access controls and Kubernetes RBAC (`Role`/`ClusterRole`/bindings).
- **enforced** rubric (fail-closed on evidence): `true` only when a **strict wiring authority**
  references the policy by identifier, basename, or path — a GitHub Actions workflow,
  `Makefile`/`justfile`/`Taskfile`, `.pre-commit-config.yaml`, or a `kustomization.yaml`/ArgoCD
  application. A validator script or test merely *existing* is **not** enforcement. Prose/named
  invariants are recorded as **declared** (`enforced:false`); their enforcement, if any, lives in
  the gate/policy-as-code record that actually checks them. `enforced:false` is the **gap set**.
- **ref_count / sources** — blast radius. `sources[0]` is the definition site; the rest are every
  first-party site that references the policy's identifier (word-bounded global ripgrep). Non-distinctive
  identifiers (>150 sites — generic words) collapse to the definition site only, so `ref_count` stays honest.

## Blast-radius model

This inventory is a bipartite graph, catalog-ready and directly mappable onto GBRG
(Governed Blast-Radius Graph, `~/dev/sociosphere/gbrg`).

```
node (policy)     : pol://<id>            — one per distinct policy/rule (a record)
node (usage site) : code://<repo>/<file>  — a first-party reference location
edge (depends-on) : code://<repo>/<file>  --references-->  pol://<id>
```

- Each record's `sources[]` (past index 0) **is** the edge set for that policy node.
  `ref_count` is the policy node's in-degree = its blast radius.
- A policy with high `ref_count` and `enforced:false` is a prioritised remediation target:
  widely depended upon, but nothing in CI proves it actually fires.

### How other agents query it

- **Reuse**: filter by `kind`/`engine`; take the highest-`ref_count` member (most depended-upon).
- **Gap sweep (the point)**: filter `enforced:false` — that is every policy the estate *declares*
  but does not demonstrably *gate* (ties to the `sourceos-gate-gap` theme: "has the contracts,
  missing the gates").
- **Dependency tracing**: given `pol://<id>`, reverse-reachability over `sources[]` yields every
  file/repo that would break or drift if the policy changes or is removed.

## Competitor / client hard rule

First-party policies are the point and are included at full fidelity (rego, kyverno, SHACL,
gitleaks rulesets, WallGuard/RBAC, invariants). No client or competitor marketing materials are
harvested. Vendored/build trees (`node_modules`, `dist`, `target`, `vendor`, git-pinned `@<sha>`
external ontologies such as `science-on-schema.org`) and pure-math/theorem repos are excluded.
