# estate-graph (P2 population)

The estate graph turns the catalog's **source manifests into a typed RDF graph** so
agents reason over one graph instead of reading every repo. It is the population (ABox)
side of the Estate Catalog Ontology (ontogenesis #130 / #131): each `sources/src.*.json`
becomes a `cat:CatalogEntry` describing a `cat:EstateResource`, typed by the ontogenesis
**estate-catalog** binding vocabulary — which is grounded in KBpedia/KKO, the same upper
language HellGraph uses.

## Files
- `estate-graph.ttl` — generated. One `cat:CatalogEntry` + `cat:EstateResource` per source
  (`catalogId`, `owner` org, `status`, `dct:title`, `dct:license`, `dct:subject` = domain,
  `cat:provenanceRef`).
- `../../tools/emit_estate_graph.py` — emitter (stdlib only), reads `sources/src.*.json`.
- `../../tools/validate_estate_graph.py` — parse → SHACL-conform (against the vendored
  ontogenesis vocabulary in `vendor/ontogenesis/`) → run the live-proof SPARQL query.

## Run
```
make estate-graph          # regenerate estate-graph.ttl
make validate-estate-graph # regenerate + SHACL-validate + live-proof query
```

## Why this is the "live" proof
The population is validated against the *real* binding vocabulary's SHACL (not fixtures),
and answered with a real SPARQL query — e.g. "active catalog entries by owner org" — over
real estate sources. That is "reason over the estate, don't read it," on real data.

## Follow-ups (#130)
- Enrich instances with cross-catalog edges (`dependsOn`/`runsOn`/`consumesData`/`usesModel`)
  from the connectivity datasets (`ds.agents-manifests`, `ds.ontologies` import edges) so
  blast-radius traversals become live.
- Type model sources as `cat:Model` once a `modelDigest` is available (join to the model store).
- Re-sync `vendor/ontogenesis/` when the estate-catalog vocabulary changes.
