# Catalog contribution extractors.
#
# Single source of truth for turning ONE estate repo into its per-dataset
# contribution shard(s). Fetched by the git-ops-standards reusable workflow
# (catalog-contribute.yml) and run scoped to the caller repo on each merge to
# main, so every repo keeps its own slice of the catalog current.
#
# Contract shared by every extractor CLI in this package:
#
#     python3 extractors/extract_<dataset>.py <repo_path> <repo_name> [--out FILE]
#
#   * <repo_path>  filesystem root of the repo to scan (read-only).
#   * <repo_name>  logical repo name written into every record's sources[].repo
#                  (must match the src.<repo> id family in the manifest).
#   * --out FILE   write the shard here; default is stdout.
#
# Output: JSONL, ONE record per distinct item, sorted deterministically so a
# re-run on an unchanged repo is byte-identical (idempotent). Every record's
# sources[] is scoped to THIS repo only; the catalog-side assembler
# (tools/assemble_dataset.py) merges same-id records across repo shards.
