#!/usr/bin/env python3
"""schemas-contracts extractor (ds.schemas-contracts).

Emits ONE repo's contribution shard: one record per CONTRACT file found in
<repo_path> (JSON-Schema, Protobuf, Avro, OpenAPI/AsyncAPI, SHACL, or a clearly
contract-defining TS/Zod/Pydantic module under a `contracts/` dir), in the SAME
record schema as `datasets/schemas-contracts/contracts.jsonl` (see SCHEMA.md).

    python3 extractors/extract_schemas_contracts.py <repo_path> <repo_name> [--out FILE]

`id = ct-<sha1[:12] of repo\\0path>` — stable + idempotent for unmoved files, and
byte-compatible with the central harvest's ids. `consumers[]` are best-effort
`$ref`/import blast-radius edges resolved WITHIN this repo (a per-repo shard sees
only its own tree; the central assembler already treats consumers as a floor).

Read-only, stdlib-only, deterministic.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_hex, run  # noqa: E402

# Reference-file surfaces we scan for consumer edges (basename / $id occurrences).
REF_EXTS = {".json", ".yaml", ".yml", ".proto", ".avsc", ".ttl", ".md",
            ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".rs", ".go"}
MAX_REF_FILES = 6000
CONSUMER_CAP = 40

_VER_TOKEN = re.compile(r"\bv(\d+(?:\.\d+){0,2})\b")
_SCHEMA_KEYWORDS = ("properties", "type", "$ref", "allOf", "anyOf", "oneOf",
                    "required", "definitions", "$defs", "patternProperties")


def _version_from(*texts: str) -> str:
    for t in texts:
        if not t:
            continue
        m = _VER_TOKEN.search(t)
        if m:
            return "v" + m.group(1)
    return ""


def _classify(relpath: str, text: str) -> tuple[str, str, str, str] | None:
    """Return (kind, schema_id, version, intent) for a contract file, else None."""
    name = os.path.basename(relpath)
    low = name.lower()

    # --- Protobuf ---
    if low.endswith(".proto"):
        pkg = ""
        m = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.MULTILINE)
        if m:
            pkg = m.group(1)
        svc = re.search(r"^\s*service\s+(\w+)", text, re.MULTILINE)
        msg = re.search(r"^\s*message\s+(\w+)", text, re.MULTILINE)
        bits = []
        if svc:
            bits.append(f"service {svc.group(1)}")
        if msg:
            bits.append(f"message {msg.group(1)}")
        intent = (pkg + (": " if pkg and bits else "") + ", ".join(bits)).strip()
        return "protobuf", pkg, _version_from(pkg, name), intent

    # --- Avro ---
    if low.endswith(".avsc"):
        schema_id = ""
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                ns = obj.get("namespace", "")
                nm = obj.get("name", "")
                schema_id = ".".join(x for x in (ns, nm) if x)
        except Exception:
            pass
        return "avro", schema_id, "", ""

    # --- OpenAPI / AsyncAPI ---
    if (low.startswith("openapi") or low.startswith("asyncapi")) and low.endswith((".yaml", ".yml", ".json")):
        title, ver = "", ""
        mt = re.search(r"^\s*title:\s*(.+)$", text, re.MULTILINE)
        mv = re.search(r"^\s*version:\s*['\"]?([\w.\-]+)", text, re.MULTILINE)
        if low.endswith(".json"):
            try:
                obj = json.loads(text)
                info = obj.get("info", {}) if isinstance(obj, dict) else {}
                title = str(info.get("title", "") or "")
                ver = str(info.get("version", "") or "")
            except Exception:
                pass
        if not title and mt:
            title = mt.group(1).strip().strip("'\"")
        if not ver and mv:
            ver = mv.group(1)
        return "openapi", title, ver, (f"OpenAPI: {title}" if title else "OpenAPI document")

    # --- SHACL ---
    if low.endswith(".shacl.ttl") or ("sh:NodeShape" in text or "sh:PropertyShape" in text):
        if low.endswith(".ttl"):
            return "shacl", "", "", "SHACL shape graph"

    # --- JSON Schema ---
    if low.endswith(".schema.json"):
        return _jsonschema_fields(name, text)
    if low.endswith(".json"):
        try:
            obj = json.loads(text)
        except Exception:
            return None
        if isinstance(obj, dict) and (
            "$schema" in obj and "json-schema.org" in str(obj.get("$schema", ""))
            or ("$id" in obj and any(k in obj for k in _SCHEMA_KEYWORDS))
        ):
            return _jsonschema_fields(name, text, obj)

    # --- other: Zod/TypeBox/Pydantic contract modules under a contracts/ dir ---
    parts = relpath.lower().split("/")
    if ("contracts" in parts or ".contract." in low) and low.endswith((".ts", ".tsx", ".py")):
        defines = (
            re.search(r"\b(z|Type)\.(object|Object)\b", text)          # zod / typebox
            or re.search(r"class\s+\w+\(BaseModel\)", text)             # pydantic
            or re.search(r"export\s+(interface|type)\s+\w+", text)      # TS contract
        )
        if defines:
            stem = Path(name).stem
            return "other", "", _version_from(name), f"TS/interface contract module ({name})" \
                if low.endswith((".ts", ".tsx")) else f"Pydantic/py contract module ({name})"
    return None


def _jsonschema_fields(name: str, text: str, obj: dict | None = None):
    if obj is None:
        try:
            obj = json.loads(text)
        except Exception:
            obj = {}
    if not isinstance(obj, dict):
        obj = {}
    schema_id = str(obj.get("$id", "") or "")
    version = str(obj.get("version", obj.get("$version", "")) or "")
    if not version:
        version = _version_from(schema_id, name)
    intent = str(obj.get("title", "") or obj.get("description", "") or "")
    intent = " ".join(intent.split())[:200]
    return "json-schema", schema_id, version, intent


def extract(repo_path: str, repo_name: str) -> list[dict]:
    contracts: list[dict] = []
    # 1) find contract files
    scan_exts = {".proto", ".avsc", ".json", ".yaml", ".yml", ".ttl", ".ts", ".tsx", ".py"}
    for path in iter_files(repo_path, scan_exts):
        text = read_text(path)
        if text is None:
            continue
        relpath = rel(repo_path, path)
        got = _classify(relpath, text)
        if got is None:
            continue
        kind, schema_id, version, intent = got
        contracts.append({
            "id": "ct-" + sha1_hex(f"{repo_name}\x00{relpath}", 12),
            "name": os.path.basename(relpath),
            "kind": kind,
            "repo": repo_name,
            "path": relpath,
            "schema_id": schema_id,
            "version": version,
            "consumers": [],
            "intent": intent,
            "consumer_count": 0,
        })
    if not contracts:
        return []

    # 2) best-effort consumer edges within this repo (basename / $id occurrences)
    by_basename: dict[str, list[dict]] = {}
    for c in contracts:
        by_basename.setdefault(c["name"], []).append(c)
    ids = {c["path"]: c for c in contracts}

    ref_count = 0
    for path in iter_files(repo_path, REF_EXTS):
        if ref_count >= MAX_REF_FILES:
            break
        relpath = rel(repo_path, path)
        if relpath in ids:
            continue  # a contract file does not consume itself
        text = read_text(path)
        if text is None:
            continue
        ref_count += 1
        for base, recs in by_basename.items():
            if base in text:
                for c in recs:
                    if c["path"] == relpath:
                        continue
                    c.setdefault("_consumers_set", set()).add(f"{repo_name}/{relpath}")

    for c in contracts:
        cons = sorted(c.pop("_consumers_set", set()))
        c["consumer_count"] = len(cons)
        c["consumers"] = cons[:CONSUMER_CAP]
    contracts.sort(key=lambda r: r["id"])
    return contracts


if __name__ == "__main__":
    raise SystemExit(run("schemas-contracts", extract))
