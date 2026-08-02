.PHONY: validate validate-wallguard-catalog-visibility validate-internal-ops-libraries

validate: validate-wallguard-catalog-visibility validate-internal-ops-libraries

validate-wallguard-catalog-visibility:
	python3 tools/validate_wallguard_catalog_visibility.py

validate-internal-ops-libraries:
	python3 tools/validate_internal_ops_libraries.py
