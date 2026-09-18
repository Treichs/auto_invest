# 0007. Code structure is ports and adapters

**Status**: Accepted
**Date**: 2026-09-18

## Context
The rubric must run on two engines and be tested without either.

## Decision
The rubric is plain Python over simple data objects. Each engine gets a thin adapter that builds those objects and acts on the verdict.

## Consequences
The rubric package imports no trading engine, and a test enforces it. Moving between engines changes only an adapter.
