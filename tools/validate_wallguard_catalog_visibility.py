#!/usr/bin/env python3
"""Validate WallGuard catalog visibility examples."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "wallguard-catalog-visibility.schema.json"
EXAMPLE_DIR = ROOT / "examples" / "wallguard-catalog-visibility"
RESTRICTED_CLASSES = {"client_confidential", "matter_restricted", "wall_restricted"}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_schema(instance: dict, schema: dict, *, source_label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        lines = [f"{source_label} failed schema validation:"]
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            lines.append(f" - {location}: {error.message}")
        raise ValueError("\n".join(lines))


def semantic_diagnostics(record: dict) -> list[str]:
    diagnostics: list[str] = []
    labels = record["resource_labels"]
    resource_wall = labels["wall_ref"]
    active_wall = record["active_wall_ref"]
    classification = labels["classification"]
    same_wall = resource_wall == active_wall
    decision = record["visibility_decision"]
    metadata_visibility = record["metadata_visibility"]
    existence_visible = record["existence_visible"]
    rank_or_list_eligible = record["rank_or_list_eligible"]

    if classification in RESTRICTED_CLASSES and not same_wall:
        if decision == "visible":
            diagnostics.append("restricted outside-wall resource cannot be visible")
        if metadata_visibility == "full":
            diagnostics.append("restricted outside-wall resource cannot expose full metadata")
        if existence_visible:
            diagnostics.append("restricted outside-wall resource existence must be hidden")
        if rank_or_list_eligible:
            diagnostics.append("restricted outside-wall resource cannot be rank/list eligible")

    if decision == "visible":
        if metadata_visibility != "full":
            diagnostics.append("visible records require full metadata visibility")
        if not existence_visible:
            diagnostics.append("visible records require existence_visible=true")
        if not rank_or_list_eligible:
            diagnostics.append("visible records should be rank/list eligible")

    if decision in {"withheld", "quarantined", "fail_closed"}:
        if existence_visible:
            diagnostics.append("withheld/quarantined/fail_closed records cannot expose existence")
        if rank_or_list_eligible:
            diagnostics.append("withheld/quarantined/fail_closed records cannot be rank/list eligible")
        if metadata_visibility == "full":
            diagnostics.append("withheld/quarantined/fail_closed records cannot expose full metadata")

    if not any(ref.startswith("policy-fabric://") for ref in record.get("policy_refs", [])):
        diagnostics.append("policy_refs must include a Policy Fabric ref")
    if not all(ref.startswith("wallguard-receipt://") for ref in record.get("receipt_refs", [])):
        diagnostics.append("receipt_refs must be WallGuard receipt refs")

    return diagnostics


def main() -> int:
    schema = load_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    examples = sorted(EXAMPLE_DIR.glob("*.json"))
    if not examples:
        raise SystemExit("No WallGuard catalog visibility examples found")

    results = []
    for path in examples:
        record = load_json(path)
        validate_schema(record, schema, source_label=str(path.relative_to(ROOT)))
        diagnostics = semantic_diagnostics(record)
        actual = "fail" if diagnostics else "pass"
        result = {"example": path.name, "expected": "pass", "actual": actual, "diagnostics": diagnostics}
        results.append(result)
        if actual != "pass":
            raise ValueError(json.dumps(result, indent=2))

    print(json.dumps({"ok": True, "checked": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
