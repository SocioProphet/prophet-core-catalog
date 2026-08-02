# Provider references — policy note

This dataset **includes** patterns that reference third-party AI providers/models
(e.g. model-router allow-lists like `gpt-4o|claude-3-5|gemini`, and leaked-key
detectors like `sk-ant-…`, `sk-proj-…`, `ANTHROPIC_API_KEY`). Records that do so are
tagged `"provider_reference": true` (41 today).

**Decision (Lord Michael, 2026-08-02):** these are **first-party** security and routing
policies — the estate has no clients today, so these are *our own* policies, not client
policies. Leaked-key detectors exist to catch our own key spills; router allow-lists
encode which providers we route to. They are included deliberately, at full fidelity,
and source file paths are **not** masked.

The hard rule that still holds: **no *competitor* brand/marketing materials, and no
client materials.** That rule scrubbed the seed deck (Palantir / BAAP / Liminal). It does
**not** exclude our own security detectors or integration surface. If a client is
onboarded whose policy requires withholding provider references, split this into an
`organization`/`restricted`-visibility variant then — do not weaken the detectors now.

_History: an earlier revision quarantined 25 such patterns out of the public corpus; this
note supersedes that quarantine, which has been reversed._
