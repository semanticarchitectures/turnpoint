import pytest

from turnpoint.core import Route, Turnpoint


def _route() -> Route:
    # Notional points on the equator, one degree apart.
    return Route("T", [Turnpoint("A", 0, 0), Turnpoint("B", 0, 1), Turnpoint("C", 0, 2)])


def test_legs_and_total():
    r = _route()
    legs = r.legs(groundspeed_kt=120.0)
    assert [(leg.from_name, leg.to_name) for leg in legs] == [("A", "B"), ("B", "C")]
    assert legs[0].distance_nm == pytest.approx(60.1077, abs=1e-3)
    assert legs[0].true_course_deg == pytest.approx(90.0)
    assert legs[0].ete_min == pytest.approx(legs[0].distance_nm / 2.0)
    assert r.total_distance_nm() == pytest.approx(2 * legs[0].distance_nm)


def test_no_groundspeed_means_no_time():
    assert _route().legs()[0].ete_min is None


def test_bad_groundspeed_rejected():
    with pytest.raises(ValueError):
        _route().legs(groundspeed_kt=0)
