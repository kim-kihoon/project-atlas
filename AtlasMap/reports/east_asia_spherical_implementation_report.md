# Atlas East Asia spherical-grid implementation report

Date: 2026-07-18

Status: **implemented and release-gate validated**

## Scope and grid

The QGIS milestone builds KOR, PRK, CHN, MNG, JPN and TWN simultaneously on
the immutable OGC ISEA3H level-11 grid on the WGS84 authalic sphere. DGGAL
0.0.6 supplies canonical zone identity, spherical area, cell type and
adjacency. QGIS LTR 3.44.12 uses `EPSG:8857` Equal Earth for regional
intersection calculations and `EPSG:3857` Web Mercator for project/preview
display; projection does not define topology.

The full world contract contains 1,771,472 cells: 1,771,460 hexagons and 12
pentagons. The East Asia selection contains 39,812 cells, of which 39,811 are
hexagons and one is a pentagon located in the CHN-owned selection.

## Deterministic allocation

| Country | Tiles |
| --- | ---: |
| KOR | 332 |
| PRK | 418 |
| CHN | 32,215 |
| JPN | 1,262 |
| MNG | 5,461 |
| TWN | 124 |
| **Total** | **39,812** |

National ownership is derived from greatest country-or-ocean overlap. Admin-1
ownership then applies the universal feasible one-tile representation floor
and greatest-overlap rule. At this finite resolution, Macau SAR, Penghu,
Kinmen and Matsu Islands have no compatible positive-overlap representative
that can be assigned without violating the ownership constraints; they remain
explicit validation evidence rather than receiving manual exceptions.

## Verification result

`reports/east_asia_validation_report.md` records an overall **PASS**. It covers
canonical ISEA3H ID round trips, level, cell type, spherical area, complete
uncut projected geometry, non-overlap, canonical and symmetric adjacency,
complete topology-derived Admin-1/capital logical sides, national ownership,
naming, city classification, capital representation, exact national population
reconciliation, relative paths and QGIS labeling/layer order.

The generated deliverables are `Atlas_East_Asia.qgz`,
`data/processed/Atlas_East_Asia.gpkg`, the CSV/GeoJSON exports, the overview
preview, allocation report and validation report. No QGIS plugin is required;
DGGAL is installed as a pinned scripted runtime dependency.

## Boundary-rendering correction

The original renderer incorrectly assumed that DGGAL's neighbor-list order was
the same as its refined boundary-side order. Canonical adjacency IDs were
therefore correct while some displayed lines were taken from the wrong side of
the cell, producing scattered dots and misplaced capital segments. The builder
now assigns sides to neighbors by deterministic one-to-one spherical proximity.

All 10,096 Admin-1/country/exterior logical sides and 103 capital logical sides
remain individual validation evidence. QGIS renders topology-derived merged
chains instead: 328 administrative/country/exterior chains and six capital
chains. Flat caps, miter joins and scale-appropriate widths remove endpoint
blobs. Validation confirms that every shared side lies on its participating
cells and that chain merging preserves total length to sub-meter precision.

## Capital display and gameplay scope decision

The capital rule now separates map presentation from gameplay effects. Every
tile carrying the configured capital naming-unit code has `is_capital=true`,
and the yellow topology-derived line surrounds only the exterior of that whole
capital-name tile group. Internal edges within the group cancel. Differently
named tiles in the same capital Admin-1 no longer receive the yellow outline.

Each configured country also has exactly one `is_capital_anchor=true` tile: the
capital naming unit's representative real-city anchor. Future capital-only
bonuses, facilities or district-slot adjustments apply only to this anchor, so
a geographically large capital-name group does not receive multiplied gameplay
benefits. Neither field changes national ownership, Admin-1 ownership, city
fill class or population allocation. The build and release-gate validator now
enforce both scopes from `config/atlas_east_asia.json`.
