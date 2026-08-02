# estate-graph (P2 population + P3 dependency edges)

The estate graph turns the catalog's inventory into a typed RDF **dependency graph** so
agents reason over one graph instead of reading every repo. It is the population (ABox)
side of the Estate Catalog Ontology (ontogenesis #130 / #131): resources become
`cat:CatalogEntry`/`cat:EstateResource` typed by the ontogenesis **estate-catalog**
binding vocabulary — grounded in KBpedia/KKO, the same upper language HellGraph uses.

## Files
- `estate-graph.ttl` — generated (P2). One `cat:CatalogEntry` + `cat:EstateResource` per
  source (`catalogId`, `owner` org, `status`, `dct:title`, `dct:license`, `dct:subject`,
  `cat:provenanceRef`).
- `estate-edges.ttl` — generated (P3). Cross-catalog `cat:dependsOn` edges from the
  inventory datasets — `models.used_by`, `services.consumers`, `ontologies.imports` —
  keyed on the same `res:<slug>` scheme so a model used_by `noetica` JOINS `res:noetica`
  from `src.noetica`: one graph.
- `../../tools/emit_estate_graph.py` — P2 emitter (stdlib), reads `sources/src.*.json`.
- `../../tools/emit_estate_edges.py` — P3 edge emitter (stdlib), reads the inventory datasets.
- `../../tools/validate_estate_graph.py` — parse → SHACL-conform (vendored vocabulary) →
  run the live-proof reasoning queries, including **blast radius** (transitive
  `cat:dependsOn+`).

## Run
```
make estate-graph          # regenerate estate-graph.ttl + estate-edges.ttl
make validate-estate-graph # regenerate + freshness-check + SHACL-validate + reasoning queries
```

## Why this is the "live" proof
Real instances are validated against the *real* binding vocabulary's SHACL (not fixtures),
and real questions are answered over the graph — including **blast radius** ("if this
breaks, what breaks", via transitive `cat:dependsOn+`). Already surfaces real findings,
e.g. `upper-core.ttl` as the highest-blast-radius artifact in the estate. That is "reason
over the estate, don't read it," on real data.

## Follow-ups (#130)
- Type model refs as `cat:Model` once a `modelDigest` is available (join to the model
  store / model-plane); today model refs carry no digest, so they are `cat:EstateResource`
  with `dct:subject "model"`.
- Richer typed edges (`consumesData`/`runsOn`/`usesModel`) once target types carry their
  required fields — currently expressed as generic `cat:dependsOn` to stay SHACL-safe under
  rdfs range-coercion.
- Re-sync `vendor/ontogenesis/` when the estate-catalog vocabulary changes.
