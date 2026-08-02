#!/usr/bin/env python3
"""Select the estate repos the central re-harvest should read-only clone.

Data-driven from `sources/src.*.json` (no hand-maintained list): every first-party
SocioProphet estate repo in a code-ish domain is a candidate. The central
`catalog-refresh` workflow clones each ANONYMOUSLY (public repos need no auth) and
best-effort-skips any that don't clone, so this list can be broad without a token.

Emits TSV lines: `<owner/repo>\t<repo_name>` where repo_name is the logical name
used in `sources[].repo` (the part after the org), matching the extractor contract
`python3 extractors/extract_<ds>.py <repo_path> <repo_name>`.

    python3 tools/select_refresh_repos.py                 # all first-party code repos
    python3 tools/select_refresh_repos.py --public-only   # only auth:none / privacy:public
    python3 tools/select_refresh_repos.py --limit 30      # bound the set
    python3 tools/select_refresh_repos.py --org SocioProphet

Deterministic (sorted, public-first). Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"

# Domains that carry cloneable source worth re-harvesting with the code extractors.
CODE_DOMAINS = {"code", "security", "ontology"}


def _candidates(org: str, public_only: bool):
    rows = []
    for f in sorted(SOURCES.glob("src.*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        provider = d.get("provider", "") or ""
        if "/" not in provider:
            continue  # not an owner/repo provider (e.g. a plain vendor name)
        owner, repo = provider.split("/", 1)
        if org and owner != org:
            continue
        if d.get("domain") not in CODE_DOMAINS:
            continue
        access = d.get("access", {}) or {}
        policy = d.get("policy", {}) or {}
        is_public = access.get("auth") == "none" or policy.get("privacy_class") == "public"
        if public_only and not is_public:
            continue
        # repo_name = the sources[].repo logical name = src.<name> tail after any "__"
        name = f.name[len("src."):-len(".json")]
        repo_name = name.split("__", 1)[-1]
        # public-first, then aldphabetical, for a stable bounded prefix
        rows.append((0 if is_public else 1, f"{owner}/{repo}", repo_name))
    rows.sort()
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description="Select estate repos for the central catalog re-harvest.")
    p.add_argument("--org", default="SocioProphet", help="restrict to this GitHub org (default SocioProphet; empty = any).")
    p.add_argument("--public-only", action="store_true", help="only repos marked auth:none / privacy:public.")
    p.add_argument("--limit", type=int, default=0, help="cap the number of repos (0 = no cap).")
    args = p.parse_args()
    rows = _candidates(args.org, args.public_only)
    if args.limit > 0:
        rows = rows[: args.limit]
    for _pub, slug, repo_name in rows:
        sys.stdout.write(f"{slug}\t{repo_name}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
