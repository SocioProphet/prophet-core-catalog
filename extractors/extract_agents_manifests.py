#!/usr/bin/env python3
"""agents-manifests extractor (ds.agents-manifests).

Emits ONE repo's contribution shard: one record per AGENT artifact in <repo_path> —
agent manifests / registry specs, prophet-mesh & blueprint YAML agent defs, Claude
Markdown subagents (YAML frontmatter), MCP servers (`.mcp*.json`), A2A cards, and
capability/tool-grant declarations — in the SAME record schema as
`datasets/agents-manifests/agents.jsonl` (see SCHEMA.md), including the `connections`
sub-graph and the agent-plane / registry / standard substrate refs.

    python3 extractors/extract_agents_manifests.py <repo_path> <repo_name> [--out FILE]

`id = ag-<sha1[:12] of repo::path::name>` — stable + idempotent (deterministic per
declaration site). Read-only, stdlib-only.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_hex, run  # noqa: E402

# substrate binding: presence of these repo names anywhere in the artifact -> ref
_PLANE = re.compile(r"agentplane|prophet-mesh", re.IGNORECASE)
_REGISTRY = re.compile(r"agent-registry", re.IGNORECASE)
_STANDARD = re.compile(r"socioprophet-agent-standards|agent-standard", re.IGNORECASE)
_CAP_TOKEN = re.compile(r"(surface://|tool://|control:|sefirot:|grant://)[\w:./@-]+")


def _agent_id(repo: str, path: str, name: str) -> str:
    return "ag-" + sha1_hex(f"{repo}::{path}::{name}", 12)


def _refs(repo: str, path: str, name: str, kind: str, caps, auth, intent, conns) -> dict:
    blob = json.dumps([caps, auth, intent, conns])
    return {
        "id": _agent_id(repo, path, name),
        "name": name, "kind": kind, "repo": repo, "path": path,
        "declared_capabilities": caps, "authority_refs": auth, "intent": intent,
        "connections": conns,
        "agent_plane_ref": ("src.prophet-mesh" if "prophet-mesh" in blob.lower()
                            else ("src.agentplane" if "agentplane" in blob.lower() else None)),
        "registry_ref": ("src.agent-registry" if _REGISTRY.search(blob) else None),
        "standard_ref": ("src.socioprophet-agent-standards" if _STANDARD.search(blob) else None),
    }


def _empty_conns() -> dict:
    return {"skills": [], "tools": [], "prompts": [], "preferences": [], "personas": []}


def _md_frontmatter(text: str) -> dict | None:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return None
    fm: dict = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if km:
            fm[km.group(1).strip().lower()] = km.group(2).strip().strip("'\"")
    return fm


def _from_md_subagent(repo, relpath, text, prefs) -> dict | None:
    fm = _md_frontmatter(text)
    if not fm or "name" not in fm or "description" not in fm:
        return None
    name = fm["name"]
    tools = [t.strip() for t in re.split(r"[,\s]+", fm.get("tools", "")) if t.strip()]
    conns = _empty_conns()
    conns["tools"] = tools
    conns["prompts"] = [relpath]
    conns["preferences"] = list(prefs)
    caps = tools[:]
    auth = [a.strip() for a in re.split(r"[,\s]+", fm.get("model", "")) if a.strip()]
    return _refs(repo, relpath, name, "claude-subagent", caps, auth, fm["description"][:200], conns)


def _from_mcp_json(repo, relpath, obj, prefs) -> list[dict]:
    out = []
    servers = obj.get("mcpServers") or obj.get("servers") or {}
    if isinstance(servers, dict):
        for sname, spec in servers.items():
            caps = []
            if isinstance(spec, dict):
                cmd = spec.get("command")
                if cmd:
                    caps = [f"cmd:{cmd}"]
            conns = _empty_conns()
            conns["tools"] = [f"mcp://{repo}/{sname}"]
            conns["preferences"] = list(prefs)
            out.append(_refs(repo, relpath, sname, "mcp-server", caps, [],
                             f"MCP server '{sname}' declared in {os.path.basename(relpath)}", conns))
    return out


# Top-level keys that mark a JSON as an agent artifact (not just any config that
# happens to mention "a2a" in a vendored source name).
_AGENT_KEYS = {"agentSpec", "agent_spec", "agentManifest", "declared_capabilities",
               "capabilities", "tool_grants", "toolGrants", "skillManifest", "a2a",
               "agent", "agent_id", "coordinate_vector", "sefirot"}
# Catalog's own source/dataset manifests must never be mistaken for agents.
_CATALOG_MANIFEST_KEYS = {"schema", "lineage", "quality", "access", "provenance", "freshness"}


def _looks_agentish(relpath: str, obj: dict) -> bool:
    low = relpath.lower()
    base = os.path.basename(low)
    if base == "manifest.json" and _CATALOG_MANIFEST_KEYS & set(obj):
        return False
    sid = str(obj.get("id", ""))
    if sid.startswith(("ds.", "src.")):
        return False
    if "/agents/" in ("/" + low) or low.startswith("agents/"):
        return True
    if any(h in base for h in ("agent", "subagent", "a2a", "capabilit", "tool-grant",
                               "toolgrant", "blueprint", "skillmanifest", "coordinate-vector",
                               "persona")):
        return True
    return bool(_AGENT_KEYS & set(obj))


def _from_json_agent(repo, relpath, obj) -> dict | None:
    if not isinstance(obj, dict) or not _looks_agentish(relpath, obj):
        return None
    name = obj.get("id") or obj.get("agent_id") or obj.get("name") or obj.get("agent")
    if not isinstance(name, str) or not name:
        return None
    blob = json.dumps(obj)
    kind = "other"
    low = json.dumps(obj).lower()
    base = os.path.basename(relpath).lower()
    if "agentspec" in low or "agentmanifest" in low or "agentregistration" in low or base.endswith("agent-spec.example.json"):
        kind = "agent-manifest"
    elif "toolgrant" in low or "tool-grants" in base or "capabilitydeclaration" in low:
        kind = "capability-decl"
    elif "a2a" in low or "skillmanifest" in low or "bundle" in low:
        kind = "a2a-card"
    elif "coordinatevector" in low or "sefirot" in low:
        kind = "other"
    else:
        if not ("capabilit" in low or "surface://" in low or "tool://" in low or "agent" in base):
            return None
    caps = sorted(set(_CAP_TOKEN.findall(blob)))
    # pull declared capability list if present
    for k in ("capabilities", "declared_capabilities", "surfaces"):
        v = obj.get(k)
        if isinstance(v, list):
            caps = sorted(set(caps) | {str(x) for x in v if isinstance(x, str)})
    auth = sorted(set(_CAP_TOKEN.findall(blob)))
    for k in ("authority", "authority_refs", "grants", "policy_refs", "evidence"):
        v = obj.get(k)
        if isinstance(v, list):
            auth = sorted(set(auth) | {str(x) for x in v if isinstance(x, str)})
    conns = _empty_conns()
    conns["tools"] = sorted({t for t in _CAP_TOKEN.findall(blob) if t.startswith("tool://")})
    intent = str(obj.get("description") or obj.get("intent") or obj.get("summary") or "")[:200]
    if not intent:
        intent = f"{kind.replace('-', ' ')} ({name})"
    return _refs(repo, relpath, name, kind, caps, auth, intent, conns)


def _from_yaml_blueprint(repo, relpath, text) -> dict | None:
    if "capabilities:" not in text:
        return None
    nm = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
    name = nm.group(1).strip().strip("'\"") if nm else Path(relpath).stem
    cap_block = re.search(r"^capabilities:\s*\n((?:\s*-\s*.+\n?)+)", text, re.MULTILINE)
    caps = re.findall(r"-\s*([A-Za-z0-9_./:-]+)", cap_block.group(1)) if cap_block else []
    if not caps:
        return None
    auth = sorted(set(re.findall(r"(control:[\w-]+)", text)))
    desc = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
    conns = _empty_conns()
    conns["prompts"] = [relpath]
    intent = (desc.group(1).strip() if desc else "")[:200]
    return _refs(repo, relpath, name, "blueprint", caps, auth, intent, conns)


def extract(repo_path: str, repo_name: str) -> list[dict]:
    records: list[dict] = []
    prefs = [p for p in ("AGENTS.md", "CLAUDE.md") if os.path.isfile(os.path.join(repo_path, p))]
    for path in iter_files(repo_path, {".md", ".json", ".yaml", ".yml"}):
        relpath = rel(repo_path, path)
        base = os.path.basename(relpath).lower()
        text = read_text(path)
        if text is None:
            continue
        ext = Path(path).suffix.lower()
        if ext == ".md":
            low = relpath.lower()
            if "/agents/" in ("/" + low) or low.startswith("agents/") or "subagent" in low:
                r = _from_md_subagent(repo_name, relpath, text, prefs)
                if r:
                    records.append(r)
        elif ext == ".json":
            try:
                obj = json.loads(text)
            except Exception:
                continue
            if base.startswith(".mcp") or base == "mcp.json" or base.endswith(".mcp.json") or \
               (isinstance(obj, dict) and ("mcpServers" in obj or "servers" in obj)):
                records += _from_mcp_json(repo_name, relpath, obj, prefs)
            else:
                r = _from_json_agent(repo_name, relpath, obj)
                if r:
                    records.append(r)
        else:  # yaml
            low = relpath.lower()
            if "/agents/" in ("/" + low) or low.startswith("agents/") or "blueprint" in low:
                r = _from_yaml_blueprint(repo_name, relpath, text)
                if r:
                    records.append(r)
    # dedup by id (same declaration site)
    agg: dict[str, dict] = {}
    for r in records:
        agg.setdefault(r["id"], r)
    return sorted(agg.values(), key=lambda r: r["id"])


if __name__ == "__main__":
    raise SystemExit(run("agents-manifests", extract))
