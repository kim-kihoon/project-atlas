# Atlas East Asia planar-grid implementation report (superseded)

Date: 2026-07-17

Status: **rejected historical experiment**. Production uses OGC ISEA3H level 11
as documented in `east_asia_spherical_implementation_report.md` and
`GLOBAL_MAP_RULES.md`.

Former status: regional release gate PASS; world-edge behavior remained future work

## Scope

The production map now builds KOR, PRK, CHN, MNG, JPN and TWN together. CGAZ
6.0.0 supplies the common ADM0/ADM1/ADM2 boundary snapshot. GeoNames, WorldPop
2020 UN-adjusted 1 km rasters and UN WPP 2024 use the same country-neutral
population and city pipeline for all six countries.

## Grid decision

The OGC ISEA3H prototype was rejected for gameplay because a spherical
hex/pentagon mesh cannot keep one globally constant north-up edge orientation.
Production returned to a planar pointy-top regular-hex lattice:

- CRS: `ESRI:54009` World Mollweide
- fixed global origin: `(0, 0)`
- target and validated tile area: 200 km2
- canonical ID: `ATLAS_MOLL_A200_P_R{row}_C{column}`
- topology: complete regular hexagons only; no pentagons or face seams
- ownership: greatest country-or-ocean overlap, then same-country Admin-1
- future world gate: antimeridian pairing and polar/world-outline behavior are
  explicitly deferred and are not claimed complete

The first planar implementation exposed an incorrect stagger-axis formula that
created 16.666667 km2 overlaps between adjacent rows. The release validator
caught it. The generator now uses the standard odd-row pointy-top layout and
the final map has no overlap or non-manifold edges.

## Deterministic allocation

| Country | Tiles |
| --- | ---: |
| KOR | 480 |
| PRK | 613 |
| CHN | 46,466 |
| JPN | 1,839 |
| MNG | 7,849 |
| TWN | 178 |
| **Total** | **57,425** |

National population sums reconcile exactly to the configured 2026 UN WPP
medium-variant totals. All six capitals are represented and capital Admin-1
groups use topology-derived yellow exterior outlines.

## Finite-resolution Admin-1 findings

The one-tile representation floor applies only when a positive-overlap tile can
be reassigned without removing another official Admin-1's last tile. At the
200 km2 resolution the following source Admin-1 units are infeasible and remain
at zero tiles:

- Macau Special Administrative Region (CHN)
- Penghu (TWN)
- Matsu Islands (TWN)

These are reported consequences of the uniform grid, not manual overrides.

## Country-neutral naming corrections

The registry generator spatially maps GeoNames Admin-1 codes to CGAZ polygons.
Administrative suffixes such as `Municipality`, `Prefecture`, `Province`,
`Autonomous Region` and `Special Administrative Region` are normalized by one
shared rule. GeoNames capital alternate names are mapped to the containing
aggregate Admin-1 without country-specific code branches. Aggregate city-level
Admin-1 naming units use the complete official Admin-1 geometry, which resolved
Beijing and Ulaanbaatar capital anchoring consistently.

Two Chinese naming units have neither a usable positive GeoNames population nor
a positive WorldPop zonal sum. They remain explicit `unknown` values rather
than receiving invented population:

- `CHN-43563684B30737817496648:dongshanxian`
- `CHN-43563684B97104103456250:macau-special-administrative-region`

## Release evidence

- QGIS: 3.44.12 LTR
- regional validation: `reports/east_asia_validation_report.md` — PASS
- allocation report: `reports/east_asia_allocation_report.md`
- QGIS project: `Atlas_East_Asia.qgz`
- GeoPackage: `data/processed/Atlas_East_Asia.gpkg`
- preview: `previews/Atlas_East_Asia_Overview.png`
- exports: `exports/Atlas_East_Asia_Tiles.csv` and `.geojson`

The authoritative design contract is `GLOBAL_MAP_RULES.md`; this report records
the implementation and does not override it.
