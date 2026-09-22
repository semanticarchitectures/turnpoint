# 0007. Plan model v1: altitude, Plan wrapper, provenance events

- Status: accepted
- Date: 2026-09-22

## Context
The Phase 1 exit criterion in `docs/PLAN.md` is an agent planning a
*terrain-clear* route. The v0 `Route`/`Turnpoint` model in
`src/turnpoint/core/route.py` has no altitude field, so terrain clearance
cannot be expressed. `docs/PLAN.md` also already claims "plan model v0" as
a delivered Phase 0 artifact, but no spec file existed for it until now
(`docs/specs/plan-model.md`).

## Decision
Add `altitude_ft: float | None` to `Turnpoint` (additive, backward
compatible). Introduce a `Plan` model above `Route`: an identified,
persisted wrapper (`id`, `name`, `turnpoints`, `created_at`, `updated_at`)
that converts to a `Route` for leg math rather than duplicating it.
Introduce an append-only provenance event per plan mutation (`actor`,
`tool_call`, `tool_call_args`, `created_at`, `parent_event_id`), satisfying
the provenance agent-interface property in `docs/PLAN.md`. Full shapes are
in `docs/specs/plan-model.md` and `docs/specs/route-schema.md`.

## Consequences
`src/turnpoint/store` and `src/turnpoint/api` can now be built against a
documented schema instead of an implicit one. Existing `Route`/`Turnpoint`
construction in `core/route.py` and the MCP server's `compute_route_legs`
tool keep working unchanged, since `altitude_ft` defaults to `None`.
Terrain-clearance checking (Phase 1 `terrain` module) depends on this field
being populated by the caller; it is never inferred.

## Alternatives considered
Store altitude as an optional field on `Leg` instead of `Turnpoint`
(rejected: altitude is a property of a planned point, not a derived leg
value, and `Leg` stays purely computed per `docs/specs/plan-model.md`).
Model climb/descent profiles now (rejected as premature — no consumer
needs it yet; flagged as an open gap instead of guessed at).
