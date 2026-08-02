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
       secrets: inherit   # forwards the SHARED GH_OPS_APP_* org secrets (already set)
   ```

2. **Nothing else to set.** The credential is minted in CI from the estate's
   shared ops App, whose org secrets already exist (see below). `secrets: inherit`
   forwards them; you create no new secret. Until the shared App is configured
   (`vars.GH_OPS_APP_CONFIGURED == 'true'`) the stub is inert — it no-ops rather
   than fails.

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

## The credential requirement — minted in CI from the shared ops App, never a PAT, never a per-consumer secret

Writing a shard into THIS repo from another repo's CI needs a cross-repo write
credential. Per estate policy (**all tokens minted in CI — no manual PATs, no
standing operator-set secrets**), the reusable workflow **mints a short-lived
GitHub App installation token in CI** (via `actions/create-github-app-token`,
scoped with `repositories: prophet-core-catalog` so the token can write nowhere
else) from the estate's **shared ops App** — the same App `board-parity.yml` and
`estate-ci-health.yml` mint from. There is **no catalog-specific secret**: no
`CATALOG_APP_ID`, no `CATALOG_APP_PRIVATE_KEY`, no `CATALOG_CONTRIB_TOKEN`, no PAT.

### There is no per-consumer operator step

Consumers set **nothing**. The token is minted from two org secrets that
**already exist** for the estate's ops App:

- **`GH_OPS_APP_ID`** — the shared org App's numeric App ID.
- **`GH_OPS_APP_PRIVATE_KEY`** — its PEM private key.
- gated by the variable **`vars.GH_OPS_APP_CONFIGURED == 'true'`**.

These were provisioned once, estate-wide, for `board-parity` / `estate-ci-health`;
this loop reuses them rather than minting a second App with its own standing
secret. Caller stubs forward them with `secrets: inherit` (which creates no new
secret — it just makes the existing org secrets visible to the reusable
workflow); the workflow mints the token per run, uses it for the cross-repo
checkout/push/PR, and it expires when the job ends. The private key is never
echoed and the minted token is never hard-coded.

Until `vars.GH_OPS_APP_CONFIGURED == 'true'` (and the two secrets are forwarded),
every caller stub is **inert** (no-op) — the workflow mints nothing and exits 0 —
so wiring consumers ahead of the App bootstrap is safe.

### The one-time, estate-wide bootstrap (not per-repo, not a standing catalog secret)

The shared `GH_OPS_APP_*` org secrets are already set. The only catalog-specific
prerequisite is that the shared App grants **`Contents: Read & write`** +
**`Pull requests: Read & write`** (it is already installed org-wide, so no
install step, and the minted token is still scoped down to this repo only). That
one permission grant is the irreducible human step: GitHub does **not** expose
GitHub-App permission management to WIF/OIDC/Actions identities, so no CI job can
perform it. It is a one-time grant on an App that already exists — not a new App,
not a new secret, and not repeated per consumer.
