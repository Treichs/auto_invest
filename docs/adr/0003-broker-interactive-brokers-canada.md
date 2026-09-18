# 0003. Broker is Interactive Brokers Canada

**Status**: Accepted
**Date**: 2026-09-18

## Context
Wealthsimple has no API and closes automated accounts. Alpaca does not accept Canadians. Questrade falls under a regulator rule that bars orders from a client-run automated system.

## Decision
Interactive Brokers Canada, through IB Gateway and the TWS API, trading US-listed securities only.

## Consequences
A phone approval of the login about once a week. Canadian-listed securities are out of scope.
