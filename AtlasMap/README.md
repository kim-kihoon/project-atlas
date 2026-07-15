# Atlas Korea QGIS Map

This directory contains the reproducible GIS pipeline for the Republic of Korea
prototype map used by **Atlas**. The map uses complete regular hexagons in
EPSG:5179 and assigns each tile first to its dominant country-or-ocean overlap,
then to a first-level administrative area.

There is no fixed national tile count. A tile belongs to Korea only when Korean
land occupies more of it than any neighboring country or the ocean. Korean
tiles are assigned to the administrative area occupying their largest portion.
Each configured admin area is guaranteed one tile only when dominant-overlap
assignment would otherwise leave it unrepresented. Historical target counts
are advisory report values.

Administrative ownership and city type are independent. For example, a tile
containing Yongin remains owned by Gyeonggi (`admin1_code=KR-41`) while its
population-based `city_class` can be `metropolis`. City status changes fill
color, never administrative borders.

Tile display names must belong to the tile's administrative owner. Within each
admin-1 area, cities and counties occupying at least 5% of a hex enter a global
first-pass matching that gives each unit at most one representative tile, with
known population as the priority and overlap as the deterministic preference.
Remaining tiles use their largest-overlap same-owner unit. City class and
capital color follow the final tile name, not an independently located point.

The map uses exactly four tile fill classes: ordinary administrative tile,
light-blue city (500,000-999,999), dark-navy metropolis (1,000,000+), and
gold capital. Ordinary tiles do
not receive separate province colors. Thick dark lines between tiles with
different `admin1_code` values carry the administrative-boundary information.
Those lines render as a single dark stroke above tile fills. Dashed blue coastal
lines include only outer tile edges adjacent to an ocean-dominant grid cell;
they never outline a complete coastal hex. No city-marker layer is displayed or
published.

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

## Main outputs

- `Atlas_Korea.qgz`: QGIS project; open this first in QGIS.
- `data/processed/Atlas_Korea.gpkg`: source, city/county naming reference,
  candidates, final tiles, admin borders, and ocean-adjacent coastal edges.
- `previews/Atlas_Korea_Overview.png`: rendered overview.
- `reports/allocation_report.md`: target and actual tile allocation.
- `reports/validation_report.md`: release-gate validation results.
- `exports/Atlas_Korea_Tiles.geojson` and `.csv`: Unreal-oriented exports.

QGIS terms for beginners: a **layer** is one collection of map features; a
**GeoPackage** is one database file that can hold several layers; a **CRS** is
the coordinate system used to locate and measure those features.

All shared paths are relative to this directory. Do not save a QGIS layer using
an absolute path.
