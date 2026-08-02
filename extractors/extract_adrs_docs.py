#!/usr/bin/env python3
"""adrs-docs extractor (ds.adrs-docs).

Emits ONE repo's contribution shard covering BOTH primary files of the dataset:
Architecture Decision Records (`adr.*` ids -> datasets/adrs-docs/adrs.jsonl) and key
load-bearing docs (`doc.*` ids -> datasets/adrs-docs/docs.jsonl), in the SAME record
schemas as those files (see SCHEMA.md). The two record families are told apart by id
prefix (`adr.` vs `doc.`), which is how the harvest assembler routes them back.

    python3 extractors/extract_adrs_docs.py <repo_path> <repo_name> [--out FILE]

Read-only, stdlib-only, deterministic.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, run  # noqa: E402

DOCS_CAP = 40

_STATUS_SYNONYMS = {
    "approved": "accepted", "adopted": "accepted", "active": "accepted", "final": "accepted",
    "draft": "proposed", "wip": "proposed",
    "retired": "deprecated", "obsolete": "deprecated",
    "declined": "rejected", "withdrawn": "rejected", "abandoned": "rejected",
}
_STATUS_CANON = {"proposed", "accepted", "superseded", "deprecated", "rejected"}
_DOC_SIGNALS = ("design", "architect", "spec", "governance", "rfc", "contract", "invariant",
                "charter", "threat", "security", "runbook", "overview", "protocol", "schema",
                "proposal", "roadmap", "decision", "policy", "conformance", "ontology",
                "glossary", "principles", "whitepaper")
_ADR_FILE = re.compile(r"(?:^|[/_-])adr[-_ ]?(\d{1,4})", re.IGNORECASE)
_NUM_FILE = re.compile(r"^(\d{1,4})[-_]")


def _slug(path: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")


def _norm_status(raw: str) -> str:
    s = raw.strip().lower().split()[0] if raw.strip() else ""
    s = _STATUS_SYNONYMS.get(s, s)
    return s if s in _STATUS_CANON else "unknown"


def _find_status(text: str) -> str:
    fm = re.search(r"^status:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    if fm:
        return _norm_status(fm.group(1))
    sec = re.search(r"^#{1,4}\s*status\s*\n+\s*([^\n]+)", text, re.IGNORECASE | re.MULTILINE)
    if sec:
        return _norm_status(re.sub(r"^[-*\s]+", "", sec.group(1)))
    line = re.search(r"^\s*[-*]?\s*status\s*[:|]\s*([A-Za-z]+)", text, re.IGNORECASE | re.MULTILINE)
    if line:
        return _norm_status(line.group(1))
    tbl = re.search(r"\|\s*status\s*\|\s*([A-Za-z]+)", text, re.IGNORECASE)
    if tbl:
        return _norm_status(tbl.group(1))
    return "unknown"


def _title(text: str, fallback: str) -> str:
    fm = re.search(r"^title:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    if fm:
        return fm.group(1).strip().strip("'\"")
    h1 = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if h1:
        return h1.group(1).strip()
    return fallback


def _first_para(text: str) -> str:
    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)  # strip front-matter
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block or block.startswith("#") or block.startswith("|") or block.startswith("```"):
            continue
        return " ".join(block.split())[:200]
    return ""


def _is_adr(relpath: str, text: str) -> bool:
    low = relpath.lower()
    name = os.path.basename(low)
    if "template" in name or name in ("readme.md", "index.md"):
        return False
    in_adr_dir = bool(re.search(r"(^|/)(adr|adrs|decisions)(/|$)", low)) or "docs/adr" in low
    named = bool(_ADR_FILE.search(name)) or (bool(_NUM_FILE.match(name)) and in_adr_dir)
    if named or in_adr_dir:
        return True
    has_status = re.search(r"^status:", text, re.IGNORECASE | re.MULTILINE) or \
        re.search(r"^#{1,4}\s*status", text, re.IGNORECASE | re.MULTILINE)
    has_decision = re.search(r"^#{1,4}\s*(decision|context)", text, re.IGNORECASE | re.MULTILINE)
    return bool(has_status and has_decision)


def _adr_record(repo: str, relpath: str, text: str) -> dict:
    name = os.path.basename(relpath)
    m = _ADR_FILE.search(name) or _NUM_FILE.match(name) or _ADR_FILE.search(relpath)
    number = f"{int(m.group(1)):04d}" if m else None
    sup = re.search(r"supersedes\s+adr[-\s]?(\d{1,4})", text, re.IGNORECASE)
    supby = re.search(r"(?:superseded|replaced)\s+by\s+adr[-\s]?(\d{1,4})", text, re.IGNORECASE)
    date = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    key = number if number else _slug(Path(name).stem)
    return {
        "id": f"adr.{repo.lower()}.{key}",
        "adr_number": number,
        "title": _title(text, name),
        "status": _find_status(text),
        "repo": repo,
        "path": relpath,
        "supersedes": (f"{int(sup.group(1)):04d}" if sup else None),
        "superseded_by": (f"{int(supby.group(1)):04d}" if supby else None),
        "date": (date.group(1) if date else None),
        "intent": _first_para(text),
    }


def _doc_kind(relpath: str, title: str) -> str:
    blob = (relpath + " " + title).lower()
    if os.path.basename(relpath).lower() == "readme.md":
        return "readme"
    for kw, kind in (("govern", "governance"), ("charter", "governance"), ("policy", "governance"),
                     ("invariant", "governance"), ("compliance", "governance"), ("wall", "governance"),
                     ("authz", "governance"), ("spec", "spec"), ("contract", "spec"), ("schema", "spec"),
                     ("protocol", "spec"), ("api", "spec"), ("conformance", "spec"), ("rfc", "rfc"),
                     ("proposal", "rfc"), ("design", "design"), ("architect", "design"),
                     ("overview", "design"), ("model", "design"), ("topology", "design")):
        if kw in blob:
            return kind
    return "other"


def extract(repo_path: str, repo_name: str) -> list[dict]:
    adrs: list[dict] = []
    docs: list[dict] = []
    seen_adr_ids: dict[str, int] = {}
    for path in iter_files(repo_path, {".md", ".markdown"}):
        relpath = rel(repo_path, path)
        text = read_text(path)
        if text is None:
            continue
        if _is_adr(relpath, text):
            rec = _adr_record(repo_name, relpath, text)
            n = seen_adr_ids.get(rec["id"], 0) + 1
            seen_adr_ids[rec["id"]] = n
            if n > 1:
                rec["id"] = f"{rec['id']}-{n}"
            adrs.append(rec)
            continue
        # key-doc candidate: top-level README always, else docs/** hitting the signal filter
        low = relpath.lower()
        is_readme = low == "readme.md"
        under_docs = low.startswith("docs/")
        title = _title(text, os.path.basename(relpath))
        signal = any(sig in (low + " " + title.lower()) for sig in _DOC_SIGNALS)
        if is_readme or (under_docs and signal):
            docs.append({
                "id": f"doc.{repo_name.lower()}.{_slug(relpath)}",
                "title": title,
                "kind": _doc_kind(relpath, title),
                "repo": repo_name,
                "path": relpath,
                "intent": _first_para(text),
            })
    docs.sort(key=lambda r: r["id"])
    docs = docs[:DOCS_CAP]
    adrs.sort(key=lambda r: r["id"])
    return adrs + docs


if __name__ == "__main__":
    raise SystemExit(run("adrs-docs", extract))
