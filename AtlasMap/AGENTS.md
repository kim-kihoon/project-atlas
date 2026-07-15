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
validation constraint. Assign each tile first to its highest-population
overlapping same-owner unit. A duplicated unit keeps its largest-overlap
representative; redistribute its other tiles to unrepresented compatible units
in population order. Any positive overlap is eligible. Derive `city_class`
and capital color from the final named unit. Do not publish or display city
marker points; place data remains an internal classification source.

Use exactly four tile fill classes: `admin`, `city`, `metropolis`, and
`capital`. All ordinary administrative tiles share one fill color. Make
admin-1 ownership legible through the `admin1_tile_borders` layer, whose lines
must be substantially stronger than ordinary tile outlines.

Render a complete dark outline for each same-owner tile group using explicit
hex-edge topology. Same-owner shared edges cancel; different-owner and exterior
edges remain exactly once. Do not publish a separate coastal-line layer until
the administrative borders and tile layout are final.
