#!/usr/bin/env python3
"""Project EstateAdmissibilityReport documents into the catalog, with a recomputed A-F grade.

  emit      harvest reports from a sourceos-spec checkout -> admissibility.jsonl
  validate  recompute every committed grade from the row's own measurements and fail on drift

The grade is never carried from the source document. A report that asserted its own grade
could assert one its measurements do not support, which is the whole failure mode this
dataset exists to make visible — same reason the country coverage grading in the Data
Catalogue is computed from scope x income rather than declared per country.

An estate grading D or F at cold start is the CORRECT answer, not a defect. Most estates
engage without a maintained glossary — if they had one they would not need the classifier —
so the low grade is the deliverable, not an embarrassment to be smoothed away.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "classification-admissibility"
JSONL = DATASET / "admissibility.jsonl"

LAYERS = (
    "L1-ontodt-type",
    "L2-ontodq-profile",
    "L3-business-glossary",
    "L4-operational-semantics",
    "L5-table-topic",
    "L6-schema-key-graph",
)


def grade(admissible: int, degraded: int, n_eff: float, floor: float) -> tuple[str, str]:
    """A-F trust grade, derived only from what was measured."""
    quorum = n_eff >= floor
    if admissible <= 3:
        return "F", f"only {admissible}/6 layers admissible — below any meaningful quorum"
    if admissible == 6 and quorum:
        if degraded == 0:
            return "A", "all six layers admissible on their primary channels, quorum earned"
        return "B", f"all six layers admissible but {degraded} on a fallback channel"
    if quorum:
        return "C", f"{admissible}/6 layers admissible; quorum holds on a reduced stack (n_eff {n_eff} >= {floor})"
    return "D", (
        f"{admissible}/6 layers admissible but n_eff {n_eff} < floor {floor} — the layers present "
        f"are not independent enough to license POS"
    )


def row_from_report(rep: dict) -> dict:
    layers = [
        {
            "layer": layer["layer"],
            "admissible": layer["admissible"],
            "reason": layer.get("reason"),
            "degraded": bool(layer.get("degraded", False)),
        }
        for layer in rep["layers"]
    ]
    admissible = sum(1 for layer in layers if layer["admissible"])
    degraded = sum(1 for layer in layers if layer["degraded"])
    q = rep["quorum"]
    g, note = grade(admissible, degraded, q["nEff"], q["nEffFloor"])
    return {
        "id": "adm-" + hashlib.sha256(rep["id"].encode()).hexdigest()[:12],
        "estate": rep["estateRef"],
        "generated_at": rep["generatedAt"],
        "cold_start_phase": rep["coldStartPhase"],
        "layers": layers,
        "admissible_count": admissible,
        "degraded_count": degraded,
        "n_eff": q["nEff"],
        "n_eff_floor": q["nEffFloor"],
        "pos_available": q["posAvailable"],
        "grade": g,
        "grade_note": note,
        "source_report": rep["id"],
    }


def cmd_emit(spec_dir: Path) -> int:
    reports = []
    for f in sorted((spec_dir / "examples").glob("estate_admissibility_report*.json")):
        reports.append(json.loads(f.read_text(encoding="utf-8")))
    if not reports:
        print(f"FAIL: no EstateAdmissibilityReport documents under {spec_dir}/examples", file=sys.stderr)
        return 1
    DATASET.mkdir(parents=True, exist_ok=True)
    JSONL.write_text("".join(json.dumps(row_from_report(r), sort_keys=True) + "\n" for r in reports))
    print(json.dumps({"ok": True, "emitted": len(reports), "path": str(JSONL.relative_to(ROOT))}, indent=2))
    return 0


def cmd_validate() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}
    rows = [json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()]
    if not rows:
        print("FAIL: dataset is empty", file=sys.stderr)
        return 1

    for row in rows:
        rid = row["id"]
        seen = {layer["layer"] for layer in row["layers"]}
        if seen != set(LAYERS):
            failures.append(
                f"{rid}: expected all six layers, got {sorted(seen)} — an omitted layer is "
                f"indistinguishable from an admissible one"
            )
        else:
            checks[f"six-layers:{rid}"] = True

        for layer in row["layers"]:
            if not layer["admissible"] and not layer.get("reason"):
                failures.append(f"{rid}/{layer['layer']}: inadmissible without a named reason")
            else:
                checks[f"reasoned:{rid}:{layer['layer']}"] = True

        adm = sum(1 for layer in row["layers"] if layer["admissible"])
        deg = sum(1 for layer in row["layers"] if layer["degraded"])
        if adm != row["admissible_count"] or deg != row["degraded_count"]:
            failures.append(f"{rid}: counts disagree with the layer list")
        else:
            checks[f"counts:{rid}"] = True

        g, _ = grade(adm, deg, row["n_eff"], row["n_eff_floor"])
        if g != row["grade"]:
            failures.append(
                f"{rid}: grade {row['grade']!r} but its own measurements give {g!r} — the grade is "
                f"recomputed, never asserted"
            )
        else:
            checks[f"grade:{rid}"] = True

        if row["pos_available"] and row["n_eff"] < row["n_eff_floor"]:
            failures.append(
                f"{rid}: pos_available at n_eff below floor — below the floor the honest outputs "
                f"are ZERO and NEG only"
            )
        else:
            checks[f"pos-gate:{rid}"] = True

    # Prove the grader spans its own range. A grading function only ever exercised on one
    # estate is a constant with extra steps.
    bands = {
        "A": grade(6, 0, 5.0, 4.0)[0],
        "B": grade(6, 2, 5.0, 4.0)[0],
        "C": grade(5, 1, 5.0, 4.0)[0],
        "D": grade(5, 1, 3.0, 4.0)[0],
        "F": grade(3, 0, 5.0, 4.0)[0],
    }
    for expected, got in bands.items():
        if expected != got:
            failures.append(f"grader band {expected} returned {got} — grading function is wrong")
        else:
            checks[f"band:{expected}"] = True
    # Degradation must actually cost something, or the A/B split is decorative.
    if grade(6, 0, 5.0, 4.0)[0] == grade(6, 1, 5.0, 4.0)[0]:
        failures.append("degraded layers do not affect the grade — the A/B distinction is vacuous")
    else:
        checks["degradation-costs"] = True

    for m in failures:
        print(f"FAIL: {m}", file=sys.stderr)
    ok = not failures and all(checks.values())
    print(json.dumps({"ok": ok, "rows": len(rows), "checks": checks}, indent=2, sort_keys=True))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("emit", "validate"))
    ap.add_argument("--spec-dir", type=Path, default=Path.home() / "dev" / "sourceos-spec")
    args = ap.parse_args()
    return cmd_emit(args.spec_dir) if args.command == "emit" else cmd_validate()


if __name__ == "__main__":
    raise SystemExit(main())
