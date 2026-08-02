# Ontologies & RDF Graph Inventory — Schema & Blast-Radius Model

Governed, catalog-ready inventory of the SocioProphet estate's **formal ontologies and
RDF/turtle graphs** (OWL / RDFS / SKOS / SHACL vocabularies, plus JSON-LD contexts and
`n3`/`rdf` graphs). Produced by a READ-ONLY `rdflib` harvest of first-party source under
`~/dev`. Distinct from `ds.topic-vocabulary`, which holds the *topic-model-derived* SKOS —
this dataset catalogs the **hand-authored formal vocabularies** (cross-referenced, not
duplicated).

## Files

| file | contents |
|---|---|
| `ontologies.jsonl` | one JSON object per FIRST-PARTY graph file (record schema below) |
| `third-party-vendored.jsonl` | one object per VENDORED EXTERNAL ontology source dir — recorded for provenance, **not** ingested as ours |
| `manifest.json` | catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`) |
| `README.md` | overview + parse-failure gaps + blast-radius (largest / most-imported) |
| `SCHEMA.md` | this file |

## Record schema (`ontologies.jsonl`)

```json
{
  "id": "onto-<sha1[0:12] of repo/path>",
  "name": "<file basename>",
  "kind": "owl|rdfs|skos|shacl|jsonld|rdf|n3",
  "repo": "<first-party repo dir under ~/dev>",
  "path": "<path within repo>",
  "base_iri": "<owl:Ontology / skos:ConceptScheme subject, or empty-prefix ns; null if none>",
  "triples": <int>,          // len(graph) after rdflib parse; 0 if parse failed
  "classes": <int>,          // owl:Class ∪ rdfs:Class subjects
  "properties": <int>,       // owl:{Object,Datatype,Annotation}Property ∪ rdf:Property
  "concepts": <int>,         // skos:Concept subjects
  "parses": <bool>,          // did rdflib parse it standalone?
  "imports": ["<iri>", ...], // owl:imports targets = blast-radius OUT-edges
  "intent": "<one line: rdfs:comment/dcterms:description of the ontology, else path heuristic>",
  "parse_error": "<present only when parses=false: the rdflib exception>"
}
```

Field notes:
- **id** is a stable content hash of `repo/path`, so re-harvest is idempotent for unmoved files.
- **kind** is inferred from semantic signal, not just extension: a `.jsonld` carrying
  `sh:NodeShape` is `shacl`; one carrying `skos:Concept` is `skos`; `owl:Ontology`/`owl:Class`
  ⇒ `owl`; `rdfs:Class` only ⇒ `rdfs`. `.shacl.ttl` (or any `sh:NodeShape`/`sh:PropertyShape`)
  ⇒ `shacl`.
- **triples/classes/properties/concepts** come from the parsed graph; a file that fails to
  parse reports `triples:0` and its exception in `parse_error` (honest — not silently dropped).
- **base_iri** is the declared ontology/scheme subject where present (often `null` for SHACL
  shape files and JSON-LD contexts).

## Governance / scope (hard rule)

- **First-party only.** Canonical estate repos under `~/dev`. Worktree / superset clones
  (`*.wt`, `*-chronos-superset`, `*-kairos-draft`, `*-mesh-*`), build mirrors (`dist/`,
  `build/`), and language envs (`.venv`, `node_modules`, `site-packages`) are skipped so the
  same graph is not counted twice. `AgenticaForge` / `agent-inbox` (estate-boundary, third
  party) are excluded.
- **Vendored EXTERNAL ontologies are flagged, not ingested.** SWEET, science-on-schema.org,
  environmental-exposure-ontology, gene-ontology obographs, BCO-DMO, and KBpedia **KKO** are
  recorded in `third-party-vendored.jsonl` at source-dir granularity (upstream + file count)
  — their triples are **not** attributed to the estate.
- **Derived SKOS lives elsewhere.** `prophet-core-catalog`'s own topic-model turtle is the
  `ds.topic-vocabulary` product and is cross-referenced (`upstream_datasets`), not re-ingested.
- No client / competitor marketing materials.

## Blast-radius model

Ontologies form an import graph, catalog-ready and directly mappable onto GBRG
(Governed Blast-Radius Graph):

```
node (graph)   :  onto://<id>  — one per graph file (a corpus record; base_iri is its logical IRI)
edge (imports) :  onto://<A>  --owl:imports-->  <IRI of B>
```

- Each record's `imports[]` **is** the OUT-edge set for that graph node.
- Reverse-reachability over `imports[]` (group by target IRI) yields the **in-degree** =
  blast radius: every graph that would break if the imported ontology changes. The estate's
  `Upper/upper-core.ttl` is imported **64×** — the highest-blast-radius graph in the estate
  (change it and 64 graphs are affected). See README for the ranked list.
- In GBRG terms a graph maps as a `SemanticCell` (`kind: ontology`, `cell_id: onto://<id>`)
  and each `owl:imports` is an `imports`-kind edge (`from` importer DEPENDS-ON `to` imported
  ontology), matching GBRG edge orientation.

### How other agents query it

- **Reuse / find a vocabulary**: filter `ontologies.jsonl` by `kind` (`owl` for classes,
  `shacl` for validation shapes, `skos` for concept schemes) and `repo`; read `base_iri` to
  import it, `intent` for what it covers.
- **Trace dependents (blast radius)**: given an ontology IRI, collect every record whose
  `imports[]` contains it → those are the graphs that break on change.
- **Fix the gaps**: filter `parses:false` → the graphs that do not load under `rdflib`
  (dead remote `@context`, invalid Turtle) — the remediation queue.
