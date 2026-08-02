# Quarantine — competitor-named patterns withheld from the public dataset

Per Lord Michael's hard rule (*no competitor brands or materials referenced or captured*), **25** patterns that name third-party AI models/vendors or encode AI key prefixes are **withheld from the public `regex-corpus.jsonl`** (and brand tokens are masked out of source file paths). They remain in the internal harvest (`~/dev/_regex-harvest/quarantine-competitor-review.jsonl`) for review.

**Judgment call for Michael:** several are *defensive* secret-scanning shapes (e.g. `sk-ant-…`, `sk-proj-…`) whose purpose is catching leaked keys, and some are model-router allow-lists. They are security/routing assets, but they name competitors, so they are excluded from anything public. Decide per row: (a) keep withheld, (b) re-include the credential *shape* with the brand token generalised (e.g. `sk-[A-Za-z0-9_-]{20,}`), or (c) hold them in an `organization`-visibility internal dataset.

| id | risk | pattern (truncated) |
|---|---|---|
| `rx-08adaaaf78` | benign | `dall-e\|gpt-image` |
| `rx-0e955e721f` | catastrophic | `\b(?:sk-[A-Za-z0-9_-]{16,}\|rk_(?:live\|test)_[A-Za-z0-9]{20,}\|` |
| `rx-13917220a7` | benign | `gpt-4o\|gpt-4-turbo\|gpt-4\.\|o1\|o3\|gpt-5` |
| `rx-24085f1d44` | catastrophic | `sk-(?:proj-\|svcacct-\|None-)?[A-Za-z0-9_-]{32,}` |
| `rx-2b18b634c9` | benign | `reason\|deepseek\|think` |
| `rx-2b5662f982` | benign | `llama3.2:3b\|3b` |
| `rx-2e4cff7e2d` | benign | `\bclaude\s*ops\b` |
| `rx-34e5e39132` | catastrophic | `sk-ant-[A-Za-z0-9_-]{20,}` |
| `rx-3b6d1f6b9d` | benign | `claude-3-5\|sonnet-4\|opus-4\|haiku-4` |
| `rx-3e224006f4` | benign | `^(claude\|gpt\|o1\|o3\|gemini\|mistral\|deepseek\|grok\|command\` |
| `rx-4581795500` | catastrophic | `sk-[A-Za-z0-9]{20,}` |
| `rx-66a8b5494a` | catastrophic | `sk-proj-[A-Za-z0-9_-]{20,}` |
| `rx-6762af1f82` | benign | `\b([a-z][a-z0-9_-]*\.service\|prometheusd\|ollama\|noetica\w*\|h` |
| `rx-84450c0ac4` | sensitive | `\.noetica\/runtime\/ollama$` |
| `rx-8bfb91a613` | benign | `\bclaude\.json` |
| `rx-902957fea0` | benign | `llama-server\|no runner\|runner.*not found\|binary not found` |
| `rx-a55a48c253` | benign | `claude-3-5\|sonnet-4\|opus-4` |
| `rx-ae4b625905` | benign | `claude-3\|claude-(sonnet\|opus\|haiku)` |
| `rx-b310888f56` | benign | `no local ollama\|ollama runtime\|ECONNREFUSED\|connect\|loading\` |
| `rx-be9e7354c6` | benign | `\bgeminigops\b` |
| `rx-c3aa3b26e9` | benign | `\bfast\b\|small\|quick\|llama` |
| `rx-d518bcdffe` | catastrophic | `\b(?:sk-[A-Za-z0-9_-]{16,}\|AKIA[0-9A-Z]{16}\|ghp_[A-Za-z0-9]{30` |
| `rx-de659591ed` | catastrophic | `\bOPENAI_API_KEY\s*=\s*[^\s\"'`]+` |
| `rx-e1eb6d31fa` | catastrophic | `sk-ant-[A-Za-z0-9_-]{24,}` |
| `rx-fac545ebbd` | benign | `^Claude\s+` |
