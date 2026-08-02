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
       secrets: inherit   # forwards CATALOG_APP_ID / CATALOG_APP_PRIVATE_KEY
   ```

2. Ensure the two org secrets **`CATALOG_APP_ID`** + **`CATALOG_APP_PRIVATE_KEY`**
   exist (see below). Until BOTH do, the stub is inert — it will no-op rather than
   fail.

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

## The credential requirement — token minted in CI, never a PAT

Writing a shard into THIS repo from another repo's CI needs a cross-repo write
credential. Per estate policy (**secrets are minted in CI, never long-lived
PATs**), the reusable workflow **mints a short-lived GitHub App installation
token in CI** (via `actions/create-github-app-token`, scoped to
`prophet-core-catalog` only) from the App's id + private key. There is **no PAT
anywhere** — no `CATALOG_CONTRIB_TOKEN`, no hand-created token.

### The only operator setup (one-time)

1. **Create a GitHub App** named `socioprophet-catalog-contributor` under the
   `SocioProphet` org with **repository permissions** `Contents: Read & write`
   and `Pull requests: Read & write`, and **nothing else** (no org permissions,
   no account permissions).
2. **Install** that App on **`SocioProphet/prophet-core-catalog` only** — select
   "Only select repositories" and pick just this repo. No other repos, no org-wide
   install.
3. Generate a private key for the App and store **two org secrets**:
   - **`CATALOG_APP_ID`** — the App's numeric App ID.
   - **`CATALOG_APP_PRIVATE_KEY`** — the full PEM private key.

That's it. Callers forward these two secrets (`secrets: inherit`, or map
`CATALOG_APP_ID` / `CATALOG_APP_PRIVATE_KEY` explicitly); the reusable workflow
mints the token per run, uses it for the cross-repo checkout/push/PR, and it
expires when the job ends. The private key is never echoed and the minted token
is never hard-coded.

Until BOTH secrets are set org-wide, every caller stub is **inert** (no-op) — the
workflow cannot mint a token and simply exits 0 — so wiring consumers ahead of
the App is safe.
