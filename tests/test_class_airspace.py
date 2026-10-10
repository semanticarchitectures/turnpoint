"""tests/fixtures/class_airspace/sample.shp is a real excerpt (5 of 5612
records) of the FAA's own Class Airspace shapefile (SOURCES.md S-020),
not synthetic -- same real field values, real boundary coordinates."""

from pathlib import Path

import pytest

from turnpoint.aero import list_class_airspace_near, parse_class_airspace

FIXTURE = Path(__file__).parent / "fixtures" / "class_airspace" / "sample.shp"
CYCLE = "2026-09-03"


def test_parse_class_airspace_imports_all_records():
    airspaces, report = parse_class_airspace(FIXTURE, CYCLE)
    assert report.imported_count == 5
    assert {a.name for a in airspaces} == {
        "LOS ANGELES CLASS D",
        "ENTERPRISE CLASS E5",
        "SAN FRANCISCO CLASS B",
        "LONG ISLAND MACARTHUR AIRPORT CLASS C",
        "SOUTH FLORIDA LOW",
    }


def test_class_b_fields():
    airspaces, _ = parse_class_airspace(FIXTURE, CYCLE)
    sfo = next(a for a in airspaces if a.name == "SAN FRANCISCO CLASS B")
    assert sfo.airspace_class == "B"
    assert sfo.type_code == "CLASS"
    assert sfo.upper_val == pytest.approx(10000.0)
    assert sfo.upper_uom == "FT"
    assert sfo.upper_code == "MSL"
    assert sfo.upper_desc == "TI"
    assert sfo.lower_val == pytest.approx(4000.0)
    assert sfo.lower_uom == "FT"
    assert sfo.lower_code == "MSL"
    assert sfo.exclusion is False
    assert sfo.nasr_cycle == CYCLE
    # Real SFO-area coordinates, not a placeholder.
    lat, lon = sfo.boundary[0]
    assert lat == pytest.approx(37.47, abs=0.1)
    assert lon == pytest.approx(-121.96, abs=0.1)


def test_surface_based_class_e_floor():
    airspaces, _ = parse_class_airspace(FIXTURE, CYCLE)
    e5 = next(a for a in airspaces if a.name == "ENTERPRISE CLASS E5")
    assert e5.lower_val == pytest.approx(700.0)
    assert e5.lower_code == "SFC"


def test_not_applicable_altitude_sentinel_becomes_none():
    # The FAA's raw shapefile has UPPER_VAL=-9998 for these ("and above,"
    # no explicit ceiling) with UPPER_UOM/UPPER_CODE both blank -- that
    # combination means "no value," not a literal -9998 ft ceiling.
    airspaces, _ = parse_class_airspace(FIXTURE, CYCLE)
    e5 = next(a for a in airspaces if a.name == "ENTERPRISE CLASS E5")
    assert e5.upper_val is None
    assert e5.upper_desc == "AA"


def test_multipart_record_keeps_exterior_ring_and_flags_fidelity_issue():
    airspaces, report = parse_class_airspace(FIXTURE, CYCLE)
    south_fl = next(a for a in airspaces if a.name == "SOUTH FLORIDA LOW")
    assert len(south_fl.boundary) > 0
    assert not report.fully_faithful
    issue = next(i for i in report.skipped if "SOUTH FLORIDA LOW" in i.item)
    assert "polygon parts" in issue.reason


def test_boundary_is_lat_lon_not_lon_lat():
    # pyshp/shapefile convention is (lon, lat); Turnpoint's is (lat, lon)
    # everywhere else (OverlayFeature, Threat, geodesy) -- LA is a real
    # point near (34, -118), not (-118, 34).
    airspaces, _ = parse_class_airspace(FIXTURE, CYCLE)
    la = next(a for a in airspaces if a.name == "LOS ANGELES CLASS D")
    lat, lon = la.boundary[0]
    assert 30 < lat < 40
    assert -125 < lon < -115


def test_list_class_airspace_near():
    # San Francisco Class B's boundary centroid is near (37.6, -122.3);
    # Los Angeles Class D is ~550nm away -- well outside a 50nm radius.
    nearby, _ = list_class_airspace_near(37.6, -122.3, 50.0, FIXTURE, CYCLE)
    names = {a.name for a in nearby}
    assert "SAN FRANCISCO CLASS B" in names
    assert "LOS ANGELES CLASS D" not in names


def test_parse_class_airspace_reports_source_and_format():
    _, report = parse_class_airspace(FIXTURE, CYCLE)
    assert report.source_path == str(FIXTURE)
    assert report.format == "class-airspace-shapefile"
