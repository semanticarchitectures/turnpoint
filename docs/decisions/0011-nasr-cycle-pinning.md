# 0011. FAA NASR data: caller-supplied cycle, no live fetch

- Status: accepted
- Date: 2026-09-24

## Context
FAA NASR airport/navaid data (`docs/specs/aero-data.md`) refreshes every
28 days and is published as CSV. `AGENTS.md` §6 requires every MCP tool
response to name the data set and version it used, and determinism
(`AGENTS.md` §6) forbids network calls inside planning computations.

## Decision
`src/turnpoint/aero/nasr.py`'s parsing and query functions take the CSV
file path and the NASR cycle date (e.g. `"2026-08-06"`) as required
caller-supplied arguments — never read from the file's contents, never
fetched from the FAA over the network, never inferred as "whatever's
current." Every result carries `nasr_cycle` on each `Airport`/`Navaid`,
and every MCP/API response names it in `meta`.

## Consequences
A result is always reproducible against a stated data version, matching
how `terrain.elevation_m`'s `dted_source` and `tiles`' tile sources
already work — the operator supplies the data file and asserts which
version it is. Fetching and updating NASR extracts is an operational
concern outside this repo, not something Turnpoint automates.

## Alternatives considered
Auto-download the current NASR cycle at query time (rejected: a network
call inside a planning-adjacent computation, and "current" is not a
reproducible answer — the same query could return different data on
different days with no record of which cycle produced a given result).
