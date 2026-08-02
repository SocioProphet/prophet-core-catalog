#!/usr/bin/env python3
"""Regex operational-dataset extractor (ds.regex-operational-dataset).

Emits ONE repo's contribution shard: one JSON record per DISTINCT regex pattern
found in <repo_path>, in the SAME record schema as
`datasets/regex-operational-dataset/regex-corpus.jsonl` (see SCHEMA.md), with
every source location scoped to <repo_name>. The catalog-side assembler merges
same-`id` records across repo shards (union sources, sum use_count, union flags).

    python3 extractors/extract_regex.py <repo_path> <repo_name> [--out FILE]

Read-only, stdlib-only, deterministic (idempotent on unchanged input).

Provider-reference policy (datasets/regex-operational-dataset/PROVIDER-REFERENCE-NOTE.md):
first-party provider/model routing allow-lists (gpt-4o|claude-3-5|gemini) and
leaked-key detectors (sk-ant-, ANTHROPIC_API_KEY, ghp_, AKIA…) are INCLUDED at
full fidelity and tagged `provider_reference: true` — they are our own security
and routing policy, not client materials. The only hard exclusion is *competitor
/ client marketing* brand words (COMPETITOR_WORDS), logged, never emitted.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_10, run  # noqa: E402

# ---------------------------------------------------------------------------
# Language surfaces we harvest regex literals from.
# ---------------------------------------------------------------------------
EXT_LANG = {
    ".py": "python",
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js",
    ".ts": "ts", ".tsx": "ts",
    ".rs": "rust",
    ".json": "jsonschema",   # only "pattern"/"patternProperties" keys are read
}

# ---------------------------------------------------------------------------
# Hard exclusion: competitor / client MARKETING brand words (word-bounded, ci).
# Credential-format + provider-routing detectors are NOT here — they are kept
# and tagged provider_reference (see module docstring + PROVIDER-REFERENCE-NOTE).
# ---------------------------------------------------------------------------
COMPETITOR_WORDS = [
    "palantir", "foundry", "databricks", "snowflake", "glean", "darktrace",
    "crowdstrike", "c3.ai", "scale ai", "abnormal", "baap", "liminal",
]
_COMPETITOR_RE = re.compile(
    "|".join(r"\b" + re.escape(w) + r"\b" for w in COMPETITOR_WORDS), re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Heuristic seed classifiers (category / risk_class) — curation seeds, not final
# governance labels, exactly as documented in SCHEMA.md.
# ---------------------------------------------------------------------------
_SECRET_HINTS = re.compile(
    r"sk-|AKIA|ghp_|gho_|github_pat|xox[baprs]-|-----BEGIN|api[_-]?key|secret|"
    r"bearer|authorization|token|private[_-]?key|password|passwd|credential",
    re.IGNORECASE,
)
_PII_HINTS = re.compile(
    r"@|e[-_]?mail|phone|ssn|social.?security|\bpii\b|passport|iban|credit.?card|"
    r"\d\{3\}|\bdob\b", re.IGNORECASE,
)
_URL_HINTS = re.compile(r"https?://|ftp://|www\.|\\\.[a-z]{2,}|://", re.IGNORECASE)
_PATH_HINTS = re.compile(r"\\/|/\$|\.\.|\bpath\b|\\\.\.\\|\.\./|~/", re.IGNORECASE)
_VERSION_HINTS = re.compile(r"\bv?\d\b|semver|\d\+\\\.\d|version|\bsha256\b|[a-f0-9]\{", re.IGNORECASE)
_VALIDATION_HINTS = re.compile(r"^\^|\$$|\{[0-9]", re.IGNORECASE)

# provider / model routing + leaked-key detectors -> provider_reference: true
_PROVIDER_REF = re.compile(
    r"sk-ant|sk-proj|anthropic|openai|\bgpt-?\d|claude|gemini|\bllama\b|mistral|"
    r"ollama|cohere|huggingface|bedrock|vertex|\bgroq\b|perplexity|deepseek|"
    r"ANTHROPIC_API_KEY|OPENAI_API_KEY|GEMINI_API_KEY|model[_-]?router",
    re.IGNORECASE,
)

# catastrophic-backtracking shapes (ReDoS suspects)
_REDOS = [
    re.compile(r"\([^)]*[+*]\)[+*]"),     # (…+)+  (…*)*  (…+)*  (…*)+
    re.compile(r"\(\?:[^)]*[+*]\)[+*]"),   # (?:…+)+
    re.compile(r"\(\\S\+\)\+"),            # (\S+)+
    re.compile(r"\(\.\*\)\*"),             # (.*)*
    re.compile(r"\([^)]*\|[^)]*\)[+*]"),   # alternation under outer quantifier
]


def classify_category(pattern: str) -> str:
    if _SECRET_HINTS.search(pattern):
        return "secret"
    if _URL_HINTS.search(pattern):
        return "url"
    if _PII_HINTS.search(pattern):
        return "pii"
    if _PATH_HINTS.search(pattern):
        return "path"
    if _VERSION_HINTS.search(pattern):
        return "version"
    if _VALIDATION_HINTS.search(pattern):
        return "validation"
    return "other"


def classify_risk(pattern: str, category: str) -> str:
    if category == "secret" or _SECRET_HINTS.search(pattern):
        return "catastrophic"
    if re.search(r"rm\s|--force|drop\s+table|\.\.\/|path.?travers|\$\(|`", pattern, re.IGNORECASE):
        return "catastrophic"
    if category in {"pii", "path", "url"}:
        return "sensitive"
    return "benign"


def is_redos(pattern: str) -> bool:
    return any(rx.search(pattern) for rx in _REDOS)


def is_provider_ref(pattern: str) -> bool:
    return bool(_PROVIDER_REF.search(pattern))


def is_competitor(pattern: str) -> bool:
    return bool(_COMPETITOR_RE.search(pattern))


# ---------------------------------------------------------------------------
# Per-language literal scanners. Each yields (pattern, flags, lineno).
# These are deliberately conservative: over-matching is worse than missing an
# exotic literal, and category/risk are seeds anyway.
# ---------------------------------------------------------------------------
_PY_RE_CALL = re.compile(
    r"""re(?:gex)?\.(?:compile|match|search|fullmatch|findall|finditer|sub|split)\s*\(\s*
        r?(['"])(?P<body>(?:\\.|(?!\1).)*?)\1""",
    re.VERBOSE,
)
_JS_LITERAL = re.compile(r"(?<![A-Za-z0-9_$)\]/])/(?P<body>(?:\\.|\[[^\]]*\]|[^/\n\\])+?)/(?P<flags>[gimsuy]*)")
_JS_NEW_REGEXP = re.compile(r"""new\s+RegExp\(\s*(['"])(?P<body>(?:\\.|(?!\1).)*?)\1(?:\s*,\s*(['"])(?P<flags>[gimsuy]*)\3)?""")
_RUST_REGEX = re.compile(r"""Regex::new\(\s*r?(?:#*)"(?P<body>(?:\\.|[^"])*?)"(?:#*)\)""")
_JSON_PATTERN = re.compile(r'"pattern(?:Properties)?"\s*:\s*"(?P<body>(?:\\.|[^"])*?)"')


def scan_python(text: str):
    for m in _PY_RE_CALL.finditer(text):
        yield m.group("body"), "", text.count("\n", 0, m.start()) + 1


def scan_js(text: str):
    for m in _JS_LITERAL.finditer(text):
        body = m.group("body")
        if body.strip() in ("", "*", "="):
            continue
        yield body, "".join(sorted(set(m.group("flags") or ""))), text.count("\n", 0, m.start()) + 1
    for m in _JS_NEW_REGEXP.finditer(text):
        yield m.group("body"), "".join(sorted(set(m.group("flags") or ""))), text.count("\n", 0, m.start()) + 1


def scan_rust(text: str):
    for m in _RUST_REGEX.finditer(text):
        yield m.group("body"), "", text.count("\n", 0, m.start()) + 1


def scan_jsonschema(text: str):
    # Only real JSON Schemas carry regex in "pattern"; cheap guard against huge
    # unrelated JSON blobs.
    if '"pattern"' not in text and '"patternProperties"' not in text:
        return
    for m in _JSON_PATTERN.finditer(text):
        yield m.group("body"), "", text.count("\n", 0, m.start()) + 1


SCANNERS = {
    "python": scan_python,
    "js": scan_js,
    "ts": scan_js,
    "rust": scan_rust,
    "jsonschema": scan_jsonschema,
}


def _decode(raw: str, lang: str) -> str:
    """Turn a host-literal body into the raw regex source (mirror SCHEMA.md)."""
    if lang == "python":
        # Bodies were captured from r"" or "" literals; keep backslashes literal.
        return raw
    return raw


def extract(repo_path: str, repo_name: str) -> list[dict]:
    # id -> aggregated record
    agg: dict[str, dict] = {}
    excluded = 0
    for path in iter_files(repo_path, EXT_LANG):
        lang = EXT_LANG[Path(path).suffix.lower()]
        text = read_text(path)
        if text is None:
            continue
        relpath = rel(repo_path, path)
        for raw, flags, lineno in SCANNERS[lang](text):
            pattern = _decode(raw, lang)
            if not pattern or len(pattern) > 1000:
                continue
            if is_competitor(pattern):
                excluded += 1
                continue
            pid = "rx-" + sha1_10(pattern)
            rec = agg.get(pid)
            src = {"repo": repo_name, "file": relpath, "line": lineno}
            if rec is None:
                category = classify_category(pattern)
                agg[pid] = {
                    "id": pid,
                    "pattern": pattern,
                    "flags": flags,
                    "lang": lang,
                    "intent": "",
                    "category": category,
                    "sources": [src],
                    "use_count": 1,
                    "risk_class": classify_risk(pattern, category),
                    "redos_suspect": is_redos(pattern),
                    "competitor_clean": True,
                    "provider_reference": is_provider_ref(pattern),
                }
            else:
                rec["sources"].append(src)
                rec["use_count"] += 1
                rec["flags"] = "".join(sorted(set(rec["flags"]) | set(flags)))
    # Stable ordering inside each record's sources[] for idempotency.
    for rec in agg.values():
        rec["sources"].sort(key=lambda s: (s["repo"], s["file"], s["line"]))
    if excluded:
        sys.stderr.write(f"[extract_regex] {repo_name}: excluded {excluded} competitor-marketing hit(s)\n")
    return list(agg.values())


if __name__ == "__main__":
    raise SystemExit(run("regex-operational-dataset", extract))
