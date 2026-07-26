# Architecture

## Why two protocols, not one

**MCP (Model Context Protocol)** is vertical: it standardizes how one agent reaches into tools/data it needs to do its own job. Before MCP, connecting N agent frameworks to M tools meant N x M bespoke integrations; MCP makes it N + M.

**A2A (Agent2Agent)** is horizontal: it standardizes how independent agents delegate work to each other and get results back, without either side needing to know the other's internals. An **Agent Card** (served at `/.well-known/agent-card.json`) is the public "business card" describing what an agent can do and how to reach it; a **Task** is the stateful unit of delegated work (`submitted -> working -> completed/failed`).

In this system: each specialist uses **MCP** to reach GitHub's data. The Coordinator uses **A2A** to hand work to the specialists and collect results.

```
GitHub Actions (issues: opened)
        |
        v
   Coordinator  --A2A-->  Duplicate Detector --MCP--> GitHub MCP Server --> GitHub API
   (A2A client,  --A2A-->  Labeler            --MCP-->        ^
    MCP client)  --A2A-->  Priority Scorer     --MCP-->        |
        |                                                       |
        +----------------------- MCP (final write) -------------+
        |
        v
   Audit Log MCP Server (SQLite) <-- MCP -- Coordinator
```

## Key design decisions

- **GitHub's MCP server is reused** (hosted, PAT-authenticated) rather than rebuilt - real tool schemas were inspected live (`list_tools()`, `inputSchema`) rather than assumed, which surfaced real facts: `search_issues` does semantic (not keyword) matching, labels are a flat `labels: string[]` on `issue_write`, and there's no "list all labels" tool at all - so the label taxonomy (`taxonomy.py`) is our own fixed, documented convention.
- **The audit log MCP server is built from scratch** specifically to get hands-on MCP *server*-authoring experience, not just client usage.
- **Reconciliation is deterministic code, not a fourth "judge" LLM call** (`coordinator/reconcile.py`): duplicate-confidence bands (>=0.8 "likely", 0.5-0.8 "possible", below that not mentioned), a `type == "question"` -> priority capped at `p2` rule, and missing-specialist handling as a first-class outcome, not an exception. This is boring on purpose - boring is auditable, unit-testable, and lets you report a real number like "the priority cap fired on X% of issues."
- **The system never auto-closes issues or auto-merges PRs.** GitHub's `issue_write` actually supports `state_reason: "duplicate"` natively, but using it requires also setting `state: closed` - which would take the decision out of the maintainer's hands. The Duplicate Detector only ever *flags* a candidate in a comment.
- **Real bugs found via live runs, not assumed away**: `candidate_issue_number` renders as `1.0` not `1` because protobuf's `Struct` type stores all numbers as doubles; `response_format: json_schema` is not reliably enforced by free-tier models (confirmed empirically - one returned plain prose, ignoring the schema entirely); and this project's chosen free model intermittently returns empty content with `finish_reason: "stop"` and normal token usage (~1-in-3, confirmed via `usage`/`finish_reason` inspection, not assumed to be a token-budget issue) - handled with bounded retries rather than silently trusting the first response.
