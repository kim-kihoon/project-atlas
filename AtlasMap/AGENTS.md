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

Every tile display name must belong to the tile's `admin1_code`; this is a hard
validation constraint. First match eligible same-owner cities/counties to at
most one representative tile with population priority and overlap preference,
then fill remaining tiles by largest same-owner overlap. Derive `city_class`
and capital color from the final named unit. City marker points are reference
data only and must not independently select or color a tile.
