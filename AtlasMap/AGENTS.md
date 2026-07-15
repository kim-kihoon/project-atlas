# AtlasMap Agent Rules

Follow the repository-root `AGENTS.md`. This directory is the portable QGIS
project root. Every path stored in QGIS projects, configuration, scripts,
reports, and metadata must be relative to this directory. Use
`config/atlas_korea.json` as the only source for map design constants. Select
country tiles by dominant country-or-ocean overlap with no fixed national tile
count, then assign each selected tile only to its same-country dominant admin
overlap. Build KOR and PRK simultaneously on one shared grid; a tile's
`country_iso3`, dominant territory, and Admin-1 country must agree. Admin target
counts are advisory; only configured minimum
representation is mandatory. Never report completion unless build, validation,
export, and preview generation all succeed.

Keep administrative ownership (`admin1_code`) independent from population-based
tile type (`city_class`, `is_capital`). City type may override fill color but
must never create city boundary lines; only differing admin ownership creates
administrative borders.

National ownership is a hard boundary. No override, Admin-1 assignment, naming
unit, or population-based classification may transfer a tile between KOR and
PRK. Shared KOR/PRK hex edges use `edge_type=country`; same-country ownership
changes use `edge_type=admin`.

Every tile display name must belong to the tile's `admin1_code`; this is a hard
validation constraint. Assign each tile first to its highest-population
overlapping same-owner unit. A duplicated unit keeps its largest-overlap
representative; redistribute its other tiles to unrepresented compatible units
in population order. Any positive overlap is eligible. Reserve distinct
compatible representatives for qualifying real cities when the grid permits.
Only those real-city anchor tiles receive an initial `city_class`: 100,000+
means `city` and 1,000,000+ means `metropolis`. An ordinary tile over 100,000
remains `admin` but sets `city_upgrade_eligible` for player-selected promotion.
Capital color follows the final name and overrides the city color. Do not publish or display city
marker points; place data remains an internal classification source.

Use the same GeoNames dump schema in every country. A naming unit population
must be a positive integer. When an ADM2 record is zero, negative, or invalid,
recover it first from the largest positive populated-place record sharing its
admin-2 code, then from one sharing its normalized name and admin-1 owner.
Persist the recovery method and GeoNames identifier. These values guide naming
only; do not expose a second naming-unit population on the game tile.

If neither GeoNames recovery produces a positive value, use the configured
WorldPop UN-adjusted 1 km raster zonal sum for the naming-unit polygon. Store
the WorldPop DOI as `population_source_id`; never insert a manual country value.

Allocate game population separately: a represented real city's anchor receives
its GeoNames population. WorldPop weights and largest remainder distribute the
remaining national population across non-anchor tiles so the configured UN WPP
medium-variant national sum remains exact. Store only this one population value.

Use exactly four tile fill classes: `admin`, `city`, `metropolis`, and
`capital`. All ordinary administrative tiles share one fill color. Make
admin-1 ownership legible through the `admin1_tile_borders` layer, whose lines
must be substantially stronger than ordinary tile outlines.

Render a complete dark outline for each same-owner tile group using explicit
hex-edge topology. Same-owner shared edges cancel; different-owner and exterior
edges remain exactly once. Do not publish a separate coastal-line layer until
the administrative borders and tile layout are final.
