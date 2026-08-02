#!/usr/bin/env python3
"""ontologies extractor (ds.ontologies).

Emits ONE repo's contribution shard: one record per FIRST-PARTY RDF/ontology graph
file in <repo_path> (OWL / RDFS / SKOS / SHACL / JSON-LD / N3 / RDF), parsed with
`rdflib`, in the SAME record schema as `datasets/ontologies/ontologies.jsonl`
(see SCHEMA.md).

    python3 extractors/extract_ontologies.py <repo_path> <repo_name> [--out FILE]

`id = onto-<sha1[:12] of repo/path>` — stable, idempotent, byte-compatible with the
central harvest. `imports[]` are the owl:imports OUT-edges (blast-radius). A file that
fails to parse honestly reports triples:0, parses:false, and its exception in
`parse_error` rather than being silently dropped.

rdflib is the ONLY non-stdlib dependency (declared in requirements.txt and installed by
the refresh workflow). Read-only, deterministic.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_hex, run  # noqa: E402

EXT_FORMAT = {
    ".ttl": "turtle", ".owl": "xml", ".rdf": "xml", ".rdfs": "xml",
    ".n3": "n3", ".nt": "nt", ".jsonld": "json-ld", ".json-ld": "json-ld",
}

# Vendored EXTERNAL ontology trees are NOT ingested as ours (see SCHEMA governance).
THIRD_PARTY_MARKERS = ("/sources/", "science-on-schema", "sweet", "gene-ontology",
                       "bcodmo", "kbpedia", "environmental-exposure", "obographs")


def _rdflib():
    try:
        import rdflib  # noqa: F401
        return rdflib
    except Exception:
        return None


def _kind(g, ext: str, text: str) -> str:
    from rdflib import RDF, RDFS, OWL
    from rdflib.namespace import SKOS
    SH = "http://www.w3.org/ns/shacl#"
    if any(str(o) in (SH + "NodeShape", SH + "PropertyShape") for o in g.objects(None, RDF.type)):
        return "shacl"
    if (None, RDF.type, SKOS.Concept) in g or (None, RDF.type, SKOS.ConceptScheme) in g:
        return "skos"
    if (None, RDF.type, OWL.Ontology) in g or (None, RDF.type, OWL.Class) in g:
        return "owl"
    if (None, RDF.type, RDFS.Class) in g:
        return "rdfs"
    return {".jsonld": "jsonld", ".n3": "n3"}.get(ext, "rdf")


def _base_iri(g):
    from rdflib import RDF, OWL
    from rdflib.namespace import SKOS
    for s in g.subjects(RDF.type, OWL.Ontology):
        return str(s)
    for s in g.subjects(RDF.type, SKOS.ConceptScheme):
        return str(s)
    ns = dict(g.namespaces())
    if "" in ns:
        return str(ns[""])
    return None


def extract(repo_path: str, repo_name: str) -> list[dict]:
    rdflib = _rdflib()
    records: list[dict] = []
    for path in iter_files(repo_path, set(EXT_FORMAT)):
        relpath = rel(repo_path, path)
        low = ("/" + relpath.lower())
        if any(mk in low for mk in THIRD_PARTY_MARKERS):
            continue  # vendored external — recorded centrally in third-party-vendored.jsonl, not here
        text = read_text(path)
        if text is None:
            continue
        ext = Path(path).suffix.lower()
        rid = "onto-" + sha1_hex(f"{repo_name}/{relpath}", 12)
        rec = {
            "id": rid, "name": Path(relpath).name, "kind": {".jsonld": "jsonld"}.get(ext, "rdf"),
            "repo": repo_name, "path": relpath, "base_iri": None,
            "triples": 0, "classes": 0, "properties": 0, "concepts": 0,
            "parses": False, "imports": [],
            "intent": _path_intent(relpath),
        }
        if rdflib is None:
            rec["parse_error"] = "rdflib not available"
            records.append(rec)
            continue
        try:
            from rdflib import Graph, RDF, RDFS, OWL
            from rdflib.namespace import SKOS
            g = Graph()
            g.parse(data=text, format=EXT_FORMAT[ext])
            rec["parses"] = True
            rec["triples"] = len(g)
            rec["kind"] = _kind(g, ext, text)
            rec["base_iri"] = _base_iri(g)
            classes = set(g.subjects(RDF.type, OWL.Class)) | set(g.subjects(RDF.type, RDFS.Class))
            props = (set(g.subjects(RDF.type, OWL.ObjectProperty))
                     | set(g.subjects(RDF.type, OWL.DatatypeProperty))
                     | set(g.subjects(RDF.type, OWL.AnnotationProperty))
                     | set(g.subjects(RDF.type, RDF.Property)))
            concepts = set(g.subjects(RDF.type, SKOS.Concept))
            rec["classes"] = len(classes)
            rec["properties"] = len(props)
            rec["concepts"] = len(concepts)
            rec["imports"] = sorted(str(o) for o in g.objects(None, OWL.imports))
            intent = _graph_intent(g)
            if intent:
                rec["intent"] = intent
        except Exception as e:  # honest parse-failure record, not a silent drop
            rec["parse_error"] = f"{type(e).__name__}: {e}"[:300]
        records.append(rec)
    return sorted(records, key=lambda r: r["id"])


def _path_intent(relpath: str) -> str:
    stem = Path(relpath).stem.replace(".shacl", "").replace("-", " ").replace("_", " ")
    parent = Path(relpath).parent.name
    return f"{stem} ({parent})" if parent and parent != "." else stem


def _graph_intent(g) -> str:
    from rdflib import RDFS, OWL
    from rdflib.namespace import DCTERMS
    for _s, _p, o in g.triples((None, RDFS.comment, None)):
        return " ".join(str(o).split())[:200]
    for _s, _p, o in g.triples((None, DCTERMS.description, None)):
        return " ".join(str(o).split())[:200]
    for onto in g.subjects(None, OWL.Ontology):
        for o in g.objects(onto, RDFS.label):
            return " ".join(str(o).split())[:200]
    return ""


if __name__ == "__main__":
    raise SystemExit(run("ontologies", extract))
