"""Fidelity reports: every importer (src/turnpoint/formats/*) returns one.

Silent data loss is a bug (AGENTS.md section 4). See docs/specs/plan-model.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


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


def fidelity_report_dict(report: FidelityReport) -> dict[str, Any]:
    """Serialize a FidelityReport for an API/MCP response.

    ``dataclasses.asdict`` only serializes fields, not the
    ``fully_faithful`` property — every caller needs that value, so it's
    added explicitly here rather than each call site remembering to.
    """
    return {**asdict(report), "fully_faithful": report.fully_faithful}
