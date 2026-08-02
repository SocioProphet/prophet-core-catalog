# Estate Agents & Manifests Catalog (`ds.agents-manifests`)

A governed, catalog-registered inventory of the SocioProphet estate's **agents** and their
**manifests / declared capabilities**, so that **agents can discover other agents, read their
declared authority, and trace the blast radius of any capability, grant, or dependency.**

Seeded 2026-08-02 by a read-only harvest of 8 first-party `~/dev` repos. **101 agent artifacts.**

## Contents
| File | What |
|---|---|
| `manifest.json` | Catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`). |
| `agents.jsonl` | **101** agent records; one per declaration site (a manifest, blueprint, subagent, MCP server, A2A card, or capability grant). |
| `SCHEMA.md` | Record schema + the connectivity model and discovery/blast-radius recipes. |

## What was harvested
| kind | n | source |
|---|---|---|
| `capability-decl` | 28 | agent-registry `AgentCapabilityDeclaration`/`ToolGrant`; `agent_descriptors` capability records |
| `a2a-card` | 26 | agentplane `Bundle`s; TurtleTerm A2A/agent-interop `SkillManifest`s |
| `claude-subagent` | 22 | SCOPE-D `agents/**.md` (YAML frontmatter: name/description/tools) |
| `blueprint` | 11 | prophet-mesh `agents/*.yaml` + `blueprints/*.yaml` |
| `agent-manifest` | 7 | agent-registry `AgentSpec` / `AgentRegistration` |
| `mcp-server` | 6 | `mcp.json` / `.mcp.json` (SCOPE-D, smart-tree) |
| `other` | 1 | ProCybernetica `AgentCoordinateVector` persona vector |

Repos: `agent-registry` (15), `agent_descriptors` (20), `agentplane` (16), `prophet-mesh` (11),
`SCOPE-D` (25), `TurtleTerm` (10), `smart-tree` (3), `ProCybernetica` (1).

## The catalog is a **connected graph**, not a list — mandated by policy
Every record carries a `connections` object linking the agent to the other agent-substrate
assets — `{skills, tools, prompts, preferences, personas}` — and three substrate cross-refs:
`agent_plane_ref` (which plane it runs on), `registry_ref` (its registry admission entry),
`standard_ref` (the standard it conforms to). This connectivity is **required by
`agent-catalog-connectivity.policy`** (authored in `SocioProphet/socioprophet-agent-standards`):
no agent may declare authority it cannot trace to a substrate. `tools`/contracts compose with
`ds.schemas-contracts` as shared graph nodes.

**Connection coverage (of 101 agents):** tools 53 · preferences 44 · prompts 33 · skills 10 · personas 3.

## 🔴 Invisible-authority risk set (the point of this dataset)
**46 agents declare capabilities but trace to NO authority manifest and have NO registry entry**
(`declared_capabilities` non-empty, `authority_refs` empty, `registry_ref` null):

| repo / kind | n | why it matters |
|---|---|---|
| `agent_descriptors` capability-decl | 20 | descriptors declare potent verbs — `policy.evaluate`, **`kill.agent`**, `quorum.vote` — with no owner, grant, or policy ref |
| SCOPE-D `claude-subagent` | 20 | cloud enum/exploit subagents (IAM, KMS, Secrets, STS, exploit, attack-paths) hold powerful `tools:` with no manifest/grant behind them |
| SCOPE-D + smart-tree `mcp-server` | 6 | MCP tool surfaces declared with no governing authority ref |

These are the "no invisible authority" targets: capability is asserted, but the warrant for it
is not declared anywhere the catalog can see.

## 🔴 Unregistered / unstandardized gap set
- **86 / 101 agents have no `registry_ref`** — only the 15 agent-registry `AgentSpec`/`AgentRegistration`/capability records are admitted to `SocioProphet/agent-registry`. Every prophet-mesh blueprint, SCOPE-D subagent, agentplane bundle, TurtleTerm card, and descriptor is **unregistered**.
- **101 / 101 agents have no `standard_ref`** — *no* agent currently carries an explicit conformance link to a `SocioProphet/socioprophet-agent-standards` profile. The entire population is the **unstandardized** set pending enforcement of `agent-catalog-connectivity.policy`. (prophet-mesh blueprints declare `required_controls`, which *map* to the estate CONTROL_PROFILE, but the conformance is not declared in-band.)

## Discovery / blast-radius (how agents use it)
- **Discover an agent** → filter `agents.jsonl` by `kind` / `repo` / `declared_capabilities`.
- **What authority does agent X hold?** → `declared_capabilities` (claimed) vs `authority_refs` (traced); the gap is the audit.
- **Who uses tool/skill Y?** → reverse-index `connections.tools` / `connections.skills`.
- **Invisible-authority sweep** → `declared_capabilities` non-empty ∧ `authority_refs` empty ∧ `registry_ref` null.

## Governance
- **First-party only.** Excluded: AgenticaForge, agent-inbox, the openclaw fork (`SourceOS-Linux/openclaw`, an upstream personal-assistant fork), vendored nested repo copies, and duplicate/superset checkouts (`*.wt`, `*-chronos-superset`, `*-kairos-draft`, prophet-platform branch clones).
- **Validate:** `python tools/validate_dataset_manifest.py datasets/agents-manifests/manifest.json`, and `make validate` for catalog-wide referential integrity. Both pass.

## Expanding it
Add records to `agents.jsonl` (same schema, `id = ag-<sha1[:12] of repo::path::name>`), keep
third-party/vendored agents out, fill `connections` + the three substrate refs, re-run the
validator, and bump `manifest.json` `version`. See the program doc
[`docs/ASSET-CATALOG-PROGRAM.md`](../../docs/ASSET-CATALOG-PROGRAM.md).
