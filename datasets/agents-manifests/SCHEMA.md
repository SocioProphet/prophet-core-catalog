# Agents & Manifests Catalog — Schema & Connectivity Model

Governed, catalog-ready inventory of the SocioProphet estate's **agents** and their
**manifests / declared capabilities**, so agents can discover other agents, read their
declared authority, and trace capability blast radius. Produced by a READ-ONLY harvest
of first-party source under `~/dev`. First-party only.

## Files

| file | contents |
|---|---|
| `agents.jsonl` | one JSON object per distinct agent artifact (record schema below) |
| `manifest.json` | catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`) |
| `README.md` | overview + the "invisible authority" / unregistered-agent gap sets |
| `SCHEMA.md` | this file |

## Record schema (`agents.jsonl`)

```json
{
  "id": "ag-<sha1[:12] of repo+path+agent-name>",
  "name": "<agent id / manifest name>",
  "kind": "agent-manifest|blueprint|claude-subagent|mcp-server|a2a-card|capability-decl|other",
  "repo": "<first-party repo>",
  "path": "<path within repo>",
  "declared_capabilities": [ "<capability / surface / tool / sefirot the agent declares>" ],
  "authority_refs": [ "<manifest / grant / policy / control / revocation ref it traces to>" ],
  "intent": "<one-line: what the agent is for>",
  "connections": {
    "skills":      [ "<skill file / SkillManifest / SKILL.md path>" ],
    "tools":       [ "<MCP tool/server ref, tool:// grant, tool name>" ],
    "prompts":     [ "<system-prompt / blueprint / subagent .md path>" ],
    "preferences": [ "<settings.json / CLAUDE.md / AGENTS.md / keybindings path>" ],
    "personas":    [ "<persona / AgentCoordinateVector / sefirot vector ref>" ]
  },
  "agent_plane_ref": "src.agentplane | src.prophet-mesh | null",
  "registry_ref":    "src.agent-registry | null",
  "standard_ref":    "src.socioprophet-agent-standards | null"
}
```

### `kind` rubric
- **agent-manifest** — a registry admission record: `AgentSpec`, `AgentManifest`, `AgentRegistration` (agent-registry family).
- **blueprint** — a declarative agent definition (`prophet-mesh/agents/*.yaml`, `blueprints/*.yaml`) with a `capabilities:` list.
- **claude-subagent** — a Markdown subagent with YAML frontmatter (`name`/`description`/`tools`), e.g. SCOPE-D `agents/**.md`.
- **mcp-server** — one MCP server declared in an `mcp.json` / `.mcp.json` config (the tool surface agents attach to).
- **a2a-card** — an agent-to-agent card: agentplane `Bundle` (A2A/MCP protocol identity + governance context) or a TurtleTerm A2A/agent-interop `SkillManifest`.
- **capability-decl** — a standalone capability/authority grant: `AgentCapabilityDeclaration`, `ToolGrant`, `agent_descriptors` capability records.
- **other** — agent-adjacent artifacts that don't fit above (e.g. a ProCybernetica `AgentCoordinateVector` persona vector).

### Field notes
- **id** is a content hash of `repo::path::name`, so re-harvest is idempotent and the same agent declared in two sites yields two records (two declaration sites = two blast-radius nodes).
- **declared_capabilities** are what the agent *claims it can do* (surfaces, tools, operation types, capability names, sefirot). This is the "authority declared" side of no-invisible-authority.
- **authority_refs** are what the capability *traces back to*: an owner ref, a policy profile, a tool grant, a required control, an evidence/revocation ref, a policy gate. An agent with capabilities but an **empty `authority_refs` and no `registry_ref`** is an *invisible-authority* risk (see README).
- **connections** are best-effort edges to the other agent-substrate assets. `tools` cross-reference `ds.schemas-contracts` where the tool is a contract; `skills`/`preferences`/`prompts`/`personas` are repo-local paths or cross-repo refs.
- **agent_plane_ref / registry_ref / standard_ref** bind the agent to the three substrate systems (agentplane / agent-registry / socioprophet-agent-standards). A `null` `registry_ref` or `standard_ref` = the agent is **unregistered / unstandardized** (a governance gap).

## Connectivity model (why this is a graph, not a list)

Mandated by policy — `agent-catalog-connectivity.policy` (authored in
`SocioProphet/socioprophet-agent-standards`). Every agent must connect to the
substrate it depends on so authority is never invisible:

```
agent  --declares-->  capability            (declared_capabilities[])
agent  --traces-to-->  authority             (authority_refs[]: grant/policy/control/evidence)
agent  --uses-->       skill | tool | prompt (connections{skills,tools,prompts})
agent  --shaped-by-->  preference | persona  (connections{preferences,personas})
agent  --runs-on-->    agent-plane           (agent_plane_ref)
agent  --admitted-by-->agent-registry        (registry_ref)
agent  --conforms-to-->agent-standard        (standard_ref)
```

`tools` and contracts already cataloged in `ds.schemas-contracts` are shared nodes:
the two datasets compose into one estate agent-substrate graph.

## Blast-radius / discovery recipes (how agents use it)

- **Discover agents** → read `agents.jsonl`; filter by `kind` / `repo` / `declared_capabilities`.
- **What authority does agent X hold?** → its `declared_capabilities` (claimed) vs `authority_refs` (traced). A gap between them is the audit target.
- **Who can call tool/skill Y?** → reverse-index `connections.tools` / `connections.skills` across records.
- **Invisible-authority sweep** → records with non-empty `declared_capabilities` and empty `authority_refs` **and** null `registry_ref`.
- **Unregistered / unstandardized gap** → records with null `registry_ref` (never admitted to the registry) or null `standard_ref` (conform to no declared standard).

## Hard rule (governance)

First-party only. Excluded: third-party trees (AgenticaForge, agent-inbox, the openclaw
fork), vendored nested repo copies, and duplicate/superset working checkouts (`*.wt`,
`*-chronos-superset`, `*-kairos-draft`, prophet-platform branch clones). The dataset
validator (`tools/validate_dataset_manifest.py`) is fail-closed on schema + JSONL validity;
`make validate` additionally enforces catalog-source referential integrity.
