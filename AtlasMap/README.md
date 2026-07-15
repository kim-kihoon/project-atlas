# Atlas Korean Peninsula QGIS Map

This directory contains the reproducible GIS pipeline for the Korean Peninsula
prototype map used by **Atlas**. It builds the Republic of Korea and the
Democratic People's Republic of Korea together on one common regular-hex grid
in EPSG:5179. Each tile goes first to its dominant country-or-ocean overlap,
then only to a first-level administrative area belonging to that same country.

There is no fixed national tile count. A tile belongs to KOR or PRK only when
that country's land occupies more of it than every neighboring country and the
ocean. The two countries are evaluated simultaneously, so they cannot claim the
same tile or assign a tile to an administrative area across the national border.
Country-border edges are stored separately from ordinary admin-border edges.
Tiles are then assigned to the same-country administrative area occupying their
largest portion.
Each configured admin area is guaranteed one tile only when dominant-overlap
assignment would otherwise leave it unrepresented. Historical target counts
are advisory report values.

Administrative ownership and city type are independent. For example, a tile
containing Yongin remains owned by Gyeonggi (`admin1_code=KR-41`) while its
population-based `city_class` can be `metropolis`. City status changes fill
color, never administrative borders.

Tile display names must belong to the tile's administrative owner. Every tile
first goes to the highest-population same-owner city or county that overlaps it
at all. A duplicated unit keeps the tile where it occupies the most area; its
other tiles become vacancies. Unrepresented units then take compatible
vacancies in population order, choosing their largest-overlap vacancy. There is
no minimum overlap threshold. City class and
capital color follow the final tile name, not an independently located point.

The map uses exactly four tile fill classes: ordinary administrative tile,
light-blue city (100,000-999,999), dark-navy metropolis (1,000,000+), and
gold capital. Ordinary tiles do not receive separate province colors. Population
comes from the globally uniform GeoNames dump. A non-positive ADM2 population
is automatically repaired from the largest positive populated-place record
with the same admin-2 code, then by the same normalized name; the chosen method
and source identifier are retained for audit. If GeoNames still has no positive
value, the final fallback is a zonal sum from the globally consistent 2020
WorldPop 1 km UN-adjusted population raster.
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

## Main outputs

- `Atlas_Korea.qgz`: QGIS project; open this first in QGIS.
- `data/processed/Atlas_Korea.gpkg`: source, city/county naming reference,
  candidates, final tiles, and admin borders. Coastal lines are deferred.
- `previews/Atlas_Korea_Overview.png`: rendered overview.
- `reports/allocation_report.md`: target and actual tile allocation.
- `reports/validation_report.md`: release-gate validation results.
- `exports/Atlas_Korea_Tiles.geojson` and `.csv`: Unreal-oriented exports.

The current deterministic build contains 160 KOR tiles and 204 PRK tiles.
Adding PRK is regression-gated against all 160 existing KOR tiles and their
previous Admin-1 counts.

QGIS terms for beginners: a **layer** is one collection of map features; a
**GeoPackage** is one database file that can hold several layers; a **CRS** is
the coordinate system used to locate and measure those features.

All shared paths are relative to this directory. Do not save a QGIS layer using
an absolute path.
