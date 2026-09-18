# 0015. Claude builds the system and reviews the journal, never trades

**Status**: Accepted
**Date**: 2026-09-18

## Context
A decision made by a language model cannot be replayed over history, so it cannot pass the stage gates.

## Decision
No language model in the order path. Claude Code writes and tests the code and reviews the journal after the close.

## Consequences
Every trading decision is code with a recorded rubric version. Claude Code never sets live mode, raises a ceiling, or places an order.
