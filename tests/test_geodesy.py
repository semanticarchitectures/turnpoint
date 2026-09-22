"""Geodesy tests against published or exactly derivable reference values."""

import math

import pytest

from turnpoint.geodesy import METERS_PER_NM, destination_point, range_bearing


def dms(d: float, m: float, s: float) -> float:
    sign = -1.0 if d < 0 else 1.0
    return sign * (abs(d) + m / 60.0 + s / 3600.0)


# Flinders Peak to Buninyong, the worked example in the ICSM GDA Technical Manual
# (SOURCES S-007). Published on GRS80; WGS 84 differs in flattening only at the
# 1e-11 level, which moves this 55 km line by far less than the tolerance used here.
FLINDERS = (dms(-37, 57, 3.72030), dms(144, 25, 29.52440))
BUNINYONG = (dms(-37, 39, 10.15610), dms(143, 55, 35.38390))


def test_inverse_matches_published_worked_example():
    g = range_bearing(*FLINDERS, *BUNINYONG)
    assert g.distance_m == pytest.approx(54972.271, abs=0.002)
    assert g.initial_bearing_deg == pytest.approx(dms(306, 52, 5.37), abs=1e-5)
    # Published reverse azimuth is 127 10 25.07; final bearing is that plus 180.
    assert g.final_bearing_deg == pytest.approx(dms(127, 10, 25.07) + 180.0, abs=1e-5)


def test_direct_is_inverse_of_inverse():
    g = range_bearing(*FLINDERS, *BUNINYONG)
    lat, lon = destination_point(*FLINDERS, g.initial_bearing_deg, g.distance_m)
    assert lat == pytest.approx(BUNINYONG[0], abs=1e-9)
    assert lon == pytest.approx(BUNINYONG[1], abs=1e-9)


def test_one_degree_along_equator_is_exact_arc_of_semi_major_axis():
    # The equator is a geodesic; length = a * pi / 180 with a = 6378137 m (WGS 84).
    g = range_bearing(0.0, 0.0, 0.0, 1.0)
    assert g.distance_m == pytest.approx(6378137.0 * math.pi / 180.0, abs=1e-6)
    assert g.initial_bearing_deg == pytest.approx(90.0)


def test_bearings_are_normalised_to_0_360():
    g = range_bearing(0.0, 0.0, 0.0, -1.0)
    assert g.initial_bearing_deg == pytest.approx(270.0)


def test_nautical_mile_is_exact():
    assert METERS_PER_NM == 1852.0


@pytest.mark.parametrize("lat,lon", [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_out_of_range_coordinates_are_rejected(lat, lon):
    with pytest.raises(ValueError):
        range_bearing(lat, lon, 0, 0)
