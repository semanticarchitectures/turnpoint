# 0001. Clean-room implementation under Apache 2.0

- Status: accepted
- Date: 2026-09-21

## Context
GTRI released FalconView source under the LGPL in 2009. Studying it would make format work easier but would arguably make Turnpoint a derivative work.

## Decision
Turnpoint is written clean-room from public sources only and licensed Apache 2.0, consistent with ENSIM and ENCAP. The protocol is in `CLEAN_ROOM.md`.

## Consequences
Format fidelity depends on public documentation and self-made sample files. Every format decision must cite a logged source.

## Alternatives considered
Reference the LGPL source and adopt LGPL; fork and modernize the LGPL code base.
