# Estate Services & Endpoints Inventory (`ds.services-endpoints`)

A governed, catalog-registered inventory of the SocioProphet estate's **services and
endpoints** — Kubernetes services/ingresses/deployments, ArgoCD apps, docker-compose
services, gRPC services, and HTTP APIs (FastAPI/Flask/Express/Fastify/Nest/OpenAPI) —
so that **other agents can find every service surface and trace its blast radius**
(who exposes it, who calls it).

Seeded 2026-08-02 by a read-only harvest of first-party `~/dev` repos.

## Contents
| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `services.jsonl` | **430** service surfaces across **27** repos; one record per surface (`id`, `name`, `kind`, `repo`, `path`, `endpoints[]`, `consumers[]`, `intent`). |
| `SCHEMA.md` | Record schema + the exposes/calls blast-radius model and query recipes. |

## Inventory (by kind)
| kind | count |
|---|---|
| `deployment` | 96 |
| `compose-service` | 93 |
| `k8s-service` | 85 |
| `http-api` | 103 |
| `argocd-app` | 30 |
| `ingress` | 13 |
| `grpc-service` | 10 |
| **total** | **430** |

## Externally-exposed services (ingress = the front doors)
The **13** `kind: ingress` records are the estate's externally-reachable surface. Each
lists `host/path -> backendService`. The stable production hosts:

- `mesh.socioprophet.ai` → `prophet-mesh-lb` (prophet-platform)
- `search-api.socioprophet.ai` → `search-gateway` (prophet-platform)
- `socbase.socioprophet.ai` → `socbase-gateway` (prophet-platform)
- `lab.socioprophet.ai` → `jupyterlab` (prophet-platform)
- `studio.socioprophet.ai`, `registry.socioprophet.ai`, `matrix.socioprophet.ai` (prophet-platform)
- `searx.socioprophet.ai` → `searxng` (BearBrowser)
- `shell.example.com` → `cloudshell-fog-gateway` (prophet-platform; placeholder host)

Hosts under `*.example.invalid` / `*.example.com` are template/placeholder ingresses
(k3s samples, cloudshell base) — surfaced but not live front doors.

**To audit the attack surface:** `jq 'select(.kind=="ingress")' services.jsonl`.

## Services with no discernible consumer
**226** of the `k8s-service` / `http-api` / `grpc-service` / `compose-service` records
have an empty `consumers[]` — no *statically inferable* caller. Only **65** records
carry an inferred consumer (Ingress→backend Service, and compose `depends_on`).

Caveat (honest): `consumers[]` is populated only from in-repo structural edges
(Ingress backends, compose `depends_on`). Cross-repo HTTP/gRPC callers are **not yet
resolved**, so "no consumer" means *not statically linked here*, not *provably unused*.
Treat the empty set as a **candidate-orphan / needs-tracing** list, not a delete list.

**To list them:** `jq 'select(.consumers|length==0) | select(.kind=="k8s-service" or .kind=="http-api" or .kind=="grpc-service")' services.jsonl`.

## Blast-radius / dependency tracing (how agents use it)
- **What does a service expose?** → `endpoints[]` on its record (routes for APIs, ports for k8s/compose).
- **Who calls a service?** → `consumers[]` (best-effort). For an ingress, its backend service is in `endpoints[]` (the exposes edge).
- **What is reachable from outside?** → `kind == "ingress"`.
- **Highest-surface APIs** = most `endpoints[]` — e.g. the Porter `ClusterControlPlaneService` gRPC contract (12 rpc), the OpenCog sidecar FastAPI servers in Noetica, and the prophet-platform mesh/eval-fabric route tables.

## Governance
- **First-party only.** Provider *integration* surface is **included** (e.g. the Porter `porter.v1.ClusterControlPlaneService` gRPC contract we integrate against is our own API surface). Client materials and competitor marketing are excluded.
- **Duplicate clones deduped** by `git remote get-url origin` before harvest (kept one canonical dir per upstream repo), so the same service is not counted N times. Dropped: `prophet-platform-{hellgraph-metrics,hellgraph-outage-fix,mesh-gate-fix,mesh-portability}`, `holmes-fix-search-wiring`, `sociosphere-kairos-draft`.
- **Skipped:** `*.wt` worktrees, `_*` dirs, `*-chronos-superset`/`*-chronos-ci` mirrors, `node_modules`/`vendor`/`dist`/`target`/`build`/`.venv`. **Excluded:** third-party AgenticaForge / agent-inbox.
- `endpoints` / `consumers` are **best-effort heuristic** extraction (static, not runtime discovery) — curation seeds, not a governance guarantee.
- **Validate:** `python tools/validate_dataset_manifest.py datasets/services-endpoints/manifest.json` (and `make validate`).

## Expanding it
Add records to `services.jsonl` (same schema, `id = svc-<sha1[0:10] of kind|repo|path|name>`),
keep client/competitor materials out, re-run the validator, bump `manifest.json` `version`.
Resolving cross-repo HTTP/gRPC callers into `consumers[]` is the next enrichment (turns
the 226 candidate-orphans into a true call graph). Part of the Asset Catalog Program
(`docs/ASSET-CATALOG-PROGRAM.md`, `services/endpoints` roadmap row).
