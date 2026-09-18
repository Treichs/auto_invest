# auto_invest

Global rules in `~/.claude/CLAUDE.md` apply here and are not repeated.

## About the project

A personal automated trading system for US index ETFs through Interactive Brokers Canada. Every trade passes a two-tier rubric (eight must-pass checks, then a five-component signal score) inside hard limits that sit outside the strategy. Research runs on QuantConnect's free plan with LEAN; paper and live run on self-hosted NautilusTrader. The rubric is plain Python with ports and adapters, so it is tested alone and ported between engines by swapping a thin adapter.

## Non-negotiable rules

- Plan first in plain language, then wait for approval before changing anything.
- Existing, maintained libraries before custom code. Names come from the blueprint, never invented.
- Every rubric function has tests. A check that cannot be evaluated fails.
- The rubric package imports no trading engine.
- No loose comments in code. Tidy folders. No file or folder lists in documentation.
- Decisions are recorded as architecture decision records, one short file per decision, from the template in the ADR folder.
- Never commit secrets. Credentials live only in `.env`, which Git ignores and Claude Code cannot read. `.env` is the only real environment file.
- Never set trading mode to live, never raise a hard ceiling, never edit `config/ceilings.toml`, and never place an order outside the paper account. Those are the owner's alone.
- Never push without being asked.

## Key commands

Run from the repo root.

- `uv sync` installs the pinned Python and every dependency into `.venv`.
- `uv run pytest` runs the tests.
- `pre-commit run --all-files` runs the secret scanner over every file; it also runs on each commit.

## Doc links

- [Blueprint](docs/blueprint.md): the approved design.
- [Build plan](docs/build-plan.md): the eight phases and their exit criteria.
- [Architecture decision records](docs/adr/): one file per locked decision.
- Specs land in `docs/superpowers/specs/` and plans in `docs/superpowers/plans/`, written by the Superpowers plugin.
