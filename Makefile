.PHONY: validate validate-wallguard-catalog-visibility validate-internal-ops-libraries estate-graph validate-estate-graph

validate: validate-wallguard-catalog-visibility validate-internal-ops-libraries validate-estate-graph

validate-wallguard-catalog-visibility:
	python3 tools/validate_wallguard_catalog_visibility.py

validate-internal-ops-libraries:
	python3 tools/validate_internal_ops_libraries.py

# Population (P2) + cross-catalog dependency edges (P3): emit the estate graph.
estate-graph:
	python3 tools/emit_estate_graph.py
	python3 tools/emit_estate_edges.py

# Regenerate + validate: real instances SHACL-conform to the vendored ontogenesis
# estate-catalog vocabulary; the committed graph is not stale vs the datasets; and
# the live-proof reasoning queries (incl. blast radius) return rows.
validate-estate-graph:
	python3 tools/emit_estate_graph.py
	python3 tools/emit_estate_edges.py
	@git diff --exit-code -- datasets/estate-graph/estate-graph.ttl datasets/estate-graph/estate-edges.ttl || { echo "ERR: datasets/estate-graph/*.ttl is stale vs datasets — run 'make estate-graph' and commit"; exit 1; }
	python3 tools/validate_estate_graph.py
