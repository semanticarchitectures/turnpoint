"""Print products: PDF exports built from a plan (docs/PLAN.md Phase 4).

Only a route card exists today -- turnpoints and legs as a table, not a
plotted chart image. Other product types can follow the same
``build_x(plan, ...) -> bytes`` shape whenever a concrete need appears.
"""

from turnpoint.products.route_card import build_route_card

__all__ = ["build_route_card"]
