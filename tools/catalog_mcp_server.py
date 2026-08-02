#!/usr/bin/env python3
"""Catalog MCP server that rides the HOUSE PROTOCOL (TriTRPC transport profile).

This is deliberately NOT a vanilla stdio / JSON-RPC 2.0 MCP server. Per the estate
policy "every MCP surface MUST ride the TriTRPC transport profile" (see
`docs/CATALOG-MCP.md` and socioprophet-agent-standards `031-mcp-house-protocol.md`),
every request and response this server carries is a **house-protocol typed blob**:

  * canonical JSON  — UTF-8, sorted object keys, no insignificant whitespace,
                      exact enum strings (matches TriTRPC
                      `docs/AGENT_SANDBOX_TRANSPORT_PROFILE.md`);
  * digest binding  — `sha256:<lowercase-hex>` over the canonical payload bytes,
                      bound in the envelope as `payload_digest`;
  * typed media type — request  `application/vnd.socioprophet.catalog-query+json;v=0`
                       response `application/vnd.socioprophet.catalog-result+json;v=0`;
  * typed envelope  — media type + payload digest + semantic schema ref + producer
                      identity/attestation + parent ref;
  * method naming   — `catalog.<tool>.REQ` / `catalog.<tool>.RES` (mirrors the
                      TriTRPC CLI `--method X.REQ` style).

The MCP tools exposed are the six catalog queries, reusing the existing
`catalog_query.py` index-loading logic (`_load`, `IDX`):

  catalog.define        catalog.who_uses     catalog.blast_radius
  catalog.search        catalog.stats        catalog.dataset

Frame-binding seam: these typed blobs are the *carried artifact*. Binding them into
the ternary TriTRPC wire frame (TritPack243 / TLEB3 / XChaCha20-Poly1305 AEAD, see
TriTRPC `reference/tritrpc_v1.py`) is out of scope here and is documented as a seam in
`docs/CATALOG-MCP.md`; this module conforms to the canonical-JSON + digest + media-type
+ method-naming transport profile, which is what the estate policy mandates.

Usage:
  # house-protocol frame server: reads newline-delimited REQ blobs on stdin,
  # writes newline-delimited RES blobs on stdout (one JSON object per line).
  catalog_mcp_server.py serve

  # one-shot: build a REQ frame, dispatch it, print the RES frame.
  catalog_mcp_server.py call catalog.who_uses '{"query": "numpy"}'

  # emit a canonical REQ frame (no dispatch) — useful for fixtures/tooling.
  catalog_mcp_server.py req catalog.stats '{}'

  # MCP tool discovery (the house-protocol analogue of tools/list).
  catalog_mcp_server.py describe

  # regenerate the conformance fixtures under fixtures/catalog_mcp/.
  catalog_mcp_server.py emit-fixtures
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# Reuse the existing catalog_query logic (index location + loader).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog_query import IDX, _load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "catalog_mcp"

# ---- house-protocol transport constants -------------------------------------

SCHEMA_VERSION = "socioprophet-catalog-mcp-transport.v0"
MEDIA_REQ = "application/vnd.socioprophet.catalog-query+json;v=0"
MEDIA_RES = "application/vnd.socioprophet.catalog-result+json;v=0"
SEMANTIC_REQ = "prophet-core-catalog:catalog-mcp.v0#/CatalogQuery"
SEMANTIC_RES = "prophet-core-catalog:catalog-mcp.v0#/CatalogResult"
PRODUCER = "prophet-core-catalog/tools/catalog_mcp_server.py@catalog-mcp.v0"
TRANSPORT_PROFILE = "tritrpc:docs/AGENT_SANDBOX_TRANSPORT_PROFILE.md"

# MCP tool surface. Each tool declares its single query argument (None = no args).
TOOL_SPECS = {
    "catalog.define": {
        "arg": "term",
        "summary": "Define a glossary term (business/data vocabulary).",
    },
    "catalog.who_uses": {
        "arg": "query",
        "summary": "Who uses an asset/repo — dependency edges touching a substring.",
    },
    "catalog.blast_radius": {
        "arg": "asset_id",
        "summary": "Blast radius of an asset — every edge into or out of it.",
    },
    "catalog.search": {
        "arg": "text",
        "summary": "Full-text search across cataloged assets.",
    },
    "catalog.stats": {
        "arg": None,
        "summary": "Catalog registry stats (datasets, assets, glossary, edges).",
    },
    "catalog.dataset": {
        "arg": "dataset",
        "summary": "List the assets contributed by a named dataset.",
    },
}

RESULT_CAP = 50


class TransportError(Exception):
    """Raised when a frame violates the house-protocol transport profile."""


# ---- canonicalization + digest (identical profile to TriTRPC) ---------------

def canonical_bytes(payload: object) -> bytes:
    """RFC-8785-style canonical JSON per the TriTRPC transport profile:
    UTF-8, sorted keys, no insignificant whitespace, exact enum strings."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def payload_digest(payload: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def method_of(tool: str, kind: str) -> str:
    if kind not in {"REQ", "RES"}:
        raise ValueError(kind)
    return f"{tool}.{kind}"


# ---- envelope construction --------------------------------------------------

def _blob_id(tool: str, kind: str, payload: object) -> str:
    tail = payload_digest(payload).split(":", 1)[1][:12]
    return f"blob_{tool.replace('.', '_')}_{kind.lower()}_{tail}"


def build_request_blob(tool: str, args: dict) -> dict:
    if tool not in TOOL_SPECS:
        raise TransportError(f"unknown tool {tool!r}")
    payload = {"tool": tool, "args": args or {}}
    return {
        "schema_version": SCHEMA_VERSION,
        "blob_id": _blob_id(tool, "REQ", payload),
        "media_type": MEDIA_REQ,
        "method": method_of(tool, "REQ"),
        "semantic_schema_ref": SEMANTIC_REQ,
        "transport_profile": TRANSPORT_PROFILE,
        "payload_digest": payload_digest(payload),
        "payload": payload,
        "producer": PRODUCER,
        "attestation_ref": None,
        "parent_ref": None,
    }


def build_response_blob(request_blob: dict, result: dict) -> dict:
    tool = request_blob["payload"]["tool"]
    payload = {"tool": tool, "result": result}
    return {
        "schema_version": SCHEMA_VERSION,
        "blob_id": _blob_id(tool, "RES", payload),
        "media_type": MEDIA_RES,
        "method": method_of(tool, "RES"),
        "semantic_schema_ref": SEMANTIC_RES,
        "transport_profile": TRANSPORT_PROFILE,
        "payload_digest": payload_digest(payload),
        "payload": payload,
        "producer": PRODUCER,
        "attestation_ref": None,
        # parent ref binds the response to the exact request frame it answers.
        "parent_ref": request_blob["blob_id"],
        "in_reply_to_digest": request_blob["payload_digest"],
    }


# Envelope fields every house-protocol frame MUST carry.
REQUIRED_FIELDS = (
    "schema_version",
    "blob_id",
    "media_type",
    "method",
    "semantic_schema_ref",
    "payload_digest",
    "payload",
    "producer",
)


def verify_request_blob(blob: dict) -> dict:
    """Validate an inbound REQ frame against the transport profile; return payload."""
    if not isinstance(blob, dict):
        raise TransportError("frame is not a JSON object")
    for field in REQUIRED_FIELDS:
        if field not in blob:
            raise TransportError(f"missing envelope field: {field}")
    if blob["schema_version"] != SCHEMA_VERSION:
        raise TransportError(f"bad schema_version {blob['schema_version']!r}")
    if blob["media_type"] != MEDIA_REQ:
        raise TransportError(f"request media_type must be {MEDIA_REQ}")
    got = payload_digest(blob["payload"])
    if got != blob["payload_digest"]:
        raise TransportError(
            f"digest mismatch: canonical={got} bound={blob['payload_digest']}"
        )
    payload = blob["payload"]
    tool = payload.get("tool")
    if tool not in TOOL_SPECS:
        raise TransportError(f"unknown tool {tool!r}")
    if blob["method"] != method_of(tool, "REQ"):
        raise TransportError(
            f"method {blob['method']!r} does not match tool {tool!r} REQ"
        )
    return payload


# ---- catalog query handlers (reuse catalog_query index; return structured) --

def _q(payload: dict) -> str:
    return str(payload.get("args", {}).get(TOOL_SPECS[payload["tool"]]["arg"], "")).strip()


def h_stats(_payload: dict) -> dict:
    idx = json.loads((IDX / "index.json").read_text(encoding="utf-8"))
    return {
        "datasets": idx.get("datasets"),
        "assets": idx.get("assets"),
        "glossary_terms": idx.get("glossary_terms"),
        "edges": idx.get("edges"),
        "registry": idx.get("registry", []),
    }


def h_search(payload: dict) -> dict:
    q = _q(payload).lower()
    hits = [a for a in _load("assets.jsonl") if q in a.get("search", "")]
    rows = [
        {
            "asset_id": a["asset_id"],
            "dataset": a["dataset"],
            "name": a["name"],
            "kind": a.get("kind"),
            "repo": a.get("repo"),
            "path": a.get("path"),
        }
        for a in hits[:RESULT_CAP]
    ]
    return {"query": q, "count": len(hits), "capped": len(rows), "rows": rows}


def h_define(payload: dict) -> dict:
    q = _q(payload).lower()
    gl = [g for g in _load("glossary.jsonl") if q in (g.get("name") or "").lower()]
    rows = [
        {
            "name": g["name"],
            "kind": g.get("kind"),
            "definition": g.get("definition"),
            "related_terms": g.get("related_terms", [])[:8],
            "narrower_terms": g.get("narrower_terms", [])[:8],
            "repos": g.get("repos", []),
        }
        for g in gl[:RESULT_CAP]
    ]
    return {"term": q, "count": len(gl), "capped": len(rows), "rows": rows}


def h_who_uses(payload: dict) -> dict:
    q = _q(payload).lower()
    es = [
        e
        for e in _load("edges.jsonl")
        if q in (e.get("to") or "").lower() or q in (e.get("from") or "").lower()
    ]
    rows = [
        {"from": e.get("from"), "rel": e.get("rel"), "to": e.get("to"), "line": e.get("line")}
        for e in es[:RESULT_CAP]
    ]
    return {"query": q, "count": len(es), "capped": len(rows), "rows": rows}


def h_blast_radius(payload: dict) -> dict:
    aid = _q(payload)
    es = [e for e in _load("edges.jsonl") if e.get("from") == aid or e.get("to") == aid]
    rows = [
        {"from": e.get("from"), "rel": e.get("rel"), "to": e.get("to"), "line": e.get("line")}
        for e in es[:RESULT_CAP]
    ]
    return {"asset_id": aid, "count": len(es), "capped": len(rows), "rows": rows}


def h_dataset(payload: dict) -> dict:
    ds = _q(payload)
    rows = [a for a in _load("assets.jsonl") if a["dataset"] == ds]
    out = [
        {"asset_id": a["asset_id"], "name": a["name"], "kind": a.get("kind"), "repo": a.get("repo")}
        for a in rows[:RESULT_CAP]
    ]
    return {"dataset": ds, "count": len(rows), "capped": len(out), "rows": out}


HANDLERS = {
    "catalog.stats": h_stats,
    "catalog.search": h_search,
    "catalog.define": h_define,
    "catalog.who_uses": h_who_uses,
    "catalog.blast_radius": h_blast_radius,
    "catalog.dataset": h_dataset,
}


def dispatch(request_blob: dict) -> dict:
    """Verify an inbound REQ frame, run the tool, return a bound RES frame."""
    payload = verify_request_blob(request_blob)
    result = HANDLERS[payload["tool"]](payload)
    return build_response_blob(request_blob, result)


# ---- serialization helpers --------------------------------------------------

def dumps_pretty(blob: dict) -> str:
    # frames are stored/emitted pretty for humans; the DIGEST is over canonical
    # payload bytes, so pretty framing does not weaken the binding (mirrors the
    # TriTRPC agent-sandbox transport fixtures, which are also indented).
    return json.dumps(blob, indent=2, ensure_ascii=False, sort_keys=True)


def dumps_line(blob: dict) -> str:
    return json.dumps(blob, ensure_ascii=False, sort_keys=True)


# ---- CLI / server -----------------------------------------------------------

def _describe() -> dict:
    return {
        "server": "prophet-core-catalog.catalog-mcp",
        "transport": {
            "profile": TRANSPORT_PROFILE,
            "schema_version": SCHEMA_VERSION,
            "request_media_type": MEDIA_REQ,
            "response_media_type": MEDIA_RES,
            "digest": "sha256 over canonical JSON payload",
        },
        "tools": [
            {
                "name": name,
                "method_req": method_of(name, "REQ"),
                "method_res": method_of(name, "RES"),
                "arg": spec["arg"],
                "summary": spec["summary"],
            }
            for name, spec in TOOL_SPECS.items()
        ],
    }


def emit_fixtures() -> int:
    good = FIXTURE_DIR / "good"
    good.mkdir(parents=True, exist_ok=True)
    # Real queries against the committed index so fixtures carry real answers.
    seeds = [
        ("catalog.stats", {}),
        ("catalog.who_uses", {"query": "skills"}),
        ("catalog.define", {"term": "topic"}),
    ]
    written = []
    for tool, args in seeds:
        req = build_request_blob(tool, args)
        res = dispatch(req)
        rp = good / f"{tool.replace('.', '_')}.req.json"
        sp = good / f"{tool.replace('.', '_')}.res.json"
        rp.write_text(dumps_pretty(req) + "\n", encoding="utf-8")
        sp.write_text(dumps_pretty(res) + "\n", encoding="utf-8")
        written += [rp, sp]
    for p in written:
        print(f"wrote {p.relative_to(ROOT)}")
    print(f"emitted {len(written)} good fixture frame(s); tamper bad/ fixtures by hand")
    return 0


def serve() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = dispatch(req)
            sys.stdout.write(dumps_line(res) + "\n")
        except (TransportError, ValueError, KeyError) as exc:
            err = {
                "schema_version": SCHEMA_VERSION,
                "media_type": MEDIA_RES,
                "method": "catalog.error.RES",
                "error": str(exc),
            }
            sys.stdout.write(dumps_line(err) + "\n")
        sys.stdout.flush()
    return 0


def main(argv) -> int:
    if not argv:
        sys.exit(__doc__)
    cmd, rest = argv[0], argv[1:]
    if cmd == "serve":
        return serve()
    if cmd == "describe":
        print(dumps_pretty(_describe()))
        return 0
    if cmd == "emit-fixtures":
        return emit_fixtures()
    if cmd == "req":
        tool = rest[0]
        args = json.loads(rest[1]) if len(rest) > 1 else {}
        print(dumps_pretty(build_request_blob(tool, args)))
        return 0
    if cmd == "call":
        tool = rest[0]
        args = json.loads(rest[1]) if len(rest) > 1 else {}
        req = build_request_blob(tool, args)
        print(dumps_pretty(dispatch(req)))
        return 0
    sys.exit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
