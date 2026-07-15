# AtlasMap Agent Rules

Follow the repository-root `AGENTS.md`. This directory is the portable QGIS
project root. Every path stored in QGIS projects, configuration, scripts,
reports, and metadata must be relative to this directory. Use
`config/atlas_korea.json` as the only source for map design constants. Select
country tiles by dominant country-or-ocean overlap with no fixed national tile
count, then assign each Korean tile to its dominant admin overlap. Admin target
counts are advisory; only configured minimum
representation is mandatory. Never report completion unless build, validation,
export, and preview generation all succeed.

Keep administrative ownership (`admin1_code`) independent from population-based
tile type (`city_class`, `is_capital`). City type may override fill color but
must never create city boundary lines; only differing admin ownership creates
administrative borders.

Keep tile display naming independent as well. The default tile name is the
largest-overlap configured city/county unit. Review missing units by descending
known population and allow one representative-name exception only above the
configured overlap floor, only against a lower-population current name, and
only when the current unit keeps at least one other tile. A naming exception
must never change `admin1_code`, `city_class`, fill classification, or borders.
