# Services & Endpoints Inventory — Schema & Blast-Radius Model

Governed, catalog-ready seed of the SocioProphet estate's SERVICE and ENDPOINT
surface. Produced by a READ-ONLY harvest of first-party source under `~/dev`
(2026-08-02). One record per distinct service surface, so agents can find every
service and trace its blast radius (who exposes it, who calls it).

## Files

| file | contents |
|---|---|
| `services.jsonl` | one JSON object per service surface (record schema below) |
| `manifest.json` | catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`) |
| `README.md` | overview + externally-exposed / no-consumer surfaces + query recipes |
| `SCHEMA.md` | this file |

## Record schema (`services.jsonl`)

```json
{
  "id": "svc-<sha1[0:10] of kind|repo|path|name>",
  "name": "<service / API / route-group name>",
  "kind": "k8s-service|ingress|deployment|http-api|grpc-service|compose-service|argocd-app|other",
  "repo": "<first-party repo dir under ~/dev>",
  "path": "<file path within repo>",
  "endpoints": [ "<route or port, best-effort>" ],
  "consumers": [ "<who calls it, best-effort>" ],
  "intent": "<one-line: what this surface is>"
}
```

### `kind` — what each value means and how `endpoints[]` is populated

| kind | source | `endpoints[]` |
|---|---|---|
| `k8s-service` | k8s `Service` | `PROTO port[->targetPort]` per `spec.ports` |
| `ingress` | k8s `Ingress` | `host/path -> backendService` per rule (**externally exposed**) |
| `deployment` | k8s `Deployment` / `StatefulSet` / `DaemonSet` / Argo `Rollout` | `container:containerPort` |
| `argocd-app` | ArgoCD `Application` (`argoproj.io`) | `ns=<destination namespace>`; `intent` carries the source repoURL |
| `compose-service` | `docker-compose.yml` service | `published:target` ports; `intent` carries image/build + depends_on |
| `grpc-service` | `service X {}` in `.proto` | `rpc <Method>` per method; `name` is `package.Service` |
| `http-api` | FastAPI/Flask decorators, Express/Fastify/Nest routes, OpenAPI/Swagger `paths` | `VERB /path` (VERB ∈ GET/POST/…/WS/MOUNT/ANY) |
| `other` | reserved | — |

Field notes:
- **id** is a stable content hash of `kind|repo|path|name`, so re-harvest is idempotent
  for unchanged surfaces; identical surfaces collapse to one record whose `endpoints[]`
  are unioned.
- **endpoints** and **consumers** are BEST-EFFORT heuristic extraction, not runtime
  discovery. Very large route tables are capped (JS 200, OpenAPI 300 entries).
- **consumers** are populated only where an edge is statically inferable:
  an `ingress` names its backend `Service` (Ingress → Service), and a compose service's
  `depends_on` names the services it calls (`compose:<caller>` → target). Absence of a
  consumer means *not statically inferable here*, not *unused*.

## Blast-radius model

This inventory is a graph of service surfaces, catalog-ready and mappable onto GBRG
(Governed Blast-Radius Graph, `~/dev/sociosphere/gbrg`), mirroring the regex dataset's
bipartite projection.

```
node (service) :  svc://<id>                 — one per surface (a services.jsonl record)
node (endpoint):  route/port on that service — an element of endpoints[]
edge (exposes) :  ingress svc://<id>  --exposes-->  k8s-service svc://<id'>   (external front door)
edge (calls)   :  consumer            --calls-->    svc://<id>                 (consumers[])
```

- Each record's `consumers[]` are inbound "calls" edges; an `ingress` record's backend
  reference is an "exposes" edge into the k8s-service it fronts.
- In GBRG terms a service is a `SemanticCell` (`kind: service`, `cell_id: svc://<id>`) and
  each consumer is an `imports`-kind edge (`from` consumer DEPENDS-ON `to` service),
  matching GBRG edge orientation in `contracts/graph-edge.schema.json`.

### How other agents query it

- **Find a service surface**: filter `services.jsonl` by `repo` / `kind` / `name`; the
  routes and ports are in `endpoints[]`.
- **Externally-exposed attack surface**: `kind == "ingress"` — every host/path reachable
  from outside the cluster, with the backend service it fronts.
- **Blast radius of a change**: given a service, its `consumers[]` are the callers that
  break if it changes; given an `ingress`, its backend is the service that goes dark if
  the route is pulled. A `k8s-service` with an ingress in front and no internal consumer
  is a pure edge service; a service with many `consumers[]` is a high-in-degree hub.
- **Orphans / dead-surface sweep**: a `k8s-service`/`http-api`/`grpc-service` with an
  empty `consumers[]` and no fronting `ingress` is a candidate orphan (caveat: consumers
  are only *statically* inferred; cross-repo HTTP/gRPC calls are not yet resolved).

## Hard rule (governance)

First-party only. Provider *integration* surface is INCLUDED (e.g. the Porter
`ClusterControlPlaneService` gRPC contract we integrate against is our own API surface,
not client material). Excluded: client materials and competitor marketing. Duplicate
local clones of the same upstream repo are collapsed by `git remote get-url origin`
before harvest so the same service is not counted N times. The dataset validator
(`tools/validate_dataset_manifest.py`) is fail-closed on schema + JSONL validity.
