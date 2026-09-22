# data/

Local map, elevation and aeronautical data goes here. Everything in this
folder except this file is git-ignored.

Only public, unclassified, freely redistributable data may be used with this
repository's tests, demos and documentation: FAA NASR and CIFP, USGS and SRTM
elevation, FAA raster charts, and the NOAA World Magnetic Model.

Never place CUI, FOUO, limited-distribution or export-controlled data in any
path that is tracked by git. `scripts/check_markings.py` runs before every
commit and in CI as a backstop, not as a substitute for judgment.
