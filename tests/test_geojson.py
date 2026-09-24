from pathlib import Path

from turnpoint.formats import import_geojson

FIXTURES = Path(__file__).parent / "fixtures" / "geojson"


def test_imports_point_line_polygon():
    features, report = import_geojson(FIXTURES / "sample.geojson")
    assert report.fully_faithful
    assert report.imported_count == 3
    types = [f.geometry_type for f in features]
    assert types == ["point", "line", "polygon"]


def test_point_coordinates_are_lat_lon_not_lon_lat():
    features, _ = import_geojson(FIXTURES / "sample.geojson")
    point = features[0]
    # source is [lon=-77.0377, lat=38.8521]; OverlayFeature is (lat, lon).
    assert point.coordinates == [(38.8521, -77.0377)]


def test_properties_are_preserved():
    features, _ = import_geojson(FIXTURES / "sample.geojson")
    assert features[0].properties["name"] == "checkpoint alpha"


def test_unsupported_geometry_is_skipped_not_silently_dropped():
    features, report = import_geojson(FIXTURES / "edge_cases.geojson")
    assert not report.fully_faithful
    reasons = [issue.reason for issue in report.skipped]
    assert any("unsupported geometry type: MultiPoint" in r for r in reasons)
    assert any("no geometry" in r for r in reasons)
    # multipoint and null-geometry features are skipped, not imported
    assert all(f.properties.get("name") != "multipoint not supported" for f in features)


def test_altitude_is_flagged_but_point_still_imports():
    features, report = import_geojson(FIXTURES / "edge_cases.geojson")
    altitude_feature = next(f for f in features if f.properties["name"] == "point with altitude")
    assert altitude_feature.coordinates == [(38.8521, -77.0377)]
    assert any("altitude present in source" in issue.reason for issue in report.skipped)


def test_polygon_hole_is_flagged_but_exterior_still_imports():
    features, report = import_geojson(FIXTURES / "edge_cases.geojson")
    polygon = next(f for f in features if f.properties["name"] == "polygon with hole")
    assert len(polygon.coordinates) == 5  # exterior ring only
    assert any("polygon holes present" in issue.reason for issue in report.skipped)


def test_source_path_and_format_recorded():
    path = FIXTURES / "sample.geojson"
    _, report = import_geojson(path)
    assert report.source_path == str(path)
    assert report.format == "geojson"
