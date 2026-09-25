from turnpoint.core import Threat


def test_threat_holds_notional_fields():
    threat = Threat(
        id="1",
        name="test threat",
        threat_type="NOTIONAL-SAM-A",
        lat=38.0,
        lon=-77.0,
        engagement_radius_nm=20.0,
        sensor_height_ft=0.0,
        sidc=None,
        actor="tester",
        created_at="2026-09-24T00:00:00+00:00",
    )
    assert threat.threat_type == "NOTIONAL-SAM-A"
    assert threat.engagement_radius_nm == 20.0
    assert threat.sidc is None
