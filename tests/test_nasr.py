from pathlib import Path

import pytest

from turnpoint.aero import (
    get_airport,
    get_navaid,
    list_airports_near,
    parse_airports,
    parse_navaids,
)

FIXTURES = Path(__file__).parent / "fixtures" / "nasr"
CYCLE = "2026-08-06"


def test_parse_airports():
    airports, report = parse_airports(FIXTURES / "apt_base_sample.csv", CYCLE)
    assert report.fully_faithful
    assert report.imported_count == 3
    assert [a.ident for a in airports] == ["TP01", "TP02", "TP03"]


def test_airport_fields():
    airports, _ = parse_airports(FIXTURES / "apt_base_sample.csv", CYCLE)
    a = airports[0]
    assert a.icao_id == "KTP1"
    assert a.name == "TURNPOINT TEST FIELD ONE"
    assert a.lat == pytest.approx(38.8521)
    assert a.lon == pytest.approx(-77.0377)
    assert a.elevation_ft == pytest.approx(15.0)
    assert a.site_type == "A"
    assert a.facility_use == "PU"
    assert a.nasr_cycle == CYCLE


def test_airport_missing_icao_is_none_not_error():
    airports, report = parse_airports(FIXTURES / "apt_base_sample.csv", CYCLE)
    assert airports[2].icao_id is None
    assert report.fully_faithful  # a missing optional field is not a fidelity issue


def test_airport_edge_cases_are_skipped_not_silently_dropped():
    airports, report = parse_airports(FIXTURES / "apt_base_edge_cases.csv", CYCLE)
    # TP06 (bad ELEV) and TP07 (no ELEV) still import -- a bad/missing
    # elevation doesn't block the whole row, just its own field.
    assert {a.ident for a in airports} == {"TP06", "TP07"}
    reasons = [i.reason for i in report.skipped]
    assert any("missing ARPT_ID" in r for r in reasons)
    assert any("missing LAT_DECIMAL" in r for r in reasons)
    assert any("non-numeric coordinates" in r for r in reasons)
    assert any("non-numeric ELEV" in r for r in reasons)


def test_airport_missing_elevation_is_not_an_error():
    # TP07 has ident + valid coordinates but no ELEV -- should import fine,
    # even though the fixture's other rows are malformed.
    airports, _ = parse_airports(FIXTURES / "apt_base_edge_cases.csv", CYCLE)
    tp07 = next(a for a in airports if a.ident == "TP07")
    assert tp07.elevation_ft is None


def test_get_airport_by_ident():
    a = get_airport("TP01", FIXTURES / "apt_base_sample.csv", CYCLE)
    assert a.name == "TURNPOINT TEST FIELD ONE"


def test_get_airport_by_icao_id():
    a = get_airport("KTP2", FIXTURES / "apt_base_sample.csv", CYCLE)
    assert a.ident == "TP02"


def test_get_airport_missing_raises():
    with pytest.raises(KeyError):
        get_airport("NOPE", FIXTURES / "apt_base_sample.csv", CYCLE)


def test_list_airports_near():
    # TP01 (38.8521, -77.0377) and TP02 (38.9, -77.0) are close together;
    # TP03 (40.0, -76.5) is much farther away.
    nearby, _ = list_airports_near(38.85, -77.03, 50.0, FIXTURES / "apt_base_sample.csv", CYCLE)
    assert {a.ident for a in nearby} == {"TP01", "TP02"}


def test_parse_navaids():
    navaids, report = parse_navaids(FIXTURES / "nav_base_sample.csv", CYCLE)
    assert report.fully_faithful
    assert report.imported_count == 2
    assert navaids[0].nav_type == "VOR"
    assert navaids[0].nasr_cycle == CYCLE


def test_navaid_edge_cases_are_skipped_not_silently_dropped():
    navaids, report = parse_navaids(FIXTURES / "nav_base_edge_cases.csv", CYCLE)
    assert navaids == []
    reasons = [i.reason for i in report.skipped]
    assert any("missing NAV_ID" in r for r in reasons)
    assert any("missing LAT_DECIMAL" in r for r in reasons)


def test_get_navaid_by_ident():
    n = get_navaid("TPV", FIXTURES / "nav_base_sample.csv", CYCLE)
    assert n.name == "TURNPOINT TEST VOR"


def test_get_navaid_missing_raises():
    with pytest.raises(KeyError):
        get_navaid("NOPE", FIXTURES / "nav_base_sample.csv", CYCLE)
