# FalconView drawing file import

Per `CLEAN_ROOM.md`'s procedure for format work: sources are listed and
logged *before* being relied on (done — `SOURCES.md` S-004, S-012, S-013),
then this spec is written, then tests, then implementation. This file
also serves the purpose decision-record-0012 describes: everything below
marked **ASSUMED** is this project's own invention, not sourced, and
should be the first thing checked if real FalconView documentation
becomes legitimately available later.

**A "FalconView Drawing File Format Interface Control Document" turned up
in public search results and was deliberately not opened or used** — that
is FalconView SDK/ICD material, forbidden by `AGENTS.md` §1 without
written permission logged in `SOURCES.md`, which does not exist (see
`CLEAN_ROOM.md`'s outreach log: GTRI has not replied). See `SOURCES.md`
S-013 for the exact note.

## DOCUMENTED (cited, not invented)

From the public FME reader documentation (S-004, S-012, S-013):

- Drawing files are Microsoft Access databases: `.mdb`, `.accdb`, or the
  native `.drw` extension.
- The database has exactly one table, **`Main`**, with **exactly 3
  fields**: feature number, type, data.
- Six feature types exist: **Line, Oval, Text, Bullseye, Rectangle,
  Axis**.
- Each feature type has named attributes (FME's own terms for what it
  exposes from the file — these names are real and cited, not invented):
  - Common to all: `DATA_TYPE_TOOLTIP`, `DATA_TYPE_HELP`,
    `DATA_TYPE_COMMENT`, `DATA_TYPE_COLOR`, `DATA_TYPE_COLOR2`,
    `DATA_TYPE_NAME`, `DATA_TYPE_LABEL`, `DATA_TYPE_LABEL_PARAM`,
    `DATA_TYPE_LABEL_OFFSET`, `DATA_TYPE_TEXT_PARAM`.
  - Line: `DATA_TYPE_MOVETO` (start point), `DATA_TYPE_LINETO` (end
    point), `DATA_TYPE_LINE_PARAM`.
  - Oval: `DATA_TYPE_CENTER`.
  - Text: `DATA_TYPE_CENTER`, `DATA_TYPE_TEXT`, `DATA_TYPE_FONT`.
  - Bullseye: `DATA_TYPE_FIX_TEXT`, `DATA_TYPE_FIX_BEARING`,
    `DATA_TYPE_CENTER`.
  - Rectangle: `DATA_TYPE_CENTER`.
  - Axis: has a documented *concept* (a crosshair with a width ratio) but
    **no named attribute** is given in the source for it or its ratio.
- Coordinate format: a string like `N50.123456W85.123456` — a hemisphere
  letter (`N`/`S`) directly prefixed to a decimal-degree latitude,
  immediately followed by a hemisphere letter (`E`/`W`) prefixed to a
  decimal-degree longitude. No separator between the two.
- Oval has "an angle, and horizontal and vertical radii"; Rectangle has
  "a height and width" — these are documented as *existing concepts*, but
  **no attribute name is given for any of them** in the source.

## ASSUMED (this project's invention — flag for review first)

Every item here is a guess, clearly labeled in code, made to produce a
working best-effort importer rather than nothing. None of it should be
treated as fact about real FalconView files.

1. **Literal `Main` table column names.** The source says "feature
   number, type, data" descriptively, not as literal column identifiers.
   Assumed: a column matching (case-insensitively) `FEATURE_NUM` or
   `FEATURE_NUMBER`; a column matching `TYPE` or `FEATURE_TYPE`; a column
   matching `DATA`. The importer looks for these candidates rather than
   hardcoding one exact string, and reports a fidelity issue naming the
   columns it actually found if none match.
2. **How the `type` field encodes which of the six feature types a row
   is.** Assumed: the field holds the type name itself, uppercase
   (`"LINE"`, `"OVAL"`, `"TEXT"`, `"BULLSEYE"`, `"RECTANGLE"`, `"AXIS"`),
   not a numeric or other code. A value not matching one of these six is
   reported as an unrecognized type, not silently skipped or guessed at.
3. **How the `data` field packs multiple named attributes into one
   column.** Assumed: a single delimited string,
   `DATA_TYPE_KEY=value;DATA_TYPE_KEY=value;...`, using the *documented*
   attribute names above as keys. This reuses real, cited names for the
   keys — the only invention is the delimiter/packing scheme itself, not
   the vocabulary.
4. **Shape/size fidelity for Oval, Rectangle, Bullseye and Axis.** Since
   no attribute name is documented for radii, height/width, ring count or
   width ratio, these four types import as a single **point** at their
   `DATA_TYPE_CENTER` only — their true 2D extent is not reconstructed.
   Every such feature gets an explicit `FidelityIssue` saying so (never
   silently reduced without comment, per `AGENTS.md` §4). **Line** and
   **Text** are not affected: a line's full 2-point geometry is captured
   from `MOVETO`/`LINETO`, and text has no meaningful "shape" beyond its
   position — its string content and font import into `properties`
   without loss.

## Mapping to `Overlay`

| FV feature type | `OverlayFeature.geometry_type` | Coordinates | Fidelity note |
| --- | --- | --- | --- |
| Line | `line` | `[MOVETO, LINETO]` | none — full fidelity |
| Text | `point` | `[CENTER]` | none — text/font preserved in `properties` |
| Oval | `point` | `[CENTER]` | angle/radii not reconstructed (assumption 4) |
| Rectangle | `point` | `[CENTER]` | height/width not reconstructed (assumption 4) |
| Bullseye | `point` | `[CENTER]` | ring count/spacing not reconstructed (assumption 4) |
| Axis | `point` | `[CENTER]` | width ratio not reconstructed (assumption 4); `CENTER` itself isn't in the documented attribute list either — if absent, the feature is skipped entirely and reported |

Every attribute the `data` field parses to, other than the ones used for
coordinates, lands verbatim in `OverlayFeature.properties` (plus
`fv_feature_type` naming the original FalconView type) — nothing parsed
is thrown away, even where the geometry itself is simplified.

## Testing strategy

`access-parser` (verified Apache-2.0, no `mdbtools` dependency,
`docs/THIRD_PARTY.md`) is read-only, and no permissively-licensed
Python library can *write* a `.mdb`/`.accdb` file — so a real binary
fixture can't be constructed the way GeoJSON/GPX/KML's text fixtures
were. The row-interpretation logic (`_parse_main_rows` in
`src/turnpoint/formats/fvimport/drawing.py`) is a pure function over
plain dicts shaped like `access_parser.AccessParser.parse_table()`'s
return value, so it's fully unit-tested without a real file. The
`AccessParser` I/O integration itself (opening a real `.mdb` and finding
the `Main` table) is **not exercised by a test** — same honestly-flagged
gap as Phase 1's CADRG path (`src/turnpoint/tiles/cadrg.py`).

## Open gaps

- All four numbered assumptions above are open until real documentation
  or written GTRI permission is available (`CLEAN_ROOM.md`'s outreach
  log).
- The `AccessParser` I/O path is untested against any real file.
- Threat files (a separate FME-documented module) are out of scope —
  only drawing files are covered here.
