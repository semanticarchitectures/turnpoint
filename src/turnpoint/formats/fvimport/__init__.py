"""FalconView import adapters (neutral name, never "falconview" in a
module/class name, per AGENTS.md section 5). See docs/specs/fv-drawing-import.md
and decision 0012 -- built from partial public documentation with every
undocumented piece flagged as an explicit, numbered assumption."""

from turnpoint.formats.fvimport.drawing import import_fv_drawing

__all__ = ["import_fv_drawing"]
