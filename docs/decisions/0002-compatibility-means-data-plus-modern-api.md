# 0002. "Compatible" means data formats plus a modern API

- Status: accepted
- Date: 2026-09-21

## Context
FalconView's extension interfaces are Windows COM. Its surrounding suite interfaces (PFPS, JMPS, XPlan) are not public.

## Decision
Compatibility means handling FalconView data formats and offering a REST and MCP API modeled on the concepts of the FalconView SDK. No COM or plug-in binary parity.

## Consequences
Cross-platform. Existing FalconView plug-ins will not load.
