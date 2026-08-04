.PHONY: validate validate-wallguard-catalog-visibility validate-internal-ops-libraries estate-graph validate-estate-graph catalog-index emit-datahub verify-percolation verify-catalog-mcp-transport validate-srcos-glossary validate-no-case-collisions

validate: validate-wallguard-catalog-visibility validate-internal-ops-libraries validate-estate-graph verify-percolation verify-catalog-mcp-transport validate-srcos-glossary validate-no-case-collisions validate-classification-admissibility

# House-protocol conformance: the catalog MCP surface MUST ride the TriTRPC transport
# profile (canonical JSON + sha256 digest binding + typed media type + typed envelope +
# method naming). Verifier has teeth both ways: good frames MUST pass, tampered frames
# MUST be rejected. See docs/CATALOG-MCP.md and socioprophet-agent-standards
# docs/standards/031-mcp-house-protocol.md ("all MCP must use the house protocol").
verify-catalog-mcp-transport:
	python3 tools/verify_catalog_mcp_transport.py

# READ half — ingest datasets into a queryable index; emit DataHub metadata.
catalog-index:
	python3 tools/build_catalog_index.py

emit-datahub: catalog-index
	python3 tools/emit_datahub.py

# Fail-closed canary: the catalog must actually PERCOLATE (be answerable), not just
# validate as write-only git. Rebuilds the index and asserts every dataset is covered,
# the glossary + edges are non-empty, and canonical queries return real answers.
validate-classification-admissibility:
	python3 tools/grade_classification_admissibility.py validate

verify-percolation:
	python3 tools/verify_percolation.py

# Git is case-sensitive; macOS and Windows are not. Two tracked paths differing only by
# case can never both exist on disk, so the working tree is permanently dirty and every
# unrelated PR carries a spurious diff. Worse here: shards are named after repos, so a
# case-variant filename splits one repo into two across the estate graph.
validate-no-case-collisions:
	python3 tools/validate_no_case_collisions.py

validate-wallguard-catalog-visibility:
	python3 tools/validate_wallguard_catalog_visibility.py

validate-internal-ops-libraries:
	python3 tools/validate_internal_ops_libraries.py

# Drift-guard: the generated SourceOS governance glossary must match its seed (edit the
# generator/seed, not glossary.jsonl). The governance vocabulary is itself governed.
validate-srcos-glossary:
	python3 tools/ingest_srcos_glossary.py --check

# Population (P2) + cross-catalog dependency edges (P3): emit the estate graph.
estate-graph:
	python3 tools/emit_estate_graph.py
	python3 tools/emit_estate_edges.py
	python3 tools/emit_model_catalog.py

# Regenerate + validate: real instances SHACL-conform to the vendored ontogenesis
# estate-catalog vocabulary; the committed graph is not stale vs the datasets; and
# the live-proof reasoning queries (incl. blast radius + MIT/Apache-only) return rows.
validate-estate-graph:
	python3 tools/emit_estate_graph.py
	python3 tools/emit_estate_edges.py
	python3 tools/emit_model_catalog.py
	@git diff --exit-code -- datasets/estate-graph/estate-graph.ttl datasets/estate-graph/estate-edges.ttl datasets/estate-graph/estate-models.ttl || { echo "ERR: datasets/estate-graph/*.ttl is stale vs datasets — run 'make estate-graph' and commit"; exit 1; }
	python3 tools/validate_estate_graph.py
