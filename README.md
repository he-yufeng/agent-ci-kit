# agent-ci-kit

[中文文档](README_CN.md)

CI-grade evidence and safety tools for AI agents, MCP servers, and open-source contribution work.

When you ship code with AI agents, or maintain MCP servers, or send pull requests to upstream
projects, the hard part is rarely writing the change. It is proving the change is right: showing a
CI failure is a real regression and not noise, handing an agent the few files that actually matter,
keeping a broken MCP server out of `main`, turning a protocol bug into a transcript a maintainer can
read, and testing that an agent will not run a dangerous tool just because some untrusted text told
it to.

`agent-ci-kit` bundles five small, focused command-line tools that each produce that kind of
evidence and fit cleanly into CI:

| Subcommand | What it does |
|---|---|
| `agentci ci-repro` | Turn GitHub Actions failure logs into a local repro plan and a PR evidence pack. |
| `agentci patch-context` | Build a small, explainable context pack of the files that matter for one issue, failing test, or patch. |
| `agentci mcp-gate` | A CI gate for MCP servers: handshake, list tools, check the tool contract, scan for leaked secrets. |
| `agentci mcp-replay` | Record and replay MCP JSON-RPC traffic as redacted, reviewable fixtures. |
| `agentci tool-fence` | Deterministic safety regression tests for agent tool calls, replayed from fixtures in CI. |

Each tool works on its own. Together they cover the loop of contributing to and operating
agent/MCP projects with reviewable evidence instead of screenshots and "works on my machine".

## Install

```bash
pip install agent-ci-kit
```

This installs a single `agentci` command with five subcommands. Run `agentci --help` for the map,
or `agentci <subcommand> --help` for any tool.

## ci-repro

Turn a CI log into a categorized failure report and a PR comment draft. It is not a local runner
like `act` and not a linter like `actionlint`; it reads the logs you already have, finds the first
actionable failure, classifies it (regression, permission gate, network limit, dependency install,
local test failure), and extracts a likely local repro command.

```bash
gh run view 123456789 --repo owner/repo --log > run.log
agentci ci-repro plan run.log --out repro.md
agentci ci-repro comment run.log            # draft a PR comment from the first failure
```

## patch-context

Give a coding agent the files that matter for one narrow task. It reads issue text, stack traces,
failure logs, git diffs, file names, content terms, and light Python/JS/TS import links, then ranks
the files an agent should read first. Use Repomix for the whole repo and RepoWiki for durable docs;
use `patch-context` when the task is "fix this issue" or "debug this CI failure".

```bash
agentci patch-context scan --repo . --issue issue.md --top 12 > context.md
pytest -q 2>&1 | tee pytest.log
agentci patch-context from-failure --repo . pytest.log --format md
agentci patch-context from-diff --repo . --base main --format json
```

## mcp-gate

Stop shipping broken MCP servers. `mcp-gate` starts a stdio MCP server, runs the client handshake,
lists tools, checks the tool contract shape, scans observed metadata and stderr for obvious secret
leaks, and writes Markdown/JSON reports that fit into GitHub Actions. It exits non-zero when a
required check fails, so a pull request fails before a broken server lands.

```bash
agentci mcp-gate check \
  --command "python -m your_mcp_server" \
  --report mcp-gate-report.md \
  --json mcp-gate-report.json
```

Use `--fail-on-warn` if warnings should also fail CI.

## mcp-replay

Record and replay MCP JSON-RPC traffic as small JSONL fixtures. When an MCP server breaks, a
maintainer needs the message sequence, not a screenshot: which request was sent, which response came
back, whether ids matched, whether a token or local path leaked. `mcp-replay` captures that, redacts
secrets, and replays the same client messages against a server to compare response shape.

```bash
agentci mcp-replay record --command "python -m my_mcp_server" --out transcript.jsonl
agentci mcp-replay inspect transcript.jsonl --format md
agentci mcp-replay redact transcript.jsonl --out transcript.safe.jsonl
agentci mcp-replay replay transcript.safe.jsonl --command "python -m my_mcp_server"
```

## tool-fence

Put agent tool-call safety cases in your repository and run them in CI. It does not call a live
model. It replays transcript fixtures and checks whether an agent would call tools that should be
denied, confirmed first, or treated as high-risk after untrusted tool output. Real incidents usually
happen one step after the answer looks fine, when the agent reads an issue, web page, or tool result
and then calls a dangerous tool. `tool-fence` makes that boundary cheap to test.

```bash
agentci tool-fence init                 # write starter fixtures
agentci tool-fence run tests/toolfence --markdown
```

## Related projects

`agent-ci-kit` sits next to a few other tools I maintain for agent and open-source work:

- [AgentProbe](https://github.com/he-yufeng/AgentProbe) — pytest plugin for regression-testing AI agents (snapshots, semantic comparison, mock LLMs).
- [GitSense](https://github.com/he-yufeng/GitSense) — find open-source issues to work on and gauge how hard a repo is to contribute to.
- [RepoWiki](https://github.com/he-yufeng/RepoWiki) — generate wiki documentation for any codebase.
- [CoreCoder](https://github.com/he-yufeng/CoreCoder) — a minimal AI coding agent you can read end to end.

## Development

```bash
git clone https://github.com/he-yufeng/agent-ci-kit
cd agent-ci-kit
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

## License

MIT
