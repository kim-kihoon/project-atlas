# Atlas global readiness report

Generated: 2026-07-15T22:46:57.753725+00:00

Overall result: **FAIL**

- Blocking failures: 9
- Warnings: 1
- Configured prototype countries: 2

| Check | Result | Detail |
| --- | --- | --- |
| Authoritative global rules document | PASS | GLOBAL_MAP_RULES.md |
| Global boundary candidate evaluation is recorded | PASS | provider=World Bank Official Boundaries; status=rejected; report=reports/global_boundary_candidate_report.md |
| One frozen global ADM0/ADM1/ADM2 snapshot | FAIL | missing=['provider', 'version', 'reference_year', 'license', 'sha256', 'adm0_path', 'adm1_path', 'adm2_path']; candidate=World Bank Official Boundaries; candidate_status=rejected |
| Canonical snapshot requires all hierarchy levels | PASS | levels=['ADM0', 'ADM1', 'ADM2'] |
| Configured canonical boundary files exist | FAIL | paths=[None, None, None]; missing=[] |
| Configured countries do not mix boundary snapshots | FAIL | ADM1=[('data/source/natural_earth_admin1/ne_10m_admin_1_states_provinces.shp', 2022), ('data/source/sgis_2025/admin1/bnd_sido_00_2025_2Q.shp', 2025)]; ADM2=[('data/source/geoBoundaries-KOR-ADM2.geojson', 2020), ('data/source/geoBoundaries-PRK-ADM2.geojson', 2019)] |
| Global grid, world-wrap and polar policies are frozen | FAIL | missing=['crs_or_dggs', 'tile_id_scheme', 'world_wrap_policy', 'polar_policy']; prototype_crs=EPSG:5179 |
| Tile IDs are independent of ownership | FAIL | current builder prefixes tile_id with the dominant territory |
| Country and admin registry is data-driven | FAIL | registry=unset; configured_countries=2 |
| Spatial indexes are used for global boundary lookup | FAIL | QgsSpatialIndex not found in the current builder |
| Neighbor lookup is coordinate based rather than pairwise | FAIL | current builder performs an O(n^2) selected-tile neighbor scan |
| Global gate has no country-specific tile-count quotas | FAIL | prototype_regressions={'expected_country_tile_counts': ['KOR'], 'expected_admin_tile_counts': ['KR-11', 'KR-26', 'KR-27', 'KR-28', 'KR-29', 'KR-30', 'KR-31', 'KR-41', 'KR-42', 'KR-43', 'KR-44', 'KR-45', 'KR-46', 'KR-47', 'KR-48', 'KR-49', 'KR-50']} |
| Output contract is world-build capable | WARN | prototype_outputs=['data/processed/Atlas_Korea.gpkg', 'Atlas_Korea.qgz', 'previews/Atlas_Korea_Overview.png', 'exports/Atlas_Korea_Tiles.geojson', 'exports/Atlas_Korea_Tiles.csv'] |
| Prototype country coverage | INFO | configured=['KOR', 'PRK'] |

## Interpretation

This audit is separate from the Korean Peninsula release gate. A FAIL here
does not invalidate a geometrically correct Korea build; it means the current
pipeline must not yet be treated as the canonical world-map pipeline.

The authoritative design contract is `GLOBAL_MAP_RULES.md`.
