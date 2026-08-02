#!/usr/bin/env python3
"""services-endpoints extractor (ds.services-endpoints).

Emits ONE repo's contribution shard: one record per SERVICE / ENDPOINT surface in
<repo_path> — k8s Service/Ingress/Deployment/StatefulSet/DaemonSet/Rollout, ArgoCD
Application, docker-compose services, gRPC services (.proto), and HTTP APIs
(FastAPI/Flask decorators, Express/Fastify routes, OpenAPI/Swagger paths) — in the
SAME record schema as `datasets/services-endpoints/services.jsonl` (see SCHEMA.md).

    python3 extractors/extract_services_endpoints.py <repo_path> <repo_name> [--out FILE]

`id = svc-<sha1[:10] of kind|repo|path|name>` — stable, idempotent, byte-compatible
with the central harvest. YAML is read with a deliberately small stdlib line/document
scanner (no PyYAML dependency) so it runs inside any repo with a stock Python 3.

Read-only, stdlib-only, deterministic.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, rel, sha1_hex, run  # noqa: E402

JS_CAP, OPENAPI_CAP = 200, 300


def _svc_id(kind: str, repo: str, path: str, name: str) -> str:
    return "svc-" + sha1_hex(f"{kind}|{repo}|{path}|{name}", 10)


def _meta_name(doc: str) -> str:
    m = re.search(r"^metadata:\s*$", doc, re.MULTILINE)
    if m:
        tail = doc[m.end():]
        nm = re.search(r"^\s+name:\s*(.+)$", tail, re.MULTILINE)
        if nm:
            return nm.group(1).strip().strip("'\"")
    nm = re.search(r"^\s{0,4}name:\s*(.+)$", doc, re.MULTILINE)
    return nm.group(1).strip().strip("'\"") if nm else ""


def _kind_of(doc: str) -> str:
    m = re.search(r"^kind:\s*(.+)$", doc, re.MULTILINE)
    return m.group(1).strip().strip("'\"") if m else ""


def _k8s_records(repo: str, relpath: str, text: str) -> list[dict]:
    out: list[dict] = []
    for doc in re.split(r"(?m)^---\s*$", text):
        if "kind:" not in doc:
            continue
        k = _kind_of(doc)
        name = _meta_name(doc)
        if not name:
            continue
        api = re.search(r"^apiVersion:\s*(.+)$", doc, re.MULTILINE)
        api_v = api.group(1).strip() if api else ""
        if k == "Service":
            eps = []
            for pm in re.finditer(r"^\s*-?\s*port:\s*(\d+)", doc, re.MULTILINE):
                seg = doc[pm.start():pm.start() + 200]
                proto = (re.search(r"protocol:\s*(\w+)", seg) or [None, "TCP"])[1]
                tgt = re.search(r"targetPort:\s*(\S+)", seg)
                ep = f"{proto} {pm.group(1)}"
                if tgt:
                    ep += f"->{tgt.group(1).strip()}"
                eps.append(ep)
            typ = (re.search(r"^\s+type:\s*(\w+)", doc, re.MULTILINE) or [None, "ClusterIP"])[1]
            out.append(_rec("k8s-service", repo, relpath, name, sorted(set(eps)),
                            [], f"k8s Service ({typ})"))
        elif k == "Ingress":
            eps = []
            hosts = re.findall(r"^\s*-?\s*host:\s*(.+)$", doc, re.MULTILINE)
            backends = re.findall(r"(?:serviceName|name):\s*([\w.-]+)", doc)
            host = hosts[0].strip().strip("'\"") if hosts else ""
            paths = re.findall(r"^\s*-?\s*path:\s*(.+)$", doc, re.MULTILINE)
            be = backends[0] if backends else ""
            for p in (paths or [""]):
                eps.append(f"{host}{p.strip()} -> {be}".strip())
            out.append(_rec("ingress", repo, relpath, name, sorted(set(eps)),
                            [be] if be else [], "Kubernetes Ingress (externally-exposed)"))
        elif k in ("Deployment", "StatefulSet", "DaemonSet", "Rollout"):
            eps = []
            for cm in re.finditer(r"containerPort:\s*(\d+)", doc):
                eps.append(f"{name}:{cm.group(1)}")
            out.append(_rec("deployment", repo, relpath, name, sorted(set(eps)),
                            [], f"k8s {k}"))
        elif k == "Application" and "argoproj.io" in api_v:
            ns = re.search(r"namespace:\s*([\w-]+)", doc)
            repo_url = re.search(r"repoURL:\s*(\S+)", doc)
            ns_v = ns.group(1) if ns else ""
            intent = "ArgoCD Application"
            if repo_url:
                intent += f" -> {repo_url.group(1).strip()}"
            if ns_v:
                intent += f" (namespace {ns_v})"
            out.append(_rec("argocd-app", repo, relpath, name,
                            [f"ns={ns_v}"] if ns_v else [], [], intent))
    return out


def _compose_records(repo: str, relpath: str, text: str) -> list[dict]:
    out: list[dict] = []
    m = re.search(r"^services:\s*$", text, re.MULTILINE)
    if not m:
        return out
    body = text[m.end():]
    # top-level service keys are indented exactly 2 spaces under services:
    svc_iter = list(re.finditer(r"^  ([A-Za-z0-9_.-]+):\s*$", body, re.MULTILINE))
    for i, sm in enumerate(svc_iter):
        name = sm.group(1)
        seg = body[sm.end(): svc_iter[i + 1].start() if i + 1 < len(svc_iter) else len(body)]
        ports = [p.strip().strip("'\"") for p in re.findall(r"-\s*['\"]?([\d.:]+:[\d]+)['\"]?", seg)]
        depends = re.search(r"depends_on:\s*(.+?)(?:\n\S|\Z)", seg, re.DOTALL)
        dep_list = re.findall(r"-\s*([A-Za-z0-9_.-]+)", depends.group(1)) if depends else []
        image = re.search(r"image:\s*(\S+)", seg)
        build = re.search(r"build:\s*(.+)", seg)
        intent = "compose service"
        if build:
            intent += f" build={build.group(1).strip()}"
        elif image:
            intent += f" image={image.group(1).strip()}"
        if dep_list:
            intent += f" depends_on={dep_list}"
        out.append(_rec("compose-service", repo, relpath, name, sorted(set(ports)),
                        [f"compose:{d}" for d in dep_list], intent))
    return out


def _grpc_records(repo: str, relpath: str, text: str) -> list[dict]:
    out: list[dict] = []
    pkg = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.MULTILINE)
    pkg_v = pkg.group(1) if pkg else ""
    for sm in re.finditer(r"^\s*service\s+(\w+)\s*\{", text, re.MULTILINE):
        depth, i = 1, sm.end()
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[sm.end():i]
        methods = re.findall(r"\brpc\s+(\w+)", body)
        name = f"{pkg_v}.{sm.group(1)}" if pkg_v else sm.group(1)
        eps = [f"rpc {m}" for m in methods]
        out.append(_rec("grpc-service", repo, relpath, name, eps, [],
                        f"gRPC service ({len(methods)} methods)"))
    return out


_PY_ROUTE = re.compile(r"@(\w+)\.(get|post|put|patch|delete|websocket|api_route|route)\s*\(\s*['\"]([^'\"]+)")
_JS_ROUTE = re.compile(r"\b(\w+)\.(get|post|put|patch|delete|use|all|ws)\s*\(\s*['\"]([^'\"]+)")


def _http_records(repo: str, relpath: str, text: str, ext: str) -> list[dict]:
    out: list[dict] = []
    if ext == ".py":
        routes = []
        app = ""
        for m in _PY_ROUTE.finditer(text):
            app = app or m.group(1)
            verb = "WS" if m.group(2) == "websocket" else ("ANY" if m.group(2) in ("route", "api_route") else m.group(2).upper())
            routes.append(f"{verb} {m.group(3)}")
        if routes:
            framework = "fastapi" if ("FastAPI" in text or "APIRouter" in text) else ("flask" if "Flask" in text else "python")
            name = Path(relpath).stem
            out.append(_rec("http-api", repo, relpath, name, sorted(set(routes)), [],
                            f"{framework} HTTP API ({len(set(routes))} routes)"))
    elif ext in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"):
        routes = []
        for m in _JS_ROUTE.finditer(text):
            path = m.group(3)
            if not path.startswith("/"):
                continue
            verb = "MOUNT" if m.group(2) == "use" else ("ANY" if m.group(2) == "all" else ("WS" if m.group(2) == "ws" else m.group(2).upper()))
            routes.append(f"{verb} {path}")
        routes = sorted(set(routes))[:JS_CAP]
        if routes:
            name = Path(relpath).stem
            fw = "express" if "express" in text.lower() else ("fastify" if "fastify" in text.lower() else "node")
            out.append(_rec("http-api", repo, relpath, name, routes, [],
                            f"{fw} HTTP API ({len(routes)} routes)"))
    return out


def _rec(kind, repo, path, name, endpoints, consumers, intent) -> dict:
    return {
        "kind": kind, "name": name, "repo": repo, "path": path,
        "endpoints": endpoints, "intent": intent, "consumers": consumers,
        "id": _svc_id(kind, repo, path, name),
    }


def extract(repo_path: str, repo_name: str) -> list[dict]:
    records: list[dict] = []
    for path in iter_files(repo_path, {".yaml", ".yml", ".proto", ".py", ".js", ".jsx",
                                       ".mjs", ".cjs", ".ts", ".tsx"}):
        relpath = rel(repo_path, path)
        text = read_text(path)
        if text is None:
            continue
        ext = Path(path).suffix.lower()
        base = os.path.basename(relpath).lower()
        if ext in (".yaml", ".yml"):
            if base.startswith("docker-compose") or base == "compose.yaml" or base == "compose.yml":
                records += _compose_records(repo_name, relpath, text)
            if "kind:" in text and "apiVersion:" in text:
                records += _k8s_records(repo_name, relpath, text)
        elif ext == ".proto":
            records += _grpc_records(repo_name, relpath, text)
        else:
            records += _http_records(repo_name, relpath, text, ext)

    # collapse identical (kind|repo|path|name) surfaces, unioning endpoints
    agg: dict[str, dict] = {}
    for r in records:
        cur = agg.get(r["id"])
        if cur is None:
            agg[r["id"]] = r
        else:
            cur["endpoints"] = sorted(set(cur["endpoints"]) | set(r["endpoints"]))
            cur["consumers"] = sorted(set(cur["consumers"]) | set(r["consumers"]))
    return sorted(agg.values(), key=lambda r: r["id"])


if __name__ == "__main__":
    raise SystemExit(run("services-endpoints", extract))
