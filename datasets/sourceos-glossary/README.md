# SourceOS Governance Vocabulary

First-class catalog glossary entries (`kind: "governance"`) for the estate's governance vocabulary,
generated from the `sourceos-spec` GlossaryTerm contract via the governed draft→approved alignment
promotion. Only **approved** terms are ingested (drafts don't regulate state). `build_catalog_index`
aggregates `glossary.jsonl` into `catalog-index/glossary.jsonl` and emits `related`/`narrower` edges.

Regenerate: `python3 tools/ingest_srcos_glossary.py` · drift-guard: `--check`. Edit the generator or
`seed/`, never `glossary.jsonl`.
