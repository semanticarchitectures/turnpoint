#!/usr/bin/env python3
"""Demo the best-effort FalconView drawing importer (docs/specs/fv-drawing-import.md,
decision 0012) without a real .mdb file.

No permissively-licensed Python library can *write* an Access database,
so this fakes access_parser.AccessParser with a small in-memory Main
table -- the same technique tests/test_fv_drawing.py uses -- shaped like
what the importer's own documented assumptions expect. This demonstrates
the fidelity-report mechanism honestly: the Oval below degrades to a
point with an explicit flag, not a silent simplification.
"""

from __future__ import annotations

from unittest.mock import patch


class _FakeAccessParser:
    def __init__(self, path: str) -> None:
        self.catalog = {"Main": 1}

    def parse_table(self, name: str) -> dict[str, list]:
        return {
            "FEATURE_NUM": [1, 2, 3],
            "TYPE": ["LINE", "TEXT", "OVAL"],
            "DATA": [
                "DATA_TYPE_MOVETO=N38.852100W77.037700;"
                "DATA_TYPE_LINETO=N38.900000W77.000000;DATA_TYPE_COLOR=5",
                "DATA_TYPE_CENTER=N38.900000W77.000000;"
                "DATA_TYPE_TEXT=Notional checkpoint;DATA_TYPE_FONT=Arial",
                "DATA_TYPE_CENTER=N39.000000W76.500000",
            ],
        }


def main() -> None:
    from turnpoint.formats.fvimport.drawing import import_fv_drawing

    with patch("access_parser.AccessParser", _FakeAccessParser):
        features, report = import_fv_drawing("notional-sample.mdb")

    print(f"imported: {report.imported_count}  fully_faithful: {report.fully_faithful}")
    for f in features:
        print(f"  - {f.geometry_type} {f.coordinates} {f.properties}")
    print("fidelity issues:")
    for issue in report.skipped:
        print(f"  - {issue.item}: {issue.reason}")


if __name__ == "__main__":
    main()
