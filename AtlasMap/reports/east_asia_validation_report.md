# Atlas East Asia validation report

Generated: 2026-07-19T00:15:55.192581+00:00

Overall result: **PASS**

| Check | Result | Detail |
| --- | --- | --- |
| Display language is configured | PASS | display_language=en |
| Capital display and gameplay scopes are configured | PASS | capital_model={'outline_scope': 'all_tiles_with_capital_naming_unit_code', 'gameplay_bonus_scope': 'single_representative_anchor_per_country', 'group_field': 'is_capital', 'anchor_field': 'is_capital_anchor'} |
| Every country enforces same-country naming | PASS | invalid=[] |
| Every country explicitly configures naming/Admin-1 coupling | PASS | invalid=[] |
| Every country uses representative-priority then greatest-overlap fill | PASS | invalid=[] |
| GeoPackage layer loads | PASS | C:\Users\leona\Documents\Atlas\AtlasMap\data\processed\Atlas_East_Asia.gpkg |
| Analysis CRS | PASS | EPSG:8857 |
| Final country codes | PASS | wrong_country=[] |
| Tile IDs present | PASS | blank=0 |
| Tile IDs unique | PASS | duplicates=[] |
| Only configured Admin-1 owners are used | PASS | unexpected=[] |
| Frozen canonical-snapshot allocation is unchanged | PASS | country={}, admin={} |
| Exactly one admin assignment | PASS | invalid=[] |
| Admin assignment never crosses a country boundary | PASS | invalid=[] |
| Dominant country-or-ocean calculation | PASS | invalid=[] |
| Dominant-country tile selection | PASS | selection_difference=[] |
| Derived final tile count | PASS | actual=39812, derived=39812 |
| Every tile retains its dominant national owner | PASS | mismatches=[] |
| Ownership overrides are absent | PASS | invalid=[] |
| Admin-1 assignments use greatest overlap or a positive-overlap representative | PASS | invalid=[] |
| Every official Admin-1 has its configured minimum representation | PASS | minimum=1, invalid={} |
| Tile naming fields | PASS | missing=[] |
| Every tile has one display name | PASS | blank=[] |
| Tile naming methods | PASS | invalid=[] |
| Naming reference layer | PASS | units=5063 |
| Frozen canonical-snapshot Admin-1 area ranges | PASS | outside_ranges={} |
| Naming geometries follow configured Admin-1 clipping policy | PASS | strict_admin_codes=['CHN-43563684B11053367304830', 'CHN-43563684B14397599951889', 'CHN-43563684B17418114845297', 'CHN-43563684B19802372559419', 'CHN-43563684B26929678147954', 'CHN-43563684B30737817496648', 'CHN-43563684B32591653033375', 'CHN-43563684B34303967365755', 'CHN-43563684B38891657012300', 'CHN-43563684B3982601277390', 'CHN-43563684B41908353419915', 'CHN-43563684B46172434476792', 'CHN-43563684B50492231896073', 'CHN-43563684B55920014778896', 'CHN-43563684B58229551045164', 'CHN-43563684B58995436924100', 'CHN-43563684B59914390554750', 'CHN-43563684B62959128536432', 'CHN-43563684B64367354813847', 'CHN-43563684B64666899633249', 'CHN-43563684B64987462919315', 'CHN-43563684B67556328368055', 'CHN-43563684B69230098435171', 'CHN-43563684B73528730180553', 'CHN-43563684B75549295130005', 'CHN-43563684B78583622565599', 'CHN-43563684B84540832148656', 'CHN-43563684B84701301190484', 'CHN-43563684B87813050901813', 'CHN-43563684B95381459098578', 'CHN-43563684B96917371447908', 'CHN-43563684B97104103456250', 'CHN-43563684B97743196909507', 'JPN-47310658B1351727290704', 'JPN-47310658B14484689696833', 'JPN-47310658B16920518838967', 'JPN-47310658B1770087263252', 'JPN-47310658B18585040133157', 'JPN-47310658B199342310790', 'JPN-47310658B20461581662238', 'JPN-47310658B23327126724630', 'JPN-47310658B25007192225139', 'JPN-47310658B25198997079345', 'JPN-47310658B28580642450327', 'JPN-47310658B31569081891025', 'JPN-47310658B31759366295450', 'JPN-47310658B3517091690', 'JPN-47310658B36253982271084', 'JPN-47310658B40291932252870', 'JPN-47310658B41093195623763', 'JPN-47310658B49885151916407', 'JPN-47310658B50146545060878', 'JPN-47310658B51488753471902', 'JPN-47310658B52822170400832', 'JPN-47310658B53666900505284', 'JPN-47310658B53717877461658', 'JPN-47310658B55038426470858', 'JPN-47310658B56113460554138', 'JPN-47310658B56795339529760', 'JPN-47310658B57998234967550', 'JPN-47310658B61159371292051', 'JPN-47310658B6129583352403', 'JPN-47310658B64524405341851', 'JPN-47310658B66619598690773', 'JPN-47310658B70834199776359', 'JPN-47310658B78383189487115', 'JPN-47310658B79582216473080', 'JPN-47310658B82893106270036', 'JPN-47310658B83740553463450', 'JPN-47310658B84734951454670', 'JPN-47310658B84769036468911', 'JPN-47310658B84955483384411', 'JPN-47310658B89229150671737', 'JPN-47310658B89542195514726', 'JPN-47310658B9011809709100', 'JPN-47310658B92659408322453', 'JPN-47310658B93104231283628', 'JPN-47310658B94014236912993', 'JPN-47310658B99690886618857', 'JPN-47310658B99930143900280', 'KP-01', 'KP-02', 'KP-03', 'KP-04', 'KP-05', 'KP-06', 'KP-07', 'KP-08', 'KP-09', 'KP-10', 'KP-14', 'KR-11', 'KR-26', 'KR-27', 'KR-28', 'KR-29', 'KR-30', 'KR-31', 'KR-41', 'KR-42', 'KR-43', 'KR-44', 'KR-45', 'KR-46', 'KR-47', 'KR-48', 'KR-49', 'KR-50', 'MNG-14279143B15424694570155', 'MNG-14279143B20985490361275', 'MNG-14279143B22317554045022', 'MNG-14279143B31648094269757', 'MNG-14279143B32551742065768', 'MNG-14279143B32793669032275', 'MNG-14279143B35762276870520', 'MNG-14279143B39885639062119', 'MNG-14279143B47638406449643', 'MNG-14279143B49613281560709', 'MNG-14279143B49702315868913', 'MNG-14279143B52126529381065', 'MNG-14279143B54746499726346', 'MNG-14279143B59026071325992', 'MNG-14279143B63368554420497', 'MNG-14279143B69842940795179', 'MNG-14279143B70362797710090', 'MNG-14279143B7284431230829', 'MNG-14279143B7576416025221', 'MNG-14279143B76228648820573', 'MNG-14279143B81467460095364', 'MNG-14279143B84215380438566', 'TWN-90331920B22703176907123', 'TWN-90331920B28258400455048', 'TWN-90331920B28650079022847', 'TWN-90331920B3426825384645', 'TWN-90331920B34778475945127', 'TWN-90331920B35610459745524', 'TWN-90331920B44631347362338', 'TWN-90331920B45331697504939', 'TWN-90331920B54932243986706', 'TWN-90331920B60519442170303', 'TWN-90331920B61423557936862', 'TWN-90331920B66653841730450', 'TWN-90331920B68512430020187', 'TWN-90331920B7705287137405', 'TWN-90331920B80042697765976', 'TWN-90331920B81487360502151', 'TWN-90331920B88579316672132', 'TWN-90331920B89258408533695', 'TWN-90331920B8990770803141', 'TWN-90331920B90000183725132', 'TWN-90331920B93110903621752', 'TWN-90331920B98084155135420']; outside=[] |
| Dated required Admin-1 units | PASS | enforcement=report_only; mismatches=[{'country': 'PRK', 'code': 'KP-15', 'name': 'Kaesong', 'configured': False, 'generated': False, 'effective_from': '2019-01-01'}] |
| Dated administrative membership facts | PASS | enforcement=report_only; scenario_date=None; mismatches=[] |
| Population values are positive integers with provenance | PASS | invalid=[] |
| Unresolved naming-unit populations remain explicit | PASS | unresolved_count=1; examples=['CHN-43563684B30737817496648:dongshanxian'] |
| Population-descending units reserve their best available representative | PASS | missing_field=False, mismatches=[] |
| Remaining naming tiles retain greatest overlap | PASS | mismatches=[] |
| Tile name and city fill obey configured country/Admin-1 scope | PASS | mismatches=[] |
| Configured metropolitan names are represented | PASS | missing=[] |
| Maximum-overlap default names | PASS | mismatches=[] |
| Unique representatives after redistribution | PASS | invalid=[], duplicates=[] |
| City marker layer removed | PASS | layer_valid=False |
| Global tile-population classification thresholds | PASS | city=100000, metropolis=1000000 |
| Single game-tile population model fields | PASS | missing=[] |
| No second naming-unit population on game tiles | PASS | legacy=[] |
| Tile populations are non-negative integers with provenance | PASS | invalid=[] |
| Tile populations exactly reconcile to UN WPP national totals | PASS | mismatches={} |
| Represented capital tiles belong to configured countries | PASS | countries={'MNG': 1, 'CHN': 53, 'TWN': 1, 'PRK': 6, 'KOR': 2, 'JPN': 1}, invalid=[] |
| Every configured country has a represented capital | PASS | missing=[] |
| Every tile named for a capital is marked as capital | PASS | invalid=[] |
| Every country has exactly one capital gameplay anchor | PASS | counts={'MNG': 1, 'CHN': 1, 'TWN': 1, 'PRK': 1, 'KOR': 1, 'JPN': 1}, invalid=[] |
| Every represented city-name group inherits one display class | PASS | invalid_anchors=[], inconsistent=[] |
| Every capital group has one inherited anchor display class | PASS | invalid=[] |
| Initial city anchors and player upgrade eligibility are consistent | PASS | mismatches=[] |
| Exactly three tile fill classes; capital is an outline | PASS | actual=['admin', 'city', 'metropolis'] |
| Metropolis fill darker than city fill | PASS | city=#4aa3d8, metropolis=#173f6f |
| Capital outline color is configured | PASS | capital_outline=#f4c542 |
| Coastal line layer is intentionally absent | PASS | coastal_tile_outlines is not published during border development |
| Unreal runtime contract fields exist | PASS | missing=[] |
| Spherical DGGRS contract | PASS | global_count=1771472; contract={'type': 'spherical_dggrs', 'crs_or_dggs': 'OGC ISEA3H', 'definition_uri': 'https://www.opengis.net/def/dggrs/OGC/1.0/ISEA3H', 'reference_surface': 'WGS84_authalic_sphere', 'level': 11, 'chunk_level': 7, 'global_cell_count': 1771472, 'hexagon_count': 1771460, 'pentagon_count': 12, 'hexagon_area_km2': 287.9335363986343, 'pentagon_area_km2': 239.9446136655286, 'edge_refinement': 0, 'candidate_bbox_buffer_degrees': 2.0, 'topology': 'canonical_DGGRS_adjacency_five_or_six_neighbors', 'tile_id_scheme': 'ATLAS_ISEA3H_L{level}_{zone_text_id}', 'ownership_independent_tile_ids': True, 'antimeridian_policy': 'native_spherical_adjacency_no_planar_seam', 'polar_policy': 'native_spherical_cells_no_planar_singularity', 'generator': {'library': 'DGGAL', 'version': '0.0.6', 'license': 'BSD-3-Clause', 'qgis_plugin_required': False}} |
| Valid projected display geometries | PASS | invalid=[] |
| Canonical hexagon/pentagon cell types | PASS | invalid=[] |
| Stable canonical ISEA3H IDs | PASS | invalid=[] |
| Canonical spherical cell areas | PASS | outside_tolerance=[] |
| Final cells are complete uncut candidates | PASS | invalid=[] |
| Unreal runtime topology and chunk contract | PASS | invalid=[] |
| No tile overlap | PASS | overlaps=[] |
| Neighbor JSON | PASS | malformed=[] |
| Neighbor lists contain no duplicates | PASS | invalid=[] |
| Neighbor IDs exist | PASS | missing=[] |
| Neighbor symmetry | PASS | asymmetric=[] |
| No non-manifold spherical logical edges | PASS | invalid=[] |
| Neighbor lists match canonical DGGRS adjacency | PASS | invalid=[] |
| Same-owner groups use complete spherical logical-side outlines | PASS | edges=10096, invalid=[], missing=[] |
| Capital outlines use complete spherical logical sides | PASS | edges=103, invalid=[], missing=[] |
| QGIS admin borders are continuous topology render chains | PASS | chains=328, sides=10096, length_difference=0.134560, invalid=[] |
| QGIS capital outlines are continuous topology render chains | PASS | chains=6, sides=103, length_difference=0.000577, invalid=[] |
| Relative shared paths | PASS | absolute_path_hits=[] |
| QGIS project display CRS | PASS | expected=EPSG:3857 |
| QGIS labels use the configured language | PASS | display_language=en |
| Tile labels stay inside hexes with no close-zoom cutoff | PASS | tile_labels_confined=True |
| Admin summary labels are overview-only | PASS | admin_labels_overview_only=True |
| Admin border layer renders above tile fills | PASS | border_above_tiles=True |
| Capital outline layer renders above tile fills | PASS | capital_outline_above_tiles=True |

## Allocation

Targets are advisory; every feasible official Admin-1 receives its same-country representation floor, then remaining ownership follows greatest overlap.

| Code | Target | Actual | Difference |
| --- | ---: | ---: | ---: |
| KR-11 | 1 | 2 | 1 |
| KR-26 | 1 | 1 | 0 |
| KR-27 | 3 | 2 | -1 |
| KR-28 | 2 | 1 | -1 |
| KR-29 | 1 | 1 | 0 |
| KR-30 | 1 | 2 | 1 |
| KR-31 | 2 | 5 | 3 |
| KR-50 | 1 | 1 | 0 |
| KR-41 | 17 | 34 | 17 |
| KR-42 | 28 | 67 | 39 |
| KR-43 | 12 | 27 | 15 |
| KR-44 | 14 | 25 | 11 |
| KR-45 | 13 | 28 | 15 |
| KR-46 | 20 | 34 | 14 |
| KR-47 | 30 | 63 | 33 |
| KR-48 | 17 | 33 | 16 |
| KR-49 | 3 | 6 | 3 |
| KP-01 | 5 | 6 | 1 |
| KP-02 | 20 | 41 | 21 |
| KP-03 | 20 | 40 | 20 |
| KP-04 | 27 | 60 | 33 |
| KP-05 | 14 | 25 | 11 |
| KP-06 | 13 | 37 | 24 |
| KP-07 | 18 | 38 | 20 |
| KP-08 | 31 | 62 | 31 |
| KP-09 | 27 | 56 | 29 |
| KP-10 | 23 | 50 | 27 |
| KP-14 | 1 | 3 | 2 |
| CHN-43563684B75549295130005 | N/A | 487 | N/A |
| CHN-43563684B17418114845297 | N/A | 53 | N/A |
| CHN-43563684B97743196909507 | N/A | 273 | N/A |
| CHN-43563684B30737817496648 | N/A | 412 | N/A |
| CHN-43563684B11053367304830 | N/A | 1485 | N/A |
| CHN-43563684B59914390554750 | N/A | 838 | N/A |
| CHN-43563684B38891657012300 | N/A | 588 | N/A |
| CHN-43563684B78583622565599 | N/A | 626 | N/A |
| CHN-43563684B67556328368055 | N/A | 111 | N/A |
| CHN-43563684B58229551045164 | N/A | 627 | N/A |
| CHN-43563684B55920014778896 | N/A | 1557 | N/A |
| CHN-43563684B96917371447908 | N/A | 563 | N/A |
| CHN-43563684B69230098435171 | N/A | 3 | N/A |
| CHN-43563684B41908353419915 | N/A | 652 | N/A |
| CHN-43563684B64987462919315 | N/A | 714 | N/A |
| CHN-43563684B95381459098578 | N/A | 3960 | N/A |
| CHN-43563684B64367354813847 | N/A | 331 | N/A |
| CHN-43563684B87813050901813 | N/A | 586 | N/A |
| CHN-43563684B3982601277390 | N/A | 633 | N/A |
| CHN-43563684B26929678147954 | N/A | 510 | N/A |
| CHN-43563684B97104103456250 | N/A | 0 | N/A |
| CHN-43563684B64666899633249 | N/A | 168 | N/A |
| CHN-43563684B46172434476792 | N/A | 2444 | N/A |
| CHN-43563684B62959128536432 | N/A | 697 | N/A |
| CHN-43563684B58995436924100 | N/A | 502 | N/A |
| CHN-43563684B32591653033375 | N/A | 7 | N/A |
| CHN-43563684B34303967365755 | N/A | 540 | N/A |
| CHN-43563684B14397599951889 | N/A | 1717 | N/A |
| CHN-43563684B84701301190484 | N/A | 38 | N/A |
| CHN-43563684B19802372559419 | N/A | 3912 | N/A |
| CHN-43563684B50492231896073 | N/A | 5527 | N/A |
| CHN-43563684B84540832148656 | N/A | 1302 | N/A |
| CHN-43563684B73528730180553 | N/A | 352 | N/A |
| JPN-47310658B49885151916407 | N/A | 16 | N/A |
| JPN-47310658B79582216473080 | N/A | 39 | N/A |
| JPN-47310658B70834199776359 | N/A | 32 | N/A |
| JPN-47310658B1351727290704 | N/A | 16 | N/A |
| JPN-47310658B51488753471902 | N/A | 19 | N/A |
| JPN-47310658B56113460554138 | N/A | 15 | N/A |
| JPN-47310658B84955483384411 | N/A | 16 | N/A |
| JPN-47310658B52822170400832 | N/A | 50 | N/A |
| JPN-47310658B28580642450327 | N/A | 37 | N/A |
| JPN-47310658B57998234967550 | N/A | 24 | N/A |
| JPN-47310658B84769036468911 | N/A | 30 | N/A |
| JPN-47310658B99930143900280 | N/A | 267 | N/A |
| JPN-47310658B99690886618857 | N/A | 29 | N/A |
| JPN-47310658B31759366295450 | N/A | 23 | N/A |
| JPN-47310658B64524405341851 | N/A | 13 | N/A |
| JPN-47310658B25007192225139 | N/A | 54 | N/A |
| JPN-47310658B61159371292051 | N/A | 5 | N/A |
| JPN-47310658B56795339529760 | N/A | 28 | N/A |
| JPN-47310658B16920518838967 | N/A | 8 | N/A |
| JPN-47310658B3517091690 | N/A | 22 | N/A |
| JPN-47310658B50146545060878 | N/A | 24 | N/A |
| JPN-47310658B94014236912993 | N/A | 16 | N/A |
| JPN-47310658B36253982271084 | N/A | 21 | N/A |
| JPN-47310658B93104231283628 | N/A | 25 | N/A |
| JPN-47310658B9011809709100 | N/A | 29 | N/A |
| JPN-47310658B40291932252870 | N/A | 46 | N/A |
| JPN-47310658B82893106270036 | N/A | 10 | N/A |
| JPN-47310658B6129583352403 | N/A | 15 | N/A |
| JPN-47310658B84734951454670 | N/A | 42 | N/A |
| JPN-47310658B53666900505284 | N/A | 23 | N/A |
| JPN-47310658B14484689696833 | N/A | 23 | N/A |
| JPN-47310658B31569081891025 | N/A | 4 | N/A |
| JPN-47310658B55038426470858 | N/A | 6 | N/A |
| JPN-47310658B53717877461658 | N/A | 9 | N/A |
| JPN-47310658B92659408322453 | N/A | 12 | N/A |
| JPN-47310658B66619598690773 | N/A | 13 | N/A |
| JPN-47310658B41093195623763 | N/A | 23 | N/A |
| JPN-47310658B25198997079345 | N/A | 29 | N/A |
| JPN-47310658B20461581662238 | N/A | 21 | N/A |
| JPN-47310658B83740553463450 | N/A | 15 | N/A |
| JPN-47310658B199342310790 | N/A | 6 | N/A |
| JPN-47310658B78383189487115 | N/A | 11 | N/A |
| JPN-47310658B23327126724630 | N/A | 14 | N/A |
| JPN-47310658B18585040133157 | N/A | 15 | N/A |
| JPN-47310658B1770087263252 | N/A | 33 | N/A |
| JPN-47310658B89542195514726 | N/A | 19 | N/A |
| JPN-47310658B89229150671737 | N/A | 15 | N/A |
| MNG-14279143B49702315868913 | N/A | 194 | N/A |
| MNG-14279143B7284431230829 | N/A | 168 | N/A |
| MNG-14279143B7576416025221 | N/A | 405 | N/A |
| MNG-14279143B49613281560709 | N/A | 169 | N/A |
| MNG-14279143B32551742065768 | N/A | 13 | N/A |
| MNG-14279143B35762276870520 | N/A | 444 | N/A |
| MNG-14279143B47638406449643 | N/A | 385 | N/A |
| MNG-14279143B59026071325992 | N/A | 257 | N/A |
| MNG-14279143B39885639062119 | N/A | 488 | N/A |
| MNG-14279143B31648094269757 | N/A | 18 | N/A |
| MNG-14279143B20985490361275 | N/A | 351 | N/A |
| MNG-14279143B70362797710090 | N/A | 285 | N/A |
| MNG-14279143B22317554045022 | N/A | 264 | N/A |
| MNG-14279143B15424694570155 | N/A | 1 | N/A |
| MNG-14279143B84215380438566 | N/A | 144 | N/A |
| MNG-14279143B54746499726346 | N/A | 286 | N/A |
| MNG-14279143B76228648820573 | N/A | 254 | N/A |
| MNG-14279143B69842940795179 | N/A | 17 | N/A |
| MNG-14279143B81467460095364 | N/A | 243 | N/A |
| MNG-14279143B63368554420497 | N/A | 287 | N/A |
| MNG-14279143B52126529381065 | N/A | 570 | N/A |
| MNG-14279143B32793669032275 | N/A | 218 | N/A |
| TWN-90331920B54932243986706 | N/A | 5 | N/A |
| TWN-90331920B90000183725132 | N/A | 1 | N/A |
| TWN-90331920B44631347362338 | N/A | 7 | N/A |
| TWN-90331920B8990770803141 | N/A | 1 | N/A |
| TWN-90331920B98084155135420 | N/A | 4 | N/A |
| TWN-90331920B93110903621752 | N/A | 17 | N/A |
| TWN-90331920B66653841730450 | N/A | 11 | N/A |
| TWN-90331920B81487360502151 | N/A | 1 | N/A |
| TWN-90331920B60519442170303 | N/A | 0 | N/A |
| TWN-90331920B68512430020187 | N/A | 0 | N/A |
| TWN-90331920B28258400455048 | N/A | 7 | N/A |
| TWN-90331920B80042697765976 | N/A | 14 | N/A |
| TWN-90331920B89258408533695 | N/A | 5 | N/A |
| TWN-90331920B34778475945127 | N/A | 0 | N/A |
| TWN-90331920B3426825384645 | N/A | 8 | N/A |
| TWN-90331920B7705287137405 | N/A | 7 | N/A |
| TWN-90331920B35610459745524 | N/A | 7 | N/A |
| TWN-90331920B22703176907123 | N/A | 1 | N/A |
| TWN-90331920B88579316672132 | N/A | 13 | N/A |
| TWN-90331920B61423557936862 | N/A | 5 | N/A |
| TWN-90331920B45331697504939 | N/A | 7 | N/A |
| TWN-90331920B28650079022847 | N/A | 3 | N/A |
