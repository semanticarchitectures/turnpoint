from pathlib import Path

import pytest

from turnpoint.formats import import_gpx

FIXTURES = Path(__file__).parent / "fixtures" / "gpx"


def test_imports_waypoint_route_track():
    features, report = import_gpx(FIXTURES / "sample.gpx")
    assert report.fully_faithful
    assert report.imported_count == 3
    types = [f.geometry_type for f in features]
    assert types == ["point", "line", "line"]


def test_waypoint_coordinates_and_name():
    features, _ = import_gpx(FIXTURES / "sample.gpx")
    assert features[0].coordinates == [(38.8521, -77.0377)]
    assert features[0].properties["name"] == "checkpoint alpha"


def test_route_becomes_line_with_all_points():
    features, _ = import_gpx(FIXTURES / "sample.gpx")
    route_feature = features[1]
    assert route_feature.coordinates == [(38.0, -77.0), (38.5, -76.0), (38.0, -75.0)]
    assert route_feature.properties["name"] == "notional route"


def test_track_segment_becomes_line():
    features, _ = import_gpx(FIXTURES / "sample.gpx")
    track_feature = features[2]
    assert track_feature.coordinates == [(37.0, -77.0), (37.5, -76.5)]
    assert track_feature.properties["name"] == "notional track"


def test_elevation_flagged_but_point_still_imports():
    features, report = import_gpx(FIXTURES / "edge_cases.gpx")
    wpt = next(f for f in features if f.geometry_type == "point")
    assert wpt.coordinates == [(38.8521, -77.0377)]
    assert any("elevation present in source" in i.reason for i in report.skipped)


def test_too_short_route_is_skipped_not_silently_dropped():
    features, report = import_gpx(FIXTURES / "edge_cases.gpx")
    assert not any(
        f.properties.get("name") == "too short route" for f in features if f.geometry_type == "line"
    )
    assert any("fewer than 2 points" in i.reason for i in report.skipped)


def test_track_elevation_flagged():
    _, report = import_gpx(FIXTURES / "edge_cases.gpx")
    assert any("tracks[0]" in i.item and "elevation present" in i.reason for i in report.skipped)


def test_malformed_gpx_raises_value_error(tmp_path: Path):
    bad = tmp_path / "bad.gpx"
    bad.write_text("<gpx><this is not valid gpx xml")
    with pytest.raises(ValueError):
        import_gpx(bad)


def test_source_path_and_format_recorded():
    path = FIXTURES / "sample.gpx"
    _, report = import_gpx(path)
    assert report.source_path == str(path)
    assert report.format == "gpx"
