"""Tests for the best-effort FalconView drawing importer
(docs/specs/fv-drawing-import.md, decision 0012).

_parse_main_rows is pure logic over plain dicts shaped like
access_parser.AccessParser.parse_table()'s return value -- no real
.mdb file needed (none could be constructed; see the spec's "Testing
strategy"). import_fv_drawing's I/O wrapper is tested separately with
a fake AccessParser, since no permissively-licensed library can write
a real Access database to use as a fixture.
"""

from __future__ import annotations

from turnpoint.formats.fvimport.drawing import _parse_main_rows, import_fv_drawing


def _table(feature_nums, types, data) -> dict[str, list]:
    return {"FEATURE_NUM": feature_nums, "TYPE": types, "DATA": data}


def test_line_full_fidelity():
    table = _table(
        [1],
        ["LINE"],
        [
            "DATA_TYPE_MOVETO=N38.000000W77.000000;DATA_TYPE_LINETO=N39.000000W76.000000;DATA_TYPE_COLOR=5"
        ],
    )
    features, skipped = _parse_main_rows(table)
    assert len(features) == 1
    f = features[0]
    assert f.geometry_type == "line"
    assert f.coordinates == [(38.0, -77.0), (39.0, -76.0)]
    assert f.properties["DATA_TYPE_COLOR"] == "5"
    assert f.properties["fv_feature_type"] == "LINE"
    assert skipped == []  # no shape-fidelity note for LINE


def test_text_full_fidelity():
    data = (
        "DATA_TYPE_CENTER=N38.500000W77.500000;DATA_TYPE_TEXT=Notional Label;DATA_TYPE_FONT=Arial"
    )
    table = _table([1], ["TEXT"], [data])
    features, skipped = _parse_main_rows(table)
    assert len(features) == 1
    f = features[0]
    assert f.geometry_type == "point"
    assert f.coordinates == [(38.5, -77.5)]
    assert f.properties["DATA_TYPE_TEXT"] == "Notional Label"
    assert f.properties["DATA_TYPE_FONT"] == "Arial"
    assert skipped == []  # text has no meaningful "shape" beyond position


def test_oval_imports_as_point_and_flags_shape_loss():
    table = _table([1], ["OVAL"], ["DATA_TYPE_CENTER=N38.000000W77.000000"])
    features, skipped = _parse_main_rows(table)
    assert len(features) == 1
    assert features[0].geometry_type == "point"
    assert len(skipped) == 1
    assert "shape/size not reconstructed" in skipped[0].reason


def test_rectangle_imports_as_point_and_flags_shape_loss():
    table = _table([1], ["RECTANGLE"], ["DATA_TYPE_CENTER=N38.000000W77.000000"])
    features, skipped = _parse_main_rows(table)
    assert len(features) == 1
    assert any("shape/size not reconstructed" in s.reason for s in skipped)


def test_bullseye_captures_fix_attrs_and_flags_shape_loss():
    table = _table(
        [1],
        ["BULLSEYE"],
        [
            "DATA_TYPE_CENTER=N38.000000W77.000000;DATA_TYPE_FIX_TEXT=KDCA;"
            "DATA_TYPE_FIX_BEARING=090/10"
        ],
    )
    features, skipped = _parse_main_rows(table)
    assert features[0].properties["DATA_TYPE_FIX_TEXT"] == "KDCA"
    assert features[0].properties["DATA_TYPE_FIX_BEARING"] == "090/10"
    assert any("shape/size not reconstructed" in s.reason for s in skipped)


def test_axis_without_center_is_skipped_entirely():
    table = _table([1], ["AXIS"], ["DATA_TYPE_LABEL=some axis"])
    features, skipped = _parse_main_rows(table)
    assert features == []
    assert any("missing DATA_TYPE_CENTER" in s.reason for s in skipped)


def test_unrecognized_type_is_skipped_not_silently_dropped():
    table = _table([1], ["SPLINE"], ["DATA_TYPE_CENTER=N38.000000W77.000000"])
    features, skipped = _parse_main_rows(table)
    assert features == []
    assert any("unrecognized/unassumed feature type" in s.reason for s in skipped)


def test_line_missing_moveto_is_skipped():
    table = _table([1], ["LINE"], ["DATA_TYPE_LINETO=N39.000000W76.000000"])
    features, skipped = _parse_main_rows(table)
    assert features == []
    assert any("missing DATA_TYPE_MOVETO" in s.reason for s in skipped)


def test_unparseable_coordinate_is_skipped():
    table = _table([1], ["OVAL"], ["DATA_TYPE_CENTER=not-a-coordinate"])
    features, skipped = _parse_main_rows(table)
    assert features == []
    assert any("unparseable coordinates" in s.reason for s in skipped)


def test_missing_type_or_data_columns_reported():
    table = {"FEATURE_NUM": [1], "SOMETHING_ELSE": ["x"]}
    features, skipped = _parse_main_rows(table)
    assert features == []
    assert len(skipped) == 1
    assert "assumption 1" in skipped[0].reason


def test_feature_num_column_is_optional():
    # No FEATURE_NUM-like column at all -- should still parse using the
    # row index as the item label, not crash.
    table = {"TYPE": ["LINE"], "DATA": ["DATA_TYPE_MOVETO=N1.0E1.0;DATA_TYPE_LINETO=N2.0E2.0"]}
    features, skipped = _parse_main_rows(table)
    assert len(features) == 1


def test_multiple_rows_mixed_outcomes():
    table = _table(
        [1, 2, 3],
        ["LINE", "SPLINE", "TEXT"],
        [
            "DATA_TYPE_MOVETO=N1.0E1.0;DATA_TYPE_LINETO=N2.0E2.0",
            "DATA_TYPE_CENTER=N1.0E1.0",
            "DATA_TYPE_CENTER=N1.0E1.0;DATA_TYPE_TEXT=hi",
        ],
    )
    features, skipped = _parse_main_rows(table)
    assert len(features) == 2  # line and text; spline unrecognized
    assert len(skipped) == 1


class _FakeAccessParser:
    """Stands in for access_parser.AccessParser -- no real .mdb fixture
    is possible (no permissively-licensed writer exists)."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.catalog = {"Main": 1}

    def parse_table(self, name: str) -> dict[str, list]:
        assert name == "Main"
        return {
            "FEATURE_NUM": [1],
            "TYPE": ["LINE"],
            "DATA": ["DATA_TYPE_MOVETO=N38.000000W77.000000;DATA_TYPE_LINETO=N39.000000W76.000000"],
        }


class _FakeAccessParserNoMain:
    def __init__(self, path: str) -> None:
        self.catalog = {"SomeOtherTable": 1}


def test_import_fv_drawing_end_to_end(monkeypatch):
    monkeypatch.setattr("access_parser.AccessParser", _FakeAccessParser)
    features, report = import_fv_drawing("fake.mdb")
    assert len(features) == 1
    assert features[0].geometry_type == "line"
    assert report.format == "fv-drawing"
    assert report.imported_count == 1
    assert report.fully_faithful


def test_import_fv_drawing_no_main_table(monkeypatch):
    monkeypatch.setattr("access_parser.AccessParser", _FakeAccessParserNoMain)
    features, report = import_fv_drawing("fake.mdb")
    assert features == []
    assert any("no 'Main' table" in s.reason for s in report.skipped)
