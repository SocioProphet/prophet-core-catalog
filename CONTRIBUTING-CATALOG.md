# Contributing to the data catalog — the per-repo shard contract

> Lord Michael's directive: **every estate repo updates its own contribution to
> the data catalog on each merge to `main`.**

Each catalog dataset is an **assembly of per-repo shards**, not one hand-edited
monolith:

```
datasets/<dataset>/
  manifest.json                      # catalog manifest (validated)
  contributions/<repo>.jsonl         # ONE shard per contributing repo  <-- repos write here
  corpus.jsonl                       # assembled + merged (GENERATED — do not hand-edit)
  regex-corpus.jsonl                 # regex dataset only: generated alias of corpus.jsonl
  gbrg-blast-radius.jsonl            # regex dataset only: generated derived view
```

A repo owns exactly its own `contributions/<repo>.jsonl`. The catalog-side job
(`.github/workflows/assemble-catalog.yml` → `tools/assemble_dataset.py`) merges
all shards into `corpus.jsonl` and rebuilds the derived views. Records that
share an `id` across shards are merged (union `sources`, recompute `use_count` as len(sources), union
`flags`, OR the risk booleans, max `risk_class`).

## How a repo opts in

1. In the contributing repo, drop the caller stub from **git-ops-standards** into
   `.github/workflows/catalog.yml`:

   ```yaml
   # templates/catalog.yml (git-ops-standards) — copy verbatim
   name: catalog-contribute
   on:
     push:
       branches: [main]
   jobs:
     contribute:
       uses: SocioProphet/git-ops-standards/.github/workflows/catalog-contribute.yml@main
       secrets:
         catalog_token: ${{ secrets.CATALOG_CONTRIB_TOKEN }}
   ```

2. Ensure the org/repo secret **`CATALOG_CONTRIB_TOKEN`** exists (see below). Until
   it does, the stub is inert — it will no-op rather than fail.

On each merge to `main`, that workflow fetches `extractors/` from this repo (pinned
by ref), runs them scoped to the caller repo, and opens/updates a PR here writing
`datasets/<ds>/contributions/<caller-repo>.jsonl`. Merging that PR triggers
`assemble-catalog.yml`, which regenerates `corpus.jsonl`.

## The shard contract

- **Filename:** `datasets/<dataset>/contributions/<repo>.jsonl`, one repo per file.
- **One record per distinct item**, JSONL, one JSON object per line.
- **Every record carries a stable `id`** (content hash) and, for the regex
  dataset, a `pattern`. `sources[]` entries are scoped to THIS repo only:
  `{"repo": "<repo>", "file": "<path within repo>", "line": <int>}`.
- **Deterministic:** records sorted by `id`, `sources` sorted by
  `(repo, file, line)`, JSON emitted with sorted keys — a re-run on an unchanged
  repo produces byte-identical output (no PR churn).
- **Provider-reference policy** (`datasets/regex-operational-dataset/PROVIDER-REFERENCE-NOTE.md`):
  first-party provider/model routing allow-lists and leaked-key detectors are
  INCLUDED and tagged `provider_reference: true`. Competitor / client *marketing*
  brand words are the only hard exclusion.

The extractors in `extractors/` are the single source of truth for producing a
shard. Run one locally exactly as CI does:

```bash
python3 extractors/extract_regex.py /path/to/repo <repo-name> \
    --out datasets/regex-operational-dataset/contributions/<repo-name>.jsonl
python3 tools/assemble_dataset.py datasets/regex-operational-dataset   # merge + derive
python3 tools/validate_dataset_manifest.py                             # fail-closed gate
```

Available extractors (CLI contract: `<repo_path> <repo_name> [--out FILE]`):

| dataset | extractor | status |
|---|---|---|
| `ds.regex-operational-dataset` | `extractors/extract_regex.py` | working |
| `ds.topic-vocabulary` | `extractors/extract_topic_vocabulary.py` | thin hook |
| `ds.rules-policies` | `extractors/extract_rules_policies.py` | thin hook |
| `ds.ci-workflows-tests` | `extractors/extract_ci_workflows_tests.py` | thin hook |

## The token requirement

Writing a shard into THIS repo from another repo's CI needs a cross-repo write
credential. Per estate policy (**secrets are minted in CI, never long-lived
PATs**), use a **GitHub App / org installation token**, exposed to the caller as
the secret **`CATALOG_CONTRIB_TOKEN`**.

- **Secret name:** `CATALOG_CONTRIB_TOKEN`
- **Minimum scope:** `contents: write` + `pull_requests: write` **on
  `SocioProphet/prophet-core-catalog` only** (a GitHub App installation scoped to
  this one repo). No org-admin, no other repos.
- It is passed to the reusable workflow as the `catalog_token` secret input; it is
  never hard-coded and never echoed.

Until the secret is set org-wide, every caller stub is **inert** (no-op), so wiring
consumers ahead of the secret is safe.
