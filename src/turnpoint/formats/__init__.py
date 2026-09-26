"""Import adapters. Every adapter maps to the plan model in ``turnpoint.core``
and returns a fidelity report. See docs/specs/. Third-party importers can
extend this set without changing Turnpoint code -- docs/specs/plugin-api.md,
decision 0014."""

from turnpoint.formats.fvimport import import_fv_drawing
from turnpoint.formats.geojson import import_geojson
from turnpoint.formats.gpx import import_gpx
from turnpoint.formats.kml import import_kml
from turnpoint.formats.registry import get_importer, list_importers, register_importer

register_importer("geojson", import_geojson)
register_importer("gpx", import_gpx)
register_importer("kml", import_kml)
register_importer("fv-drawing", import_fv_drawing)

__all__ = [
    "get_importer",
    "import_fv_drawing",
    "import_geojson",
    "import_gpx",
    "import_kml",
    "list_importers",
    "register_importer",
]
