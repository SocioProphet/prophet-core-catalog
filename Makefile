.PHONY: validate validate-wallguard-catalog-visibility

validate: validate-wallguard-catalog-visibility

validate-wallguard-catalog-visibility:
	python3 tools/validate_wallguard_catalog_visibility.py
