# Route/plan wire schema

JSON Schema for the representation shared by `src/turnpoint/store`,
`src/turnpoint/api`, and `src/turnpoint/mcp_server` — this is what a `Plan`
looks like on the wire (API responses, MCP tool arguments/results) and, with
`id`/`created_at`/`updated_at` stripped, what a bare `Route` looks like for
stateless calculation (`compute_route_legs`). See `docs/specs/plan-model.md`
for the model this schema encodes.

## Turnpoint

```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string", "minLength": 1},
    "lat": {"type": "number", "minimum": -90, "maximum": 90},
    "lon": {"type": "number", "minimum": -180, "maximum": 180},
    "altitude_ft": {"type": ["number", "null"], "default": null}
  },
  "required": ["name", "lat", "lon"],
  "additionalProperties": false
}
```

## Leg (response-only; never accepted as input, always computed)

```json
{
  "type": "object",
  "properties": {
    "from_name": {"type": "string"},
    "to_name": {"type": "string"},
    "distance_nm": {"type": "number", "minimum": 0},
    "true_course_deg": {"type": "number", "minimum": 0, "maximum": 360},
    "ete_min": {"type": ["number", "null"]}
  },
  "required": ["from_name", "to_name", "distance_nm", "true_course_deg"],
  "additionalProperties": false
}
```

## Plan

```json
{
  "type": "object",
  "properties": {
    "id": {"type": "string"},
    "name": {"type": "string", "minLength": 1},
    "turnpoints": {
      "type": "array",
      "items": {"$ref": "#/definitions/turnpoint"},
      "minItems": 2
    },
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"}
  },
  "required": ["id", "name", "turnpoints", "created_at", "updated_at"],
  "additionalProperties": false
}
```

`id`/`created_at`/`updated_at` are server-assigned; a `POST /plans` or
`create_plan` MCP call accepts only `name` and `turnpoints`.

## Provenance event

```json
{
  "type": "object",
  "properties": {
    "id": {"type": "string"},
    "plan_id": {"type": "string"},
    "actor": {"type": "string", "minLength": 1},
    "tool_call": {"type": "string", "minLength": 1},
    "tool_call_args": {"type": "object"},
    "created_at": {"type": "string", "format": "date-time"},
    "parent_event_id": {"type": ["string", "null"]}
  },
  "required": ["id", "plan_id", "actor", "tool_call", "created_at"],
  "additionalProperties": false
}
```

## Meta block

Every API and MCP response carries this alongside its payload (see the
shared helper introduced in M2 of `docs/PLAN.md`'s Phase 1 roadmap):

```json
{
  "type": "object",
  "properties": {
    "turnpoint_version": {"type": "string"},
    "datum": {"type": "string", "const": "WGS84"},
    "geodesic_model": {"type": "string"},
    "bearings": {"type": "string", "const": "degrees true"},
    "notice": {"type": "string"}
  },
  "required": ["turnpoint_version", "datum", "notice"]
}
```

## Open gaps

- No schema yet for a `ClearanceReport` (Phase 1 `terrain.terrain_clear`
  output) or tile-service error responses — add when those modules land
  rather than guessing their shape now.
