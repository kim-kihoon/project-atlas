# Atlas QGIS Korea Project Instructions

## Mission

Build a reproducible QGIS pipeline for the modern nation-management 4X game
**Atlas**. The current deliverable is an East Asia game map containing KOR,
PRK, CHN, MNG, JPN and TWN on one continuous OGC ISEA3H level-11 spherical grid.
Work must be reproducible on macOS and Windows with QGIS LTR 3.44, PyQGIS and
`qgis_process`.

Keep `AtlasMap/GLOBAL_MAP_RULES.md` as the authoritative cross-country design
contract. Any change to ownership, naming, city, capital, population, global
grid, or validation rules must update that document together with code and
configuration.

The project is a game-map approximation. Do not enforce a fixed national tile
count. Assign each global-grid cell to the country or ocean occupying its largest
area; keep KOR- and PRK-dominant cells as their respective national tiles.
National ownership may never cross or collide and always follows greatest
country-or-ocean overlap. Guarantee every official Admin-1 one positive-overlap
representative tile inside the same dominant country whenever this can be done
without removing another area's last tile. Assign all remaining tiles to their
greatest-overlap Admin-1. When possible, choose a representative already carrying
a naming unit from that Admin-1 so visible name and ownership coincide.
Historical targets remain advisory.

## Workspace and Safety Rules

- Create all map deliverables below `AtlasMap/` in this repository.
- Before creating a path, inspect it. Never overwrite a conflicting file or
  directory without reporting the conflict first.
- Do not delete existing files, run destructive commands, create a remote Git
  repository, commit, or push.
- If this repository is not already a local Git repository, `git init` is the
  only Git mutation allowed without further user direction.
- Use English ASCII for file names, directory names, and field names. Use UTF-8
  text. Korean is allowed in attribute values and documentation.
- Use only paths relative to the `AtlasMap/` project root in project files,
  configuration, and scripts. Never hard-code macOS absolute paths or Windows
  drive paths.
- Use QGIS core functionality for GIS processing and presentation. Do not add
  QGIS plugin or external grid-generator dependencies.
- Prefer repeatable PyQGIS and `qgis_process` workflows over manual GUI edits.
- Preserve source data. Write transformed and generated layers only to the
  processed GeoPackage.
- Never invent population, city, boundary, provenance, or license data. Leave
  unknown values NULL or explicitly unset.
- Ask the user only about a genuine blocker such as a path conflict, missing
  QGIS installation, or unavailable/unclear-licensed boundary data. Make
  reasonable routine implementation choices independently.

## Required Version and Preflight

- Baseline on both platforms: QGIS LTR 3.44.
- At the start of implementation, record the OS, working directory,
  `qgis_process` path, and version.
- On macOS, the currently detected executable is
  `/Applications/QGIS.app/Contents/MacOS/qgis_process`, QGIS 3.44.12. This is a
  machine observation only and must not be stored as a runtime path in project
  files or shared scripts.
- The initial direct CLI check emitted `Cannot find proj.db`; diagnose the QGIS
  runtime environment before running GIS algorithms. Do not treat a version
  string alone as proof that processing is healthy.
- If QGIS is unavailable or its runtime is not functional, create and document
  the safe project skeleton but defer GIS processing. Report the exact next
  action required from the user.

## Canonical Project Layout

```text
AtlasMap/
├── Atlas_East_Asia.qgz
├── AGENTS.md
├── GLOBAL_MAP_RULES.md
├── README.md
├── .gitignore
├── .gitattributes
├── config/
│   └── atlas_east_asia.json
├── data/
│   ├── source/
│   │   └── README.md
│   └── processed/
│       └── Atlas_East_Asia.gpkg
├── scripts/
│   ├── build_east_asia_map.py
│   ├── validate_east_asia_map.py
│   ├── validate_global_readiness.py
│   ├── export_for_unreal.py
│   ├── run_mac.sh
│   └── run_windows.ps1
├── overrides/
│   └── tile_assignment_overrides.csv
├── exports/
├── previews/
├── reports/
│   └── global_readiness_report.md
└── logs/
```

Keep cross-platform line endings stable in `.gitattributes`. In `.gitignore`,
distinguish QGIS temporary/cache/log files and reproducible intermediates from
deliverables. The QGIS project, configuration, scripts, validation reports, and
required GeoPackage remain trackable.

## Single Source of Truth

Store every adjustable design value and validation tolerance in
`config/atlas_east_asia.json`. Do not duplicate these constants in Python:

- Countries: `KOR`, `PRK`, `CHN`, `MNG`, `JPN` and `TWN`, generated
  simultaneously on the same grid
- Canonical grid: OGC ISEA3H level 11 on the WGS84 authalic sphere, generated
  with pinned DGGAL 0.0.6
- National tile count: derived from dominant country-or-ocean overlap, not fixed
- Global cell count: 1,771,460 hexagons plus 12 pentagons
- Canonical areas: about 287.933536 km2 per hexagon and 239.944614 km2 per pentagon
- Build borders and neighbors from canonical spherical DGGRS topology.
- Canonical IDs: `ATLAS_ISEA3H_L11_{zone_text_id}`
- Antimeridian and polar continuity are native to the global topology.
- Use `EPSG:8857` Equal Earth for intersection analysis and `EPSG:3857` Web
  Mercator for QGIS project/preview display only.
- Never clip game cells to the coastline. Every final game tile remains a
  complete regular hexagon.
- Show administrative borders along shared edges between differently assigned
  cells; do not use the curved source boundary as the game border.

Original admin-1 design targets, retained for comparison and reporting rather
than used as hard validation constraints:

| Admin-1 | Tiles |
| --- | ---: |
| Seoul | 1 |
| Busan | 1 |
| Daegu | 3 |
| Incheon | 2 |
| Gwangju | 1 |
| Daejeon | 1 |
| Ulsan | 2 |
| Sejong | 1 |
| Gyeonggi | 17 |
| Gangwon | 28 |
| Chungbuk | 12 |
| Chungnam | 14 |
| Jeonbuk | 13 |
| Jeonnam | 20 |
| Gyeongbuk | 30 |
| Gyeongnam | 17 |
| Jeju | 3 |
| **Original target total** | **166** |

The configuration should also hold stable admin codes and Korean/English names,
not just the display labels in this table.

## Source Data and Provenance

- Prefer official or otherwise trustworthy public data containing all 17
  first-level administrative boundaries.
- Do not use paid, login-gated, or unclear-redistribution data without user
  approval.
- Record the source URL, download date, reference year, license, original file
  name, and checksum when available in `data/source/README.md`.
- If suitable data cannot be obtained automatically, do not fabricate or alter
  boundaries. Document the exact required format and destination path, then
  pause only the data-dependent processing stages.
- Store cleaned/reprojected data in
  `data/processed/Atlas_East_Asia.gpkg`; keep the original source unchanged.

## Build Pipeline Requirements

Implement `scripts/build_east_asia_map.py` so that the same inputs and configuration
produce the same geometries, assignments, and stable `tile_id` values:

1. Load the WGS84 admin-1 source, safely repair invalid geometries, and use an
   appropriate equal-area analysis CRS for regional intersection calculations.
2. Enumerate complete ISEA3H level-11 spherical-cell candidates near all six
   configured countries using immutable canonical DGGAL IDs.
3. Calculate each cell's intersection area and ratio against configured land and
   every admin-1 area.
4. Select uncut candidates for the game map.
5. Initially assign each tile to the admin area with greatest overlap.
6. Compare configured countries, nearby countries, and ocean in every candidate.
   Select every configured-country-dominant candidate, then reserve one positive-overlap same-country tile
   for each official Admin-1 that would otherwise have zero representation.
   Never remove another official area's last tile; keep every other tile with
   its greatest-overlap owner.
7. Keep `overrides/tile_assignment_overrides.csv` empty for ownership. Manual
   ownership overrides are forbidden because they would violate greatest overlap.
8. Calculate centers and adjacency, with deterministic IDs and symmetric
   neighbor relationships.
9. Write scores, boundary-tile details, and override use to reports.

## GeoPackage Contract

Create at least these layers in `Atlas_East_Asia.gpkg`:

- `admin1_source`: cleaned/reprojected first-level boundaries for all six countries
- `hex_candidates`: all candidates and overlap scores
- `east_asia_tiles`: all six countries' final game cells

`east_asia_tiles` must include at least:

```text
tile_id
country_iso3
admin1_code
admin1_name_ko
admin1_name_en
area_km2
land_ratio
is_coastal
center_x
center_y
neighbor_ids
population
population_year
population_method
population_source_id
city_name_ko
city_name_en
city_class
is_capital
is_capital_anchor
is_initial_city
city_upgrade_eligible
map_class
district_slots
district_1
district_2
district_3
primary_industry
terrain
source_year
manual_override
```

Do not publish a city-marker layer. Every game tile stores exactly one integer
population. Initial scenario city status is anchored to a qualifying real
GeoNames city, not automatically inferred from every dense tile:

- initial city: real city population from 100,000 to under 1,000,000, 2 district slots
- initial metropolis: real city population of 1,000,000 or more, 3 district slots
- ordinary tile: 1 district slot, even when its starting population exceeds 100,000
- capital status is separate and adds no slot

After scenario start, reaching 100,000 only makes an ordinary tile eligible for
player-selected city promotion; it does not automatically change the tile type.

Use the same GeoNames dump fields and recovery order for every country. Treat
only positive integers as valid population. If an ADM2 population is zero,
negative, or invalid, recover it from the largest positive populated-place
record with the same admin-2 code; if unavailable, use the same normalized name
within the same admin-1 owner. Persist the recovery method and GeoNames ID so
every correction is auditable. Do not add country-specific population patches.
If both GeoNames matches fail, calculate a zonal sum from the configured
WorldPop UN-adjusted 1 km raster and store its DOI as `population_source_id`.
These naming-unit populations are internal name-allocation evidence, not game
tile population. Do not publish `tile_name_population` on `east_asia_tiles`.

For game population, give each represented qualifying real city one anchor tile
whose single population equals its GeoNames city population. Subtract all city
anchors from the configured same-year UN World Population Prospects
medium-variant national total, distribute the residual over non-anchor tiles
using WorldPop spatial weights and largest remainder, and validate that each
country's tile sum matches exactly. At a finite grid resolution, a qualifying
city without a distinct compatible tile remains source evidence rather than an
initial city.

Administrative ownership and city type are independent dimensions. A city tile
inside a province keeps that province's `admin1_code`; for example, Yongin is a
Gyeonggi-owned metropolis tile. City/capital status may override fill color but
must not create city boundary lines. Administrative borders follow only shared
edges where `admin1_code` differs.

Final Admin-1 ownership is decided before display naming. Final ownership follows
the one-tile official-area representation floor, then greatest overlap. Classify
each naming unit under the current authoritative greatest-overlap Admin-1 and
clip it to that Admin-1. For naming, consider only city/county units belonging
to the tile's final Admin-1 owner. Process units globally in descending
population order; each unit reserves its maximum-overlap still-unclaimed tile.
After this unique-representative pass, fill remaining tiles with their
greatest-overlap intersecting unit; break area ties by population, then stable
unit code. Any positive overlap is eligible. A smaller unit may never evict a
matched larger unit. This priority never relaxes spatial overlap or boundaries.
If and only if no eligible ADM2/equivalent naming unit has positive overlap,
use the same-owner Admin-1 geometry and name as an auditable positive-overlap
coverage fallback. Give it zero naming-allocation population and exclude it
from the unique-representative pass; it may never change ownership.
Apply this algorithm identically to every configured country now and to every
country added during world-map expansion; do not introduce country-specific
naming branches or exceptions.
Derive initial city/metropolis fill from the anchored real-city population;
ordinary dense tiles remain `admin` and expose promotion eligibility separately.
Capital status follows the final name but never overrides fill. Set
`is_capital` on every tile carrying the represented capital naming-unit code,
and draw a yellow outline only on the exterior edges of that complete
capital-name tile group. Cancel internal edges shared by the same capital-name
group; do not include differently named tiles merely because they belong to the
capital Admin-1. Set `is_capital_anchor` on exactly one representative real-city
anchor per country. Capital-only gameplay bonuses, facilities, and slots apply
only to that anchor, not to every yellow-outlined tile.
Official capital Admin-1 areas use the same one-tile representation floor as
all other official areas. Display naming may cross neither national nor Admin-1
ownership boundaries.
For display, every same-owner tile carrying the same represented city/county
naming-unit code inherits its representative city anchor's city/metropolis `map_class`.
This applies to ordinary cities and capitals alike. Do not copy the anchor's
population, `city_class`, or `is_initial_city` status to the other tiles.

## QGIS Project and Outputs

- Save `Atlas_East_Asia.qgz` with relative data paths only.
- Use exactly three tile fill classes: normal administrative tile, city, and
  metropolis. Show capitals with a yellow group outline, not a separate fill.
  Do not use a different fill per admin-1 area;
  distinguish admin-1 ownership with complete topology-derived outlines of
  same-owner tile groups. Cancel every edge shared by same-owner tiles; retain
  different-owner and exterior edges exactly once. Never derive these outlines
  from dissolved polygon rings.
  Keep normal tile edges and admin borders visually distinct. Do not publish a
  separate coastal-line layer until the administrative borders and tile layout
  are final.
- Label each admin-1 area with its name and assigned tile count.
- Treat label scale terminology correctly: `minimumScale` is the most zoomed-out
  denominator and `maximumScale` is the most zoomed-in denominator. Tile names
  must remain enabled without a zoomed-in cutoff, fit completely inside their
  hexagons, and show `tile_id` only at an appropriate close zoom. Hide Admin-1
  summary labels at close zoom so they cannot cover tile names.
- Put real source boundaries in a separate toggleable validation group so they
  are not confused with the game-map boundary.
- Export `previews/Atlas_East_Asia_Overview.png`.
- Write `reports/east_asia_allocation_report.md` with target/actual/difference per admin,
  boundary tiles, and manual override status.
- Export final tile attributes through `scripts/export_for_unreal.py` to
  `exports/Atlas_East_Asia_Tiles.geojson` and
  `exports/Atlas_East_Asia_Tiles.csv`. Keep the GeoPackage in `EPSG:8857` and
  transform interchange exports to WGS84 where required.
- Provide `scripts/run_mac.sh` and `scripts/run_windows.ps1`. Both must invoke
  the same config and Python logic, auto-detect QGIS where practical, and accept
  a `QGIS_PROCESS` environment override. Keep platform-specific path syntax out
  of core logic.

## Validation Is a Release Gate

Implement `scripts/validate_east_asia_map.py` and fail with a nonzero exit status if
any check fails:

- Each tile round-trips to its configured ISEA3H level-11 DGGAL identity.
- Every final tile is configured-country-dominant over neighboring countries and ocean; the
  national total is derived rather than fixed.
- Every feasible official Admin-1 has at least one positive-overlap
  representative tile inside its dominant country. Every non-representative
  tile keeps its greatest-overlap owner; targets remain report-only.
- Every `tile_id` is present and unique.
- Every final geometry is a valid complete uncut spherical cell projection.
- Canonical hexagons have six neighbors and pentagons five; a regional subset may expose fewer selected neighbors.
- Spherical area and cell type match canonical DGGAL values.
- Every tile has exactly one admin assignment.
- Final tiles do not overlap one another.
- Every neighbor ID exists and all adjacency is symmetric.
- No macOS or Windows absolute path remains in shared projects or scripts.

Never report the map complete without successful script execution, validation,
and preview generation.

## Recommended Execution Order

1. Preflight QGIS and its processing/PROJ runtime.
2. Create the collision-safe `AtlasMap/` skeleton, config, documentation, and
   cross-platform launchers.
3. Acquire and document licensed admin-1 boundary data.
4. Implement the deterministic build pipeline and GeoPackage schema.
5. Build the QGIS project, styling, labels, reports, and preview.
6. Implement Unreal exports and validation.
7. Run a clean rebuild and all validation gates; inspect the preview visually.
8. Report generated files, tool versions, data provenance/license, commands,
   allocation results, opening instructions for both platforms, and blockers.

## Beginner-Friendly Handoff

Assume the user is new to QGIS. When user interaction is needed:

- Give exact menu names, button labels, and expected visual results.
- Separate commands the assistant can run from steps the user must perform.
- Explain CRS, layers, GeoPackage, and processing concepts briefly when first
  introduced.
- Provide one safest recommended path first, then optional alternatives.
- Do not ask the user to manually reproduce a step that can be scripted.
