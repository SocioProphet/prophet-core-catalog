# Provider references — policy note

This dataset **includes** third-party provider model identifiers
(e.g. `gpt-5.5`, `claude-opus-4.8`, `gemini-3.1-pro`, `mistral-large-3`,
`qwen3-32b`, `deepseek-r1`, `google/gemma-2-9b-it`) wherever they appear in the
estate's **own** routing tables, model-carry profiles, governance ledgers, or code.
Records that do so are tagged `"provider_reference": true`.

**Decision (Lord Michael, 2026-08-02):** these are **first-party** integration and
routing policy — the estate has no clients today, so a model id in `model-router`'s
`prophet-mesh-model-routing.v0.1.json` or in `noetica/prophet-mesh.manifest.json`
encodes *which providers we route to*, not any client's policy. They are included
deliberately, at full fidelity, and source file paths are **not** masked. This mirrors
the `ds.regex-operational-dataset` PROVIDER-REFERENCE decision (router allow-lists and
leaked-key detectors are first-party security/routing policy).

The hard rule that still holds: **no *competitor* brand/marketing materials, and no
client materials.** A provider model NAME in our routing config is a provider reference
(included); a competitor's *marketing deck* comparing products is not (excluded — the
same rule that scrubbed the seed deck's Palantir / BAAP / Liminal content). Benchmark
baseline rows in `prophet-platform` that compare our `noetica-7b` to frontier provider
models are our own evaluation facts, not competitor marketing, and are in scope.

If a client is onboarded whose policy requires withholding provider references, split
this into an `organization`/`restricted`-visibility variant then — do not strip the
routing surface now.
