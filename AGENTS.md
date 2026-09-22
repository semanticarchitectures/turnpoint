# AGENTS.md

Rules for AI coding assistants working in this repository, and for the people
directing them. These are hard constraints, not style preferences. If a task
conflicts with them, stop and say so.

## 1. Clean room

Turnpoint is an independent, Apache 2.0 implementation. To keep it that way:

- **Never** fetch, open, read, summarize or reproduce the FalconView source code
  released by GTRI under the LGPL, or any fork, mirror or derivative of it.
- **Never** write format or algorithm code "from memory" of how FalconView does it.
  Work from a cited public spec or from sample files in `tests/fixtures/`, and write
  the test first.
- **Never** use FalconView SDK or ICD documents unless `SOURCES.md` records written
  confirmation that this project may use them.
- Do not copy code from GPL or LGPL projects (QGIS, mdbtools, ArduPilot Mission
  Planner, QGroundControl). Reading their public *documentation* is fine.
- Full protocol: `CLEAN_ROOM.md`.

## 2. Data and classification boundary

- Public, unclassified, freely redistributable data only, in tests, docs, demos,
  issues and commit messages.
- Never add anything marked or plausibly CUI, FOUO, NOFORN, export-controlled,
  distribution-limited or classified. If unsure, leave it out and flag it.
- No real aircraft performance data and no real threat system parameters. Use
  obviously notional values (for example `NOTIONAL-SAM-A`, 20 km ring).
- `data/` is git-ignored. Do not work around that.

## 3. Cite sources

- Every format decision, constant and algorithm names its source in a comment or
  docstring, and the source has an entry in `SOURCES.md`.
- Every new dependency or data set gets an entry in `docs/THIRD_PARTY.md` with its
  license *before* it is added. Apache 2.0, MIT and BSD are fine. Anything else
  needs a decision record.

## 4. Flag gaps, do not invent

- If a spec is silent or a sample is ambiguous, record the gap in the relevant
  `docs/specs/*.md` file and raise it. Do not guess and move on.
- Importers produce a fidelity report listing everything they could not interpret.
  Silent data loss is a bug.

## 5. Naming and claims

- The project is **Turnpoint**. Do not use "FalconView" in package, module, class
  or binary names. Use `fvimport` style neutral names for the import adapter.
- The only compatibility claim allowed is "imports FalconView drawing and local
  point files", and only once tests demonstrate it.
- Every user-facing surface carries "not for operational use".

## 6. Engineering conventions

- Python 3.11+, `src/` layout, type hints everywhere, `ruff` for lint and format,
  `pytest` for tests.
- Determinism: same inputs and data versions give the same outputs. No wall-clock
  time, random seeds or network calls inside planning computations.
- Every MCP tool response names the data sets and versions it used.
- Numerical code is tested against published reference values, with the reference
  cited in the test.
- Record architectural decisions in `docs/decisions/` using the template there.
- Keep the AI-assisted development trail: meaningful commit messages, and keep the
  `Co-Authored-By` trailer when an assistant wrote the change.
