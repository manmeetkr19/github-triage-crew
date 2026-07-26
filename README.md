# GitHub Issue Triage Crew

A multi-agent system that triages newly opened GitHub issues: flags likely duplicates, applies type/priority labels, and posts one comment explaining its reasoning - built to learn MCP (tool access) and A2A (agent-to-agent coordination) hands-on, not through a framework that hides the protocols.

## The problem

Maintainers manually triage every new issue: check for duplicates, assign labels, judge priority. It doesn't scale, and backlogs grow faster than triage capacity. This system automates the first pass while keeping a human in the loop - it never auto-closes issues or auto-merges PRs, it only labels, flags, and explains.

## Architecture

- **Coordinator** (`coordinator/coordinator.py`) - an A2A *client* to three specialists, run in parallel via `asyncio.gather`, each with its own timeout. Reconciles their verdicts deterministically (`coordinator/reconcile.py` - pure, unit-tested rules, not a fourth "judge" LLM call) and performs the final GitHub write.
- **Three specialist agents**, each a standalone A2A *server* with its own Agent Card:
  - `agents/duplicate_detector.py` - semantic duplicate search via GitHub's MCP `search_issues` tool
  - `agents/labeler.py` - classifies type (bug/feature/question/docs)
  - `agents/priority_scorer.py` - scores priority (p0-p3)
- **GitHub MCP Server** - reused, GitHub's official hosted server (`clients/github_mcp_client.py` is the client wrapper).
- **Audit Log MCP Server** (`mcp_servers/audit_log_server.py`) - built from scratch (SQLite-backed), records every decision and each specialist's raw reasoning.

See `docs/ARCHITECTURE.md` for the full diagram and design rationale.

## Setup

1. `python -m venv .venv && .venv/Scripts/pip install -r requirements.txt` (or `bin/pip` on Linux/Mac)
2. Copy `.env.example` to `.env` and fill in:
   - `GITHUB_TOKEN` - a PAT with `Contents: Read and write` (this repo) and `Issues: Read and write` (target repo)
   - `OPENROUTER_API_KEY` - from [openrouter.ai/keys](https://openrouter.ai/keys)
   - `OPENROUTER_MODEL` - a free/cheap tool-calling-capable model
   - `GITHUB_REPO` - the `owner/repo` this crew operates on
3. Start the four servers: `python agents/duplicate_detector.py`, `agents/labeler.py`, `agents/priority_scorer.py`, `mcp_servers/audit_log_server.py`
4. Run the coordinator against one issue: see `scripts/06_test_coordinator.py`

## Real-world deployment

`.github/workflows/triage.yml` triggers on `issues: opened`. It must be pushed to the **target** repo being triaged (not this source repo) - GitHub only fires events for workflows defined in the repo the event happens in. The workflow checks out this source repo as a step, then runs the same four processes inside the CI job. Requires three repo secrets on the target repo: `CREW_GITHUB_TOKEN`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`.

## Evaluation

`eval/seed_sandbox_issues.py` creates a known-answer test set (since a fresh sandbox repo has no real historical labels to compare against) with deliberate duplicate pairs. `eval/run_dry_run.py` replays it through the live specialists with no GitHub writes, and `eval/metrics.py` computes type-label accuracy, priority-label accuracy, and duplicate-detection precision/recall/F1.

**Known limitation**: OpenRouter's free tier caps at 50 requests/day per account. A full 10-issue eval run alone can approach that ceiling, and this genuinely affects the real triage workflow too if many issues open in one day. The fix is either waiting for the daily reset or a small one-time paid credit top-up (10 credits -> 1000 req/day) - a real tradeoff of building on a $0 LLM tier, not a bug in this system.

## Tests

`pytest tests/` - covers the reconciliation policy and eval metrics as pure functions (no network, no LLM, can't be flaky).
