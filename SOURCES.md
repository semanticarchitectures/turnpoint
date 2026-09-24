# Sources log

Every external source that informs code, specs or data in this repository is listed
here **before** it is relied on. One row per source.

| ID | Source | URL | Retrieved | License / terms | Used for |
| --- | --- | --- | --- | --- | --- |
| S-001 | FalconView, Wikipedia | https://en.wikipedia.org/wiki/FalconView | 2026-09-21 | CC BY-SA 4.0 (facts only, no text copied) | Project background, history of the LGPL release |
| S-002 | FalconView site, GTRI | https://sites.gatech.edu/falconview/ | 2026-09-21 | Public web page | Trademark statement |
| S-003 | FalconView SDK page, GTRI | https://sites.gatech.edu/falconview/software-development-kit/ | 2026-09-21 | Public web page; the SDK itself is **not** cleared for use | List of ICD titles, distribution terms |
| S-004 | FalconView File Reader, FME documentation | https://docs.safe.com/fme/html/FME-Form-Documentation/FME-ReadersWriters/falconview/falconview.htm | 2026-09-21 | Public web page | Drawing and threat files are Access databases; drawing file has one `Main` table (feature number, type, data) |
| S-005 | C. F. F. Karney, "Algorithms for geodesics", J. Geodesy 87 (2013) | https://doi.org/10.1007/s00190-012-0578-z | 2026-09-21 | Published paper | Geodesic inverse and direct problem, via GeographicLib |
| S-006 | T. Vincenty, "Direct and inverse solutions of geodesics on the ellipsoid", Survey Review 23 (1975) | https://www.ngs.noaa.gov/PUBS_LIB/inverse.pdf | 2026-09-21 | Public (NOAA NGS) | Reference test values for geodesy |
| S-007 | ICSM, Geocentric Datum of Australia Technical Manual, worked example Flinders Peak to Buninyong | https://www.icsm.gov.au/publications/gda2020-technical-manual | 2026-09-21 | Public (CC BY 4.0) | Reference values for geodesic inverse test; values entered from recall and confirmed by independent computation, URL and figures to be re-verified against the manual |
| S-008 | OGC KML 2.3 Standard | https://www.ogc.org/standards/kml/ (spec text: http://docs.opengeospatial.org/is/12-007r2/12-007r2.html) | 2026-09-24 | Public OGC standard | Placemark/Point/LineString/Polygon/MultiGeometry structure and `lon,lat[,alt]` coordinate tuple format, `src/turnpoint/formats/kml.py` |
