# Clean-room protocol

Turnpoint aims to interoperate with FalconView data without being derived from
FalconView. This document is the record that lets us, and anyone auditing the
project, check that claim.

## Allowed sources

- Public standards: MIL-STD-2411 (RPF), MIL-PRF-89038 (CADRG), MIL-PRF-89041 (CIB),
  MIL-PRF-89020 (DTED), MIL-STD-2525, ARINC 424, OGC and IETF specifications.
- Public web pages, published papers and briefings, and publicly posted manuals,
  provided they carry no distribution limitation.
- Sample files we create ourselves, or that are published with a license permitting
  this use. Each is logged in `SOURCES.md` with its origin.
- Permissively licensed third-party libraries unrelated to the FalconView code base
  (GDAL, PROJ, GeographicLib, MapLibre and so on).

## Forbidden sources

- The GTRI open-source FalconView tree (LGPL) and anything derived from it.
- FalconView SDK and ICD material, unless and until written permission covering an
  Apache 2.0 open project is recorded in `SOURCES.md`.
- Anything marked CUI, FOUO, export-controlled or distribution-limited.
- Decompiled or disassembled FalconView binaries.

## Procedure for format work

1. Open or update the spec file in `docs/specs/` and list the sources you will use.
2. Log each source in `SOURCES.md` before relying on it.
3. Write tests from the spec and sample files.
4. Implement against the tests.
5. Record anything undetermined as an open gap in the spec file.

## AI assistants

A language model may have seen FalconView source during training. We cannot verify
that either way, so format code must be traceable to a logged source and a test,
never to model recall. Reviewers reject format code that cites nothing.

## Offers of material from third parties

If GTRI or anyone else offers source, ICDs or sample files, get the terms in writing
and record them in `SOURCES.md` **before anyone opens the material**. If the terms
do not clearly permit use in an Apache 2.0 project, decline.

## Contributor declaration

By contributing you confirm that you have not consulted forbidden sources for the
contribution. If you have previously worked on FalconView source code, say so in
your first pull request and stay away from `src/turnpoint/formats/fvimport`.

## Log of outreach

| Date | Party | What | Outcome |
| --- | --- | --- | --- |
| 2026-09-21 | GTRI, via FalconView site contact form | Described the project, asked about collaboration | Awaiting reply |
