# 0004. Taxable cash account, holding US dollars

**Status**: Accepted
**Date**: 2026-09-18

## Context
The Tax Court (2023) and the Federal Court of Appeal (2024) held that day trading inside a TFSA is a business, so its gains are taxable anyway. The system trades US-listed securities priced in USD.

## Decision
A taxable account at Interactive Brokers Canada, holding USD. Not a TFSA.

## Consequences
One currency conversion when funding, not per trade. An accountant is consulted before live trading on whether gains count as business income.
