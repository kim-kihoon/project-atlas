# Atlas Korean Peninsula QGIS Map

This directory contains the reproducible GIS pipeline for the Korean Peninsula
prototype map used by **Atlas**. It builds the Republic of Korea and the
Democratic People's Republic of Korea together on one common regular-hex grid
in EPSG:5179. Each tile goes first to its dominant country-or-ocean overlap,
then only to a first-level administrative area belonging to that same country.
The QGIS display language is controlled by `display_language`; it is currently
set to English so every tile and Admin-1 label uses one language consistently.
The authoritative cross-country allocation and validation contract is
`GLOBAL_MAP_RULES.md`.
Administrative-reference findings, including the accepted frozen-snapshot
trade-offs, are tracked in
`reports/korea_administrative_reference_audit.md`. Structural validation and
historical administrative accuracy are separate release gates.
The latest end-to-end result is recorded in
`reports/korea_full_audit_report.md`.
The latest PRK boundary-source acquisition findings are recorded in
`reports/prk_boundary_source_update_2026-07-16.md`.
The `Seo`/GeoNames investigation and restored Admin-1 representation are
recorded in `reports/korea_data_quality_findings.md`.
The detailed CGAZ ADM1/ADM2 consistency investigation covering Dalseong,
Gwangju metropolitan districts, Gwangju city classification and the missing
Yeonggwang boundary is recorded in
`reports/korea_cgaz_hierarchy_consistency_audit.md`.

There is no fixed national tile count. A tile belongs to KOR or PRK only when
that country's land occupies more of it than every neighboring country and the
ocean. The two countries are evaluated simultaneously, so they cannot claim the
same tile or assign a tile to an administrative area across the national border.
Country-border edges are stored separately from ordinary admin-border edges.
Tiles are then assigned to the same-country administrative area occupying their
largest portion.
Every feasible official Admin-1 receives one positive-overlap same-country
representative without taking another official area's last tile. Remaining
tiles retain their greatest-overlap owner; historical targets stay advisory.

ADM0, ADM1 and ADM2 now come from one pinned geoBoundaries CGAZ 6.0.0 global
snapshot (commit `1289e40e366c7b320550be1ee0614a9472d572d4`). This prioritizes
worldwide consistency, stable identifiers and reproducibility over modern
country-specific corrections. SGIS, Natural Earth, NGII and OSM files remain
audit evidence but are not active ownership inputs.
The snapshot has known KOR ADM1/ADM2 hierarchy contradictions. They are retained
and reported rather than corrected with Korea-only parent or geometry patches.
This preserves one reproducible worldwide rule; it does not mean that every
displayed Korean administrative relationship is modern or semantically exact.

Administrative ownership and city type are independent. For example, a tile
containing Yongin remains owned by Gyeonggi (`admin1_code=KR-41`) while its
real-city anchor can have a separate `city_class`. City status changes fill
color, never administrative borders.

Tile display naming follows Admin-1 ownership. Naming units are assigned and
clipped to their greatest-overlap authoritative Admin-1; each tile considers
only positive-overlap units belonging to its final owner. Units are processed globally in
descending population order, and each reserves its maximum-overlap still-free
tile. Only after this unique-representative pass are remaining tiles filled by
their greatest-overlap intersecting unit; exact area ties use population and
then stable unit code. There is no minimum overlap threshold. Display-name
population is internal naming
evidence only and is not copied into the game tile.
The same configuration-driven rule applies to KOR, PRK, and every country added
later; there are no country-specific naming exceptions.
All naming units compete in descending actual-population order. A smaller unit
cannot displace an already matched larger unit, although spatial overlap and the
finite grid can leave a city or county without a distinct hex.
When a represented city or county naming unit occupies multiple tiles, all
tiles carrying that same naming-unit code inherit the representative city
anchor's city/metropolis fill. Only that representative stores the actual city
population and initial-city gameplay state, so the national total is not
duplicated. The complete official capital Admin-1 group receives one yellow
outer outline; internal shared edges do not receive that outline. Capital
Admin-1 areas receive the same feasible one-tile floor as other official areas.

The map uses exactly three tile fill classes: ordinary administrative tile,
light-blue city, and dark-navy metropolis. Capital is a separate yellow outline
around the complete official capital Admin-1 group, not a fill class. Each represented real
city receives one anchor tile: 100,000-999,999 is an initial city and 1,000,000+
is an initial metropolis. Its one game-population value is the GeoNames city
population. The 2020 WorldPop raster distributes the remaining population over
non-anchor tiles, and largest remainder reconciles the result to the configured
2026 UN World Population Prospects national total exactly. An ordinary tile
over 100,000 stays administrative at scenario start and is instead marked
`city_upgrade_eligible`; promotion during play is the player's choice. Capital
status does not change the stored population or underlying fill class.

Tile names remain visible at every closer zoom once they enter the configured
`labeling.tile_name_min_scale` range. A label is placed only when it fits fully
inside its hex; zooming closer creates enough room for longer names. Large
Admin-1 summary labels are limited to overview scales so they do not cover tile
names. Long `tile_id` values are appended only below
`labeling.tile_id_max_scale`, where a hex has enough screen space.

GeoNames and naming-unit WorldPop sums remain internal inputs for selecting
display names. They are not alternative game-population fields.
Administrative borders are the complete topology-derived outlines of same-owner
tile groups. Every hex edge is keyed explicitly: edges shared by tiles with the
same `admin1_code` cancel, while different-owner and exterior edges remain and
render once above the tile fills. The separate coastal-line layer is temporarily
omitted until the administrative borders and tile layout are final. No
city-marker layer is displayed or published.

## Quick start (macOS)

From this directory:

```bash
./scripts/run_mac.sh all
```

The runner locates QGIS LTR, configures its PROJ database, builds the
GeoPackage/QGIS project, validates the result, and exports Unreal-friendly
files. Run individual stages with `build`, `validate`, or `export`.

## Quick start (Windows PowerShell)

```powershell
.\scripts\run_windows.ps1 all
```

If QGIS is installed in a non-standard location, set `QGIS_PROCESS` to the full
path of `qgis_process.exe` before running either launcher.

## Global-readiness audit

The Korean Peninsula release gate and the world-map readiness gate are separate.
Run the structural world-map audit through the platform launcher:

```bash
./scripts/run_mac.sh global-validate
```

```powershell
.\scripts\run_windows.ps1 global-validate
```

The audit writes `reports/global_readiness_report.md` and exits nonzero while
blocking global requirements remain. A global-readiness FAIL does not replace
or invalidate the Korea geometry validation; it prevents the prototype from
being mistaken for a world-ready pipeline.

## Main outputs

- `Atlas_Korea.qgz`: QGIS project; open this first in QGIS.
- `data/processed/Atlas_Korea.gpkg`: source, city/county naming reference,
  candidates, final tiles, and admin borders. Coastal lines are deferred.
- `previews/Atlas_Korea_Overview.png`: rendered overview.
- `reports/allocation_report.md`: target and actual tile allocation.
- `reports/validation_report.md`: release-gate validation results.
- `reports/global_readiness_report.md`: separate world-pipeline readiness audit.
- `reports/korea_cgaz_hierarchy_consistency_audit.md`: known KOR hierarchy and
  completeness conflicts in the pinned CGAZ snapshot.
- `GLOBAL_MAP_RULES.md`: authoritative global allocation and validation rules.
- `exports/Atlas_Korea_Tiles.geojson` and `.csv`: Unreal-oriented exports.

The current deterministic CGAZ build contains 158 KOR tiles and 206 PRK tiles,
364 total. Tile IDs use the immutable grid row/column namespace and do not
contain country or administrative ownership.

QGIS terms for beginners: a **layer** is one collection of map features; a
**GeoPackage** is one database file that can hold several layers; a **CRS** is
the coordinate system used to locate and measure those features.

All shared paths are relative to this directory. Do not save a QGIS layer using
an absolute path.
