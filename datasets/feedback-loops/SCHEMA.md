# Feedback Loops & Lifecycles — Schema

## `feedback-loops.jsonl`
```json
{
  "id": "loop.<slug>",
  "name": "<human name>",
  "kind": "feedback-loop",
  "trigger": "<what starts the loop>",
  "steps": ["<ordered step>", "..."],
  "feedback_signal": "<the measured signal that the loop reacts to>",
  "closes_when": "<condition under which the loop is satisfied>",
  "recorded_in": ["<repo>:<path> | <repo>#<pr/issue>"],   // evidence the loop ran (blast-radius edges)
  "dogfood": true,                                          // run on ourselves, not just customers
  "status": "live | partial | live-pending-token | designed",
  "related_datasets": ["ds.<id>"]
}
```

## `lifecycles.jsonl`
```json
{
  "id": "life.<slug>",
  "asset_class": "<schema/contract | ADR | vendored-artifact | ...>",
  "states": ["<state>", "..."],                 // ordered lifecycle states
  "transition_guard": "<the control that governs state transitions>",
  "recorded_in": ["<where the lifecycle is enforced/recorded>"],
  "dogfood": true
}
```

## Notes
- `recorded_in` entries are **blast-radius edges** from a loop/lifecycle to the concrete PR, issue,
  workflow, or file that is its evidence. A loop with an empty or unresolvable `recorded_in` is a
  **never-fired** control and should be treated as suspect.
- `status` is honest: `live-pending-token` = wired but inert until an operator action (e.g. the
  `CATALOG_CONTRIB_TOKEN` secret); `partial` = designed + partially enforced; `designed` = spec only.
- These are curation seeds, not final governance labels; expand as loops mature.
