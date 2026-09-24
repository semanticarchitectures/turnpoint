"""Fidelity reports: every importer (src/turnpoint/formats/*) returns one.

Silent data loss is a bug (AGENTS.md section 4). See docs/specs/plan-model.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FidelityIssue:
    item: str
    reason: str


@dataclass(frozen=True)
class FidelityReport:
    source_path: str
    format: str
    imported_count: int
    skipped: list[FidelityIssue] = field(default_factory=list)

    @property
    def fully_faithful(self) -> bool:
        return len(self.skipped) == 0
