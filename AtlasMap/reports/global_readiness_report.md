# Atlas global readiness report

Generated: 2026-07-16T02:39:18.115813+00:00

Overall result: **FAIL**

- Blocking failures: 4
- Warnings: 1
- Configured prototype countries: 2

| Check | Result | Detail |
| --- | --- | --- |
| Authoritative global rules document | PASS | GLOBAL_MAP_RULES.md |
| Global boundary candidate evaluation is recorded | PASS | provider=geoBoundaries CGAZ; status=accepted; report=reports/global_boundary_candidate_report.md |
| One frozen global ADM0/ADM1/ADM2 snapshot | PASS | missing=[]; candidate=geoBoundaries CGAZ; candidate_status=accepted |
| Canonical snapshot requires all hierarchy levels | PASS | levels=['ADM0', 'ADM1', 'ADM2'] |
| Configured canonical boundary files exist | PASS | paths=['data/source/geoboundaries_cgaz_6_0_0/geoBoundariesCGAZ_ADM0.zip', 'data/source/geoboundaries_cgaz_6_0_0/geoBoundariesCGAZ_ADM1.zip', 'data/source/geoboundaries_cgaz_6_0_0/geoBoundariesCGAZ_ADM2.zip']; missing=[] |
| Configured countries do not mix boundary snapshots | PASS | ADM1=[('data/source/geoboundaries_cgaz_6_0_0/geoBoundariesCGAZ_ADM1.zip', 'geoBoundariesCGAZ_ADM1.shp', 'CGAZ-6.0.0')]; ADM2=[('data/source/geoboundaries_cgaz_6_0_0/geoBoundariesCGAZ_ADM2.zip', 'geoBoundariesCGAZ_ADM2.shp', 'CGAZ-6.0.0')] |
| Global grid, world-wrap and polar policies are frozen | FAIL | missing=['crs_or_dggs', 'world_wrap_policy', 'polar_policy']; prototype_crs=EPSG:5179 |
| Tile IDs are independent of ownership | PASS | grid-coordinate scheme configured; ownership-derived prefix absent |
| Country and admin registry is data-driven | FAIL | registry=unset; configured_countries=2 |
| Spatial indexes are used for global boundary lookup | FAIL | QgsSpatialIndex not found in the current builder |
| ADM1/ADM2 hierarchy coherence is audited without country patches | FAIL | policy=country_neutral_report_only_no_automatic_repair; prototype_report=reports/korea_cgaz_hierarchy_consistency_audit.md; automated_global_audit=False |
| Neighbor lookup is coordinate based rather than pairwise | PASS | normalized edge-key topology lookup |
| Global gate has no country-specific tile-count quotas | PASS | frozen counts are regression observations; the universal one-tile official-area floor is not a country target quota |
| Output contract is world-build capable | WARN | prototype_outputs=['data/processed/Atlas_Korea.gpkg', 'Atlas_Korea.qgz', 'previews/Atlas_Korea_Overview.png', 'exports/Atlas_Korea_Tiles.geojson', 'exports/Atlas_Korea_Tiles.csv'] |
| Prototype country coverage | INFO | configured=['KOR', 'PRK'] |

## Interpretation

This audit is separate from the Korean Peninsula release gate. A FAIL here
does not invalidate a geometrically correct Korea build; it means the current
pipeline must not yet be treated as the canonical world-map pipeline.

The authoritative design contract is `GLOBAL_MAP_RULES.md`.
