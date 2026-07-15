# Atlas Korean Peninsula validation report

Generated: 2026-07-15T22:43:14.819748+00:00

Overall result: **PASS**

| Check | Result | Detail |
| --- | --- | --- |
| Display language is configured | PASS | display_language=en |
| Every country enforces same-country naming | PASS | invalid=[] |
| Every country confines naming and city fill to the final Admin-1 owner | PASS | invalid=[] |
| Every country uses representative-priority then greatest-overlap fill | PASS | invalid=[] |
| GeoPackage layer loads | PASS | C:\Users\jungle\Documents\Atlas\AtlasMap\data\processed\Atlas_Korea.gpkg |
| CRS | PASS | EPSG:5179 |
| Final country codes | PASS | wrong_country=[] |
| Tile IDs present | PASS | blank=0 |
| Tile IDs unique | PASS | duplicates=[] |
| Only configured Admin-1 owners are used | PASS | unexpected=[] |
| Existing South Korea allocation is unchanged | PASS | country={}, admin={} |
| Exactly one admin assignment | PASS | invalid=[] |
| Admin assignment never crosses a country boundary | PASS | invalid=[] |
| Dominant country-or-ocean calculation | PASS | invalid=[] |
| Dominant-country tile selection | PASS | selection_difference=[] |
| Derived final tile count | PASS | actual=365, derived=365 |
| Every tile retains its dominant national owner | PASS | mismatches=[] |
| Ownership overrides are absent | PASS | invalid=[] |
| Admin-1 assignments use greatest overlap or a positive-overlap representative | PASS | invalid=[] |
| Every official Admin-1 has its configured minimum representation | PASS | minimum=1, invalid={} |
| Tile naming fields | PASS | missing=[] |
| Every tile has one display name | PASS | blank=[] |
| Tile naming methods | PASS | invalid=[] |
| Naming reference layer | PASS | units=337 |
| Authoritative Admin-1 source area ranges | PASS | outside_ranges={} |
| Naming geometries are clipped to their authoritative Admin-1 | PASS | outside=[] |
| Population values are positive integers with provenance | PASS | invalid=[] |
| All naming-unit populations are resolved | PASS | unresolved=[] |
| Population-descending units reserve their best available representative | PASS | missing_field=False, mismatches=[] |
| Remaining naming tiles retain greatest overlap | PASS | mismatches=[] |
| Tile name and city fill stay within the tile's Admin-1 owner | PASS | mismatches=[] |
| Configured metropolitan names are represented | PASS | missing=[] |
| Maximum-overlap default names | PASS | mismatches=[] |
| Unique representatives after redistribution | PASS | invalid=[], duplicates=[] |
| City marker layer removed | PASS | layer_valid=False |
| Global tile-population classification thresholds | PASS | city=100000, metropolis=1000000 |
| Single game-tile population model fields | PASS | missing=[] |
| No second naming-unit population on game tiles | PASS | legacy=[] |
| Tile populations are non-negative integers with provenance | PASS | invalid=[] |
| Tile populations exactly reconcile to UN WPP national totals | PASS | mismatches={} |
| Represented capital tiles belong to configured countries | PASS | countries={'KOR': 1, 'PRK': 3}, invalid=[] |
| Every tile named for a capital is marked as capital | PASS | invalid=[] |
| Every represented city-name group inherits one display class | PASS | invalid_anchors=[], inconsistent=[] |
| Every capital group has one inherited anchor display class | PASS | invalid=[] |
| Initial city anchors and player upgrade eligibility are consistent | PASS | mismatches=[] |
| Exactly three tile fill classes; capital is an outline | PASS | actual=['admin', 'city', 'metropolis'] |
| Metropolis fill darker than city fill | PASS | city=#4aa3d8, metropolis=#173f6f |
| Capital outline color is configured | PASS | capital_outline=#f4c542 |
| Same-owner groups have complete topology-derived outlines | PASS | edges=524, invalid=[], topology=[], missing=[] |
| Capital outlines follow the exterior of each complete capital Admin-1 group | PASS | edges=20, invalid=[], missing=[] |
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
| Tile labels stay inside hexes with no close-zoom cutoff | PASS | tile_labels_confined=True |
| Admin summary labels are overview-only | PASS | admin_labels_overview_only=True |
| Admin border layer renders above tile fills | PASS | border_above_tiles=True |
| Capital outline layer renders above tile fills | PASS | capital_outline_above_tiles=True |

## Allocation

Targets are advisory; every official Admin-1 receives its configured same-country representation floor, then remaining ownership follows greatest overlap.

| Code | Target | Actual | Difference |
| --- | ---: | ---: | ---: |
| KR-11 | 1 | 1 | 0 |
| KR-26 | 1 | 1 | 0 |
| KR-27 | 3 | 3 | 0 |
| KR-28 | 2 | 1 | -1 |
| KR-29 | 1 | 1 | 0 |
| KR-30 | 1 | 1 | 0 |
| KR-31 | 2 | 1 | -1 |
| KR-50 | 1 | 1 | 0 |
| KR-41 | 17 | 17 | 0 |
| KR-42 | 28 | 28 | 0 |
| KR-43 | 12 | 12 | 0 |
| KR-44 | 14 | 11 | -3 |
| KR-45 | 13 | 16 | 3 |
| KR-46 | 20 | 18 | -2 |
| KR-47 | 30 | 28 | -2 |
| KR-48 | 17 | 18 | 1 |
| KR-49 | 3 | 3 | 0 |
| KP-01 | 5 | 4 | -1 |
| KP-02 | 20 | 17 | -3 |
| KP-03 | 20 | 19 | -1 |
| KP-04 | 27 | 26 | -1 |
| KP-05 | 14 | 14 | 0 |
| KP-06 | 13 | 18 | 5 |
| KP-07 | 18 | 18 | 0 |
| KP-08 | 31 | 33 | 2 |
| KP-09 | 27 | 30 | 3 |
| KP-10 | 23 | 24 | 1 |
| KP-13 | 1 | 1 | 0 |
