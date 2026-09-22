# 0003. Agents first, human viewer second

- Status: accepted
- Date: 2026-09-21

## Decision
The product core is a headless planning engine behind an MCP server. The web viewer exists so humans can watch and verify what agents plan; it is not a full desktop GIS.

## Consequences
Every capability ships as an API and MCP tool before it gets any UI. Determinism and provenance are first-class requirements.
