# Atlas QGIS Korea Project Instructions

## Mission

Build a reproducible QGIS pipeline for the modern nation-management 4X game
**Atlas**. The first deliverable is a Korean Peninsula game map containing KOR
and PRK on one common grid of complete regular hexagons. Work must be reproducible on macOS and
Windows with QGIS LTR 3.44, PyQGIS, and `qgis_process`.

The project is a game-map approximation. Do not enforce a fixed national tile
count. Assign each global-grid hex to the country or ocean occupying its largest
area; keep KOR- and PRK-dominant hexes as their respective national tiles.
Assign each tile only to a greatest-overlap admin area in the same country.
National ownership may never cross or collide. Admin target counts are advisory;
only configured minimum representation is mandatory.

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
- Use QGIS core functionality only. Do not add QGIS plugin dependencies.
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
├── Atlas_Korea.qgz
├── AGENTS.md
├── README.md
├── .gitignore
├── .gitattributes
├── config/
│   └── atlas_korea.json
├── data/
│   ├── source/
│   │   └── README.md
│   └── processed/
│       └── Atlas_Korea.gpkg
├── scripts/
│   ├── build_korea_map.py
│   ├── validate_korea_map.py
│   ├── export_for_unreal.py
│   ├── run_mac.sh
│   └── run_windows.ps1
├── overrides/
│   └── tile_assignment_overrides.csv
├── exports/
├── previews/
├── reports/
└── logs/
```

Keep cross-platform line endings stable in `.gitattributes`. In `.gitignore`,
distinguish QGIS temporary/cache/log files and reproducible intermediates from
deliverables. The QGIS project, configuration, scripts, validation reports, and
required GeoPackage remain trackable.

## Single Source of Truth

Store every adjustable design value and validation tolerance in
`config/atlas_korea.json`. Do not duplicate these constants in Python:

- Countries: Republic of Korea (`KOR`) and Democratic People's Republic of
  Korea (`PRK`), generated simultaneously on the same grid
- Project CRS: `EPSG:5179` (`KGD2002 / Unified CS`)
- National tile count: derived from dominant country-or-ocean overlap, not fixed
- Target area per regular hexagon: 605.21 km2
- Side length: approximately 15,262.55 m
- Flat-top dimensions: approximately 30,525.10 m x 26,435.51 m
- Pointy-top dimensions: approximately 26,435.51 m x 30,525.10 m
- Default orientation: `pointy_top`
- The orientation must be switchable to `flat_top` with one config value and a
  complete rebuild.
- Never clip game hexagons to the coastline. Every final game tile remains a
  complete regular hexagon.
- Show administrative borders along shared edges between differently assigned
  hexagons; do not use the curved source boundary as the game border.

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
  `data/processed/Atlas_Korea.gpkg`; keep the original source unchanged.

## Build Pipeline Requirements

Implement `scripts/build_korea_map.py` so that the same inputs and configuration
produce the same geometries, assignments, and stable `tile_id` values:

1. Load the admin-1 source, safely repair invalid geometries, and transform it
   to EPSG:5179.
2. Generate complete 605.21 km2 regular-hex candidates over Korea and nearby
   waters.
3. Calculate each hexagon's intersection area and ratio against Korean land and
   every admin-1 area.
4. Select uncut candidates for the game map.
5. Initially assign each tile to the admin area with greatest overlap.
6. Compare Korea, nearby countries, and ocean in every candidate. Select every
   Korea-dominant candidate, then assign it to its greatest-overlap Korean admin
   area. If a configured required
   admin area receives fewer than `minimum_tiles`, reassign its strongest
   overlapping candidate as an explicit minimum-representation exception.
7. Put difficult explicit adjustments in
   `overrides/tile_assignment_overrides.csv`; do not hide arbitrary exceptions
   in code.
8. Calculate centers and adjacency, with deterministic IDs and symmetric
   neighbor relationships.
9. Write scores, boundary-tile details, and override use to reports.

## GeoPackage Contract

Create at least these layers in `Atlas_Korea.gpkg`:

- `admin1_source`: cleaned/reprojected KOR and PRK first-level boundaries
- `hex_candidates`: all candidates and overlap scores
- `korea_tiles`: all KOR- and PRK-dominant final game hexagons

`korea_tiles` must include at least:

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
tile population. Do not publish `tile_name_population` on `korea_tiles`.

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

Tile display names are subordinate to administrative ownership: the named
city/county must belong to the tile's `admin1_code`. Assign every tile first to
the highest-population overlapping same-owner unit. A duplicated unit keeps its
largest-overlap representative; redistribute its other tiles to currently
unrepresented same-owner units in population order, each choosing its
largest-overlap vacancy. Any positive overlap is eligible. Reserve compatible
representative tiles for as many qualifying real cities as the grid permits.
Resolve competition for compatible tiles in descending real-city population
order without allowing a smaller city to evict a matched larger city. This
priority never relaxes spatial overlap or Admin-1 ownership constraints.
Derive initial city/metropolis fill from the anchored real-city population;
ordinary dense tiles remain `admin` and expose promotion eligibility separately.
Capital status follows the final name but never overrides fill. Draw a yellow
outline only on the exterior edges of the complete same-capital tile group.
For display, every tile in that group inherits the representative capital
anchor's city/metropolis `map_class`; do not copy its population or
`is_initial_city` status to the other tiles.

## QGIS Project and Outputs

- Save `Atlas_Korea.qgz` with relative data paths only.
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
- Show `tile_id` labels only at an appropriate zoom scale.
- Put real source boundaries in a separate toggleable validation group so they
  are not confused with the game-map boundary.
- Export `previews/Atlas_Korea_Overview.png`.
- Write `reports/allocation_report.md` with target/actual/difference per admin,
  boundary tiles, and manual override status.
- Export final tile attributes through `scripts/export_for_unreal.py` to
  `exports/Atlas_Korea_Tiles.geojson` and
  `exports/Atlas_Korea_Tiles.csv`. Keep the GeoPackage in EPSG:5179 and transform
  only exports that require another CRS.
- Provide `scripts/run_mac.sh` and `scripts/run_windows.ps1`. Both must invoke
  the same config and Python logic, auto-detect QGIS where practical, and accept
  a `QGIS_PROCESS` environment override. Keep platform-specific path syntax out
  of core logic.

## Validation Is a Release Gate

Implement `scripts/validate_korea_map.py` and fail with a nonzero exit status if
any check fails:

- CRS is EPSG:5179.
- Every final tile is Korea-dominant over neighboring countries and ocean; the
  national total is derived rather than fixed.
- Every configured admin minimum is satisfied; target counts are reported but
  are not validation gates.
- Every `tile_id` is present and unique.
- Every final geometry is valid, complete, and a regular hexagon.
- Hex area is within the configured tolerance of 605.21 km2.
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
