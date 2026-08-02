.PHONY: validate validate-wallguard-catalog-visibility validate-internal-ops-libraries estate-graph validate-estate-graph

validate: validate-wallguard-catalog-visibility validate-internal-ops-libraries validate-estate-graph

validate-wallguard-catalog-visibility:
	python3 tools/validate_wallguard_catalog_visibility.py

validate-internal-ops-libraries:
	python3 tools/validate_internal_ops_libraries.py

# P2 population: emit the estate graph from the source manifests.
estate-graph:
	python3 tools/emit_estate_graph.py

# Regenerate + validate: real instances SHACL-conform to the vendored ontogenesis
# estate-catalog vocabulary, and the live-proof SPARQL query returns rows.
validate-estate-graph:
	python3 tools/emit_estate_graph.py
	python3 tools/validate_estate_graph.py
