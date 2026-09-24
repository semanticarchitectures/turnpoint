from pathlib import Path

import pytest

from turnpoint.formats import import_kml

FIXTURES = Path(__file__).parent / "fixtures" / "kml"


def test_imports_point_line_polygon():
    features, report = import_kml(FIXTURES / "sample.kml")
    assert report.fully_faithful
    assert report.imported_count == 3
    assert [f.geometry_type for f in features] == ["point", "line", "polygon"]


def test_point_coordinates_are_lat_lon_not_lon_lat():
    features, _ = import_kml(FIXTURES / "sample.kml")
    assert features[0].coordinates == [(38.8521, -77.0377)]


def test_placemark_name_is_a_property():
    features, _ = import_kml(FIXTURES / "sample.kml")
    assert features[0].properties["name"] == "checkpoint alpha"


def test_placemark_inside_folder_is_found():
    features, _ = import_kml(FIXTURES / "sample.kml")
    assert features[1].properties["name"] == "notional boundary"
    assert features[1].geometry_type == "line"


def test_polygon_from_outer_boundary():
    features, _ = import_kml(FIXTURES / "sample.kml")
    polygon = features[2]
    assert polygon.geometry_type == "polygon"
    assert len(polygon.coordinates) == 5


def test_altitude_flagged_but_point_still_imports():
    features, report = import_kml(FIXTURES / "edge_cases.kml")
    point = next(f for f in features if f.properties.get("name") == "point with altitude")
    assert point.coordinates == [(38.8521, -77.0377)]
    assert any("altitude present in source" in i.reason for i in report.skipped)


def test_polygon_hole_flagged_but_exterior_still_imports():
    features, report = import_kml(FIXTURES / "edge_cases.kml")
    polygon = next(f for f in features if f.properties.get("name") == "polygon with hole")
    assert len(polygon.coordinates) == 5
    assert any("polygon holes present" in i.reason for i in report.skipped)


def test_no_geometry_is_skipped_not_silently_dropped():
    features, report = import_kml(FIXTURES / "edge_cases.kml")
    assert not any(f.properties.get("name") == "no geometry" for f in features)
    assert any(
        "no supported geometry" in i.reason and "no geometry" in i.item for i in report.skipped
    )


def test_multigeometry_imports_first_part_and_flags_the_rest():
    features, report = import_kml(FIXTURES / "edge_cases.kml")
    multi = next(f for f in features if f.properties.get("name") == "multigeometry")
    assert multi.geometry_type == "point"
    assert multi.coordinates == [(38.0, -77.0)]
    assert any("MultiGeometry has 2 parts" in i.reason for i in report.skipped)


def test_malformed_kml_raises_value_error(tmp_path: Path):
    bad = tmp_path / "bad.kml"
    bad.write_text("<kml><this is not valid xml")
    with pytest.raises(ValueError):
        import_kml(bad)


def test_source_path_and_format_recorded():
    path = FIXTURES / "sample.kml"
    _, report = import_kml(path)
    assert report.source_path == str(path)
    assert report.format == "kml"
