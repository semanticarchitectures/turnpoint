# 0013. Scenario format and scorer: JSON file, fixed-penalty rubric, no airspace yet

- Status: accepted
- Date: 2026-09-26

## Context

`docs/PLAN.md` Phase 3 calls for a "scenario harness: scenario files define
area, data, constraints and objectives; a scorer checks terrain clearance,
airspace, timing and threat exposure," with exit criterion "two agent
systems run one scenario and get comparable scores." No scenario file
format exists yet (`docs/specs/README.md` lists `scenario-format.md` as
"planned"); `scenarios/phase1-demo` and `phase2-demo` are walkthrough
scripts for a one-paragraph tasking, not reusable scenario definitions or
a scorer.

Two of the scorer's four named axes already have building blocks:
`turnpoint.terrain.terrain_clear` (M6) and `turnpoint.terrain.route_exposure`
(M22). Timing falls out of `Route.legs(groundspeed_kt)` (M1). Airspace does
not: `docs/specs/aero-data.md`'s "Open gaps" explicitly defers class
airspace to Phase 3 as a separate overlay-and-import effort (FAA airspace
shapefiles, a new importer, a new overlay type) — building that is a
project on the scale of M14 (NASR airports/navaids) by itself, not
something to fold into a scorer's first cut.

## Decision

**Format:** the scenario file is JSON, not YAML — no new dependency
(`AGENTS.md` rule 3), and it sits next to every other Turnpoint wire
format (`docs/specs/route-schema.md`, `plan-model.md`), which are already
all JSON Schema. Full shape in `docs/specs/scenario-format.md`. A scenario
names one `dted_source` (used the same way every other Turnpoint call
already uses it — a caller-supplied path, opened directly, never
sandboxed by the MCP server; the REST route sandboxes the *scenario file
path itself* under `DATA_DIR`, matching `nasr_source`'s existing REST
precedent, since that field is new API-facing input this decision adds),
an `objective` (start/end points, required `clearance_margin_ft`, optional
`groundspeed_kt`/`target_ete_min`/`max_ete_min` for timing), and a list of
inline notional threats (same shape as `core.Threat`, minus the store's
`id`/`actor`/`created_at` — scoring never persists them; they are scored
as pure data, not written to `ThreatStore`).

**Airspace: not scored.** `ScoreReport.airspace_checked` is always
`False`, named and returned in every result, not silently omitted — the
same "flag the gap" instinct as a `FidelityReport` (`AGENTS.md` section
4). No airspace penalty is charged for or against a route. Revisit once a
class-airspace overlay exists.

**Objective reached is a gate, not a penalty.** A route whose first/last
turnpoint isn't within `OBJECTIVE_TOLERANCE_NM` (1.0 nm) of the
objective's start/end hasn't attempted the tasking; `ScoreReport.score` is
0 regardless of how clean the rest of it is, but every other field is
still computed and returned — an agent can see *why* it scored zero, not
just that it did.

**Scoring is a fixed-penalty rubric, not weighted or learned:**

- `CLEARANCE_VIOLATION_PENALTY_PER_LEG = 25.0` — once per leg with any
  terrain-clearance sample below margin, not per sample (a leg either
  threads the terrain or it doesn't; penalizing per-sample would reward
  finer `sample_interval_nm` with a worse score for the same route).
- `THREAT_EXPOSURE_PENALTY_PER_THREAT = 15.0` — once per threat with any
  exposed sample anywhere on the route, same reasoning.
- `LATE_ARRIVAL_PENALTY_PER_MIN = 1.0` — only if `target_ete_min` is set
  and exceeded.
- `OVER_MAX_ETE_PENALTY = 30.0` — flat, only if `max_ete_min` is set and
  exceeded.
- Starts from `MAX_SCORE = 100.0`, floored at 0.

These numbers are Turnpoint's own rubric, not a claim about real-world
severity (`AGENTS.md` section 2 is about notional threat *parameters*,
not scoring weights — but the same spirit applies: these are arbitrary
and documented as such, not cited to any external standard, because none
exists for "how bad is a terrain violation compared to a late arrival").
Revisit with real usage; a fixed, inspectable rubric beats a
plausible-looking weighted score nobody can audit.

**No persistence.** `score_route(route, scenario)` is a pure function over
already-persisted inputs (a `Plan` via its `Route`, a scenario file) —
same shape as `terrain_clear`/`route_exposure`. Nothing about a scoring
run is stored; call it again and get the same answer (`AGENTS.md` section
6 determinism).

## Consequences

`src/turnpoint/scenario/` is a new top-level package (`scenario.py` for
loading/validating the JSON file, `scorer.py` for `score_route`), plus one
new MCP tool (`score_plan`) and REST route (`GET /plans/{id}/score`).
`scenarios/phase3-demo/` gets a scenario file and a demo script showing
two different routes against the same scenario producing different,
reproducible scores — the exit criterion's "comparable scores," without
needing two actual independent agent systems to demonstrate the harness
works.

## Alternatives considered

YAML for the scenario file (rejected: new dependency, `AGENTS.md` rule 3,
for a format Turnpoint uses nowhere else). A weighted/normalized score in
`[0, 1]` (rejected: hides the rubric behind arithmetic a reader has to
reverse-engineer; a flat-penalty integer-ish score down from 100 is
legible without opening the source). Persisting scoring runs alongside
plans (rejected as premature — nothing yet consumes score history; add a
store table if a concrete need appears, same reasoning as decision
0010's rejected per-overlay provenance chain).
