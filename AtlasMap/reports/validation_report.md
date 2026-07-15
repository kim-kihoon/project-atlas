# Atlas Korea validation report

Generated: 2026-07-15T02:00:36.249006+00:00

Overall result: **PASS**

| Check | Result | Detail |
| --- | --- | --- |
| GeoPackage layer loads | PASS | /Users/kimkihoon/Desktop/my-projects/atlas/AtlasMap/data/processed/Atlas_Korea.gpkg |
| CRS | PASS | EPSG:5179 |
| Final country code | PASS | wrong_country=[] |
| Tile IDs present | PASS | blank=0 |
| Tile IDs unique | PASS | duplicates=[] |
| Admin minimum representation | PASS | deficits={}, unexpected=[] |
| Exactly one admin assignment | PASS | invalid=[] |
| Dominant country-or-ocean calculation | PASS | invalid=[] |
| Dominant-country tile selection | PASS | selection_difference=[] |
| Derived final tile count | PASS | actual=160, derived=160 |
| Assignment methods | PASS | invalid=[] |
| Dominant-overlap assignments | PASS | mismatches=[] |
| Tile naming fields | PASS | missing=[] |
| Every tile has one display name | PASS | blank=[] |
| Tile naming methods | PASS | invalid=[] |
| Naming reference layer | PASS | units=161 |
| Tile name belongs to admin owner | PASS | mismatches=[] |
| Maximum-overlap default names | PASS | mismatches=[] |
| Unique representatives after redistribution | PASS | invalid=[], duplicates=[] |
| City marker layer removed | PASS | layer_valid=False |
| Exactly one capital tile | PASS | tiles=1 |
| City class follows final same-owner tile name | PASS | mismatches=[] |
| Exactly four tile color classes | PASS | actual=['admin', 'capital', 'city', 'metropolis'] |
| Metropolis fill darker than city fill | PASS | city=#4aa3d8, metropolis=#173f6f |
| Same-owner groups have complete topology-derived outlines | PASS | edges=253, invalid=[], topology=[], missing=[] |
| Coastal line layer is intentionally absent | PASS | coastal_tile_outlines is not published during border development |
| Valid geometries | PASS | invalid=[] |
| Complete regular hexagons | PASS | invalid=[] |
| Hex target area | PASS | outside_tolerance=[] |
| No tile overlap | PASS | overlaps=[] |
| Neighbor JSON | PASS | malformed=[] |
| Neighbor IDs exist | PASS | missing=[] |
| Neighbor symmetry | PASS | asymmetric=[] |
| Relative shared paths | PASS | absolute_path_hits=[] |
| Admin border layer renders above tile fills | PASS | border_above_tiles=True |

## Allocation

Targets are advisory; minimums are validation gates.

| Code | Target | Minimum | Actual | Difference |
| --- | ---: | ---: | ---: | ---: |
| KR-11 | 1 | 1 | 1 | 0 |
| KR-26 | 1 | 1 | 1 | 0 |
| KR-27 | 3 | 1 | 1 | -2 |
| KR-28 | 2 | 1 | 1 | -1 |
| KR-29 | 1 | 1 | 1 | 0 |
| KR-30 | 1 | 1 | 1 | 0 |
| KR-31 | 2 | 1 | 1 | -1 |
| KR-50 | 1 | 1 | 1 | 0 |
| KR-41 | 17 | 1 | 16 | -1 |
| KR-42 | 28 | 1 | 33 | 5 |
| KR-43 | 12 | 1 | 12 | 0 |
| KR-44 | 14 | 1 | 11 | -3 |
| KR-45 | 13 | 1 | 15 | 2 |
| KR-46 | 20 | 1 | 16 | -4 |
| KR-47 | 30 | 1 | 30 | 0 |
| KR-48 | 17 | 1 | 16 | -1 |
| KR-49 | 3 | 1 | 3 | 0 |
