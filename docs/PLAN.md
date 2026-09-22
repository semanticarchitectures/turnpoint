# Turnpoint project plan

As of 2026-09-21. Decisions are recorded individually in `docs/decisions/`.

## Purpose

Build an Apache 2.0, cross-platform, agent-drivable mission planning GIS that imports
FalconView data. An LGPL open-source FalconView has existed since 2009; it is a Windows
C++ desktop application with COM extension points. The gap Turnpoint fills is an open
mission planning tool whose whole planning surface is available to software agents.

Goals: (1) demonstrate AI-assisted development, with the repo history as evidence;
(2) give agentic systems a deterministic, scoreable mission planning testbed.

## Scope

In: raster map display; routes with leg math, timing and simple parametric fuel;
overlays for points, drawings, notional threats, airspace, airports and navaids;
elevation query, profile, line-of-sight and masking; coordinate tools (lat/long, MGRS,
UTM, magnetic variation); import of FalconView drawing and local point files; import
and export of KML, GeoJSON and GPX; API and MCP server for every operation.

Out: COM or plug-in binary parity; PFPS, JMPS or XPlan integration; aircraft-specific
performance and weapons planning; real threat parameters; any CUI or classified data;
writing FalconView files (deferred until a user needs it); operational certification.

## Architecture

```
Agents (MCP clients) --> MCP server --\
                                        >--> Planning core --> formats | terrain+geodesy | aero | plan store
Human (web viewer) --> REST/WS API ---/
Tile service (GDAL: CADRG, CIB, GeoTIFF) --> viewer and core
```

Python core, TypeScript viewer on MapLibre GL JS, SQLite or GeoPackage for storage.
The plan model is the key design artifact: a documented schema that every external
format maps to and from.

## Agent interface properties

- **Determinism:** same inputs and data versions, same outputs; responses name the data used.
- **Provenance:** every plan change records the actor and the tool call that made it.
- **Scenario harness:** scenario files define area, data, constraints and objectives; a
  scorer checks terrain clearance, airspace, timing and threat exposure.

## Phases

| Phase | Delivers | Exit criterion |
| --- | --- | --- |
| 0. Foundations | Verified capability and format inventory, source log, repo and rules, plan model v0 | Inventory confirmed or corrected; plan model reviewed |
| 1. Plan a route | GeoTIFF and CADRG tiles, DTED queries, route model and leg math, MCP tools, minimal viewer | An agent plans a terrain-clear route between two airfields from a one-paragraph tasking; a human sees it on the map |
| 2. Exchange | FAA aero data overlay; drawing and local point import with fidelity reports; KML, GeoJSON, GPX | Sample files import with a fidelity report and an agent uses the imported overlays |
| 3. Threat and terrain | Line-of-sight, masking, notional threats, MIL-STD-2525 symbols, plug-in API, scenario scorer | Two agent systems run one scenario and get comparable scores |
| 4. Breadth | Track feeds, print products, chart updates, labeling, route file import, FalconView file writing if needed | Demand-driven |

Estimate: Phases 0 and 1 in roughly 6 to 8 weeks elapsed with one architect at half-time
directing an AI coding agent; Phase 2 roughly 2 to 4 more weeks. Judgment estimates only.

## Risks

| Risk | Mitigation |
| --- | --- |
| ICDs are license-restricted for non-government use | Import-only; FalconView I/O is an adapter, not the core; decode from self-made samples |
| Unbounded "as close as possible" scope | Tiered parity; agents first; every phase ends in a demo |
| Clean-room contamination through an AI assistant | Spec-and-test-driven format code; `SOURCES.md`; `AGENTS.md` |
| Trademark or appearance of an official tool | Own name; disclaimers; GTRI contacted 2026-09-21 |
| Sensitive data drifting into a public repo | Public-only rule; marking check in pre-commit and CI; `data/` ignored |
| Plausible but unsafe agent plans | Scorer enforces hard constraints; "not for operational use" everywhere |

## Open items

- Route file (`.rte`) strategy: own documented route schema is primary; `.rte` import is best effort.
- Relationship to ENCAP and the program office knowledge base: separate repos, one-directional use.
- Trademark search on "Turnpoint" before the first tagged release.
- Short export-control review before the first tagged release.
