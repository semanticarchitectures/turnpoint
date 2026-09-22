# 0004. FalconView files are import-only; native storage is SQLite or GeoPackage

- Status: accepted
- Date: 2026-09-21

## Context
FalconView drawing, local point and threat files are Microsoft Access databases (SOURCES S-004). Permissively licensed Access readers exist for Python; writers effectively do not.

## Decision
Turnpoint imports FalconView files and stores plans natively in SQLite or GeoPackage. Writing FalconView files is deferred until a user needs it and it can be verified against a real installation.

## Consequences
No Access writer or Java sidecar. Less dependence on the ICDs. The public claim is "imports", never "round-trips".
