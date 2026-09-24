# Format and model specs

Language-neutral specifications, one file per format or model. Each lists its
sources (by `SOURCES.md` ID), the mapping to the Turnpoint plan model, and open gaps.

- [`plan-model.md`](plan-model.md): the `Turnpoint`/`Route`/`Plan`/`Overlay`
  model, provenance events and fidelity reports.
- [`route-schema.md`](route-schema.md): JSON Schema for the wire/storage
  representation of the plan model.
- [`aero-data.md`](aero-data.md): `Airport`/`Navaid` model and FAA NASR
  CSV parsing.

Planned: `fv-drawing-import.md`, `fv-local-points-import.md`,
`scenario-format.md`.
