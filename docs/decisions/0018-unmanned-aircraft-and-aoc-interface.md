# 0018. Goal revision: planning for unmanned aircraft, and the interface to the AOC

- Status: proposed (accepted when the pull request that adds it is merged)
- Date: 2026-10-26

## Context

Turnpoint's goals (`docs/PLAN.md`, 2026-09-21) are to demonstrate AI-assisted development and to give
agentic systems a deterministic, scoreable mission planning testbed. Its yardstick so far has been
FalconView: an aircrew workflow for crewed aircraft. Phases 1–3 are done on that basis.

Two things changed in October 2026:

- Kevin expects Turnpoint to be used mostly to plan missions for **unmanned aircraft**, and to stand
  for the software between unmanned mission plans and operations and the **Air Operations Center
  (AOC)**, in a future with orders of magnitude more unmanned missions than crewed ones.
- Turnpoint became a component of the Acquisition Knowledge System (AKS), whose goal is to show AI
  architecting and simulating the Air Force enterprise, then AI used in it. In the AKS integrated
  plan, Turnpoint carries demonstration milestone D4: an unmanned mission planned in Turnpoint reaches
  the AOC as UCI messages over a degraded simulated network (GMNS), and humans approve it.

Planning unmanned missions at volume needs things a FalconView-style aircrew workflow does not:
vehicle envelopes, lost-link behavior, many plans at once, deconfliction between plans, and a
machine interface to the AOC.

## Decision

1. **Goals.** Keep both existing goals. Add a third: be an open reference for the software between
   unmanned mission plans and the AOC, planned in volume. Unmanned aircraft become the primary use;
   crewed planning stays supported.
2. **FalconView compatibility stays as built, but stops being the yardstick.** Import of FalconView
   drawing files and the existing formats remain. Phase 4 ("Breadth") stays demand-driven and ranks
   below the unmanned phases.
3. **Three new phases** (dates are the AKS baseline, proposed):
   - **Phase 5, unmanned plan model** (Sep–Dec 2027): notional vehicle classes with parametric
     envelopes; an autonomy envelope per plan (geofence, altitude block, time window); lost-link and
     contingency points; launch and recovery; a communications plan naming the link types GMNS
     simulates.
   - **Phase 6, batch planning and deconfliction** (Jan–Mar 2028): many plans at once,
     deconflicted in space and time against each other and against airspace, deterministically.
   - **Phase 7, AOC handoff over UCI** (Mar–May 2028): plans exported as schema-valid UCI messages,
     mapped to AOC-DFO's message classes, carried over GMNS; tasking and status received back.
4. **Turnpoint plans; it never commands a vehicle.** Plans go to the AOC for human approval. Turnpoint
   does not send control commands to any vehicle, real or simulated.

## Consequences

- `docs/PLAN.md` gains the third goal, scope additions and Phases 5–7; `README.md` describes Turnpoint
  as mission planning for crewed and uncrewed aircraft.
- The plan model (`docs/specs/plan-model.md`) needs a versioned extension for vehicles, envelopes and
  lost-link behavior. That is Phase 5's first spec.
- The scenario scorer gains envelope containment (Phase 5) and inter-plan conflicts (Phase 6).
- UCI work depends on the public Open Arsenal schemas. Their license must be recorded in
  `docs/THIRD_PARTY.md` before any schema is added, and a decision record is needed if it is not
  Apache, MIT or BSD.
- UCI encoding should come from the shared codec package GMNS is preparing (`sa-codecs`), not a
  second implementation here; see AKS ADR 0008 (proposed).
- All existing data rules hold: notional vehicle performance only, no real datalink or C2 parameters.

## Alternatives considered

- **Keep FalconView parity as the goal and add unmanned later.** Rejected: it spends effort on
  crewed-workflow breadth the expected users will not need, and leaves D4 without a planning tool.
- **A separate unmanned planning project.** Rejected: it would duplicate the planning core, terrain,
  airspace, scorer and MCP server Turnpoint already has.
- **Let Turnpoint command simulated vehicles directly.** Rejected: it bypasses the AOC and the human
  approval the AKS demonstration must show.

## Open items for Kevin

- Notional vehicle classes to model first (for example a small tactical UAS and a medium-altitude
  long-endurance class), all with obviously notional values.
- The scale target for Phase 6 (how many concurrent plans); this is an open question in the AKS vision.
- Whether the tagline change in `README.md` is the wording you want.
