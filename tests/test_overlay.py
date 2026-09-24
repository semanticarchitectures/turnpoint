import pytest

from turnpoint.core import FidelityIssue, FidelityReport, Overlay, OverlayFeature


def test_point_feature_requires_one_coordinate():
    with pytest.raises(ValueError):
        OverlayFeature("point", [])
    OverlayFeature("point", [(0.0, 0.0)])  # does not raise


def test_line_feature_requires_two_coordinates():
    with pytest.raises(ValueError):
        OverlayFeature("line", [(0.0, 0.0)])
    OverlayFeature("line", [(0.0, 0.0), (0.0, 1.0)])  # does not raise


def test_polygon_feature_requires_three_coordinates():
    with pytest.raises(ValueError):
        OverlayFeature("polygon", [(0.0, 0.0), (0.0, 1.0)])
    OverlayFeature("polygon", [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)])  # does not raise


def test_overlay_holds_features():
    features = [OverlayFeature("point", [(0.0, 0.0)], {"name": "A"})]
    overlay = Overlay(
        id="1",
        name="test overlay",
        source_format="geojson",
        source_path="test.geojson",
        features=features,
        actor="tester",
        created_at="2026-09-23T00:00:00+00:00",
    )
    assert overlay.features[0].properties["name"] == "A"


def test_fidelity_report_fully_faithful_when_nothing_skipped():
    report = FidelityReport(source_path="a.geojson", format="geojson", imported_count=3)
    assert report.fully_faithful


def test_fidelity_report_not_faithful_when_something_skipped():
    report = FidelityReport(
        source_path="a.geojson",
        format="geojson",
        imported_count=2,
        skipped=[FidelityIssue(item="feature[2]", reason="unsupported geometry type")],
    )
    assert not report.fully_faithful
    assert report.skipped[0].reason == "unsupported geometry type"
