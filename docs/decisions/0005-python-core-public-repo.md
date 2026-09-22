# 0005. Python core, TypeScript viewer, public from the first commit

- Status: accepted
- Date: 2026-09-21

## Decision
The planning core, format library, tile service and MCP server are Python 3.11+. The viewer is TypeScript on MapLibre GL JS. The repository is public from its first commit.

## Consequences
GDAL, PROJ, geodesy and MCP tooling are first-class. A second language sits next to ENCAP's TypeScript monorepo; the format specs in `docs/specs/` are language-neutral with shared test vectors to keep a port possible. Being public from day one makes the AI-assisted development trail and the clean-room record fully visible, and means the data boundary must hold from the first commit.
