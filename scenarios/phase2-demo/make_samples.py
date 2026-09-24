#!/usr/bin/env python3
"""Generate the sample files for the Phase 2 demo.

Writes self-made, notional GeoJSON/GPX/KML/NASR-CSV samples to
data/phase2-demo/ (git-ignored; data/README.md's public-data-only rule).
Not real chart data or a real place. Run once before following
scenarios/phase2-demo/README.md.
"""

from __future__ import annotations

from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "phase2-demo"

GEOJSON = """{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {"name": "checkpoint alpha"},
      "geometry": {"type": "Point", "coordinates": [-77.0377, 38.8521]}
    },
    {
      "type": "Feature",
      "properties": {"name": "notional boundary"},
      "geometry": {
        "type": "LineString",
        "coordinates": [[-77.0, 38.0], [-76.0, 38.5], [-75.0, 38.0]]
      }
    },
    {
      "type": "Feature",
      "properties": {"name": "notional area"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [[-77.0, 38.0], [-76.0, 38.0], [-76.0, 39.0], [-77.0, 39.0], [-77.0, 38.0]]
        ]
      }
    }
  ]
}
"""

GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="turnpoint-phase2-demo" xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="38.8521" lon="-77.0377">
    <name>checkpoint alpha</name>
  </wpt>
  <rte>
    <name>notional route</name>
    <rtept lat="38.0" lon="-77.0"><name>R1</name></rtept>
    <rtept lat="38.5" lon="-76.0"><name>R2</name></rtept>
    <rtept lat="38.0" lon="-75.0"><name>R3</name></rtept>
  </rte>
</gpx>
"""

KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>checkpoint alpha</name>
      <Point>
        <coordinates>-77.0377,38.8521</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>notional area</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -77.0,38.0 -76.0,38.0 -76.0,39.0 -77.0,39.0 -77.0,38.0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""

APT_BASE_CSV = (
    "\n".join(
        [
            "ARPT_ID,ICAO_ID,ARPT_NAME,SITE_TYPE_CODE,FACILITY_USE_CODE,LAT_DECIMAL,LONG_DECIMAL,ELEV",
            "TP01,KTP1,TURNPOINT TEST FIELD ONE,A,PU,38.8521,-77.0377,15.0",
            "TP02,KTP2,TURNPOINT TEST FIELD TWO,A,PU,38.9,-77.0,120.0",
        ]
    )
    + "\n"
)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "sample.geojson").write_text(GEOJSON)
    (OUTPUT_DIR / "sample.gpx").write_text(GPX)
    (OUTPUT_DIR / "sample.kml").write_text(KML)
    (OUTPUT_DIR / "apt_base_sample.csv").write_text(APT_BASE_CSV)
    print(f"Wrote sample files to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
