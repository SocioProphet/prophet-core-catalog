# CI / Workflows / Tests Inventory — Schema & Blast-Radius Model

Governed, catalog-ready inventory of the SocioProphet estate's **CI assets** and **test
suites**. Produced by a READ-ONLY harvest of first-party source under `~/dev` (2026-08-02).
First-party only — third-party `AgenticaForge` and `agent-inbox` are excluded (estate
boundary); no client/competitor materials.

## Files

| file | contents |
|---|---|
| `ci-workflows.jsonl` | one JSON object per CI asset (GitHub Actions workflow, Makefile CI target-set, `.gitlab-ci.yml`, `justfile`, `Taskfile`) |
| `tests.jsonl` | one JSON object per `(repo, directory, framework)` test suite |
| `manifest.json` | catalog manifest (validates against `schemas/catalog.dataset.v0.1.json`) |
| `SCHEMA.md` | this file |

## Record schema — `ci-workflows.jsonl`

```json
{
  "id": "wf-<sha1[0:10] of repo/path>",
  "repo": "<repo dir under ~/dev>",
  "path": "<path within repo>",
  "type": "github-actions | makefile-ci | other",
  "name": "<workflow name: field, or filename>",
  "triggers": ["pull_request", "push", "schedule", "workflow_dispatch", ...],
  "jobs": ["<job id or CI target name>", ...],
  "gating": true,                       // fires on a merge-blocking trigger (see rubric)
  "fail_open_signals": ["if:always()", "<job>:continue-on-error"],
  "last_status": "success | failure | in_progress | null"
}
```

Field notes:
- **id** is a stable content hash of `repo/path`, so a re-harvest is idempotent for unchanged assets.
- **type**:
  - `github-actions` — a file under `.github/workflows/*.yml|*.yaml`. `name`/`triggers`/`jobs` parsed from YAML (PyYAML; regex fallback). Note YAML parses a bare `on:` key as boolean `True`; the harvester handles that.
  - `makefile-ci` — a `Makefile`/`GNUmakefile`/`*.mk` that defines at least one target whose name contains `ci` or is one of `test|lint|check|validate|verify`. `jobs` = those target names; `triggers` = `["manual"]`.
  - `other` — `.gitlab-ci.yml` (jobs = top-level stanzas; `triggers` = merge_request/push), `justfile` (jobs = recipe names), `Taskfile.yml|yaml` (jobs = task names).
- **gating** (heuristic, not branch-protection truth): `true` when `triggers` includes `pull_request`, `pull_request_target`, or `merge_group` — i.e. the asset runs on a change that can block a merge. `false` for push/schedule/dispatch-only workflows and for `makefile-ci`/most `other` assets. This is a *candidate-required-check* signal; it does **not** read GitHub branch-protection "required status checks", which are not visible from source alone.
- **fail_open_signals**: source-visible patterns that can make a check pass when it should fail — a job-level `continue-on-error: true`, or an `if: always()` guard that lets a downstream step report success regardless of upstream failure. A gating workflow with fail-open signals is a *fail-open ≡ no-gate* candidate for review.
- **last_status**: latest run conclusion (or in-flight status) from `gh run list`, matched by workflow `name`, for a **16-repo active-org sample only** (prophet-platform, sociosphere, Noetica, prophet-mesh, sp-orchestrator, prophet-sheaf/truth/aggregate, agent-registry, guardrail-fabric, model-router, memory-mesh, ProCybernetica, economic-prophet). `null` everywhere else — **null means "not queried", not "never ran".**

## Record schema — `tests.jsonl`

```json
{
  "id": "ts-<sha1[0:10] of repo|dir|framework>",
  "repo": "<repo dir under ~/dev>",
  "path": "<directory within repo holding the test files>",
  "framework": "pytest | vitest/jest | cargo | go-test",
  "test_count": 42,                     // APPROXIMATE — see rubric
  "file_count": 7,                      // test files in this dir for this framework
  "tested_target": "<inferred module/dir under test>"
}
```

Field notes:
- One record = one `(repo, directory, framework)` group, so a directory of test files collapses to a single suite record with `file_count` files and a summed `test_count`.
- **test_count** is a cheap static count of test-declaration occurrences, **not a runtime collection**:
  - `pytest` — `def test…(` / `async def test…(` in `test_*.py` / `*_test.py`
  - `vitest/jest` — `it(` / `test(` calls in `*.test.*` / `*.spec.*` (ts/tsx/js/jsx/mjs/cjs)
  - `cargo` — `#[test]` / `#[tokio::test]` / `#[async_std::test]` attributes in `*.rs`
  - `go-test` — `func Test…` / `func Benchmark…` / `func Fuzz…` in `*_test.go`
  It over-counts commented-out or table-driven declarations and under-counts parametrized cases; treat it as a magnitude, not a ground truth.
- **tested_target** is inferred from the path (the segment before a `tests/`|`test/` dir, else the parent dir); a curation seed, not authoritative.

## Harvest scope / exclusions

READ-ONLY `os.walk` over 149 first-party repos under `~/dev`. Pruned: `*.wt` worktrees,
`_*`-prefixed dirs, and `node_modules`, `target`, `dist`, `build`, `vendor`, `vendored`,
`.venv`/`venv`, `site-packages`, `coverage`, `.next`/`.nuxt`, `__pycache__`, `.terraform`, etc.
Third-party `AgenticaForge` and `agent-inbox` excluded (estate boundary). No client/competitor materials.

## Blast-radius / risk model

This inventory is a bipartite graph, catalog-ready and mappable onto GBRG
(Governed Blast-Radius Graph, `~/dev/sociosphere/gbrg`).

```
node (repo)        : repo://<repo>
node (ci asset)    : ci://<repo>/<path>          — a ci-workflows.jsonl record
node (test suite)  : test://<repo>/<path>#<fw>   — a tests.jsonl record
edge (guards)      : ci://…  --gates-->  repo://<repo>      (only when gating == true)
edge (covers)      : test://… --covers--> code://<repo>/<tested_target>
```

### How other agents query it

- **Where is this repo's merge actually gated?** → `ci-workflows.jsonl` filtered by `repo` and `gating: true`. Empty result = nothing blocks a bad merge from source (see README risk view).
- **Fail-open ≡ no-gate sweep** → `gating: true` **and** `fail_open_signals` non-empty: a check that can report green while failing.
- **Untested blast radius** → repos absent from `tests.jsonl` (zero suites) — a change there ships with no automated proof. Cross with `ci-workflows.jsonl` to find repos that *run CI but have no tests* (CI theatre).
- **Highest test mass** → sum `test_count` per repo/target; the highest-mass targets are the ones whose breakage has the widest coverage-loss blast radius.
- **Liveness** → `last_status` on the sampled repos; a gating workflow whose latest run is `failure` (or a never-run gating workflow, surfaced elsewhere) is a prioritized remediation target.
