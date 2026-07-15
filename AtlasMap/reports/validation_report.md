# Atlas Korean Peninsula validation report

Generated: 2026-07-15T12:15:30.207257+00:00

Overall result: **PASS**

| Check | Result | Detail |
| --- | --- | --- |
| Display language is configured | PASS | display_language=en |
| GeoPackage layer loads | PASS | /Users/kimkihoon/Desktop/my-projects/atlas/AtlasMap/data/processed/Atlas_Korea.gpkg |
| CRS | PASS | EPSG:5179 |
| Final country codes | PASS | wrong_country=[] |
| Tile IDs present | PASS | blank=0 |
| Tile IDs unique | PASS | duplicates=[] |
| Admin minimum representation | PASS | deficits={}, unexpected=[] |
| Existing South Korea allocation is unchanged | PASS | country={}, admin={} |
| Exactly one admin assignment | PASS | invalid=[] |
| Admin assignment never crosses a country boundary | PASS | invalid=[] |
| Dominant country-or-ocean calculation | PASS | invalid=[] |
| Dominant-country tile selection | PASS | selection_difference=[] |
| Derived final tile count | PASS | actual=364, derived=364 |
| Every tile retains its dominant national owner | PASS | mismatches=[] |
| Assignment methods | PASS | invalid=[] |
| Dominant-overlap assignments | PASS | mismatches=[] |
| Tile naming fields | PASS | missing=[] |
| Every tile has one display name | PASS | blank=[] |
| Tile naming methods | PASS | invalid=[] |
| Naming reference layer | PASS | units=337 |
| Population values are positive integers with provenance | PASS | invalid=[] |
| All naming-unit populations are resolved | PASS | unresolved=[] |
| Tile name belongs to admin owner | PASS | mismatches=[] |
| Maximum-overlap default names | PASS | mismatches=[] |
| Unique representatives after redistribution | PASS | invalid=[], duplicates=[] |
| City marker layer removed | PASS | layer_valid=False |
| Global tile-population classification thresholds | PASS | city=100000, metropolis=1000000 |
| Single game-tile population model fields | PASS | missing=[] |
| No second naming-unit population on game tiles | PASS | legacy=[] |
| Tile populations are non-negative integers with provenance | PASS | invalid=[] |
| Tile populations exactly reconcile to UN WPP national totals | PASS | mismatches={} |
| Every country has capital tiles | PASS | countries={'KOR': 1, 'PRK': 4} |
| Every tile named for a capital is marked as capital | PASS | invalid=[] |
| Initial city anchors and player upgrade eligibility are consistent | PASS | mismatches=[] |
| Exactly three tile fill classes; capital is an outline | PASS | actual=['admin', 'city', 'metropolis'] |
| Metropolis fill darker than city fill | PASS | city=#4aa3d8, metropolis=#173f6f |
| Capital outline color is configured | PASS | capital_outline=#f4c542 |
| Same-owner groups have complete topology-derived outlines | PASS | edges=526, invalid=[], topology=[], missing=[] |
| Capital outlines follow the exterior of each capital tile group | PASS | edges=20, invalid=[], missing=[] |
| Coastal line layer is intentionally absent | PASS | coastal_tile_outlines is not published during border development |
| Valid geometries | PASS | invalid=[] |
| Complete regular hexagons | PASS | invalid=[] |
| Hex target area | PASS | outside_tolerance=[] |
| No tile overlap | PASS | overlaps=[] |
| Neighbor JSON | PASS | malformed=[] |
| Neighbor IDs exist | PASS | missing=[] |
| Neighbor symmetry | PASS | asymmetric=[] |
| Relative shared paths | PASS | absolute_path_hits=[] |
| QGIS labels use the configured language | PASS | display_language=en |
| Admin border layer renders above tile fills | PASS | border_above_tiles=True |
| Capital outline layer renders above tile fills | PASS | capital_outline_above_tiles=True |

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
| KP-01 | 5 | 1 | 4 | -1 |
| KP-02 | 20 | 1 | 17 | -3 |
| KP-03 | 20 | 1 | 19 | -1 |
| KP-04 | 27 | 1 | 26 | -1 |
| KP-05 | 14 | 1 | 14 | 0 |
| KP-06 | 13 | 1 | 18 | 5 |
| KP-07 | 18 | 1 | 18 | 0 |
| KP-08 | 31 | 1 | 33 | 2 |
| KP-09 | 27 | 1 | 30 | 3 |
| KP-10 | 23 | 1 | 24 | 1 |
| KP-13 | 1 | 1 | 1 | 0 |
