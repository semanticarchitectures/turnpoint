"""Route card: a one-page printable PDF summarizing a plan's turnpoints
and legs (docs/PLAN.md Phase 4, "print products").

Deterministic like every other Turnpoint output (AGENTS.md section 6):
``build_route_card`` always returns the same bytes for the same plan and
legs. reportlab's ``invariant=1`` mode suppresses the wall-clock
creation/modification timestamps and document ID it would otherwise
embed; the only dates on the page are the plan's own
``created_at``/``updated_at``, never a fresh ``time.time()`` read at
render time.

Scope: a text/table route summary, not a plotted chart image -- printing
the route over a raster or vector chart background is a separate,
heavier feature (embedding a tile mosaic), deferred until a concrete
need appears (same "add it when needed" reasoning as decisions 0010,
0013 and 0014).
"""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from turnpoint import NOT_FOR_OPERATIONAL_USE
from turnpoint.core.route import Leg
from turnpoint.store import Plan

_BANNER_STYLE = ParagraphStyle(
    "Banner",
    fontSize=9,
    textColor=colors.white,
    backColor=colors.HexColor("#b91c1c"),
    alignment=1,  # centered -- reportlab has no named constant for this
    spaceAfter=12,
    borderPadding=4,
)

_HEADER_ROW_STYLE = [
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
]


def _styled_table(rows: list[list[str]]) -> Table:
    table = Table(rows, hAlign="LEFT")
    table.setStyle(TableStyle(_HEADER_ROW_STYLE))
    return table


def _turnpoints_table(plan: Plan) -> Table:
    header = ["Name", "Lat", "Lon", "Altitude (ft)"]
    rows = [header] + [
        [
            tp.name,
            f"{tp.lat:.5f}",
            f"{tp.lon:.5f}",
            f"{tp.altitude_ft:.0f}" if tp.altitude_ft is not None else "—",
        ]
        for tp in plan.turnpoints
    ]
    return _styled_table(rows)


def _legs_table(legs: list[Leg]) -> Table:
    header = ["From", "To", "Distance (nm)", "Course (°T)", "ETE (min)"]
    rows = [header] + [
        [
            leg.from_name,
            leg.to_name,
            f"{leg.distance_nm:.1f}",
            f"{leg.true_course_deg:.0f}",
            f"{leg.ete_min:.1f}" if leg.ete_min is not None else "—",
        ]
        for leg in legs
    ]
    return _styled_table(rows)


def build_route_card(plan: Plan, legs: list[Leg]) -> bytes:
    """Render a one-page PDF: plan header, turnpoints and legs.

    ``legs`` must be ``Route.legs()`` computed for ``plan`` -- same
    turnpoints, same order, optionally with ``groundspeed_kt`` for an
    ETE column.
    """
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        invariant=1,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
    )

    story = [
        Paragraph(NOT_FOR_OPERATIONAL_USE, _BANNER_STYLE),
        Paragraph(plan.name, styles["Title"]),
        Paragraph(
            f"Plan {plan.id} — created {plan.created_at}, updated {plan.updated_at}",
            styles["Normal"],
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("Turnpoints", styles["Heading2"]),
        _turnpoints_table(plan),
        Spacer(1, 0.2 * inch),
        Paragraph("Legs", styles["Heading2"]),
        _legs_table(legs),
    ]
    doc.build(story)
    return buf.getvalue()
