# Scenario format

JSON Schema for a Turnpoint scenario file: an area's data, an objective
and a list of notional threats, scored against a submitted route by
`turnpoint.scenario.score_route` (decision 0013). Not a wire format for
the API/MCP surface the way `route-schema.md` is — a scenario is a file
the caller names (`score_plan(plan_id, scenario_path)` over MCP, or
`GET /plans/{id}/score?scenario=<path>` over REST, where `scenario` is
resolved under `DATA_DIR` the same way `nasr_source` already is).

## Scenario

```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string", "minLength": 1},
    "description": {"type": "string", "default": ""},
    "dted_source": {"type": "string", "minLength": 1},
    "sample_interval_nm": {"type": "number", "exclusiveMinimum": 0, "default": 1.0},
    "objective": {"$ref": "#/definitions/objective"},
    "threats": {
      "type": "array",
      "items": {"$ref": "#/definitions/threat"},
      "default": []
    }
  },
  "required": ["name", "dted_source", "objective"],
  "additionalProperties": false
}
```

`dted_source` is used exactly as every other Turnpoint `dted_source`
argument: a path opened directly by `rasterio`, never validated against
a real elevation data set beyond that it opens — same caller
responsibility as `check_terrain_clearance`'s `dted_source`.

## `objective`

```json
{
  "type": "object",
  "properties": {
    "start": {"$ref": "#/definitions/point"},
    "end": {"$ref": "#/definitions/point"},
    "clearance_margin_ft": {"type": "number", "minimum": 0},
    "groundspeed_kt": {"type": ["number", "null"], "exclusiveMinimum": 0, "default": null},
    "target_ete_min": {"type": ["number", "null"], "exclusiveMinimum": 0, "default": null},
    "max_ete_min": {"type": ["number", "null"], "exclusiveMinimum": 0, "default": null}
  },
  "required": ["start", "end", "clearance_margin_ft"],
  "additionalProperties": false
}
```

- `start`/`end` name where the scored route must begin and end. A route
  whose first/last turnpoint is more than `OBJECTIVE_TOLERANCE_NM`
  (1.0 nm, `turnpoint.scenario.scorer`) from `start`/`end` scores 0 — it
  didn't attempt the tasking, no matter how clean the rest of it is
  (decision 0013).
- `clearance_margin_ft` is required, same as `check_terrain_clearance` —
  Turnpoint asserts no real-world minimum-obstacle-clearance value of
  its own (`AGENTS.md` section 2).
- `groundspeed_kt` is optional; timing is only scored when it's given
  (`Route.legs(groundspeed_kt)` needs it to compute `ete_min`).
  `target_ete_min`/`max_ete_min` are only meaningful with
  `groundspeed_kt` set, and are otherwise ignored.

## `point` (reused for `start`/`end`)

```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string", "minLength": 1},
    "lat": {"type": "number", "minimum": -90, "maximum": 90},
    "lon": {"type": "number", "minimum": -180, "maximum": 180},
    "altitude_ft": {"type": "number"}
  },
  "required": ["name", "lat", "lon", "altitude_ft"],
  "additionalProperties": false
}
```

## `threat`

Same fields as `core.Threat` (`docs/PLAN.md` Phase 3), minus the
store's `id`/`actor`/`created_at` — scenario threats are scored as pure
data and never written to `ThreatStore`.

```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string", "minLength": 1},
    "threat_type": {"type": "string", "minLength": 1},
    "lat": {"type": "number", "minimum": -90, "maximum": 90},
    "lon": {"type": "number", "minimum": -180, "maximum": 180},
    "engagement_radius_nm": {"type": "number", "exclusiveMinimum": 0},
    "sensor_height_ft": {"type": "number", "default": 0.0},
    "sidc": {"type": ["string", "null"], "default": null}
  },
  "required": ["name", "threat_type", "lat", "lon", "engagement_radius_nm"],
  "additionalProperties": false
}
```

`threat_type` should be a notional label ("NOTIONAL-SAM-A"), never a
real system's designation, same rule as `create_threat`
(`AGENTS.md` section 2).

## Score report (response shape, not stored)

```json
{
  "type": "object",
  "properties": {
    "scenario_name": {"type": "string"},
    "score": {"type": "number", "minimum": 0, "maximum": 100},
    "max_score": {"type": "number", "const": 100},
    "reached_objective": {"type": "boolean"},
    "clear": {"type": "boolean"},
    "clearance_violation_legs": {"type": "integer", "minimum": 0},
    "exposure": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "threat_name": {"type": "string"},
          "exposed": {"type": "boolean"}
        },
        "required": ["threat_name", "exposed"],
        "additionalProperties": false
      }
    },
    "ete_min": {"type": ["number", "null"]},
    "within_target_time": {"type": ["boolean", "null"]},
    "within_max_time": {"type": ["boolean", "null"]},
    "airspace_checked": {"type": "boolean", "const": false}
  },
  "required": [
    "scenario_name", "score", "max_score", "reached_objective", "clear",
    "clearance_violation_legs", "exposure", "ete_min", "within_target_time",
    "within_max_time", "airspace_checked"
  ],
  "additionalProperties": false
}
```

`airspace_checked` is always `false` — Turnpoint has no class-airspace
overlay yet (`docs/specs/aero-data.md` "Open gaps," decision 0013). It is
named explicitly rather than left out, so a caller never mistakes an
absent field for "airspace was fine."

## Open gaps

- No airspace scoring until a class-airspace overlay exists
  (`docs/specs/aero-data.md`, decision 0013). When it does, this spec
  gets an `airspace_penalty`/violation list and `airspace_checked`
  becomes conditionally `true`.
- `area` (a bounding box, named in `docs/PLAN.md`'s Phase 3 description
  of a scenario file) is not part of this v1 shape — nothing yet reads
  it; every check operates on the route and threats directly. Add it if
  a concrete consumer needs a declared area (for example, validating
  that `dted_source` actually covers the objective before scoring).
