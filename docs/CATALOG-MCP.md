# Catalog MCP over the HOUSE PROTOCOL (TriTRPC transport profile)

The catalog exposes an MCP surface — `tools/catalog_mcp_server.py` — for querying the
asset catalog. It is **not** a vanilla stdio / JSON-RPC 2.0 MCP server. Per estate
policy (`SocioProphet/socioprophet-agent-standards`
`docs/standards/031-mcp-house-protocol.md`, "every MCP surface MUST ride the TriTRPC
transport profile"), every request and response it carries is a **house-protocol typed
blob** conforming to TriTRPC `docs/AGENT_SANDBOX_TRANSPORT_PROFILE.md`.

## What "house protocol" means here (the four teeth)

1. **Canonical JSON** — UTF-8, sorted object keys, no insignificant whitespace, exact
   enum strings. The `payload` of every frame is digested over its canonical byte
   string (`json.dumps(payload, sort_keys=True, separators=(",",":"), ensure_ascii=False)`),
   identical to the TriTRPC agent-sandbox transport profile.
2. **Digest binding** — `payload_digest` is `sha256:<lowercase-hex>` over those canonical
   bytes and is bound in the envelope. A tampered or non-canonically-serialized payload
   will not hash to the bound digest and is rejected.
3. **Typed media types** — `application/vnd.socioprophet.<type>+json;v=0`:
   * request  — `application/vnd.socioprophet.catalog-query+json;v=0`
   * response — `application/vnd.socioprophet.catalog-result+json;v=0`
4. **Typed envelope + method naming** — every frame binds media type, payload digest,
   semantic schema ref, producer identity/attestation, and a parent ref, and is
   **method-named** `catalog.<tool>.REQ` / `catalog.<tool>.RES` (mirrors the TriTRPC CLI
   `--method X.REQ` style).

## MCP tools (methods)

| Tool                   | Request method              | Response method             | Argument   |
| ---------------------- | --------------------------- | --------------------------- | ---------- |
| `catalog.define`       | `catalog.define.REQ`        | `catalog.define.RES`        | `term`     |
| `catalog.who_uses`     | `catalog.who_uses.REQ`      | `catalog.who_uses.RES`      | `query`    |
| `catalog.blast_radius` | `catalog.blast_radius.REQ`  | `catalog.blast_radius.RES`  | `asset_id` |
| `catalog.search`       | `catalog.search.REQ`        | `catalog.search.RES`        | `text`     |
| `catalog.stats`        | `catalog.stats.REQ`         | `catalog.stats.RES`         | _(none)_   |
| `catalog.dataset`      | `catalog.dataset.REQ`       | `catalog.dataset.RES`       | `dataset`  |

The query logic reuses `tools/catalog_query.py` (index location `IDX` + the `_load`
loader), so the MCP surface answers from the same committed `catalog-index/`.

## Envelope shape

```json
{
  "schema_version": "socioprophet-catalog-mcp-transport.v0",
  "blob_id": "blob_catalog_who_uses_req_1824c46c0793",
  "media_type": "application/vnd.socioprophet.catalog-query+json;v=0",
  "method": "catalog.who_uses.REQ",
  "semantic_schema_ref": "prophet-core-catalog:catalog-mcp.v0#/CatalogQuery",
  "transport_profile": "tritrpc:docs/AGENT_SANDBOX_TRANSPORT_PROFILE.md",
  "payload_digest": "sha256:1824c46c07937377097af199622649239acd4de48151b48221de7157e9174083",
  "payload": { "tool": "catalog.who_uses", "args": { "query": "skills" } },
  "producer": "prophet-core-catalog/tools/catalog_mcp_server.py@catalog-mcp.v0",
  "attestation_ref": null,
  "parent_ref": null
}
```

Response frames add `parent_ref` (= the request `blob_id`) and `in_reply_to_digest`
(= the request `payload_digest`), so a result is cryptographically bound to the exact
request it answers.

## Usage

```bash
# MCP tool discovery (house-protocol analogue of tools/list)
python3 tools/catalog_mcp_server.py describe

# one-shot: build a REQ frame, dispatch it, print the RES frame
python3 tools/catalog_mcp_server.py call catalog.who_uses '{"query": "skills"}'

# frame server: newline-delimited REQ blobs on stdin -> RES blobs on stdout
python3 tools/catalog_mcp_server.py serve

# regenerate the conformance fixtures
python3 tools/catalog_mcp_server.py emit-fixtures
```

## Conformance verifier (teeth both ways)

`tools/verify_catalog_mcp_transport.py` mirrors TriTRPC's `verify_*` tools and is wired
into `make validate` via the `verify-catalog-mcp-transport` target. It:

* accepts every frame under `fixtures/catalog_mcp/good/` (a good frame MUST pass), and
* rejects every frame under `fixtures/catalog_mcp/bad/` (a tampered frame MUST fail).

It exits non-zero if a good frame is rejected **or** a tampered frame is accepted. The
committed tampered fixtures exercise each failure mode: payload-digest mismatch,
non-canonical payload serialization, wrong media type, a missing envelope field, and a
response missing its `parent_ref` binding.

```
OK: 6 good frame(s) accepted, 5 tampered frame(s) rejected
```

## Frame-binding seam (ternary TriTRPC wire frame)

The typed blobs above are the **carried artifact**. Binding them into the ternary
TriTRPC wire frame — TritPack243 trit packing, TLEB3 lengths, and the
XChaCha20-Poly1305 AEAD lane (see TriTRPC `reference/tritrpc_v1.py`, `spec/README-full-spec.md`) —
is **out of scope** for this surface and reimplementing the ternary AEAD framing is
explicitly not done here. This module conforms to the canonical-JSON + digest +
media-type + method-naming transport profile, which is the layer the estate policy
mandates for MCP surfaces.

The seam, when a Python/CLI port of the TriTRPC frame codec is wired in, is:

* the canonical `payload` bytes become the frame **payload** (Path-A Avro, or an opaque
  typed-blob attachment), and
* the envelope fields (`media_type`, `payload_digest`, `semantic_schema_ref`,
  `producer`, `parent_ref`) map to the frame's SERVICE/METHOD routing + AUX (Trace/Sig/PoE)
  structures, with `method` = `catalog.<tool>.REQ|RES`.

Note TriTRPC's own JSON-receipt canonicalization uses RFC 8785 (JCS) + BLAKE3-256; the
**transport profile** this MCP surface binds to (the agent-sandbox transport profile)
uses the sorted-keys canonical JSON + SHA-256 digest shown above, which is what
`verify_agent_sandbox_transport.py` enforces and what this verifier mirrors.
