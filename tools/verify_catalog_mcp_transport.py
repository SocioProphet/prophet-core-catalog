#!/usr/bin/env python3
"""Conformance verifier for the catalog MCP house-protocol transport.

Mirrors TriTRPC's `tools/verify_agent_sandbox_transport.py`. A catalog MCP frame is
conformant only if it is a house-protocol typed blob:

  * canonical JSON  — the bound `payload_digest` MUST equal sha256 over the canonical
                      (UTF-8, sorted-keys, no-whitespace) serialization of `payload`;
  * media type      — request `application/vnd.socioprophet.catalog-query+json;v=0`,
                      response `application/vnd.socioprophet.catalog-result+json;v=0`,
                      and it MUST agree with the method's REQ/RES suffix;
  * method naming    — `catalog.<tool>.REQ` / `catalog.<tool>.RES`, tool known;
  * typed envelope  — every REQUIRED_FIELDS field present; responses MUST carry a
                      `parent_ref` binding them to the request they answer.

TEETH BOTH WAYS: this verifier does not merely bless good frames. It runs the
`fixtures/catalog_mcp/good/` frames (which MUST all pass) AND the
`fixtures/catalog_mcp/bad/` frames (each of which MUST be rejected). If a tampered
frame slips through, or a good frame is rejected, the verifier exits non-zero.

Wired into `make validate`.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "catalog_mcp"

SCHEMA_VERSION = "socioprophet-catalog-mcp-transport.v0"
MEDIA_REQ = "application/vnd.socioprophet.catalog-query+json;v=0"
MEDIA_RES = "application/vnd.socioprophet.catalog-result+json;v=0"
KNOWN_MEDIA = {MEDIA_REQ, MEDIA_RES}
KNOWN_TOOLS = {
    "catalog.define",
    "catalog.who_uses",
    "catalog.blast_radius",
    "catalog.search",
    "catalog.stats",
    "catalog.dataset",
}
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


class NonConformant(Exception):
    """Raised when a frame violates the house-protocol transport profile."""


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_digest(payload: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def verify_frame(blob: object) -> None:
    """Raise NonConformant unless `blob` conforms to the transport profile."""
    if not isinstance(blob, dict):
        raise NonConformant("frame is not a JSON object")

    # 1. typed envelope: every required field present.
    for field in REQUIRED_FIELDS:
        if field not in blob:
            raise NonConformant(f"missing envelope field: {field}")

    # 2. schema version pin.
    if blob["schema_version"] != SCHEMA_VERSION:
        raise NonConformant(f"bad schema_version: {blob['schema_version']!r}")

    # 3. recognized media type.
    media = blob["media_type"]
    if media not in KNOWN_MEDIA:
        raise NonConformant(f"unknown media_type: {media!r}")

    # 4. semantic schema ref points at the catalog-mcp vocabulary.
    if not str(blob["semantic_schema_ref"]).startswith("prophet-core-catalog:catalog-mcp.v0#/"):
        raise NonConformant(f"bad semantic_schema_ref: {blob['semantic_schema_ref']!r}")

    # 5. method naming + REQ/RES <-> media-type agreement.
    method = str(blob["method"])
    parts = method.split(".")
    if len(parts) != 3 or parts[0] != "catalog" or parts[2] not in {"REQ", "RES"}:
        raise NonConformant(f"malformed method name: {method!r}")
    tool = f"{parts[0]}.{parts[1]}"
    kind = parts[2]
    if tool not in KNOWN_TOOLS:
        raise NonConformant(f"unknown tool in method: {tool!r}")
    expected_media = MEDIA_REQ if kind == "REQ" else MEDIA_RES
    if media != expected_media:
        raise NonConformant(f"media_type {media!r} does not match {kind} method {method!r}")

    # 6. payload tool field agrees with the method.
    payload = blob["payload"]
    if not isinstance(payload, dict) or payload.get("tool") != tool:
        raise NonConformant(f"payload.tool does not match method tool {tool!r}")

    # 7. canonical-JSON digest binding (this is what catches non-canonical / tampered
    #    payloads: a non-canonical or mutated payload will not hash to the bound digest).
    got = canonical_digest(payload)
    if got != blob["payload_digest"]:
        raise NonConformant(
            f"digest mismatch: canonical={got} bound={blob['payload_digest']}"
        )

    # 8. responses MUST bind to the request they answer.
    if kind == "RES" and not blob.get("parent_ref"):
        raise NonConformant("response frame missing parent_ref binding")


def _load(path: pathlib.Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    good_dir = FIXTURE_DIR / "good"
    bad_dir = FIXTURE_DIR / "bad"
    good = sorted(good_dir.glob("*.json"))
    bad = sorted(bad_dir.glob("*.json"))
    if not good:
        raise SystemExit("no good catalog MCP transport fixtures found")
    if not bad:
        raise SystemExit("no tampered (bad) catalog MCP transport fixtures found — "
                         "the verifier must have teeth both ways")

    failures = []

    # Teeth (accept): every good frame MUST pass.
    for path in good:
        try:
            verify_frame(_load(path))
            print(f"PASS good/{path.name}")
        except NonConformant as exc:
            failures.append(f"good/{path.name} WRONGLY REJECTED: {exc}")
            print(f"FAIL good/{path.name}: {exc}")

    # Teeth (reject): every tampered frame MUST be rejected.
    for path in bad:
        try:
            verify_frame(_load(path))
            failures.append(f"bad/{path.name} WRONGLY ACCEPTED (tamper not caught)")
            print(f"FAIL bad/{path.name}: tampered frame was accepted")
        except NonConformant as exc:
            print(f"PASS bad/{path.name} rejected: {exc}")

    if failures:
        print("\nCONFORMANCE FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"\nOK: {len(good)} good frame(s) accepted, {len(bad)} tampered frame(s) rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
