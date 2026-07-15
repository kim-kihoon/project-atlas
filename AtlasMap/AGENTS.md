# AtlasMap Agent Rules

Follow the repository-root `AGENTS.md`. This directory is the portable QGIS
project root. Every path stored in QGIS projects, configuration, scripts,
reports, and metadata must be relative to this directory. Use
`config/atlas_korea.json` as the only source for map design constants.
`GLOBAL_MAP_RULES.md` is the authoritative cross-country design contract and
must stay synchronized with allocation code, configuration, and validation.
Select country tiles by dominant country-or-ocean overlap with no fixed national tile
count, then guarantee one positive-overlap same-country representative for each
feasible official Admin-1 and assign remaining tiles to their dominant admin
overlap. Build KOR and PRK simultaneously on one shared grid; a tile's
`country_iso3`, dominant territory, and Admin-1 country must agree. Admin target
counts are advisory report values only. Never remove another Admin-1's last
tile or cross a national boundary to satisfy representation. Never report
completion unless build, validation,
export, and preview generation all succeed.

Keep administrative ownership (`admin1_code`) independent from population-based
tile type (`city_class`, `is_capital`). City type determines fill color but
must never create city boundary lines; only differing admin ownership creates
administrative borders.

Require an `admin1_source` configuration for every playable country. Use the
union of that same source for the playable country's national-overlap geometry;
keep the separate global source only for nearby non-playable country competitors.
Do not mix one boundary vintage for country dominance with another for Admin-1
ownership.

National ownership is a hard boundary. No override, Admin-1 assignment, naming
unit, or population-based classification may transfer a tile between KOR and
PRK. Shared KOR/PRK hex edges use `edge_type=country`; same-country ownership
changes use `edge_type=admin`.

Assign each naming unit to its greatest-overlap current authoritative Admin-1,
clip its geometry to that Admin-1, and consider it only for tiles with the same
final owner. Process units globally
in descending population order, letting each reserve its maximum-overlap
still-unclaimed tile. Fill remaining tiles only after this representative pass,
using greatest overlap, with population and stable unit code as tie-breakers.
Any positive overlap is eligible; a smaller unit must not displace an already
matched larger unit. Spatial overlap and boundaries remain mandatory.
Use this same configuration-driven algorithm for every current and future
country. Country-specific naming code paths and exceptions are forbidden.
Only those real-city anchor tiles receive an initial `city_class`: 100,000+
means `city` and 1,000,000+ means `metropolis`. An ordinary tile over 100,000
remains `admin` but sets `city_upgrade_eligible` for player-selected promotion.
Capital status follows the final name but does not override the tile fill. Do not
publish or display city marker points; place data remains an internal
classification source.

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

Use exactly three tile fill classes: `admin`, `city`, and `metropolis`.
Capital is not a fill class: draw one yellow topology-derived outline around
the complete official capital Admin-1 tile group, including differently named
tiles inside that administration. Cancel its internal shared edges. All ordinary
administrative tiles share one fill color. Make
admin-1 ownership legible through the `admin1_tile_borders` layer, whose lines
must be substantially stronger than ordinary tile outlines.
Official capital Admin-1 areas use the same one-tile ownership representation
floor as every other official area. Capital display naming may cross neither
national nor Admin-1 ownership boundaries.

Render a complete dark outline for each same-owner tile group using explicit
hex-edge topology. Same-owner shared edges cancel; different-owner and exterior
edges remain exactly once. Do not publish a separate coastal-line layer until
the administrative borders and tile layout are final.
Every tile carrying the same represented city/county naming-unit code inherits
the representative city anchor's `map_class` for display. This applies to
ordinary cities and capitals. Keep `city_class`, `is_initial_city`, and the
actual city population only on the representative anchor so national population
is never duplicated.

Tile-name labels have no zoomed-in cutoff and must fit completely inside their
own hexagons. Admin-1 summary labels are overview-only and must be hidden at
close zoom so they cannot obscure individual tile names.
