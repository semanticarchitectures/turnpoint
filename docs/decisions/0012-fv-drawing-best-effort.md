# 0012. FalconView drawing import: best-effort with documented assumptions

- Status: accepted
- Date: 2026-09-24

## Context
`docs/specs/fv-drawing-import.md`'s research turned up only partial
public documentation of the FalconView drawing file format (the `Main`
table has 3 fields and six feature types exist, with some named
attributes — `SOURCES.md` S-004, S-012, S-013) and none at all for local
points. The literal `Main` table column names, the `type` field's
encoding, and the `data` field's packing scheme are not publicly
documented anywhere legitimately accessible. A FalconView SDK/ICD
document surfaced in search results but was not opened — forbidden by
`AGENTS.md` §1 without written permission, which is not on file (see
`CLEAN_ROOM.md`'s outreach log).

## Decision
Build the drawing importer (`src/turnpoint/formats/fvimport/drawing.py`)
against the documented subset, with every undocumented piece filled by an
explicit, individually numbered, code-commented assumption (spec's
"ASSUMED" section) rather than leaving the importer unwritten. Every
assumption reuses documented vocabulary where one exists (the
`DATA_TYPE_*` attribute names) rather than inventing new terms. Where an
assumption causes real fidelity loss (Oval/Rectangle/Bullseye/Axis shape
data), every affected feature gets an explicit `FidelityIssue` — the
importer never claims fidelity it doesn't have.

Local points import (previously planned as a separate milestone) is not
attempted at all: zero public documentation exists for that file's
structure, so there is nothing non-invented to build against.

## Consequences
This importer will very likely not correctly parse a real
FalconView-authored drawing file, since 3 of 4 assumptions concern the
file's actual binary/text encoding. Its value is: (1) proving the
`Overlay`/`FidelityReport` pattern extends to a database-backed format,
not just text formats, (2) giving real FalconView data a place to land
the moment the assumptions are checked and corrected, and (3) making
every guess visible and numbered so correcting them later is a targeted
diff, not a rewrite. `docs/specs/fv-drawing-import.md`'s "ASSUMED"
section is the checklist for that correction.

## Alternatives considered
Defer the entire milestone until real documentation or GTRI permission
exists (rejected per explicit direction: proceed best-effort now, with
assumptions documented for later review). Silently guess without
flagging which parts are sourced vs. invented (rejected: indistinguishable
from the "write format code from memory" `AGENTS.md` §1 forbids, and
would make future correction much harder to target).
