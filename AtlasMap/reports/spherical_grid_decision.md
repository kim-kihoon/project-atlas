# Spherical grid decision

Date: 2026-07-17

Status: **accepted production decision**. The temporary planar World Mollweide
experiment is superseded. `GLOBAL_MAP_RULES.md` is the authoritative contract.

Atlas adopts OGC ISEA3H level 11 on the WGS84 authalic sphere as the canonical
world grid. The grid has 1,771,472 equal-area cells. Ordinary cells are
approximately 287.933536 km2 hexagons; the 12 topologically required pentagons
have five neighbors and 5/6 of the ordinary-cell area.

This replaces the planned extension of the Korean EPSG:5179 pointy-top grid.
The former 200 km2 output is retained only as historical migration context;
its geometry and `ATLAS_A200_*` IDs are not canonical world IDs.

## Reasons

- Native spherical topology has no antimeridian seam or polar singularity.
- Equal-area cells preserve geographic and economic comparability better than
  a gnomonic grid whose areas vary by location.
- The hierarchy and stable zone IDs support chunking, streaming and LOD.
- Level 11 remains substantially finer than the original 605.21 km2 Korean
  prototype while keeping the complete globe below two million cells.
- Twelve pentagons are a mathematical topological requirement, not map errors.

## Generator contract

- Library: DGGAL 0.0.6
- License: BSD-3-Clause
- DGGRS URI: https://www.opengis.net/def/dggrs/OGC/1.0/ISEA3H
- Dependency file: `requirements-dggs.txt`
- QGIS plugin dependency: none

DGGAL is used only to generate/query canonical cell geometry, identity,
hierarchy and adjacency. QGIS core remains responsible for boundary processing,
overlap allocation, validation styling and regional project output.

## Migration result

Ownership, Admin-1 representation, display naming, city anchoring, population
reconciliation, capital outlines and topology-derived borders retain their
current country-neutral rules. The six-country production build was regenerated
on 2026-07-17 and passed the spherical East Asia release gate with 39,812 cells.
It contains 39,811 hexagons and one pentagon. Validation checks canonical IDs,
ISEA3H level, spherical area, hexagon/pentagon topology, uncut candidate
geometry, canonical adjacency and complete logical-side rendering. The current
record is `reports/east_asia_spherical_implementation_report.md`; the earlier
Korea-only record remains migration history.
