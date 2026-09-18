# 0014. A React control panel comes later

**Status**: Accepted
**Date**: 2026-09-18

## Context
Only a custom UI can change settings, but building it before the paper gate would delay the first useful test by weeks.

## Decision
A React UI, using Supabase for login and data, is built after the paper gate once the useful screens are known.

## Consequences
Settings changes from the UI are requests, applied at the next restart after the close and checked against the ceilings. The paper-to-live switch stays off the UI.
