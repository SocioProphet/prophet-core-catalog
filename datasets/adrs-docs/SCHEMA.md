# ADRs & Key Docs — Schema & Harvest Model

Governed, catalog-ready inventory of the SocioProphet estate's **Architecture Decision
Records** and **key load-bearing docs**. Produced by a **READ-ONLY** markdown harvest of
first-party source under `~/dev` (2026-08-02). First-party only.

## Files

| file | contents |
|---|---|
| `adrs.jsonl` | one JSON object per ADR (record schema below) |
| `docs.jsonl` | one JSON object per key doc (record schema below) |
| `manifest.json` | catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`) |
| `README.md` | overview + supersession / zero-ADR sweeps |
| `SCHEMA.md` | this file |

## ADR record (`adrs.jsonl`)

```json
{
  "id": "adr.<repo>.<adr_number-or-slug>",   // stable; collisions get a -N suffix
  "adr_number": "0001",                       // zero-padded string, or null if none parseable
  "title": "ADR-0001 — Truth Surfaces (B¹¹) + Δ-Surfaces",
  "status": "proposed|accepted|superseded|deprecated|rejected|unknown",
  "repo": "<estate repo dir name>",
  "path": "<path within repo>",
  "supersedes": "0003",        // adr_number this record supersedes, or null
  "superseded_by": "0009",     // adr_number that supersedes this record, or null
  "date": "2026-04-14",        // ISO date if parseable, else null
  "intent": "<one line: the Context/Decision gist>"
}
```

Field notes:
- **id** is `adr.<repo>.<adr_number>` when a number is parseable, else `adr.<repo>.<filename-slug>`;
  duplicate ids (a repo re-using a number across sub-trees) get a `-2`, `-3`, … suffix so ids stay unique.
- **status** is normalised from the record's own front-matter `status:`, a `## Status` section, a
  `Status: …` line (bullets allowed), or a `| Status | … |` table row. Synonyms fold in
  (`approved`/`adopted`/`active`/`final` → `accepted`; `draft`/`wip` → `proposed`;
  `retired`/`obsolete` → `deprecated`; `declined`/`withdrawn`/`abandoned` → `rejected`).
  **`unknown`** = no machine-readable status found (an honest gap, not a guess).
- **supersedes / superseded_by** are pulled from `supersedes ADR-N` / `superseded by ADR-N` /
  `replaced by …` phrasing (and a superseded-by reference list). A dead ADR that names its
  replacement is followable; one that does not leaves `superseded_by: null`.

## Key-doc record (`docs.jsonl`)

```json
{
  "id": "doc.<repo>.<slug>",
  "title": "<H1 / front-matter title / filename>",
  "kind": "readme|design|spec|governance|rfc|other",
  "repo": "<estate repo dir name>",
  "path": "<path within repo>",
  "intent": "<one line: front-matter description or first real paragraph>"
}
```

- **kind** is keyword-heuristic over the path + title: `readme` (basename `README.md`);
  `governance` (govern/charter/policy/invariant/compliance/wall/authz); `spec`
  (spec/contract/schema/protocol/api/conformance); `design` (design/architect/overview/model/
  topology); `rfc` (rfc/proposal); else `other`.

## Harvest heuristics (what was included / capped)

**ADRs** — a markdown file is an ADR if any of: filename `ADR-<n>` / `<n>-…` under an `adr/`
or `decisions/` dir; path under `**/adr/**`, `**/adrs/**`, `docs/adr/**`, `decisions/**`; or
front-matter/content carrying an ADR `status` plus a `## Decision`/`## Context` section.
Index `README.md` pages and `*template*` files are **not** ADRs.

**Key docs** — top-level `README.md` (always), plus `docs/**/*.md` that hit a **signal filter**
(design, architect, spec, governance, rfc, contract, invariant, charter, threat, security,
runbook, overview, protocol, schema, proposal, roadmap, decision, policy, conformance, ontology,
glossary, principles, whitepaper, …). **Capped at 40 docs/repo** to keep the set to signal, not
every markdown file — nine dense repos hit the cap. ADR files are excluded from `docs.jsonl`
(no double-count).

**Excluded (first-party rule):** `*.wt` worktrees, `_*` dirs, `node_modules`/vendored,
`@`-pinned and `-main` embedded third-party snapshots (e.g. ESIPFed `science-on-schema.org`
decisions vendored under `gaia/cv/sources/`), `AgenticaForge` / `agent-inbox`, and all
client/competitor materials.

## Blast-radius / governance model

Each ADR is a decision node; its `repo`/`path` is where it lives, and `supersedes` /
`superseded_by` are the edges of the decision-lineage graph. A `superseded`/`deprecated` ADR
still present in-tree (see the README sweep) is a **stale-authority** hazard — an agent reading
the folder could act on a dead decision. A repo **absent** from `adrs.jsonl` is deciding things
with no durable record; the zero-ADR sweep is the backfill worklist. Docs project the same way:
a `governance`/`spec` doc is the warrant a gate or contract points back to.
