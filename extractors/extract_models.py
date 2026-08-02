#!/usr/bin/env python3
"""models extractor (ds.models).

Emits ONE repo's contribution shard: one record per distinct ML/AI MODEL the repo
routes to / runs / trains / governs, in the SAME record schema as
`datasets/models/models.jsonl` (see SCHEMA.md). First-party provider model ids that
appear in our own routing/config are INCLUDED at full fidelity and tagged
`provider_reference: true` (see PROVIDER-REFERENCE-NOTE.md).

    python3 extractors/extract_models.py <repo_path> <repo_name> [--out FILE]

`id = mdl-<sha1[:10] of provider/name>`, so the same model referenced across N repos
collapses to ONE record whose `used_by[]` unions every referencing repo — that
cross-repo union is done by the harvest assembler (merge: "union"); this per-repo
shard sets `used_by = [repo_name]`. Read-only, stdlib-only, deterministic.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_hex, run  # noqa: E402

# Models are harvested from CONFIG / code surfaces (routing tables, manifests), NOT
# prose docs — scanning Markdown yields bare family words ("deepseek") from sentences.
CONFIG_EXTS = {".json", ".yaml", ".yml", ".py", ".ts", ".tsx", ".js", ".toml"}


# Words that follow a provider prefix in code/prose but are NOT model releases.
_NOT_MODEL_TAIL = {"subagent", "agent", "agents", "tool", "tools", "code", "coder",
                   "guard", "config", "client", "model", "models", "api", "sdk"}


def _is_concrete_model(name: str) -> bool:
    """Keep real model IDs (versioned / tagged / namespaced / governed refs); drop bare
    family words like 'deepseek' / 'llama' and provider-prefixed non-models like
    'claude-subagent' that appear in prose or code."""
    if name.startswith("model://"):
        return True
    tail = re.split(r"[-/:]", name)[-1].lower()
    if tail in _NOT_MODEL_TAIL:
        return False
    if any(c.isdigit() for c in name) or ":" in name or "/" in name:
        return True
    return "-" in name and len(name) > 10  # e.g. nomic-embed-text

# A model token: an explicit model:// governed ref, or a provider-branded model id.
_MODEL_TOKEN = re.compile(
    r"""(model://[\w./@:-]+)"""
    r"""|\b((?:gpt-[\w.]+|o[134](?:-[\w.]+)?|text-embedding-[\w.-]+|davinci-\d+)"""
    r"""|(?:claude-[\w.-]+)"""
    r"""|(?:gemini-[\w.-]+|gemma-?[\w.:-]*|shieldgemma[\w.:-]*)"""
    r"""|(?:llama[\w.:-]*|codellama[\w.:-]*)"""
    r"""|(?:qwen[\w.:-]*)"""
    r"""|(?:deepseek[\w.:/-]*)"""
    r"""|(?:mistral[\w.:-]*|mixtral[\w.:-]*)"""
    r"""|(?:nomic-embed[\w.-]*)"""
    r"""|(?:sentence-transformers/[\w.-]+)"""
    r"""|(?:phi-?\d[\w.:-]*))\b""",
    re.IGNORECASE,
)

_PROVIDER = [
    ("model://socioprophet", "socioprophet"), ("model://", "socioprophet"),
    ("gpt-", "openai"), ("o1", "openai"), ("o3", "openai"), ("o4", "openai"),
    ("text-embedding", "openai"), ("davinci", "openai"),
    ("claude", "anthropic"),
    ("gemini", "google"), ("gemma", "google"), ("shieldgemma", "google"),
    ("codellama", "meta"), ("llama", "meta"),
    ("qwen", "qwen"), ("deepseek", "deepseek"),
    ("mixtral", "mistral"), ("mistral", "mistral"),
    ("nomic", "nomic"), ("sentence-transformers", "sentence-transformers"),
    ("phi", "microsoft"),
]
THIRD_PARTY = {"openai", "anthropic", "google", "meta", "qwen", "deepseek", "mistral",
               "nomic", "sentence-transformers", "microsoft"}


def _provider(name: str) -> str:
    low = name.lower()
    for pref, prov in _PROVIDER:
        if low.startswith(pref):
            return prov
    return "local"


def _role(name: str) -> str:
    low = name.lower()
    if low.startswith("model://"):
        return "governed"
    if "embed" in low or low.startswith("sentence-transformers") or low.startswith("text-embedding"):
        return "embedding"
    if "guard" in low or "shield" in low:
        return "judge"
    return "routing-target"


def extract(repo_path: str, repo_name: str) -> list[dict]:
    # governance signal: does this repo carry a governance ledger / weights manifest?
    has_ledger = False
    for path in iter_files(repo_path, {".json", ".yaml", ".yml", ".md"}):
        b = os.path.basename(path).lower()
        if "governance-ledger" in b or "weights_manifest" in b or "weights-manifest" in b:
            has_ledger = True
            break

    agg: dict[str, dict] = {}
    for path in iter_files(repo_path, CONFIG_EXTS):
        relpath = rel(repo_path, path)
        text = read_text(path)
        if text is None:
            continue
        low_path = relpath.lower()
        is_router = ("router" in low_path or "mesh" in low_path or "routing" in low_path
                     or "model" in low_path)
        for m in _MODEL_TOKEN.finditer(text):
            name = (m.group(1) or m.group(2) or "").strip().strip(".,:;)\"'")
            if not name or len(name) > 120 or not _is_concrete_model(name):
                continue
            provider = _provider(name)
            role = _role(name)
            if role == "governed":
                governed = True
            else:
                governed = has_ledger and is_router
            pid = "mdl-" + sha1_hex(f"{provider}/{name}", 10)
            if pid in agg:
                continue
            agg[pid] = {
                "id": pid, "name": name, "provider": provider, "role": role,
                "repo": repo_name, "path": relpath, "used_by": [repo_name],
                "governed": governed,
                "provider_reference": provider in THIRD_PARTY,
                "intent": f"{provider} model referenced in {os.path.basename(relpath)}",
            }
    return sorted(agg.values(), key=lambda r: r["id"])


if __name__ == "__main__":
    raise SystemExit(run("models", extract))
